"""Restricted commands and locked trial state, following Affinity Arena's runtime."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .engine import VERSION, Language, ProgramError, compile_source, execute, validate_inputs
from .generation import LOCAL_CALLS, SUBMISSIONS
from .view import render


@dataclass(frozen=True)
class Paths:
    private: Path
    public: Path
    verifier: Path


SANDBOX = Paths(Path("/opt/programming-language"), Path("/app"), Path("/logs/verifier"))


def atomic_write(path: Path, text: str, mode: int = 0o600) -> None:
    """Parents must be trusted and not replaceable by the agent."""
    fd, name = tempfile.mkstemp(prefix=".language-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Runtime:
    def __init__(self, paths: Paths = SANDBOX):
        self.paths = paths
        self.trial = json.loads((paths.private / "trial.json").read_text())
        if self.trial["version"] != VERSION:
            raise ValueError("unsupported trial version")
        self.language = Language(**self.trial["language"])

    @contextmanager
    def locked(self):
        with (self.paths.private / "lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def load(self) -> dict:
        try:
            return json.loads((self.paths.private / "state.json").read_text())
        except FileNotFoundError:
            return {"current": None, "completed": []}

    def save(self, data: dict) -> None:
        atomic_write(self.paths.private / "state.json", json.dumps(data) + "\n")

    def publish(self, data: dict) -> str:
        current = data["current"]
        text = render(self.trial, current)
        atomic_write(self.paths.public / "view.txt", text, 0o644)
        # Events contain only source/inputs supplied by the agent and public responses.
        atomic_write(
            self.paths.public / "problems" / f"problem-{current['index']:02d}.jsonl",
            "".join(json.dumps(e) + "\n" for e in current["events"]),
            0o644,
        )
        return text

    def start(self, index: int) -> str:
        with self.locked():
            data = self.load()
            current = data["current"]
            if current and current["index"] == index:
                return self.publish(data)  # Repeated setup never restores a budget.
            if index != len(data["completed"]) + 1 or not 1 <= index <= len(self.trial["problems"]):
                raise ValueError("problems must start in order after settlement")
            if current and not current["settled"]:
                raise ValueError("previous problem is not settled")
            data["current"] = {
                "index": index,
                "local_calls": 0,
                "compiler_calls": 0,
                "compiler_errors": 0,
                "runtime_calls": 0,
                "runtime_errors": 0,
                "env_actions": 0,
                "tool_calls": 0,
                "submissions": [],
                "events": [],
                "closed": False,
                "settled": False,
                "metrics": {},
            }
            self.save(data)
            return self.publish(data)

    def command(self, argv: list[str], source: str = "") -> str:
        """No file-path arguments: the unprivileged shell opens source via stdin."""
        with self.locked():
            data = self.load()
            current = data["current"]
            if current is None:
                raise ValueError("problem has not been started by the harness")
            if argv == ["status"]:
                current["tool_calls"] += 1
                self.save(data)
                return render(self.trial, current)
            if (
                len(argv) not in (2, 3)
                or argv[0] not in ("compile", "run", "submit")
                or len(argv) != (3 if argv[0] == "run" else 2)
            ):
                raise ValueError(
                    "use status | compile <problem> | run <problem> '<inputs>' | submit <problem>"
                )
            if argv[1] != f"problem-{current['index']:02d}":
                raise ValueError("command does not address the current problem")
            if current["settled"] or current["closed"]:
                raise ValueError("problem is closed")
            kind = argv[0]
            if kind != "submit" and current["local_calls"] >= LOCAL_CALLS:
                raise ValueError("local call budget exhausted; submission is still available")
            current["tool_calls"] += 1
            current["env_actions"] += 1
            if kind == "submit":
                response = self.submit(current, source)
            else:
                current["local_calls"] += 1
                response = self.local(current, kind, source, argv[2] if kind == "run" else None)
            current["events"].append(
                {"command": argv, "source": source[:8193], "response": response}
            )
            self.save(data)  # Commit before returning feedback; settlement freezes this snapshot.
            self.publish(data)
            return json.dumps(response) + "\n"

    def compile(self, current: dict, source: str):
        current["compiler_calls"] += 1
        try:
            return compile_source(self.language, source)
        except ProgramError:
            current["compiler_errors"] += 1
            raise

    def local(self, current: dict, kind: str, source: str, raw_inputs: str | None) -> dict:
        try:
            inputs = []
            if kind == "run":
                try:
                    inputs = validate_inputs(json.loads(raw_inputs))
                except (ValueError, RecursionError) as exc:
                    raise ProgramError(
                        "INPUT_ERROR", "expected an integer list in 0..65535"
                    ) from exc
            program = self.compile(current, source)
            if kind == "compile":
                return {"compiled": True}
            current["runtime_calls"] += 1
            result = execute(self.language, program, inputs)
            current["runtime_errors"] += int(result.error is not None)
            return {"output": list(result.output), "steps": result.steps, "error": result.error}
        except ProgramError as exc:
            return {"error": str(exc)}

    def submit(self, current: dict, source: str) -> dict:
        tests = self.trial["problems"][current["index"] - 1]["hidden_tests"]
        passed = 0
        runtime_error = False
        try:
            program = self.compile(current, source)
            for test in tests:
                result = execute(self.language, program, test["input"])
                passed += result.error is None and list(result.output) == test["output"]
                runtime_error |= result.error is not None
        except ProgramError:
            pass  # Submission feedback is aggregate only, including for invalid source.
        current["runtime_errors"] += int(runtime_error)
        feedback = {
            "submission": len(current["submissions"]) + 1,
            "passed": passed,
            "total": len(tests),
            "score": passed / len(tests),
        }
        current["submissions"].append({"source": source, "feedback": feedback})
        current["closed"] = passed == len(tests) or len(current["submissions"]) == SUBMISSIONS
        return feedback

    def settle(self, index: int) -> dict:
        with self.locked():
            data = self.load()
            current = data["current"]
            if current is None:
                raise ValueError("no problem to settle")
            if index in data["completed"]:
                record = json.loads((self.paths.private / f"problem-{index:02d}.json").read_text())
                self.export_verifier(record)
                return record["metrics"]
            if index != current["index"]:
                raise ValueError("verifier requested the wrong problem")
            scores = [s["feedback"]["score"] for s in current["submissions"]]
            first_success = next((i for i, score in enumerate(scores, 1) if score == 1), 0)
            current["metrics"] = {
                "reward": scores[0] if scores else 0.0,
                "first_correctness": scores[0] if scores else 0.0,
                "best_correctness": max(scores, default=0.0),
                "last_correctness": scores[-1] if scores else 0.0,
                "solved": int(bool(first_success)),
                "first_solved": int(bool(scores) and scores[0] == 1),
                "submissions": len(scores),
                "attempts_to_solve": first_success,
                "submitted": int(bool(scores)),
                "completed": 1,
                "turn": index,
                "holdout": int(self.trial["problems"][index - 1]["phase"] == "holdout"),
                **{
                    key: current[key]
                    for key in (
                        "local_calls",
                        "compiler_calls",
                        "compiler_errors",
                        "runtime_calls",
                        "runtime_errors",
                        "env_actions",
                        "tool_calls",
                    )
                },
            }
            current["settled"] = True
            data["completed"].append(index)
            atomic_write(
                self.paths.private / f"problem-{index:02d}.json", json.dumps(current) + "\n"
            )
            self.save(data)
            self.export_verifier(current)
            self.publish(data)
            return current["metrics"]

    def export_verifier(self, record: dict) -> None:
        self.paths.verifier.mkdir(parents=True, exist_ok=True)
        self.paths.verifier.chmod(0o700)
        atomic_write(
            self.paths.verifier / "reward.json", json.dumps(record["metrics"]) + "\n", 0o644
        )
        problem = self.trial["problems"][record["index"] - 1]
        atomic_write(
            self.paths.verifier / "problem.json",
            json.dumps(
                {
                    "index": record["index"],
                    "seed": self.trial["seed"],
                    "version": VERSION,
                    "visibility": self.trial["visibility"],
                    "phase": problem["phase"],
                    "family": problem["family"],
                    "submissions": record["submissions"],
                }
            )
            + "\n",
            0o644,
        )

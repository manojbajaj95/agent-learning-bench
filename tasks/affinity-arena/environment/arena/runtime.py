"""Locked, atomic persistence. Paths are injected locally, fixed in the sandbox."""

from __future__ import annotations

import fcntl
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

from .engine import Combat, State, draft, matchup_from_dict, outcome, parse_action, state_from_dict
from .metrics import grade
from .view import render


@dataclass(frozen=True)
class Paths:
    private: Path
    public: Path
    verifier: Path


SANDBOX = Paths(Path("/opt/affinity-arena"), Path("/app"), Path("/logs/verifier"))


def atomic_write(path: Path, text: str, mode: int = 0o600) -> None:
    """Only call in trusted, non-agent-writable parent directories."""
    fd, name = tempfile.mkstemp(prefix=".arena-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_beliefs(path: Path) -> object:
    # A malformed note is not a verifier failure. Never block on FIFOs or follow
    # links supplied by the agent into private state, devices, or arbitrary files.
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd) as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
                return {}
            text = stream.read(65537)
            return json.loads(text) if len(text) <= 65536 else {}
    except (OSError, ValueError, RecursionError):
        return {}


class Runtime:
    def __init__(self, paths: Paths = SANDBOX):
        self.paths = paths
        self.trial = json.loads((paths.private / "trial.json").read_text())
        self.chart = tuple(tuple(row) for row in self.trial["chart"])

    @contextmanager
    def locked(self):
        with (self.paths.private / "lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def load(self) -> dict:
        try:
            return json.loads((self.paths.private / "state.json").read_text())
        except FileNotFoundError:
            return {"current": None, "cells": [], "completed": []}

    def save(self, data: dict) -> None:
        atomic_write(self.paths.private / "state.json", json.dumps(data) + "\n")

    def view(self, data: dict) -> str:
        current = data["current"]
        if current is None:
            raise ValueError("battle has not been started by the harness")
        battle = self.trial["battles"][current["index"] - 1]
        matchup = matchup_from_dict(battle)
        team = draft(matchup, current["team"]) if current["team"] else ()
        return render(
            current["index"],
            matchup,
            team,
            state_from_dict(current["state"]),
            current["events"],
            "incomplete" if current["settled"] and not current["metrics"]["completed"] else None,
        )

    def publish(self, data: dict) -> str:
        view = self.view(data)
        atomic_write(self.paths.public / "view.txt", view, 0o644)
        record = data["current"]
        battle = self.trial["battles"][record["index"] - 1]
        public_events = [
            {"kind": "start", "battle": record["index"], **asdict(matchup_from_dict(battle))}
        ]
        public_events.extend(
            {k: v for k, v in event.items() if k != "action"} for event in record["events"]
        )
        atomic_write(
            self.paths.public / "battles" / f"battle-{record['index']:02d}.jsonl",
            "".join(json.dumps(event) + "\n" for event in public_events),
            0o644,
        )
        return view

    def start(self, index: int) -> str:
        with self.locked():
            data = self.load()
            isolated = self.trial.get("isolated_battle")
            if isolated is not None and index != isolated:
                raise ValueError("this sandbox contains only one playable battle")
            if data["current"] and data["current"]["index"] == index:
                return self.publish(data)  # Retries never reset an attempt.
            expected = isolated if isolated is not None else len(data["completed"]) + 1
            if index != expected or not 1 <= index <= len(self.trial["battles"]):
                raise ValueError("battles must start in order, after previous settlement")
            data["current"] = {
                "index": index,
                "team": [],
                "state": State()._asdict(),
                "events": [],
                "settled": False,
                "metrics": {},
            }
            self.save(data)
            return self.publish(data)

    def command(self, command: list[str]) -> str:
        with self.locked():
            data = self.load()
            if command == ["status"]:
                return self.view(data)
            current = data["current"]
            if current is None:
                raise ValueError("battle has not been started by the harness")
            state = state_from_dict(current["state"])
            if current["settled"] or outcome(state):
                raise ValueError("battle is over; actions are no longer accepted")
            matchup = matchup_from_dict(self.trial["battles"][current["index"] - 1])
            if command and command[0] == "draft":
                if current["team"]:
                    raise ValueError("a team has already been drafted")
                team = draft(matchup, command[1:])
                current["team"] = [c.name for c in team]
                event = {"kind": "draft", "command": " ".join(command), "team": current["team"]}
            else:
                if not current["team"]:
                    raise ValueError("draft a team before attacking or switching")
                team = draft(matchup, current["team"])
                action = parse_action(team, state, command)
                after, hits = Combat(team, matchup.opponent, self.chart).step(state, action)
                current["state"] = after._asdict()
                event = {
                    "kind": "tick",
                    "command": " ".join(command),
                    "action": list(action),
                    "before": state._asdict(),
                    "after": after._asdict(),
                    "hits": [hit._asdict() for hit in hits],
                    "outcome": outcome(after),
                }
                cells = {tuple(cell) for cell in data["cells"]}
                cells.update((hit.attack_affinity, hit.defender_affinity) for hit in hits)
                data["cells"] = sorted(cells)
            event["battle"] = current["index"]
            current["events"].append(event)
            self.save(
                data
            )  # One authoritative transaction; public files are recoverable projections.
            return self.publish(data)

    def settle(self, expected_index: int | None = None) -> dict:
        with self.locked():
            data = self.load()
            current = data["current"]
            if current is None:
                raise ValueError("no battle to settle")
            if expected_index is not None and expected_index != current["index"]:
                if expected_index not in data["completed"]:
                    raise ValueError("verifier requested a battle that has not completed")
                previous = json.loads(
                    (self.paths.private / f"battle-{expected_index:02d}.json").read_text()
                )
                self.export_verifier(previous)
                return previous["metrics"]
            if not current["settled"]:
                battle = self.trial["battles"][current["index"] - 1]
                current["metrics"] = grade(
                    battle,
                    self.chart,
                    matchup_from_dict(battle),
                    current,
                    data["cells"],
                    read_beliefs(self.paths.public / "affinity-chart.json"),
                )
                current["settled"] = True
                data["completed"].append(current["index"])
                atomic_write(
                    self.paths.private / f"battle-{current['index']:02d}.json",
                    json.dumps(current) + "\n",
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
        atomic_write(
            self.paths.verifier / "battle.json",
            json.dumps(
                {
                    "index": record["index"],
                    "seed": self.trial["seed"],
                    "version": self.trial["version"],
                    "team": record["team"],
                    "state": record["state"],
                    "events": record["events"],
                }
            )
            + "\n",
            0o644,
        )

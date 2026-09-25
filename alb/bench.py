"""Prepare Harbor tasks, build system run commands, and slice smoke steps."""

from __future__ import annotations

import functools
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

SMOKE_N = 10


def find_root() -> Path:
    start = Path(__file__).resolve().parent
    for path in [start, *start.parents]:
        if (path / "systems.toml").is_file() and (path / "tasks").is_dir():
            return path
    raise SystemExit("cannot find repo root (need systems.toml and tasks/)")


ROOT = find_root()
SYSTEMS_TOML = ROOT / "systems.toml"


@functools.cache
def load_config() -> dict[str, Any]:
    if not SYSTEMS_TOML.is_file():
        raise SystemExit(f"missing {SYSTEMS_TOML}")
    with SYSTEMS_TOML.open("rb") as fh:
        return tomllib.load(fh)


def system_names() -> list[str]:
    return list(load_config()["systems"])


def system_spec(system: str) -> dict[str, Any]:
    systems = load_config()["systems"]
    if system not in systems:
        raise SystemExit(f"unknown system: {system}. See {SYSTEMS_TOML}")
    spec = dict(systems[system])
    spec.setdefault("flags", [])
    spec.setdefault("needs_model", True)
    spec.setdefault("summary", "")
    pythonpath = spec.get("pythonpath")
    if pythonpath == ".":
        spec["pythonpath"] = str(ROOT)
    elif pythonpath:
        spec["pythonpath"] = str((ROOT / pythonpath).resolve())
    return spec


def harbor_example(system: str, task: str = "tally") -> str:
    spec = system_spec(system)
    cfg = load_config()
    parts = ["harbor", "run", "-p", f"tasks/{task}", "-a", spec["agent"]]
    pythonpath = spec.get("pythonpath")
    if pythonpath:
        shown = "." if pythonpath == str(ROOT) else pythonpath
        parts = [f"PYTHONPATH={shown}"] + parts
    if spec["needs_model"]:
        parts += ["-m", str(cfg["model"])]
    parts += list(spec["flags"])
    parts += ["--agent-timeout-multiplier", str(cfg["agent_timeout_multiplier"])]
    return " ".join(str(p) for p in parts)


def task_dir(name: str) -> Path:
    path = ROOT / "tasks" / name
    if not path.is_dir():
        raise SystemExit(f"unknown task: {name}")
    if not (path / "task.toml").exists() and not (path / "generate_steps.py").exists():
        raise SystemExit(f"{name} is not a runnable Harbor task")
    return path


def task_names() -> list[str]:
    names: list[str] = []
    for path in sorted((ROOT / "tasks").iterdir()):
        if not path.is_dir():
            continue
        if (path / "task.toml").exists() or (path / "generate_steps.py").exists():
            names.append(path.name)
    return names


def script_has_flag(script: Path, flag: str) -> bool:
    text = script.read_text()
    return f'"{flag}"' in text or f"'{flag}'" in text


def run(argv: list[str], *, env: dict[str, str] | None = None, dry_run: bool = False) -> None:
    print("+", " ".join(argv), flush=True)
    if dry_run:
        return
    subprocess.run(argv, check=True, env=env, cwd=ROOT)


def maybe_download(path: Path, *, force: bool = False, dry_run: bool = False) -> None:
    script = path / "download.sh"
    if not script.exists():
        return
    data = path / "data"
    if not force and data.exists() and any(data.iterdir()):
        print(f"skip download; {data} already has files")
        return
    run(["bash", str(script)], dry_run=dry_run)


def generate_steps(path: Path, n: int | None, *, dry_run: bool = False) -> None:
    script = path / "generate_steps.py"
    if not script.exists():
        return
    cmd = [sys.executable, str(script)]
    if n is not None:
        if not script_has_flag(script, "--n"):
            return
        cmd += ["--n", str(n)]
    elif script_has_flag(script, "--all"):
        cmd.append("--all")
    run(cmd, dry_run=dry_run)


def _step_blocks(task_toml: str) -> tuple[str, list[str]]:
    parts = re.split(r"(?=^\[\[steps\]\])", task_toml, flags=re.M)
    return parts[0], parts[1:]


def step_names(block: str) -> str | None:
    match = re.search(r'^name\s*=\s*"([^"]+)"', block, re.M)
    return match.group(1) if match else None


def slice_task(src: Path, dest: Path, n: int) -> Path:
    """Copy a committed-step task and keep the first n Harbor steps."""
    toml_src = src / "task.toml"
    if not toml_src.exists():
        raise SystemExit(f"{src.name} has no task.toml; run prepare first")
    head, blocks = _step_blocks(toml_src.read_text())
    if not blocks:
        raise SystemExit(f"{src.name} has no [[steps]] in task.toml")
    keep = blocks[:n]
    names = [name for name in (step_names(b) for b in keep) if name]
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns("__pycache__", ".venv", "*.pyc", ".alb"),
    )
    (dest / "task.toml").write_text(head + "".join(keep))
    steps_dir = dest / "steps"
    if steps_dir.is_dir():
        for child in steps_dir.iterdir():
            if child.name not in names:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
    print(f"smoke slice: {len(keep)} steps -> {dest}")
    return dest


def task_is_ready(path: Path) -> bool:
    steps = path / "steps"
    return (path / "task.toml").is_file() and steps.is_dir() and any(steps.iterdir())


def needs_slice(path: Path, n: int | None) -> bool:
    del path
    return n is not None


def resolve_task_path(path: Path, n: int | None, *, dry_run: bool = False) -> Path:
    if not needs_slice(path, n):
        return path
    assert n is not None
    dest = ROOT / ".alb" / "smoke" / path.name
    if dry_run:
        print(f"smoke slice: {n} steps -> {dest}")
        return dest
    return slice_task(path, dest, n)


def harbor_run_cmd(
    path: Path,
    system: str,
    *,
    model: str,
    job_name: str,
    jobs_dir: Path,
    timeout: float,
    n_concurrent: int,
    upload: bool,
    public: bool,
    extra: list[str],
) -> tuple[list[str], dict[str, str]]:
    spec = system_spec(system)
    cmd = [
        "harbor",
        "run",
        "-p",
        str(path),
        "-a",
        str(spec["agent"]),
        "--jobs-dir",
        str(jobs_dir),
        "--job-name",
        job_name,
        "--agent-timeout-multiplier",
        str(timeout),
        "--n-concurrent",
        str(n_concurrent),
    ]
    if spec["needs_model"]:
        cmd += ["-m", model]
    cmd.extend(spec["flags"])
    if upload:
        cmd.append("--upload")
        if public:
            cmd.append("--public")
    cmd.extend(extra)
    env = os.environ.copy()
    pythonpath = spec.get("pythonpath")
    if pythonpath:
        old = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(pythonpath) if not old else f"{pythonpath}{os.pathsep}{old}"
    return cmd, env


def default_job_name(task: str, system: str, n: int | None) -> str:
    name = f"{task}-{system}"
    if n is not None:
        name += f"-n{n}"
    return name


def extra_args(raw: list[str] | None) -> list[str]:
    args = list(raw or [])
    if args[:1] == ["--"]:
        return args[1:]
    return args


def resolve_job_dir(jobs_dir: Path, name: str | None) -> Path:
    if name:
        given = Path(name)
        if given.is_dir():
            return given
        path = jobs_dir / name
        if not path.is_dir():
            raise SystemExit(f"no job directory {path}")
        return path
    if not jobs_dir.is_dir():
        raise SystemExit(f"no jobs directory {jobs_dir}")
    dirs = [p for p in jobs_dir.iterdir() if p.is_dir()]
    if not dirs:
        raise SystemExit(f"no jobs in {jobs_dir}")
    return max(dirs, key=lambda p: p.stat().st_mtime)


def prepare_task(task: str, n: int | None = None, *, force: bool = False, dry_run: bool = False) -> None:
    path = task_dir(task)
    maybe_download(path, force=force, dry_run=dry_run)
    if force or not task_is_ready(path):
        generate_steps(path, None, dry_run=dry_run)
    else:
        print(f"skip generate; {path.name} already has steps")
    if needs_slice(path, n):
        resolve_task_path(path, n, dry_run=dry_run)


def run_task(
    task: str,
    system: str,
    *,
    model: str | None = None,
    job_name: str | None = None,
    jobs_dir: Path | None = None,
    n: int | None = None,
    timeout: float | None = None,
    n_concurrent: int | None = None,
    upload: bool = False,
    public: bool = False,
    dry_run: bool = False,
    extra: list[str] | None = None,
    smoke: bool = False,
) -> None:
    cfg = load_config()
    path = task_dir(task)
    if smoke and n is None:
        n = SMOKE_N
    if not task_is_ready(path):
        generate_steps(path, None, dry_run=dry_run)
    run_path = resolve_task_path(path, n, dry_run=dry_run)
    if not dry_run and not (run_path / "task.toml").exists():
        raise SystemExit(f"no task.toml at {run_path}; run prepare first")
    jobs = jobs_dir or (ROOT / "jobs")
    name = job_name or default_job_name(task, system, n)
    cmd, env = harbor_run_cmd(
        run_path,
        system,
        model=model or str(cfg["model"]),
        job_name=name,
        jobs_dir=jobs,
        timeout=float(cfg["agent_timeout_multiplier"] if timeout is None else timeout),
        n_concurrent=int(cfg["n_concurrent"] if n_concurrent is None else n_concurrent),
        upload=upload,
        public=public,
        extra=extra_args(extra),
    )
    if not dry_run and shutil.which("harbor") is None:
        raise SystemExit("harbor is not on PATH")
    run(cmd, env=env, dry_run=dry_run)
    print(f"job: {jobs / name}")


def upload_job(
    run: str,
    *,
    jobs_dir: Path | None = None,
    public: bool = False,
    dry_run: bool = False,
) -> None:
    """Upload one task run. `run` is a job name or a job directory."""
    jobs = jobs_dir or (ROOT / "jobs")
    given = Path(run)
    if given.is_dir():
        job_dir = given
    elif dry_run:
        job_dir = jobs / run
    else:
        job_dir = resolve_job_dir(jobs, run)
    cmd = ["harbor", "upload", str(job_dir)]
    if public:
        cmd.append("--public")
    if not dry_run and shutil.which("harbor") is None:
        raise SystemExit("harbor is not on PATH")
    run(cmd, dry_run=dry_run)


def print_systems() -> None:
    print(f"# {SYSTEMS_TOML.relative_to(ROOT)}")
    print()
    for name in system_names():
        spec = system_spec(name)
        print(name)
        if spec["summary"]:
            print(f"  {spec['summary']}")
        print(f"  {harbor_example(name)}")
        print(f"  alb run tally --system {name}")
        print()

#!/usr/bin/env python3
"""Reset Shopping and manage the per-step agent-browser session."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

SHOPPING_URL = os.environ.get(
    "WEBARENA_SHOPPING_URL", "http://host.docker.internal:7770"
).rstrip("/")
CONTROL_URL = os.environ.get(
    "WEBARENA_CONTROL_URL", "http://host.docker.internal:7771"
).rstrip("/")
AUTH_STATE = os.environ.get("WEBARENA_AUTH_STATE", "/opt/webarena/auth.json")
SESSION = os.environ.get("AGENT_BROWSER_SESSION", "webarena-shopping")
RESET_TIMEOUT_SEC = 60

APP = Path("/app")
TASK_PATH = APP / "task.json"
RESPONSE_PATH = APP / "agent_response.json"
INPUT_PATH = Path("/opt/webarena/agent-input.json")
HAR_PATH = Path("/logs/agent/network.har")
TRAJECTORY_PATH = Path("/logs/agent/trajectory.json")
REWARD_PATH = Path("/logs/verifier/reward.json")


def require_http_ok(url: str, method: str = "GET", opener=urlopen) -> bytes:
    request = Request(url, method=method)
    try:
        with opener(request, timeout=RESET_TIMEOUT_SEC) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(
                    f"Shopping reset failed: {method} {url} returned {response.status}"
                )
            return response.read()
    except (OSError, HTTPError, URLError) as exc:
        raise RuntimeError(
            f"Shopping reset failed: {method} {url} failed: {exc}"
        ) from exc


def reset_site() -> None:
    require_http_ok(f"{CONTROL_URL}/reset", method="POST")
    deadline = time.monotonic() + RESET_TIMEOUT_SEC
    while time.monotonic() < deadline:
        try:
            require_http_ok(f"{CONTROL_URL}/status")
            require_http_ok(SHOPPING_URL)
            return
        except RuntimeError:
            time.sleep(2)
    raise RuntimeError("Shopping reset failed health check")


def browser(
    args: list[str], check: bool = True
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["agent-browser", "--session", SESSION, "--json", *args],
        check=check,
        text=True,
        capture_output=True,
    )


def load_task(task_id: int) -> dict:
    for task in json.loads(INPUT_PATH.read_text()):
        if int(task["task_id"]) == task_id:
            return task
    raise RuntimeError(f"task {task_id} is missing from {INPUT_PATH}")


def prepare(task_id: int, task: dict | None = None) -> None:
    task = task or load_task(task_id)
    reset_site()
    APP.mkdir(parents=True, exist_ok=True)
    TASK_PATH.write_text(json.dumps(task, indent=2) + "\n")
    for path in (RESPONSE_PATH, HAR_PATH):
        path.unlink(missing_ok=True)
    browser(["close"], check=False)
    browser(["open"])
    browser(["state", "load", AUTH_STATE])
    browser(["network", "har", "start", "--content", "text"])


def capture_stop() -> dict:
    HAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    HAR_PATH.unlink(missing_ok=True)
    browser(["network", "har", "stop", str(HAR_PATH)])
    if not HAR_PATH.is_file():
        raise RuntimeError("network.har is missing after capture-stop")
    try:
        return json.loads(HAR_PATH.read_text())
    except json.JSONDecodeError as exc:
        raise RuntimeError("network.har is invalid JSON") from exc


def har_metrics(har: dict, shopping_url: str) -> dict[str, float]:
    origin = urlsplit(shopping_url)
    urls = {
        (parts.scheme, parts.netloc, parts.path)
        for entry in har.get("log", {}).get("entries", [])
        if (parts := urlsplit(entry.get("request", {}).get("url", "")))
        and (parts.scheme, parts.netloc) == (origin.scheme, origin.netloc)
    }
    return {"unique_urls": float(len(urls))}


def trajectory_metrics(path: Path | None = None) -> dict[str, float]:
    path = path or TRAJECTORY_PATH
    if not path.is_file():
        return {"agent_browser_commands": 0.0}

    def count(value) -> int:
        if isinstance(value, dict):
            commands = sum(
                1
                for key, item in value.items()
                if key == "command"
                and isinstance(item, str)
                and "agent-browser" in shlex.split(item)
            )
            return commands + sum(count(item) for item in value.values())
        if isinstance(value, list):
            return sum(count(item) for item in value)
        return 0

    return {"agent_browser_commands": float(count(json.loads(path.read_text())))}


def collect_metrics() -> dict[str, float]:
    if not HAR_PATH.is_file():
        raise RuntimeError("network.har is missing")
    try:
        har = json.loads(HAR_PATH.read_text())
    except json.JSONDecodeError as exc:
        raise RuntimeError("network.har is invalid JSON") from exc
    return {**har_metrics(har, SHOPPING_URL), **trajectory_metrics()}


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit("usage: runtime.py prepare TASK_ID | capture-stop")
    if argv[0] == "prepare" and len(argv) == 2:
        prepare(int(argv[1]))
    elif argv == ["capture-stop"]:
        capture_stop()
    else:
        raise SystemExit("usage: runtime.py prepare TASK_ID | capture-stop")


if __name__ == "__main__":
    main(sys.argv[1:])

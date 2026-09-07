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
    "WEBARENA_CONTROL_URL", "http://host.docker.internal:7772"
).rstrip("/")
AUTH_STATE = os.environ.get("WEBARENA_AUTH_STATE", "/opt/webarena/auth.json")
SESSION = os.environ.get("AGENT_BROWSER_SESSION", "webarena-shopping")
REQUEST_TIMEOUT_SEC = int(os.environ.get("WEBARENA_REQUEST_TIMEOUT_SEC", "30"))
RESET_TIMEOUT_SEC = int(os.environ.get("WEBARENA_RESET_TIMEOUT_SEC", "600"))
HEALTH_PATH = "/customer/account/login"
ACCOUNT_PATH = "/customer/account"
DATASET_PATH = Path("/opt/webarena/dataset.json")

APP = Path("/app")
TASK_PATH = APP / "task.json"
RESPONSE_PATH = APP / "agent_response.json"
INPUT_PATH = Path("/opt/webarena/agent-input.json")
HAR_PATH = Path("/logs/agent/network.har")
TRAJECTORY_PATH = Path("/logs/agent/trajectory.json")
REWARD_PATH = Path("/logs/verifier/reward.json")


def require_http_ok(
    url: str,
    method: str = "GET",
    opener=urlopen,
    timeout: int | None = None,
) -> bytes:
    request = Request(url, method=method)
    try:
        with opener(
            request, timeout=REQUEST_TIMEOUT_SEC if timeout is None else timeout
        ) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(
                    f"Shopping reset failed: {method} {url} returned {response.status}"
                )
            return response.read()
    except (OSError, HTTPError, URLError) as exc:
        raise RuntimeError(
            f"Shopping reset failed: {method} {url} failed: {exc}"
        ) from exc


def require_healthy_status(url: str, opener=urlopen) -> dict:
    try:
        data = json.loads(require_http_ok(url, opener=opener))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Shopping reset failed: {url} is not healthy") from exc
    if not data.get("success"):
        raise RuntimeError(
            f"Shopping reset failed: {url} is not healthy: {data.get('message', data)}"
        )
    return data


def reset_site() -> None:
    require_http_ok(
        f"{CONTROL_URL}/reset", method="POST", timeout=RESET_TIMEOUT_SEC
    )
    deadline = time.monotonic() + RESET_TIMEOUT_SEC
    while time.monotonic() < deadline:
        try:
            require_healthy_status(f"{CONTROL_URL}/status")
            require_http_ok(f"{SHOPPING_URL}{HEALTH_PATH}")
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


def render_task(task: dict) -> dict:
    rendered = dict(task)
    rendered["start_urls"] = [
        url.replace("__SHOPPING__", SHOPPING_URL)
        for url in task.get("start_urls") or []
    ]
    return rendered


def parse_browser_url(stdout: str) -> str:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return stdout.strip()
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        value = data.get("data", data.get("url", data.get("result", "")))
        if isinstance(value, dict):
            value = value.get("url", "")
        return str(value)
    return stdout.strip()


def require_authenticated() -> None:
    browser(["open", f"{SHOPPING_URL}{ACCOUNT_PATH}"])
    url = parse_browser_url(browser(["get", "url"]).stdout)
    if "login" in urlsplit(url).path.lower():
        raise RuntimeError("authenticated state is not logged in")


def prepare(task_id: int, task: dict | None = None) -> None:
    if not Path(AUTH_STATE).is_file():
        raise RuntimeError(f"auth state is missing: {AUTH_STATE}")
    task = render_task(task or load_task(task_id))
    reset_site()
    APP.mkdir(parents=True, exist_ok=True)
    TASK_PATH.write_text(json.dumps(task, indent=2) + "\n")
    for path in (RESPONSE_PATH, HAR_PATH):
        path.unlink(missing_ok=True)
    browser(["close"], check=False)
    browser(["open"])
    browser(["state", "load", AUTH_STATE])
    require_authenticated()
    browser(["network", "har", "start", "--content", "text"])


def capture_stop() -> dict:
    HAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    HAR_PATH.unlink(missing_ok=True)
    result = browser(["network", "har", "stop", str(HAR_PATH)], check=False)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            "HAR capture failed; do not close the browser or stop HAR "
            f"during the task: {detail}"
        )
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


def command_tokens(item: str) -> list[str]:
    try:
        return shlex.split(item)
    except ValueError:
        return item.split()


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
                and "agent-browser" in command_tokens(item)
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


def evaluator_status_name(status) -> str:
    for attr in ("value", "name"):
        value = getattr(status, attr, None)
        if value:
            return str(value).rsplit(".", 1)[-1]
    return str(status).rsplit(".", 1)[-1]


def build_evaluator():
    from webarena_verified.api import WebArenaVerified
    from webarena_verified.types.config import WebArenaVerifiedConfig

    config = WebArenaVerifiedConfig(
        test_data_file=DATASET_PATH,
        environments={"__SHOPPING__": {"urls": [SHOPPING_URL]}},
    )
    return WebArenaVerified(config=config)


def evaluate(
    task_id: int,
    evaluator=None,
    metrics: dict[str, float] | None = None,
    response_path: Path | None = None,
) -> dict[str, float]:
    response_path = response_path or RESPONSE_PATH
    if not response_path.is_file():
        raise RuntimeError("agent_response.json is missing")
    if not HAR_PATH.is_file():
        raise RuntimeError("network.har is missing")
    result = (evaluator or build_evaluator()).evaluate_task(
        task_id=task_id,
        agent_response=response_path,
        network_trace=HAR_PATH,
    )
    if evaluator_status_name(getattr(result, "status", "")) == "ERROR":
        raise RuntimeError(getattr(result, "error_msg", None) or "evaluator error")
    reward = {"reward": float(result.score), **(metrics or collect_metrics())}
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REWARD_PATH.write_text(json.dumps(reward) + "\n")
    return reward


def main(argv: list[str]) -> None:
    if not argv:
        raise SystemExit(
            "usage: runtime.py prepare TASK_ID | capture-stop | evaluate TASK_ID"
        )
    if argv[0] == "prepare" and len(argv) == 2:
        prepare(int(argv[1]))
    elif argv == ["capture-stop"]:
        capture_stop()
    elif argv[0] == "evaluate" and len(argv) == 2:
        evaluate(int(argv[1]))
    else:
        raise SystemExit(
            "usage: runtime.py prepare TASK_ID | capture-stop | evaluate TASK_ID"
        )


if __name__ == "__main__":
    main(sys.argv[1:])

#!/usr/bin/env python3
"""Reset Shopping and manage the per-step webcmd session."""

from __future__ import annotations

import json
import os
import re
import shlex
import signal
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
PROFILE = os.environ.get("WEBCMD_PROFILE", "webarena")
SESSION_NAME = os.environ.get("WEBCMD_SESSION_NAME", "shopping")
REQUEST_TIMEOUT_SEC = int(os.environ.get("WEBARENA_REQUEST_TIMEOUT_SEC", "30"))
RESET_TIMEOUT_SEC = int(os.environ.get("WEBARENA_RESET_TIMEOUT_SEC", "600"))
LOGIN_WAIT_SEC = int(os.environ.get("WEBARENA_LOGIN_WAIT_SEC", "30"))
SHOPPING_EMAIL = os.environ.get(
    "WEBARENA_SHOPPING_EMAIL", "emma.lopez@gmail.com"
)
SHOPPING_PASSWORD = os.environ.get("WEBARENA_SHOPPING_PASSWORD", "Password.123")
HEALTH_PATH = "/customer/account/login"
ACCOUNT_PATH = "/customer/account"
DATASET_PATH = Path("/opt/webarena/dataset.json")
HAR_RECORDER = Path(
    os.environ.get("WEBARENA_HAR_RECORDER", "/opt/webarena/har_recorder.mjs")
)

APP = Path("/app")
TASK_PATH = APP / "task.json"
RESPONSE_PATH = APP / "agent_response.json"
SESSION_PATH = APP / "webcmd-session"
INPUT_PATH = Path("/opt/webarena/agent-input.json")
HAR_PATH = Path("/logs/agent/network.har")
JSONL_PATH = Path("/logs/agent/network.jsonl")
PID_PATH = Path("/logs/agent/har-recorder.pid")
TRAJECTORY_PATH = Path("/logs/agent/trajectory.json")
PI_LOG_PATH = Path("/logs/agent/pi.txt")
REWARD_PATH = Path("/logs/verifier/reward.json")
WEBCMD_HOME = Path(os.environ.get("HOME", "/home/agent")) / ".webcmd"
CDP_PORT = int(os.environ.get("WEBARENA_CDP_PORT", "9222"))


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


def run_webcmd(
    args: list[str],
    session: str | None = None,
    check: bool = True,
    stdin: str | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = ["webcmd"]
    if PROFILE:
        cmd += ["--profile", PROFILE]
    if session:
        cmd += ["--session", session]
    cmd += args
    result = subprocess.run(
        cmd,
        check=False,
        text=True,
        capture_output=True,
        input=stdin,
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"webcmd {' '.join(args)} failed: {detail}")
    return result


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


def parse_session_id(stdout: str) -> str:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"webcmd session id missing: {stdout}") from exc
    if isinstance(data, dict) and data.get("id"):
        return str(data["id"])
    raise RuntimeError(f"webcmd session id missing: {stdout}")


def parse_run_url(stdout: str) -> str:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return stdout.strip()
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        value = data.get("result", data.get("url", data.get("page", "")))
        if isinstance(value, dict):
            value = value.get("url", "")
        return str(value)
    return stdout.strip()


def browser_run(
    session_id: str, source: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    return run_webcmd(
        ["browser", "run", "--stdin", "--no-snapshot-diff"],
        session=session_id,
        check=check,
        stdin=source,
    )


def require_authenticated(session_id: str) -> None:
    deadline = time.monotonic() + LOGIN_WAIT_SEC
    source = (
        f"await page.goto('{SHOPPING_URL}{ACCOUNT_PATH}');\n"
        "return { url: page.url() };\n"
    )
    while True:
        opened = browser_run(session_id, source, check=False)
        if opened.returncode == 0:
            url = parse_run_url(opened.stdout or "")
            if url and "login" not in urlsplit(url).path.lower():
                return
        if time.monotonic() >= deadline:
            raise RuntimeError("authenticated state is not logged in")
        time.sleep(1)


def login(session_id: str) -> None:
    browser_run(
        session_id,
        (
            f"await page.goto('{SHOPPING_URL}{HEALTH_PATH}');\n"
            f"await page.locator('#email').first().fill('{SHOPPING_EMAIL}');\n"
            f"await page.locator('#pass').first().fill('{SHOPPING_PASSWORD}');\n"
            "await page.locator('#send2').first().click();\n"
            "await page.waitForTimeout(2000);\n"
            "return { url: page.url() };\n"
        ),
    )


def create_session() -> str:
    run_webcmd(["profile", "create", PROFILE], check=False)
    return parse_session_id(
        run_webcmd(["session", "create", SESSION_NAME, "-f", "json"]).stdout
    )


def launch_session(attempts: int = 3) -> str:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            return create_session()
        except RuntimeError as exc:
            last = exc
            if attempt + 1 == attempts:
                raise
            time.sleep(1)
    raise last or RuntimeError("webcmd session create failed")


def cdp_ready(endpoint: str) -> bool:
    try:
        with urlopen(Request(f"{endpoint}/json/version"), timeout=1) as response:
            return 200 <= response.status < 300
    except (OSError, HTTPError, URLError):
        return False


def cdp_ports_from_ps() -> list[int]:
    try:
        output = subprocess.check_output(["ps", "-axo", "command="], text=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    ports: list[int] = []
    for line in output.splitlines():
        if "--type=" in line:
            continue
        match = re.search(r"--remote-debugging-port=(\d+)", line)
        if match:
            ports.append(int(match.group(1)))
    return ports


def find_cdp_endpoint(root: Path | None = None) -> str | None:
    root = root or WEBCMD_HOME
    if root.is_dir():
        for port_file in root.rglob("DevToolsActivePort"):
            try:
                port = int(port_file.read_text().splitlines()[0])
            except (OSError, ValueError, IndexError):
                continue
            if port > 0:
                return f"http://127.0.0.1:{port}"
    for port in cdp_ports_from_ps():
        if port > 0:
            return f"http://127.0.0.1:{port}"
    return f"http://127.0.0.1:{CDP_PORT}"


def wait_for_cdp() -> str:
    deadline = time.monotonic() + max(LOGIN_WAIT_SEC, 30)
    while True:
        endpoint = find_cdp_endpoint()
        if endpoint and cdp_ready(endpoint):
            return endpoint
        if time.monotonic() >= deadline:
            raise RuntimeError("CDP endpoint is missing")
        time.sleep(0.5)


def stop_har_recorder() -> None:
    if not PID_PATH.is_file():
        return
    try:
        os.kill(int(PID_PATH.read_text().strip()), signal.SIGTERM)
    except (OSError, ValueError):
        pass
    PID_PATH.unlink(missing_ok=True)


def start_har_recorder() -> None:
    endpoint = wait_for_cdp()
    JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSONL_PATH.unlink(missing_ok=True)
    proc = subprocess.Popen(
        ["node", str(HAR_RECORDER), endpoint, str(JSONL_PATH)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(proc.pid))


def stop_browser() -> None:
    stop_har_recorder()
    session = SESSION_PATH.read_text().strip() if SESSION_PATH.is_file() else ""
    if session:
        run_webcmd(["session", "close", session, "--force"], check=False)
    run_webcmd(["daemon", "stop"], check=False)
    try:
        subprocess.run(
            ["pkill", "-f", "chromium"], check=False, capture_output=True
        )
    except FileNotFoundError:
        return


def prepare(task_id: int, task: dict | None = None) -> None:
    task = render_task(task or load_task(task_id))
    reset_site()
    APP.mkdir(parents=True, exist_ok=True)
    TASK_PATH.write_text(json.dumps(task, indent=2) + "\n")
    for path in (RESPONSE_PATH, HAR_PATH, JSONL_PATH):
        path.unlink(missing_ok=True)
    stop_browser()
    session_id = launch_session()
    SESSION_PATH.write_text(session_id + "\n")
    login(session_id)
    require_authenticated(session_id)
    start_har_recorder()


def header_list(headers) -> list[dict[str, str]]:
    if isinstance(headers, list):
        return [
            {"name": str(item.get("name", "")), "value": str(item.get("value", ""))}
            for item in headers
            if isinstance(item, dict)
        ]
    if isinstance(headers, dict):
        return [{"name": str(name), "value": str(value)} for name, value in headers.items()]
    return []


def events_to_har(events: list[dict]) -> dict:
    entries = []
    for event in events:
        post = event.get("postData") or ""
        request = {
            "method": event.get("method") or "GET",
            "url": event.get("url") or "",
            "httpVersion": "HTTP/1.1",
            "cookies": [],
            "headers": header_list(event.get("headers")),
            "queryString": [],
            "headersSize": -1,
            "bodySize": len(post),
        }
        if post:
            request["postData"] = {
                "mimeType": "application/x-www-form-urlencoded",
                "text": post,
            }
        entries.append(
            {
                "startedDateTime": event.get("startedDateTime")
                or "1970-01-01T00:00:00.000Z",
                "time": 0,
                "request": request,
                "response": {
                    "status": int(event.get("status") or 0),
                    "statusText": event.get("statusText") or "",
                    "httpVersion": "HTTP/1.1",
                    "cookies": [],
                    "headers": [],
                    "content": {"size": 0, "mimeType": ""},
                    "redirectURL": "",
                    "headersSize": -1,
                    "bodySize": 0,
                },
                "cache": {},
                "timings": {"send": 0, "wait": 0, "receive": 0},
            }
        )
    return {
        "log": {
            "version": "1.2",
            "creator": {"name": "webarena-webcmd", "version": "0"},
            "entries": entries,
        }
    }


def capture_stop() -> dict | None:
    stop_har_recorder()
    if not JSONL_PATH.is_file():
        return None
    events = []
    for line in JSONL_PATH.read_text().splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    har = events_to_har(events)
    HAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    HAR_PATH.write_text(json.dumps(har) + "\n")
    return har


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


def uses_agent_browser(command: str) -> bool:
    return "webcmd" in command_tokens(command)


def pi_log_metrics(path: Path | None = None) -> dict[str, float]:
    path = path or PI_LOG_PATH
    if not path.is_file():
        return {"agent_browser_commands": 0.0}
    count = 0
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "tool_execution_start":
            continue
        command = (event.get("args") or {}).get("command")
        if isinstance(command, str) and uses_agent_browser(command):
            count += 1
    return {"agent_browser_commands": float(count)}


def trajectory_metrics(path: Path | None = None) -> dict[str, float]:
    path = path or TRAJECTORY_PATH
    if not path.is_file():
        return pi_log_metrics()

    def count(value) -> int:
        if isinstance(value, dict):
            commands = sum(
                1
                for key, item in value.items()
                if key == "command"
                and isinstance(item, str)
                and uses_agent_browser(item)
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


def write_reward(reward: dict) -> dict:
    REWARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    REWARD_PATH.write_text(json.dumps(reward) + "\n")
    return reward


def evaluate(
    task_id: int,
    evaluator=None,
    metrics: dict[str, float] | None = None,
    response_path: Path | None = None,
) -> dict[str, float]:
    response_path = response_path or RESPONSE_PATH
    if not response_path.is_file() or not HAR_PATH.is_file():
        if metrics is None:
            try:
                metrics = collect_metrics()
            except RuntimeError:
                metrics = {"unique_urls": 0.0, **trajectory_metrics()}
        return write_reward({"reward": 0.0, **metrics})
    result = (evaluator or build_evaluator()).evaluate_task(
        task_id=task_id,
        agent_response=response_path,
        network_trace=HAR_PATH,
    )
    if evaluator_status_name(getattr(result, "status", "")) == "ERROR":
        raise RuntimeError(getattr(result, "error_msg", None) or "evaluator error")
    return write_reward(
        {"reward": float(result.score), **(metrics or collect_metrics())}
    )


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
    try:
        main(sys.argv[1:])
    except Exception as exc:
        print(exc, flush=True)
        raise

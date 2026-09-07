#!/usr/bin/env python3
"""Recreate the official Shopping container before each Harbor step."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

CONTAINER = "webarena_verified_shopping"
IMAGE = "am1n3e/webarena-verified-shopping"
ORIGIN = os.environ.get(
    "WEBARENA_SHOPPING_URL", "http://host.docker.internal:7770"
).rstrip("/")
SITE_PORT = int(os.environ.get("WEBARENA_SHOPPING_PORT", "7770"))
ENV_CTRL_PORT = int(os.environ.get("WEBARENA_ENV_CTRL_PORT", "7771"))
BROKER_PORT = int(os.environ.get("WEBARENA_BROKER_PORT", "7772"))
RESET_TIMEOUT_SEC = int(os.environ.get("WEBARENA_RESET_TIMEOUT_SEC", "600"))


def docker_bin() -> str:
    found = shutil.which("docker")
    if found:
        return found
    fallback = Path.home() / ".docker" / "bin" / "docker"
    if fallback.is_file():
        return str(fallback)
    raise RuntimeError("docker CLI not found")


def docker(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [docker_bin(), *args],
        check=True,
        text=True,
        capture_output=True,
    )


def http_json(url: str, method: str = "GET") -> dict:
    request = Request(url, method=method)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def control_ready() -> bool:
    try:
        data = http_json(f"http://127.0.0.1:{ENV_CTRL_PORT}/status")
    except (OSError, HTTPError, URLError, json.JSONDecodeError, ValueError):
        return False
    return bool(data.get("success"))


def site_ready() -> bool:
    url = f"http://127.0.0.1:{SITE_PORT}/customer/account/login"
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=10) as response:
            return response.status < 500
    except HTTPError as exc:
        return exc.code < 500
    except (OSError, URLError):
        return False


def wait_until_ready() -> None:
    deadline = time.monotonic() + RESET_TIMEOUT_SEC
    while time.monotonic() < deadline:
        if control_ready() and site_ready():
            return
        time.sleep(2)
    raise RuntimeError("Shopping reset failed health check")


def recreate_shopping() -> None:
    docker(["rm", "-f", CONTAINER])
    docker(
        [
            "run",
            "-d",
            "--name",
            CONTAINER,
            "-p",
            f"{SITE_PORT}:80",
            "-p",
            f"{ENV_CTRL_PORT}:8877",
            "-e",
            f"WA_ENV_CTRL_EXTERNAL_SITE_URL={ORIGIN}",
            IMAGE,
        ]
    )
    wait_until_ready()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] != "/status":
            self._send(404, {"success": False, "message": "not found"})
            return
        ready = control_ready() and site_ready()
        self._send(
            200,
            {"success": ready, "message": "ok" if ready else "not ready"},
        )

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/reset":
            self._send(404, {"success": False, "message": "not found"})
            return
        try:
            recreate_shopping()
        except Exception as exc:
            self._send(500, {"success": False, "message": str(exc)})
            return
        self._send(200, {"success": True, "message": "reset"})

    def log_message(self, format, *args) -> None:
        print("reset-broker:", args[0] if args else format)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", BROKER_PORT), Handler)
    print(f"reset broker listening on 0.0.0.0:{BROKER_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()

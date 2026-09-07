"""Thin Harbor agent: built-in Pi + save-sessions extension."""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import override

from harbor.environments.base import BaseEnvironment

from .agent import PiTrajectoryAgent

_EXTENSION_HOST_PATH = Path(__file__).resolve().parent / "extensions" / "save-sessions.ts"
_EXTENSION_CONTAINER_PATH = "/opt/pi-sessions/save-sessions.ts"


class PiSessionsAgent(PiTrajectoryAgent):
    """Pi coding agent with session logs copied to /app/sessions/ on shutdown."""

    @staticmethod
    @override
    def name() -> str:
        return "pi-sessions"

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        await super().install(environment)
        await self.exec_as_root(
            environment,
            command=("mkdir -p /opt/pi-sessions /app/sessions && chmod 777 /app/sessions"),
        )
        await environment.upload_file(
            _EXTENSION_HOST_PATH,
            _EXTENSION_CONTAINER_PATH,
        )
        await self.exec_as_root(
            environment,
            command=f"chmod a+r {shlex.quote(_EXTENSION_CONTAINER_PATH)}",
        )

    @override
    def build_cli_flags(self) -> str:
        # Inherit Pi.run() so credentials, custom endpoint configuration, resume,
        # and trajectory parsing stay identical to the baseline harness.
        return f"{super().build_cli_flags()} -e {shlex.quote(_EXTENSION_CONTAINER_PATH)}".strip()

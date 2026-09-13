"""Native Harbor Pi with ordered tools, timeout cleanup, and an error guard."""

import asyncio
from pathlib import Path
from typing import override

from harbor.agents.installed.pi import Pi
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from .trace import read_pi_errors

PI_VERSION = "0.85.1"
EXTENSION = Path(__file__).with_name("sequential-tools.ts")
REMOTE_EXTENSION = "/opt/language-pi/sequential-tools.ts"
STOP_SCRIPT = Path(__file__).with_name("stop_pi.py")
REMOTE_STOP_SCRIPT = "/opt/language-pi/stop_pi.py"


class PiProviderFailure(RuntimeError):
    """The trial must be inspected before any further model calls."""


class SequentialPi(Pi):
    def __init__(self, *args, version=PI_VERSION, **kwargs):
        if version != PI_VERSION:
            raise ValueError(f"SequentialPi is validated with Pi {PI_VERSION}; got {version!r}")
        super().__init__(*args, version=version, **kwargs)
        self._provider_failures: list[str] = []

    @staticmethod
    @override
    def name() -> str:
        return "language-pi-sequential"

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        await super().install(environment)
        await self.exec_as_root(environment, command="mkdir -p /opt/language-pi")
        await environment.upload_file(EXTENSION, REMOTE_EXTENSION)
        await environment.upload_file(STOP_SCRIPT, REMOTE_STOP_SCRIPT)
        await self.exec_as_root(
            environment,
            command=(
                f"chmod 755 /opt/language-pi && chmod 644 {REMOTE_EXTENSION} {REMOTE_STOP_SCRIPT}"
            ),
        )

    @override
    def build_cli_flags(self) -> str:
        return f"{super().build_cli_flags()} -e {REMOTE_EXTENSION}".strip()

    @override
    async def run(
        self, instruction: str, environment: BaseEnvironment, context: AgentContext
    ) -> None:
        if self._provider_failures:
            raise PiProviderFailure(
                "No further model calls after a Pi assistant failure: "
                + "; ".join(self._provider_failures)
            )
        try:
            await super().run(instruction, environment, context)
        except asyncio.CancelledError:
            # Cancelling Docker exec does not terminate the process in the container.
            # Finish cleanup before Harbor transfers logs or starts the next step.
            try:
                result = await asyncio.shield(
                    self.exec_as_root(
                        environment,
                        command=f"python3 -I {REMOTE_STOP_SCRIPT}",
                        timeout_sec=10,
                    )
                )
                self.logs_dir.mkdir(parents=True, exist_ok=True)
                (self.logs_dir / "timeout-cleanup.json").write_text(result.stdout or "{}")
            except Exception as exc:
                self._provider_failures.append(f"Timeout cleanup failed: {type(exc).__name__}")
                self.logger.exception("Failed to stop expired Pi processes")
            raise

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
        super().populate_context_post_run(context)
        errors = read_pi_errors(self.logs_dir / self._OUTPUT_FILENAME)
        self._provider_failures = list(dict.fromkeys([*self._provider_failures, *errors]))

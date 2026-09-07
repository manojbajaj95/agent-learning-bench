"""Keep native Pi execution/resume; export downloaded events for Harbor's viewer."""

from typing import override

from harbor.agents.installed.pi import Pi
from harbor.models.agent.context import AgentContext

from .convert import export_trajectory


class PiTrajectoryAgent(Pi):
    SUPPORTS_ATIF = True

    @staticmethod
    @override
    def name() -> str:
        return "pi-trajectory"

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
        super().populate_context_post_run(context)
        source = self.logs_dir / self._OUTPUT_FILENAME
        if source.is_file():
            export_trajectory(source, version=self.version() or "unknown", replace=True)

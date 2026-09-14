"""Task-local Pi adapter: native execution/resume with Harbor viewer export."""

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
            try:
                export_trajectory(source, version=self.version() or "unknown", replace=True)
            except Exception:
                # Viewer export is auxiliary: never mask an agent timeout or
                # prevent Harbor from verifying and archiving this attempt.
                self.logger.warning(
                    "Trajectory export failed; native Pi logs preserved", exc_info=True
                )

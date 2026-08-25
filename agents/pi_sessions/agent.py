"""Thin Harbor agent: built-in Pi + save-sessions extension."""

from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import override

from harbor.agents.installed.base import with_prompt_template
from harbor.agents.installed.pi import Pi
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

_EXTENSION_HOST_PATH = Path(__file__).resolve().parent / "extensions" / "save-sessions.ts"
_EXTENSION_CONTAINER_PATH = "/opt/pi-sessions/save-sessions.ts"


class PiSessionsAgent(Pi):
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
            command=(
                "mkdir -p /opt/pi-sessions /app/sessions && "
                "chmod 777 /app/sessions"
            ),
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
    @with_prompt_template
    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        escaped_instruction = shlex.quote(instruction)

        if not self.model_name or "/" not in self.model_name:
            raise ValueError("Model name must be in the format provider/model_name")

        provider, _ = self.model_name.split("/", 1)

        env: dict[str, str] = {}
        keys: list[str] = []

        if provider == "amazon-bedrock":
            keys.extend(["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION"])
        elif provider == "anthropic":
            keys.extend(["ANTHROPIC_API_KEY", "ANTHROPIC_OAUTH_TOKEN"])
        elif provider == "github-copilot":
            keys.append("GITHUB_TOKEN")
        elif provider == "google":
            keys.extend(
                [
                    "GEMINI_API_KEY",
                    "GOOGLE_GENERATIVE_AI_API_KEY",
                    "GOOGLE_APPLICATION_CREDENTIALS",
                    "GOOGLE_CLOUD_PROJECT",
                    "GOOGLE_CLOUD_LOCATION",
                    "GOOGLE_GENAI_USE_VERTEXAI",
                    "GOOGLE_API_KEY",
                ]
            )
        elif provider == "groq":
            keys.append("GROQ_API_KEY")
        elif provider == "huggingface":
            keys.append("HF_TOKEN")
        elif provider == "mistral":
            keys.append("MISTRAL_API_KEY")
        elif provider == "openai":
            keys.append("OPENAI_API_KEY")
        elif provider == "openrouter":
            keys.append("OPENROUTER_API_KEY")
        elif provider == "xai":
            keys.append("XAI_API_KEY")

        for key in keys:
            val = os.environ.get(key)
            if val:
                env[key] = val

        model_args = (
            f"--provider {provider} --model {self.model_name.split('/', 1)[1]} "
        )

        cli_flags = self.build_cli_flags()
        if cli_flags:
            cli_flags += " "
        resume_flag = "--continue " if self._resume else ""

        skills_command = self._build_register_skills_command()
        if skills_command:
            await self.exec_as_agent(environment, command=skills_command)

        extension_flag = f"-e {shlex.quote(_EXTENSION_CONTAINER_PATH)} "

        await self.exec_as_agent(
            environment,
            command=(
                f". ~/.nvm/nvm.sh; "
                f"pi --print --mode json --session-dir /logs/agent/pi/sessions "
                f"{extension_flag}"
                f"{resume_flag}"
                f"{model_args}"
                f"{cli_flags}"
                f"{escaped_instruction} "
                f'2>&1 </dev/null | grep -v \'"type":"message_update"\' | '
                f"stdbuf -oL tee /logs/agent/{self._OUTPUT_FILENAME}"
            ),
            env=env,
        )

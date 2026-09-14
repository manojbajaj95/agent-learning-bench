"""Keyless Harbor test agent exercising Pi's log paths across resumed steps."""

import json
import shlex

from harbor.agents.nop import NopAgent
from harbor.trial.errors import AgentTimeoutError

from affinity_agent import PiTrajectoryAgent

_PROBE = """
import os
import re
from pathlib import Path

assert os.geteuid() == 2000
index = int(re.search(r'battle (\\d+) of 20', Path('/app/view.txt').read_text())[1])
directory = Path('/logs/agent/pi/sessions')
directory.mkdir(parents=True, exist_ok=True)
session = directory / 'resume-probe.jsonl'
previous = session.read_text().splitlines() if session.exists() else []
assert previous == [str(i) for i in range(1, index)], previous
with session.open('a') as stream:
    stream.write(str(index) + '\\n')
Path('/logs/agent/pi.txt').write_text('resumed battle ' + str(index) + '\\n')
assert not os.access('/opt/affinity-arena/trial.json', os.R_OK)
assert not os.access('/logs/verifier/reward.json', os.R_OK)
"""


class ResumeProbeAgent(NopAgent):
    SUPPORTS_RESUME = True

    @staticmethod
    def name() -> str:
        return "arena-resume-probe"

    async def run(self, instruction, environment, context) -> None:
        result = await environment.exec("python3 -c " + shlex.quote(_PROBE))
        if result.return_code:
            raise RuntimeError(result.stderr or result.stdout)

    async def resume(self, instruction, environment, context) -> None:
        await self.run(instruction, environment, context)


class ExportProbeAgent(PiTrajectoryAgent):
    """Exercise timeout cleanup and verification without installing Pi or using an API."""

    def __init__(self, *args, interior=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.interior = interior

    async def setup(self, environment) -> None:
        pass

    async def run(self, instruction, environment, context, **kwargs) -> None:
        event = {"type": "message_end", "message": {"role": "user", "content": "Play."}}
        log = json.dumps(event) + '\n{"type":'
        if self.interior:
            log += '\n{"type":"agent_end"}\n'
        script = (
            "from pathlib import Path; Path('/logs/agent/pi.txt').write_text(" + repr(log) + ")"
        )
        result = await environment.exec("python3 -c " + shlex.quote(script))
        if result.return_code:
            raise RuntimeError(result.stderr or result.stdout)
        raise AgentTimeoutError("intentional keyless timeout probe")

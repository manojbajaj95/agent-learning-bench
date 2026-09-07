from pathlib import Path
import sys

sys.path.insert(0, "/opt/web")
from web import grade
from rewardkit import criterion


@criterion(description="answer.json matches the gold fact or form confirmation")
def correctness(workspace: Path) -> bool:
    return grade()

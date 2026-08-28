from pathlib import Path
import json
import sys

sys.path.insert(0, "/opt/f1")
from f1 import ANSWER_PATH, GOLD_PATH, STEP_PATH, answers_match, gold_result
from rewardkit import criterion


@criterion(description="answer.json matches gold SQL result")
def correctness(workspace: Path) -> bool:
    if not ANSWER_PATH.exists() or not STEP_PATH.exists():
        return False
    step = int(STEP_PATH.read_text().strip())
    gold = json.loads(GOLD_PATH.read_text())[step - 1]
    try:
        pred = json.loads(ANSWER_PATH.read_text())
    except json.JSONDecodeError:
        return False
    return answers_match(pred, gold_result(gold["SQL"]))

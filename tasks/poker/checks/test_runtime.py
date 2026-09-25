from pathlib import Path

from poker_game.engine import START_STACK
from poker_game.runtime import Runtime


def test_fold_and_settle(tmp_path: Path):
    runtime = Runtime(tmp_path / "private", tmp_path / "app", tmp_path / "verifier")
    view = runtime.start(1)
    assert "Your hand:" in view
    runtime.command(["act", "fold"])
    metrics = runtime.settle(1)
    assert metrics["chips"] == START_STACK - 5
    assert metrics["reward"] == START_STACK - 5
    assert metrics["env_actions"] == 1
    assert (tmp_path / "verifier" / "reward.txt").read_text().strip() == str(START_STACK - 5)
    assert "Hand 2" in runtime.command(["status"])

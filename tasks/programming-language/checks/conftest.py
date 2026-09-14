import json
import sys
from pathlib import Path

import pytest

TASK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK / "environment"))
sys.path.insert(0, str(TASK))
sys.path.insert(0, str(TASK.parents[1]))

from language_game.generation import generate_trial
from language_game.runtime import Paths, Runtime


@pytest.fixture
def runtime_factory(tmp_path):
    def create(name="trial", seed=1, visibility="hidden"):
        root = tmp_path / name
        paths = Paths(root / "private", root / "app", root / "verifier")
        paths.private.mkdir(parents=True)
        (paths.public / "problems").mkdir(parents=True)
        (paths.public / "workspace").mkdir()
        (paths.private / "trial.json").write_text(json.dumps(generate_trial(seed, visibility)))
        return Runtime(paths)

    return create


@pytest.fixture
def runtime(runtime_factory):
    return runtime_factory()

import json
import sys
from pathlib import Path

import pytest

TASK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK / "environment"))
sys.path.insert(0, str(TASK))
sys.path.insert(0, str(TASK.parents[1]))

from arena.runtime import Paths, Runtime


@pytest.fixture(scope="session")
def trial():
    return json.loads((TASK / "environment" / "trial.json").read_text())


@pytest.fixture
def runtime(tmp_path, trial):
    paths = Paths(tmp_path / "private", tmp_path / "app", tmp_path / "verifier")
    paths.private.mkdir()
    (paths.public / "battles").mkdir(parents=True)
    (paths.private / "trial.json").write_text(json.dumps(trial))
    return Runtime(paths)

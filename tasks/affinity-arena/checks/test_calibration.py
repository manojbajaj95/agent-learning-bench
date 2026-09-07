"""Learning magnitude is descriptive; correctness and completeness remain checked."""

import pytest

from calibrate import calibration_checks, render_report


@pytest.fixture
def rows():
    return [
        {
            "seed": 1,
            "policy": policy,
            "battle": battle,
            "reward": 0.75 if policy == "oracle" else 0.4,
            "won": int(policy == "oracle"),
            "regret": 0 if policy == "oracle" else 0.35,
            "opt_rate": int(policy == "oracle"),
            "draft_ok": int(policy == "oracle"),
            "cells_seen": 0.1,
            "ticks": 6,
            "oracle_ticks": 6,
        }
        for policy in ("oracle", "learner", "memoryless")
        for battle in range(1, 21)
    ]


def test_flat_or_declining_learning_is_not_a_correctness_failure(rows):
    assert all(calibration_checks(rows).values())
    for row in rows:
        if row["policy"] == "learner" and row["battle"] >= 11:
            row["reward"] = 0.2
    checks = calibration_checks(rows)
    assert checks == {"complete_schedule": True, "oracle_exact": True}
    report = render_report(rows, checks)
    assert "late − early = -0.200" in report
    assert "without acceptance thresholds" in report
    assert "Acceptance gates" not in report


@pytest.mark.parametrize(
    "field,value",
    [
        ("won", 0),
        ("regret", 0.1),
        ("opt_rate", 0.9),
        ("draft_ok", 0),
        ("ticks", 7),
    ],
)
def test_oracle_errors_still_fail(rows, field, value):
    rows[0][field] = value
    assert not calibration_checks(rows)["oracle_exact"]


def test_incomplete_duplicate_or_empty_data_fail(rows):
    assert not calibration_checks(rows[:-1])["complete_schedule"]
    assert not calibration_checks([*rows[:-1], rows[0]])["complete_schedule"]
    assert not any(calibration_checks([]).values())

import json

from tools.report_runs import summarize_trial

from analyze import METRICS, analyze_job, report


def test_report_preserves_raw_scores_costs_and_marks_incomplete_runs(tmp_path):
    trial_dir = tmp_path / "trial"
    trial_dir.mkdir()
    metrics = dict.fromkeys(METRICS, 0)
    metrics.update(reward=0.25, first_correctness=0.25, best_correctness=1, solved=1, completed=1)
    data = {
        "task_name": "agent-learning-bench/programming-language",
        "trial_name": "trial",
        "step_results": [
            {"step_name": f"problem-{i:02d}", "verifier_result": {"rewards": metrics}}
            for i in range(1, 21)
        ],
    }
    path = trial_dir / "result.json"
    path.write_text(json.dumps(data))
    summaries = analyze_job(tmp_path)
    assert not summaries[0]["issues"]
    assert summaries[0]["phases"]["holdout"]["reward"] == 0.25
    assert list(summaries[0]["phases"]) == ["foundation", "practice", "transfer", "holdout"]
    assert "phase differences alone do not measure learning" in report(summaries)
    assert "problem-20" in report(summaries)
    assert summarize_trial(data)["mean_reward"] == 0.25
    assert summaries[0]["n_input_tokens"] is None
    data["step_results"].pop()
    path.write_text(json.dumps(data))
    assert analyze_job(tmp_path)[0]["issues"]
    data["step_results"][0]["exception_info"] = {"exception_type": "AgentTimeoutError"}
    path.write_text(json.dumps(data))
    assert "AgentTimeoutError" in analyze_job(tmp_path)[0]["issues"]


def test_report_flags_provider_stops_even_without_harbor_exception(tmp_path):
    trial = tmp_path / "trial"
    logs = trial / "steps" / "problem-01" / "agent"
    logs.mkdir(parents=True)
    (trial / "result.json").write_text(
        json.dumps(
            {
                "task_name": "agent-learning-bench/programming-language",
                "trial_name": "trial",
                "step_results": [{"step_name": "problem-01"}],
            }
        )
    )
    (logs / "pi.txt").write_text(
        json.dumps(
            {
                "type": "message_end",
                "message": {
                    "role": "assistant",
                    "stopReason": "error",
                    "errorMessage": "Provider stopped with: MALFORMED_FUNCTION_CALL",
                },
            }
        )
    )
    summary = analyze_job(tmp_path)[0]
    assert any("MALFORMED_FUNCTION_CALL" in issue for issue in summary["issues"])
    assert summary["steps"][0]["pi_errors"] == ["Provider stopped with: MALFORMED_FUNCTION_CALL"]
    assert summary["steps"][0]["agent_status"] == "Pi assistant error"
    result_path = trial / "result.json"
    result = json.loads(result_path.read_text())
    result["step_results"].append(
        {"step_name": "problem-02", "exception_info": {"exception_type": "PiProviderFailure"}}
    )
    result_path.write_text(json.dumps(result))
    summaries = analyze_job(tmp_path)
    assert summaries[0]["steps"][1]["agent_status"] == "not attempted (error guard)"
    assert "not attempted (error guard)" in report(summaries)

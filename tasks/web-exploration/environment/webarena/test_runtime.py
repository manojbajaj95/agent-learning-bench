#!/usr/bin/env python3
"""Tests for the WebArena Shopping runtime."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import runtime


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.paths = mock.patch.multiple(
            runtime,
            APP=root / "app",
            TASK_PATH=root / "app" / "task.json",
            RESPONSE_PATH=root / "app" / "agent_response.json",
            HAR_PATH=root / "logs" / "agent" / "network.har",
            TRAJECTORY_PATH=root / "logs" / "agent" / "trajectory.json",
            REWARD_PATH=root / "logs" / "verifier" / "reward.json",
        )
        self.paths.start()
        self.addCleanup(self.paths.stop)

    @staticmethod
    def failing_opener(request, timeout):
        raise OSError("connection refused")

    def test_prepare_resets_before_starting_har(self):
        task = {
            "task_id": 21,
            "intent": "Find item",
            "start_urls": ["http://shop/"],
        }
        with mock.patch.object(runtime, "reset_site") as reset, mock.patch.object(
            runtime, "browser"
        ) as browser:
            runtime.prepare(21, task=task)

        reset.assert_called_once_with()
        self.assertEqual(task, json.loads(runtime.TASK_PATH.read_text()))
        self.assertEqual(
            [
                mock.call(["close"], check=False),
                mock.call(["open"]),
                mock.call(["state", "load", runtime.AUTH_STATE]),
                mock.call(["network", "har", "start", "--content", "text"]),
            ],
            browser.call_args_list,
        )

    def test_browser_invokes_agent_browser_directly(self):
        completed = subprocess.CompletedProcess([], 0, "{}", "")
        with mock.patch.object(runtime.subprocess, "run", return_value=completed) as run:
            result = runtime.browser(["open", "http://shop/"], check=False)

        self.assertIs(completed, result)
        run.assert_called_once_with(
            [
                "agent-browser",
                "--session",
                runtime.SESSION,
                "--json",
                "open",
                "http://shop/",
            ],
            check=False,
            text=True,
            capture_output=True,
        )

    def test_capture_stop_requires_valid_har(self):
        def write_invalid(_args):
            runtime.HAR_PATH.parent.mkdir(parents=True, exist_ok=True)
            runtime.HAR_PATH.write_text("not json")

        with mock.patch.object(runtime, "browser", side_effect=write_invalid):
            with self.assertRaisesRegex(RuntimeError, "network.har is invalid JSON"):
                runtime.capture_stop()

    def test_capture_stop_requires_har_file(self):
        with mock.patch.object(runtime, "browser"):
            with self.assertRaisesRegex(RuntimeError, "network.har is missing"):
                runtime.capture_stop()

    def test_capture_stop_saves_and_returns_har(self):
        har = {"log": {"entries": []}}

        def write_har(args):
            self.assertEqual(
                ["network", "har", "stop", str(runtime.HAR_PATH)], args
            )
            runtime.HAR_PATH.parent.mkdir(parents=True, exist_ok=True)
            runtime.HAR_PATH.write_text(json.dumps(har))

        with mock.patch.object(runtime, "browser", side_effect=write_har):
            self.assertEqual(har, runtime.capture_stop())

    def test_har_metrics_count_unique_normalized_shopping_urls(self):
        har = {
            "log": {
                "entries": [
                    {"request": {"url": "http://shop/a?one=1"}},
                    {"request": {"url": "http://shop/a?two=2#fragment"}},
                    {"request": {"url": "http://other/b"}},
                    {"request": {"url": "http://shop/c"}},
                ]
            }
        }
        self.assertEqual(
            {"unique_urls": 2.0}, runtime.har_metrics(har, "http://shop")
        )

    def test_trajectory_metrics_count_agent_browser_command_tokens_recursively(self):
        runtime.TRAJECTORY_PATH.parent.mkdir(parents=True)
        runtime.TRAJECTORY_PATH.write_text(
            json.dumps(
                {
                    "steps": [
                        {"tool_calls": [{"arguments": {"command": "agent-browser open"}}]},
                        {
                            "nested": {
                                "command": "cd /app && agent-browser click @e1",
                                "description": "agent-browser is not a command field",
                            }
                        },
                        {"command": "agent-browser-helper open"},
                    ]
                }
            )
        )

        self.assertEqual(
            {"agent_browser_commands": 2.0}, runtime.trajectory_metrics()
        )

    def test_evaluate_writes_reward_and_metrics(self):
        runtime.RESPONSE_PATH.parent.mkdir(parents=True)
        runtime.RESPONSE_PATH.write_text('{"answer": "done"}')
        runtime.HAR_PATH.parent.mkdir(parents=True)
        runtime.HAR_PATH.write_text('{"log": {"entries": []}}')
        evaluator = mock.Mock()
        evaluator.evaluate_task.return_value = SimpleNamespace(
            score=1.0, status="SUCCESS"
        )

        reward = runtime.evaluate(
            21,
            evaluator=evaluator,
            metrics={"unique_urls": 4.0, "agent_browser_commands": 7.0},
        )

        self.assertEqual(
            {
                "reward": 1.0,
                "unique_urls": 4.0,
                "agent_browser_commands": 7.0,
            },
            reward,
        )
        self.assertEqual(reward, json.loads(runtime.REWARD_PATH.read_text()))
        evaluator.evaluate_task.assert_called_once_with(
            task_id=21,
            agent_response=runtime.RESPONSE_PATH,
            network_trace=runtime.HAR_PATH,
        )

    def test_missing_response_is_infrastructure_error(self):
        missing_path = runtime.APP / "missing-agent-response.json"
        with self.assertRaisesRegex(RuntimeError, "agent_response.json is missing"):
            runtime.evaluate(21, evaluator=mock.Mock(), response_path=missing_path)

    def test_evaluator_error_propagates(self):
        runtime.RESPONSE_PATH.parent.mkdir(parents=True)
        runtime.RESPONSE_PATH.write_text("{}")
        runtime.HAR_PATH.parent.mkdir(parents=True)
        runtime.HAR_PATH.write_text("{}")
        evaluator = mock.Mock()
        evaluator.evaluate_task.side_effect = ValueError("evaluation failed")

        with self.assertRaisesRegex(ValueError, "evaluation failed"):
            runtime.evaluate(21, evaluator=evaluator)

    def test_reset_failure_is_not_reward_zero(self):
        with self.assertRaisesRegex(RuntimeError, "Shopping reset failed"):
            runtime.require_http_ok(
                "http://control/reset", method="POST", opener=self.failing_opener
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Unit tests for the WebArena shopping step generator."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_steps import ROOT, generate, load_shopping_tasks


class GeneratorTests(unittest.TestCase):
    def shopping_rows(self, count: int) -> list[dict]:
        return [
            {
                "task_id": task_id,
                "intent_template_id": 200 + task_id,
                "sites": ["shopping"],
                "intent": f"Shopping task {task_id}",
                "start_urls": ["__SHOPPING__"],
                "results_schema": {"type": "array", "items": {"type": "string"}},
                "eval": [],
            }
            for task_id in range(21, 21 + count)
        ]

    def write_json(self, rows: list[dict]) -> Path:
        path = Path(self.temp_dir.name) / "tasks.json"
        path.write_text(json.dumps(rows))
        return path

    def write_dataset(self, root: Path, rows: list[dict]) -> Path:
        path = root / "data" / "webarena-verified.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows) + "\n")
        return path

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.temp_root = Path(self.temp_dir.name)

    def test_generated_step_contract(self) -> None:
        rows = self.shopping_rows(3)
        self.write_dataset(self.temp_root, rows)
        generate(rows, self.temp_root, limit=None)
        setup = (self.temp_root / "steps/task-0021/workdir/setup.sh").read_text()
        verify = (self.temp_root / "steps/task-0021/tests/test.sh").read_text()
        manifest = (self.temp_root / "task.toml").read_text()
        self.assertIn("runtime.py prepare 21", setup)
        self.assertIn("/logs/agent/prepare.log", setup)
        self.assertIn("runtime.py capture-stop", verify)
        self.assertIn("runtime.py evaluate 21", verify)
        self.assertEqual(3, manifest.count("[[steps]]"))
        self.assertIn('schema_version = "1.4"', manifest)
        self.assertIn('multi_step_reward_strategy = "mean"', manifest)
        self.assertIn('user = "agent"', manifest)
        self.assertIn('network_mode = "public"', manifest)
        self.assertEqual(4, manifest.count("timeout_sec = 300.0"))
        self.assertEqual(4, manifest.count("timeout_sec = 180.0"))
        self.assertIn(
            'artifacts = ["/app/agent_response.json", "/app/task.json", '
            '"/app/notes.md", "/logs/agent/network.har"]',
            manifest,
        )
        agent_rows = json.loads(
            (self.temp_root / "data" / "agent-input.json").read_text()
        )
        self.assertEqual(
            {"type": "array", "items": {"type": "string"}},
            agent_rows[0]["results_schema"],
        )

    def test_filters_exact_shopping_only(self) -> None:
        rows = [
            {"task_id": 2, "sites": ["shopping"], "intent": "b", "start_urls": ["__SHOPPING__"], "eval": []},
            {"task_id": 1, "sites": ["shopping", "reddit"], "intent": "x", "start_urls": [], "eval": []},
            {"task_id": 3, "sites": ["shopping"], "intent": "c", "start_urls": ["__SHOPPING__"], "eval": []},
        ]
        path = self.write_json(rows)
        self.assertEqual([2, 3], [row["task_id"] for row in load_shopping_tasks(path)])

    def test_rejects_duplicate_task_ids(self) -> None:
        rows = [
            {"task_id": 2, "sites": ["shopping"], "intent": "a", "start_urls": ["__SHOPPING__"], "eval": []},
            {"task_id": 2, "sites": ["shopping"], "intent": "b", "start_urls": ["__SHOPPING__"], "eval": []},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate task_id 2"):
            load_shopping_tasks(self.write_json(rows))

    def test_generate_writes_under_provided_root(self) -> None:
        repo_steps = ROOT / "steps"
        repo_step_names = (
            {path.name for path in repo_steps.iterdir() if path.is_dir()}
            if repo_steps.is_dir()
            else set()
        )

        alt_root = Path(self.temp_dir.name) / "alt"
        alt_root.mkdir()
        rows = [
            {
                "task_id": 21,
                "intent_template_id": 222,
                "sites": ["shopping"],
                "intent": "Find reviewers",
                "start_urls": ["__SHOPPING__/example.html"],
                "eval": [],
            },
        ]
        self.write_dataset(alt_root, rows)
        generate(rows, alt_root, limit=None)

        step = alt_root / "steps" / "task-0021"
        self.assertTrue(step.is_dir())
        self.assertEqual(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "runuser -u agent -- python3 /opt/webarena/runtime.py capture-stop\n"
            "python3 /opt/webarena/runtime.py evaluate 21\n",
            (step / "tests" / "test.sh").read_text(),
        )
        self.assertTrue((alt_root / "data" / "agent-input.json").is_file())
        self.assertTrue(
            (alt_root / "environment" / "data" / "agent-input.json").is_file()
        )
        self.assertFalse((alt_root / "environment" / "data" / "auth.json").exists())
        self.assertEqual(
            rows,
            json.loads(
                (
                    alt_root
                    / "environment"
                    / "data"
                    / "webarena-verified.json"
                ).read_text()
            ),
        )
        self.assertTrue((alt_root / "task.toml").is_file())
        if repo_steps.is_dir():
            self.assertEqual(
                repo_step_names,
                {path.name for path in repo_steps.iterdir() if path.is_dir()},
            )
        else:
            self.assertFalse(repo_steps.exists())

    def test_dockerfile_pins_external_tools(self) -> None:
        text = (ROOT / "environment" / "Dockerfile").read_text()
        self.assertIn("agent-browser@0.36.0", text)
        self.assertIn("webarena-verified==1.2.3", text)
        self.assertIn("node:24-bookworm-slim", text)
        self.assertIn("chromium", text)
        self.assertIn("AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium", text)
        self.assertNotIn("WEBARENA_AUTH_STATE", text)
        self.assertNotIn("auth.json", text)
        self.assertIn("HOME=/home/agent", text)
        self.assertIn("/home/agent/.agents/skills/agent-browser", text)
        self.assertIn("COPY webarena/runtime.py /opt/webarena/runtime.py", text)
        self.assertIn("COPY data/ /opt/webarena/", text)
        self.assertIn("/app/notes.md", text)
        self.assertNotIn("setup_22.x", text)
        self.assertNotIn("agent-browser install", text)
        self.assertNotIn("/app/.pi/skills", text)
        self.assertNotIn("COPY web/", text)
        self.assertNotIn("/opt/web/", text)

    def test_readme_does_not_require_cookie_auth(self) -> None:
        text = (ROOT / "README.md").read_text()
        self.assertIn("python3 tasks/web-exploration/reset_broker.py", text)
        self.assertIn("http://host.docker.internal:7770", text)
        self.assertIn("logs in after each reset", text)
        self.assertIn("tasks/web-exploration/run_smoke.sh", text)
        self.assertNotIn("auto_login.py", text)

    def test_instruction_covers_statuses_and_browser_lifecycle(self):
        text = (ROOT / "instruction.md").read_text()
        self.assertIn("NOT_FOUND_ERROR", text)
        self.assertIn("ACTION_NOT_ALLOWED_ERROR", text)
        self.assertIn("error_details", text)
        self.assertIn("results_schema", text)
        self.assertIn("do not close the browser", text.lower())
        self.assertIn("retrieved_data", text)

    def test_generate_does_not_stage_auth(self) -> None:
        root = Path(self.temp_dir.name) / "stale-auth"
        rows = [
            {
                "task_id": 21,
                "intent_template_id": 222,
                "sites": ["shopping"],
                "intent": "Find item",
                "start_urls": ["__SHOPPING__"],
                "eval": [],
            }
        ]
        self.write_dataset(root, rows)
        (root / "data" / "auth.json").write_text('{"cookies": []}\n')

        generate(rows, root, limit=None)

        self.assertFalse((root / "environment" / "data" / "auth.json").exists())

    def test_generate_stages_full_evaluator_dataset(self) -> None:
        root = Path(self.temp_dir.name) / "full-dataset"
        rows = []
        for task_id in range(1, 813):
            if task_id <= 187:
                rows.append(
                    {
                        "task_id": task_id,
                        "intent_template_id": 1000 + task_id,
                        "sites": ["shopping"],
                        "intent": f"Shopping task {task_id}",
                        "start_urls": ["__SHOPPING__"],
                        "eval": [],
                    }
                )
            else:
                rows.append(
                    {
                        "task_id": task_id,
                        "sites": ["reddit"],
                        "intent": f"Other task {task_id}",
                        "start_urls": ["__REDDIT__"],
                        "eval": [],
                    }
                )
        self.write_dataset(root, rows)
        shopping = load_shopping_tasks(root / "data" / "webarena-verified.json")
        generate(shopping, root, limit=3)

        staged = json.loads(
            (root / "environment" / "data" / "webarena-verified.json").read_text()
        )
        self.assertEqual(812, len(staged))
        self.assertEqual(3, len(json.loads((root / "data" / "agent-input.json").read_text())))
        self.assertEqual(3, (root / "task.toml").read_text().count("[[steps]]"))


if __name__ == "__main__":
    unittest.main()

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
    def write_json(self, rows: list[dict]) -> Path:
        path = Path(self.temp_dir.name) / "tasks.json"
        path.write_text(json.dumps(rows))
        return path

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

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
        (alt_root / "data").mkdir()
        (alt_root / "data" / "auth.json").write_text('{"cookies": []}\n')
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
        self.assertTrue((alt_root / "environment" / "data" / "auth.json").is_file())
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
        self.assertIn("/app/.pi/skills/agent-browser", text)
        self.assertIn("COPY webarena/runtime.py /opt/webarena/runtime.py", text)
        self.assertIn("COPY data/ /opt/webarena/", text)
        self.assertNotIn("COPY web/", text)
        self.assertNotIn("/opt/web/", text)

    def test_generate_removes_stale_staged_auth(self) -> None:
        root = Path(self.temp_dir.name) / "stale-auth"
        staged_auth = root / "environment" / "data" / "auth.json"
        staged_auth.parent.mkdir(parents=True)
        staged_auth.write_text('{"stale": true}\n')
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

        generate(rows, root, limit=None)

        self.assertFalse(staged_auth.exists())


if __name__ == "__main__":
    unittest.main()

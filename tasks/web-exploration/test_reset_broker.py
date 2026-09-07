#!/usr/bin/env python3
"""Tests for the host-side Shopping reset broker."""

from __future__ import annotations

import subprocess
import unittest
from unittest import mock

import reset_broker


class ResetBrokerTests(unittest.TestCase):
    def test_recreate_uses_container_visible_origin(self) -> None:
        with mock.patch.object(
            reset_broker,
            "docker",
            return_value=subprocess.CompletedProcess([], 0, "", ""),
        ) as run:
            with mock.patch.object(reset_broker, "wait_until_ready"):
                reset_broker.recreate_shopping()

        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(["rm", "-f", "webarena_verified_shopping"], commands[0])
        run_cmd = commands[1]
        self.assertEqual("run", run_cmd[0])
        self.assertIn("am1n3e/webarena-verified-shopping", run_cmd)
        self.assertIn(
            "WA_ENV_CTRL_EXTERNAL_SITE_URL=http://host.docker.internal:7770",
            run_cmd,
        )

    def test_status_ok_requires_success_true(self) -> None:
        with mock.patch.object(
            reset_broker,
            "http_json",
            return_value={"success": False, "message": "starting"},
        ):
            self.assertFalse(reset_broker.control_ready())


if __name__ == "__main__":
    unittest.main(verbosity=2)

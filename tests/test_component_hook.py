from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "plugins" / "rootloom" / "hooks" / "run_component_hook.py"
SPEC = importlib.util.spec_from_file_location("run_component_hook", SCRIPT)
assert SPEC and SPEC.loader
component_hook = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(component_hook)


class ComponentHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="component-hook-test-", dir=Path.home())
        self.addCleanup(self.temp_dir.cleanup)
        self.codex_home = Path(self.temp_dir.name) / ".codex"
        self.policy = self.codex_home / ".rootloom" / "components.json"

    def write_policy(self, project: bool) -> None:
        self.policy.parent.mkdir(parents=True)
        self.policy.write_text(
            json.dumps(
                {
                    "hooks": {
                        "project-guidance-hook": project,
                    },
                    "managed_by": component_hook.MANAGED_BY,
                    "schema_version": 1,
                    "selected_capabilities": [],
                    "selected_components": [],
                }
            ),
            encoding="utf-8",
        )

    def test_absent_policy_disables_all_hooks(self) -> None:
        for name in component_hook.HOOK_COMMANDS:
            enabled, error = component_hook.hook_enabled(name, self.policy)
            self.assertFalse(enabled)
            self.assertIsNone(error)

    def test_managed_policy_controls_project_hook(self) -> None:
        self.write_policy(project=True)
        self.assertEqual(
            component_hook.hook_enabled("project-guidance-hook", self.policy),
            (True, None),
        )

    def test_invalid_or_symlinked_policy_fails_closed(self) -> None:
        self.policy.parent.mkdir(parents=True)
        self.policy.write_text("{}", encoding="utf-8")
        enabled, error = component_hook.hook_enabled("project-guidance-hook", self.policy)
        self.assertFalse(enabled)
        self.assertIn("not a managed", error or "")

        outside = Path(self.temp_dir.name) / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        self.policy.unlink()
        self.policy.symlink_to(outside)
        enabled, error = component_hook.hook_enabled("project-guidance-hook", self.policy)
        self.assertFalse(enabled)
        self.assertIn("symbolic link", error or "")

        self.policy.unlink()
        self.policy.parent.rmdir()
        outside_dir = Path(self.temp_dir.name) / "outside-policy-dir"
        outside_dir.mkdir()
        self.policy.parent.symlink_to(outside_dir, target_is_directory=True)
        enabled, error = component_hook.hook_enabled("project-guidance-hook", self.policy)
        self.assertFalse(enabled)
        self.assertIn("symbolic link", error or "")

    def test_disabled_hook_exits_without_invoking_handler(self) -> None:
        self.write_policy(project=False)
        env = os.environ.copy()
        env["CODEX_HOME"] = str(self.codex_home)
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "project-guidance-hook"],
            input=json.dumps({"cwd": str(self.temp_dir.name), "source": "startup"}),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO_ROOT
    / "plugins"
    / "rootloom"
    / "skills"
    / "setup-rootloom"
    / "scripts"
    / "setup_rootloom.py"
)
SPEC = importlib.util.spec_from_file_location("setup_rootloom", SCRIPT)
assert SPEC and SPEC.loader
setup = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = setup
SPEC.loader.exec_module(setup)


class SetupRootloomTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="rootloom-setup-", dir=Path.home())
        self.addCleanup(self.temporary.cleanup)
        self.codex_home = Path(self.temporary.name) / "codex-home"
        self.codex_home.mkdir()

    def test_personal_is_default_and_contains_only_personal_components(self) -> None:
        result = setup.apply_plan(self.codex_home, replace_conflicts=False)
        self.assertEqual(result["capabilities"], list(setup.PRESETS["personal"]))
        self.assertTrue((self.codex_home / "AGENTS.md").is_file())
        self.assertTrue((self.codex_home / "rules" / "rootloom.rules").is_file())
        self.assertFalse((self.codex_home / "agents").exists())
        self.assertFalse((self.codex_home / "high-assurance.config.toml").exists())
        policy = json.loads(
            (self.codex_home / setup.COMPONENT_POLICY_PATH).read_text(encoding="utf-8")
        )
        self.assertEqual(policy["hooks"], {"project-guidance-hook": True})

    def test_plan_apply_status_and_rollback_round_trip(self) -> None:
        version, _targets, actions, _desired = setup.build_plan(self.codex_home)
        self.assertTrue(version)
        self.assertTrue(all(item.action == "create" for item in actions))

        applied = setup.apply_plan(self.codex_home, replace_conflicts=False)
        self.assertEqual(applied["status"], "applied")
        status = setup.status_payload(self.codex_home)
        self.assertEqual(status["status"], "installed")
        self.assertTrue(all(item["action"] == "unchanged" for item in status["actions"]))

        rolled_back = setup.rollback(self.codex_home)
        self.assertEqual(rolled_back["status"], "rolled_back")
        self.assertFalse((self.codex_home / "AGENTS.md").exists())
        self.assertFalse((self.codex_home / "rules" / "rootloom.rules").exists())
        self.assertFalse((self.codex_home / setup.COMPONENT_POLICY_PATH).exists())

    def test_user_owned_conflict_requires_explicit_replacement_and_restores_mode(self) -> None:
        agents = self.codex_home / "AGENTS.md"
        agents.write_text("# Mine\n", encoding="utf-8")
        if os.name != "nt":
            agents.chmod(0o644)
        with self.assertRaisesRegex(RuntimeError, "user-owned conflicts"):
            setup.apply_plan(self.codex_home, replace_conflicts=False)

        setup.apply_plan(self.codex_home, replace_conflicts=True)
        setup.rollback(self.codex_home)
        self.assertEqual(agents.read_text(encoding="utf-8"), "# Mine\n")
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(agents.stat().st_mode), 0o644)

    def test_rollback_refuses_post_setup_edits(self) -> None:
        setup.apply_plan(self.codex_home, replace_conflicts=False)
        agents = self.codex_home / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8") + "\n# edit\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "changed after setup"):
            setup.rollback(self.codex_home)

    def test_capability_change_requires_rollback(self) -> None:
        setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["guidance"],
        )
        with self.assertRaisesRegex(RuntimeError, "roll back first"):
            setup.apply_plan(
                self.codex_home,
                replace_conflicts=False,
                capabilities=setup.PRESETS["personal"],
            )
        setup.rollback(self.codex_home)
        result = setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["personal"],
        )
        self.assertEqual(result["status"], "applied")

    def test_update_rollback_restores_previous_install_and_all_unwinds_chain(self) -> None:
        setup.apply_plan(self.codex_home, replace_conflicts=False)
        original = (self.codex_home / "AGENTS.md").read_bytes()
        original_desired = setup.desired_bytes

        def updated(target: object, capabilities: tuple[str, ...]) -> bytes:
            value = original_desired(target, capabilities)
            if isinstance(target, setup.Target) and target.relative_path == "AGENTS.md":
                return value + b"\n# simulated update\n"
            return value

        with mock.patch.object(setup, "desired_bytes", side_effect=updated):
            setup.apply_plan(self.codex_home, replace_conflicts=False)
        self.assertNotEqual((self.codex_home / "AGENTS.md").read_bytes(), original)

        one = setup.rollback(self.codex_home)
        self.assertEqual(one["status"], "rolled_back_to_previous")
        self.assertEqual((self.codex_home / "AGENTS.md").read_bytes(), original)
        self.assertEqual(setup.load_state(self.codex_home)["status"], "installed")

        all_result = setup.rollback_all(self.codex_home)
        self.assertEqual(all_result["status"], "rolled_back_all")
        self.assertFalse((self.codex_home / "AGENTS.md").exists())

    def test_skills_only_disables_hook_without_global_assets(self) -> None:
        result = setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["skills-only"],
        )
        self.assertEqual(result["capabilities"], [])
        self.assertFalse((self.codex_home / "AGENTS.md").exists())
        policy = json.loads(
            (self.codex_home / setup.COMPONENT_POLICY_PATH).read_text(encoding="utf-8")
        )
        self.assertEqual(policy["hooks"], {"project-guidance-hook": False})
        self.assertEqual(setup.status_payload(self.codex_home)["capabilities"], [])

        args = mock.Mock(preset=None, capabilities=None)
        self.assertEqual(setup.selected_capabilities(args, self.codex_home), ())

    def test_explicit_empty_status_selection_does_not_fall_back_to_personal(self) -> None:
        status = setup.status_payload(self.codex_home, ())
        self.assertEqual(status["capabilities"], [])
        self.assertEqual(status["components"], [])
        self.assertEqual(
            [item["path"] for item in status["actions"]],
            [str(setup.COMPONENT_POLICY_PATH)],
        )

    def test_setup_lock_refuses_competing_operation(self) -> None:
        with setup.setup_lock(self.codex_home):
            with self.assertRaisesRegex(RuntimeError, "another Rootloom setup operation"):
                setup.apply_plan(self.codex_home, replace_conflicts=False)

    def test_symlinked_target_is_refused(self) -> None:
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        (self.codex_home / "rules").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "symlinked"):
            setup.apply_plan(self.codex_home, replace_conflicts=True)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == "__main__":
    unittest.main()

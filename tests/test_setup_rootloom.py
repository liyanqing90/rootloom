from __future__ import annotations

import importlib.util
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest import mock
from pathlib import Path


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


class RootloomSetupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="rootloom-test-", dir=Path.home())
        self.addCleanup(self.temp_dir.cleanup)
        self.codex_home = Path(self.temp_dir.name) / ".codex"
        self.codex_home.mkdir()

    def test_apply_preserves_config_and_rollback_restores_baseline(self) -> None:
        original_config = (
            'model = "example-model"\n\n'
            "[agents]\n"
            "max_threads = 6\n"
            "max_depth = 2\n"
            "interrupt_message = false\n\n"
            "[features]\n"
            "hooks = true\n"
        )
        (self.codex_home / "config.toml").write_text(original_config, encoding="utf-8")

        result = setup.apply_plan(self.codex_home, replace_conflicts=False)
        self.assertEqual(result["status"], "applied")
        self.assertIn("rootloom:managed", (self.codex_home / "AGENTS.md").read_text())

        with (self.codex_home / "config.toml").open("rb") as handle:
            config = tomllib.load(handle)
        self.assertEqual(config["model"], "example-model")
        self.assertTrue(config["features"]["hooks"])
        self.assertEqual(config["agents"]["max_threads"], 4)
        self.assertEqual(config["agents"]["max_depth"], 1)
        self.assertTrue(config["agents"]["interrupt_message"])

        status = setup.status_payload(self.codex_home)
        self.assertTrue(all(item["action"] == "unchanged" for item in status["actions"]))

        rolled_back = setup.rollback(self.codex_home)
        self.assertEqual(rolled_back["status"], "rolled_back")
        self.assertEqual(
            (self.codex_home / "config.toml").read_text(encoding="utf-8"),
            original_config,
        )
        self.assertFalse((self.codex_home / "AGENTS.md").exists())
        self.assertFalse((self.codex_home / "agents" / "evidence_explorer.toml").exists())

    def test_user_owned_guidance_blocks_atomic_apply(self) -> None:
        custom = "# My policy\n\n- Preserve this file.\n"
        agents = self.codex_home / "AGENTS.md"
        agents.write_text(custom, encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "user-owned conflicts"):
            setup.apply_plan(self.codex_home, replace_conflicts=False)
        self.assertEqual(agents.read_text(encoding="utf-8"), custom)
        self.assertFalse((self.codex_home / "config.toml").exists())

        result = setup.apply_plan(self.codex_home, replace_conflicts=True)
        self.assertEqual(result["status"], "applied")
        self.assertIn("Global Codex Working Agreement", agents.read_text(encoding="utf-8"))
        setup.rollback(self.codex_home)
        self.assertEqual(agents.read_text(encoding="utf-8"), custom)

    def test_apply_compensates_when_state_commit_fails(self) -> None:
        original_atomic = setup.atomic_write

        def fail_state(path: Path, value: bytes, mode: int = 0o600) -> None:
            if path.name == "state.json":
                raise OSError("injected state commit failure")
            original_atomic(path, value, mode)

        with mock.patch.object(setup, "atomic_write", side_effect=fail_state):
            with self.assertRaisesRegex(OSError, "injected state commit failure"):
                setup.apply_plan(
                    self.codex_home,
                    replace_conflicts=False,
                    capabilities=setup.PRESETS["engineering"],
                )

        self.assertFalse((self.codex_home / "AGENTS.md").exists())
        self.assertFalse((self.codex_home / "rules" / "rootloom.rules").exists())
        self.assertFalse((self.codex_home / setup.COMPONENT_POLICY_PATH).exists())
        self.assertFalse((self.codex_home / setup.STATE_DIRNAME / "state.json").exists())

    def test_setup_lock_rejects_a_competing_transaction(self) -> None:
        with setup.setup_lock(self.codex_home):
            with self.assertRaisesRegex(RuntimeError, "another Rootloom setup transaction"):
                setup.apply_plan(
                    self.codex_home,
                    replace_conflicts=False,
                    capabilities=setup.PRESETS["guidance"],
                )

        result = setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["guidance"],
        )
        self.assertEqual(result["status"], "applied")

    def test_interrupted_setup_recovery_restores_pre_transaction_state(self) -> None:
        result = setup.apply_plan(self.codex_home, replace_conflicts=False)
        transaction = Path(result["transaction"])
        journal_path = transaction / "recovery.json"
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        journal["phase"] = "applying"
        journal_path.write_text(json.dumps(journal), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "requires 'recover'"):
            setup.apply_plan(self.codex_home, replace_conflicts=False)
        recovered = setup.recover(self.codex_home)
        self.assertEqual(recovered["status"], "recovered")
        self.assertFalse((self.codex_home / setup.STATE_DIRNAME / "state.json").exists())
        self.assertEqual(setup.recover(self.codex_home)["status"], "no_recovery_required")

    def test_superseded_terminal_recovery_journal_is_inert(self) -> None:
        result = setup.apply_plan(self.codex_home, replace_conflicts=False)
        transaction = Path(result["transaction"])
        journal_path = transaction / "recovery.json"
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        journal["format"] = "rootloom-setup-recovery-v1"
        journal_path.write_text(json.dumps(journal), encoding="utf-8")

        self.assertEqual(setup.unresolved_transactions(self.codex_home), [])
        self.assertEqual(setup.recover(self.codex_home)["status"], "no_recovery_required")

    def test_interrupted_setup_recovery_refuses_ambiguous_user_edit(self) -> None:
        result = setup.apply_plan(self.codex_home, replace_conflicts=False)
        transaction = Path(result["transaction"])
        journal_path = transaction / "recovery.json"
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        journal["phase"] = "applying"
        journal_path.write_text(json.dumps(journal), encoding="utf-8")
        manifest = json.loads((transaction / "manifest.json").read_text(encoding="utf-8"))
        target = self.codex_home / manifest["files"][0]["path"]
        target.write_text("user changed after interruption", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "changed after interruption"):
            setup.recover(self.codex_home)

    def test_interrupted_rollback_recovery_restores_installed_state(self) -> None:
        setup.apply_plan(self.codex_home, replace_conflicts=False)
        installed_state = setup.load_state(self.codex_home)
        managed = {
            relative: (self.codex_home / relative).read_bytes()
            for relative in installed_state["files"]
        }
        original_journal = setup.write_recovery_journal
        interrupted = False

        def interrupt_after_first_mutation(
            transaction: Path,
            phase: str,
            applied_paths: list[str],
        ) -> None:
            nonlocal interrupted
            original_journal(transaction, phase, applied_paths)
            if phase == "applying" and not interrupted:
                interrupted = True
                raise SystemExit("simulated rollback interruption")

        with mock.patch.object(
            setup,
            "write_recovery_journal",
            side_effect=interrupt_after_first_mutation,
        ):
            with self.assertRaisesRegex(SystemExit, "simulated rollback interruption"):
                setup.rollback(self.codex_home)

        self.assertTrue(setup.unresolved_transactions(self.codex_home))
        recovered = setup.recover(self.codex_home)
        self.assertEqual(recovered["status"], "recovered")
        self.assertEqual(setup.load_state(self.codex_home), installed_state)
        for relative, expected in managed.items():
            self.assertEqual((self.codex_home / relative).read_bytes(), expected)

    def test_recovery_rejects_unknown_target_before_mutation(self) -> None:
        result = setup.apply_plan(self.codex_home, replace_conflicts=False)
        transaction = Path(result["transaction"])
        victim = self.codex_home / "unmanaged-user-file.txt"
        victim.write_text("preserve me", encoding="utf-8")
        manifest_path = transaction / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"].append(
            {
                "path": victim.name,
                "before_exists": False,
                "before_hash": None,
                "before_mode": None,
                "after_hash": setup.sha256_bytes(victim.read_bytes()),
                "backup": None,
            }
        )
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        setup.write_recovery_journal(transaction, "applying", [])

        with self.assertRaisesRegex(ValueError, "invalid recovery target"):
            setup.recover(self.codex_home)
        self.assertEqual(victim.read_text(encoding="utf-8"), "preserve me")

    def test_recovery_preflights_backup_hash_before_mutation(self) -> None:
        agents = self.codex_home / "AGENTS.md"
        agents.write_text("# User policy\n", encoding="utf-8")
        result = setup.apply_plan(
            self.codex_home,
            replace_conflicts=True,
            capabilities=setup.PRESETS["guidance"],
        )
        transaction = Path(result["transaction"])
        setup.write_recovery_journal(transaction, "applying", [])
        manifest = json.loads((transaction / "manifest.json").read_text(encoding="utf-8"))
        entry = next(item for item in manifest["files"] if item["path"] == "AGENTS.md")
        (transaction / entry["backup"]).write_text("corrupt backup", encoding="utf-8")
        managed_agents = agents.read_bytes()
        installed_state = (self.codex_home / setup.STATE_DIRNAME / "state.json").read_bytes()

        with self.assertRaisesRegex(RuntimeError, "backup hash"):
            setup.recover(self.codex_home)
        self.assertEqual(agents.read_bytes(), managed_agents)
        self.assertEqual(
            (self.codex_home / setup.STATE_DIRNAME / "state.json").read_bytes(),
            installed_state,
        )

    def test_recovery_rejects_manifest_drift_before_mutation(self) -> None:
        result = setup.apply_plan(self.codex_home, replace_conflicts=False)
        transaction = Path(result["transaction"])
        setup.write_recovery_journal(transaction, "applying", [])
        manifest_path = transaction / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        omitted = manifest["files"].pop()
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        target = self.codex_home / omitted["path"]
        expected = target.read_bytes()

        with self.assertRaisesRegex(RuntimeError, "manifest changed"):
            setup.recover(self.codex_home)
        self.assertEqual(target.read_bytes(), expected)

    def test_recovery_rejects_mode_drift_before_mutation(self) -> None:
        result = setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["guidance"],
        )
        transaction = Path(result["transaction"])
        setup.write_recovery_journal(transaction, "applying", [])
        agents = self.codex_home / "AGENTS.md"
        state_path = self.codex_home / setup.STATE_DIRNAME / "state.json"
        installed_state = state_path.read_bytes()
        agents.chmod(0o644)

        with self.assertRaisesRegex(RuntimeError, "mode changed"):
            setup.recover(self.codex_home)
        self.assertEqual(state_path.read_bytes(), installed_state)
        self.assertEqual(setup.file_mode(agents), 0o644)

    def test_rollback_restores_original_file_mode(self) -> None:
        agents = self.codex_home / "AGENTS.md"
        agents.write_text("# User policy\n", encoding="utf-8")
        agents.chmod(0o644)

        setup.apply_plan(
            self.codex_home,
            replace_conflicts=True,
            capabilities=setup.PRESETS["guidance"],
        )
        setup.rollback(self.codex_home)

        self.assertEqual(agents.read_text(encoding="utf-8"), "# User policy\n")
        self.assertEqual(stat.S_IMODE(agents.stat().st_mode), 0o644)

    def test_rollback_compensates_when_state_commit_fails(self) -> None:
        setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["engineering"],
        )
        managed_paths = (
            self.codex_home / "AGENTS.md",
            self.codex_home / "config.toml",
            self.codex_home / "rules" / "rootloom.rules",
            self.codex_home / setup.COMPONENT_POLICY_PATH,
            self.codex_home / setup.STATE_DIRNAME / "state.json",
        )
        before = {
            path: (
                path.read_bytes() if path.is_file() else None,
                stat.S_IMODE(path.stat().st_mode) if path.is_file() else None,
            )
            for path in managed_paths
        }
        original_atomic = setup.atomic_write
        failed = False

        def fail_once(path: Path, value: bytes, mode: int = 0o600) -> None:
            nonlocal failed
            if path.name == "state.json" and not failed:
                failed = True
                raise OSError("injected rollback state commit failure")
            original_atomic(path, value, mode)

        with mock.patch.object(setup, "atomic_write", side_effect=fail_once):
            with self.assertRaisesRegex(
                OSError,
                "injected rollback state commit failure",
            ):
                setup.rollback(self.codex_home)

        for path, (content, mode) in before.items():
            self.assertEqual(path.read_bytes() if path.is_file() else None, content)
            self.assertEqual(
                stat.S_IMODE(path.stat().st_mode) if path.is_file() else None,
                mode,
            )
        self.assertEqual(setup.load_state(self.codex_home)["status"], "installed")

    def test_rollback_refuses_to_erase_post_setup_edits(self) -> None:
        setup.apply_plan(self.codex_home, replace_conflicts=False)
        agents = self.codex_home / "AGENTS.md"
        agents.write_text(agents.read_text(encoding="utf-8") + "\n- Personal note.\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "changed after setup"):
            setup.rollback(self.codex_home)

    def test_rollback_refuses_post_setup_mode_drift(self) -> None:
        setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["guidance"],
        )
        agents = self.codex_home / "AGENTS.md"
        agents.chmod(0o644)

        with self.assertRaisesRegex(RuntimeError, "changed after setup"):
            setup.rollback(self.codex_home)
        self.assertEqual(setup.file_mode(agents), 0o644)
        self.assertEqual(setup.load_state(self.codex_home)["status"], "installed")

    def test_setup_refuses_symlinked_managed_directories_even_with_replace(self) -> None:
        outside = Path(self.temp_dir.name) / "outside-agents"
        outside.mkdir()
        (self.codex_home / "agents").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "symlinked targets"):
            setup.apply_plan(self.codex_home, replace_conflicts=True)
        self.assertEqual(list(outside.iterdir()), [])

    def test_rollback_rejects_tampered_transaction_paths(self) -> None:
        result = setup.apply_plan(self.codex_home, replace_conflicts=False)
        manifest_path = Path(result["transaction"]) / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["files"][0]["path"] = "../../outside"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "manifest changed"):
            setup.rollback(self.codex_home)

    def test_rollback_rejects_tampered_previous_state_before_mutation(self) -> None:
        result = setup.apply_plan(self.codex_home, replace_conflicts=False)
        manifest_path = Path(result["transaction"]) / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["previous_state"] = {
            "status": "installed",
            "capabilities": list(setup.FULL_CAPABILITIES),
            "latest_transaction": "../../escape",
        }
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        before = (self.codex_home / "AGENTS.md").read_bytes()
        with self.assertRaisesRegex(RuntimeError, "manifest changed"):
            setup.rollback(self.codex_home)
        self.assertEqual((self.codex_home / "AGENTS.md").read_bytes(), before)

    def test_rules_distinguish_commit_push_and_destructive_reset(self) -> None:
        codex = shutil.which("codex")
        if codex is None:
            self.skipTest("Codex CLI is required for executable Rules contract tests")
        rules = (
            REPO_ROOT
            / "plugins"
            / "rootloom"
            / "assets"
            / "system"
            / "rules"
            / "rootloom.rules"
        )
        expected = {
            ("git", "commit", "-m", "test"): "allow",
            ("git", "push", "origin", "main"): "prompt",
            ("git", "reset", "--hard"): "forbidden",
        }
        for command, decision in expected.items():
            completed = subprocess.run(
                [codex, "execpolicy", "check", "--rules", str(rules), "--", *command],
                check=True,
                capture_output=True,
                text=True,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["decision"], decision, command)

    def test_runtime_project_trust_is_preserved_by_status_and_rollback(self) -> None:
        setup.apply_plan(self.codex_home, replace_conflicts=False)
        config_path = self.codex_home / "config.toml"
        config_path.write_text(
            config_path.read_text(encoding="utf-8")
            + '\n[projects."/tmp/example"]\ntrust_level = "trusted"\n',
            encoding="utf-8",
        )

        status = setup.status_payload(self.codex_home)
        self.assertTrue(all(item["action"] == "unchanged" for item in status["actions"]))

        result = setup.rollback(self.codex_home)
        self.assertEqual(result["status"], "rolled_back")
        with config_path.open("rb") as handle:
            config = tomllib.load(handle)
        self.assertNotIn("agents", config)
        self.assertEqual(config["projects"]["/tmp/example"]["trust_level"], "trusted")

    def test_rollback_rejects_changes_to_managed_agent_limits(self) -> None:
        setup.apply_plan(self.codex_home, replace_conflicts=False)
        config_path = self.codex_home / "config.toml"
        config_path.write_text(
            config_path.read_text(encoding="utf-8").replace(
                "max_threads = 4",
                "max_threads = 5",
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(RuntimeError, "config.toml changed after setup"):
            setup.rollback(self.codex_home)

    def test_legacy_block_markers_cannot_capture_later_project_tables(self) -> None:
        config_path = self.codex_home / "config.toml"
        config_path.write_text(
            "[agents]\n"
            f"{setup.LIMITS_START}\n"
            "max_threads = 4\n"
            "max_depth = 1\n"
            "interrupt_message = true\n\n"
            '[projects."/tmp/example"]\n'
            'trust_level = "trusted"\n'
            f"{setup.LIMITS_END}\n",
            encoding="utf-8",
        )

        setup.apply_plan(self.codex_home, replace_conflicts=False)

        rendered = config_path.read_text(encoding="utf-8")
        self.assertNotIn(setup.LIMITS_START, rendered)
        self.assertNotIn(setup.LIMITS_END, rendered)
        self.assertEqual(rendered.count(setup.MANAGED_TOKEN), 3)
        with config_path.open("rb") as handle:
            config = tomllib.load(handle)
        self.assertEqual(config["projects"]["/tmp/example"]["trust_level"], "trusted")

    def test_engineering_preset_omits_all_delegation_control_assets(self) -> None:
        result = setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["engineering"],
        )

        self.assertEqual(result["capabilities"], list(setup.PRESETS["engineering"]))
        self.assertTrue((self.codex_home / "AGENTS.md").is_file())
        self.assertTrue(
            (self.codex_home / "rules" / "rootloom.rules").is_file()
        )
        self.assertFalse((self.codex_home / "config.toml").exists())
        self.assertFalse((self.codex_home / "agents").exists())
        self.assertFalse((self.codex_home / "high-assurance.config.toml").exists())

        policy = json.loads(
            (self.codex_home / setup.COMPONENT_POLICY_PATH).read_text(encoding="utf-8")
        )
        self.assertTrue(policy["hooks"]["project-guidance-hook"])
        self.assertFalse(policy["hooks"]["subagent-audit-hook"])

    def test_skills_only_preset_disables_both_hooks_without_global_assets(self) -> None:
        result = setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["skills-only"],
        )

        self.assertEqual(result["capabilities"], [])
        self.assertFalse((self.codex_home / "AGENTS.md").exists())
        self.assertFalse((self.codex_home / "config.toml").exists())
        self.assertFalse((self.codex_home / "rules").exists())
        policy = json.loads(
            (self.codex_home / setup.COMPONENT_POLICY_PATH).read_text(encoding="utf-8")
        )
        self.assertEqual(
            policy["hooks"],
            {
                "project-guidance-hook": False,
                "subagent-audit-hook": False,
            },
        )
        status = setup.status_payload(self.codex_home)
        self.assertEqual(status["capabilities"], [])
        self.assertEqual(status["components"], [])
        self.assertEqual(
            [item["path"] for item in status["actions"]],
            [setup.COMPONENT_POLICY_PATH],
        )

    def test_high_assurance_capability_closes_its_delegation_dependency(self) -> None:
        selected = setup.normalize_capabilities(("high-assurance",))
        self.assertEqual(selected, ("delegation-control", "high-assurance"))

        setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=selected,
        )

        self.assertTrue((self.codex_home / "config.toml").is_file())
        self.assertTrue((self.codex_home / "agents" / "evidence_explorer.toml").is_file())
        self.assertTrue((self.codex_home / "high-assurance.config.toml").is_file())
        self.assertFalse((self.codex_home / "AGENTS.md").exists())
        self.assertFalse((self.codex_home / "rules").exists())

    def test_capability_selection_change_requires_explicit_rollback(self) -> None:
        setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["guidance"],
        )

        with self.assertRaisesRegex(RuntimeError, "capability selection differs"):
            setup.apply_plan(
                self.codex_home,
                replace_conflicts=False,
                capabilities=setup.PRESETS["engineering"],
            )

        setup.rollback(self.codex_home)
        result = setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["engineering"],
        )
        self.assertEqual(result["status"], "applied")

    def test_rollback_all_unwinds_update_chain_before_layer_change(self) -> None:
        setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["guidance"],
        )
        original_guidance = (self.codex_home / "AGENTS.md").read_bytes()
        original_desired_bytes = setup.desired_bytes

        def updated_desired(*args: object, **kwargs: object) -> bytes:
            value = original_desired_bytes(*args, **kwargs)
            target = args[0]
            if isinstance(target, setup.Target) and target.relative_path == "AGENTS.md":
                return value + b"\n# simulated managed release update\n"
            return value

        with mock.patch.object(setup, "desired_bytes", side_effect=updated_desired):
            result = setup.apply_plan(
                self.codex_home,
                replace_conflicts=False,
                capabilities=setup.PRESETS["guidance"],
            )
        self.assertEqual(result["status"], "applied")
        self.assertNotEqual((self.codex_home / "AGENTS.md").read_bytes(), original_guidance)

        one_step = setup.rollback(self.codex_home)
        self.assertEqual(one_step["status"], "rolled_back_to_previous")
        self.assertEqual((self.codex_home / "AGENTS.md").read_bytes(), original_guidance)

        all_steps = setup.rollback_all(self.codex_home)
        self.assertEqual(all_steps["status"], "rolled_back_all")
        self.assertFalse((self.codex_home / "AGENTS.md").exists())
        self.assertFalse((self.codex_home / setup.COMPONENT_POLICY_PATH).exists())

        replacement = setup.apply_plan(
            self.codex_home,
            replace_conflicts=False,
            capabilities=setup.PRESETS["engineering"],
        )
        self.assertEqual(replacement["status"], "applied")


if __name__ == "__main__":
    unittest.main()

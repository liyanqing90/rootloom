from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO_ROOT
    / "plugins"
    / "rootloom"
    / "skills"
    / "seed-project-guidance"
    / "scripts"
    / "seed_project_guidance.py"
)
SPEC = importlib.util.spec_from_file_location("seed_project_guidance", SCRIPT)
assert SPEC and SPEC.loader
seeder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(seeder)


class ProjectGuidanceSeederTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(prefix="seeder-test-", dir=Path.home())
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name) / "sample-app"
        self.root.mkdir()

    def init_repo(self) -> Path:
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "README.md").write_text(
            "# Sample App\n\nA small service for testing evidence-backed project guidance.\n",
            encoding="utf-8",
        )
        (self.root / "package.json").write_text(
            json.dumps(
                {
                    "name": "sample-app",
                    "description": "A deterministic sample application.",
                    "packageManager": "pnpm@10.0.0",
                    "scripts": {
                        "test": "vitest run",
                        "lint": "eslint .",
                        "build": "vite build",
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        return self.root

    def test_probe_skips_non_repository(self) -> None:
        with tempfile.TemporaryDirectory(prefix="seeder-non-repo-") as temp_dir:
            result = seeder.probe(Path(temp_dir))
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "not_a_git_repository")

    def test_untrusted_repository_is_not_modified(self) -> None:
        self.init_repo()
        with mock.patch.object(seeder, "_trusted_project_roots", return_value=[]):
            result = seeder.seed(self.root)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "untrusted_project")
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_seed_is_evidence_backed_and_idempotent(self) -> None:
        self.init_repo()
        first = seeder.seed(self.root, allow_untrusted=True)
        self.assertEqual(first["status"], "created")
        guidance = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("A deterministic sample application.", guidance)
        self.assertIn("`pnpm run test`", guidance)
        self.assertIn("`pnpm run lint`", guidance)
        self.assertIn("`pnpm-lock.yaml`", guidance)
        self.assertIn("`src/`", guidance)

        second = seeder.seed(self.root, allow_untrusted=True)
        self.assertEqual(second["status"], "unchanged")
        self.assertEqual(guidance, (self.root / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertTrue(seeder.validate(self.root / "AGENTS.md")["valid"])

    def test_non_javascript_repository_does_not_invent_npm(self) -> None:
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "README.md").write_text(
            "# Python Utility\n\nA standard-library Python utility.\n",
            encoding="utf-8",
        )
        (self.root / "Makefile").write_text(
            "test:\n\tpython3 -m unittest\n",
            encoding="utf-8",
        )

        probe = seeder.probe(self.root)
        self.assertIsNone(probe["package_manager"])

        result = seeder.seed(self.root, allow_untrusted=True)
        self.assertEqual(result["status"], "created")
        guidance = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotIn("JavaScript package scripts", guidance)
        self.assertNotIn("Use `npm`", guidance)

    def test_readme_metadata_ignores_fenced_headings_and_reads_html_h1(self) -> None:
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        (self.root / "README.md").write_text(
            "<h1 align=\"center\">Real Project</h1>\n\n"
            "```markdown\n# Wrong Example Name\n```\n\n"
            "A real project description.\n",
            encoding="utf-8",
        )

        probe = seeder.probe(self.root)
        self.assertEqual(probe["name"], "Real Project")
        self.assertEqual(probe["description"], "A real project description.")

    def test_probe_rejects_evidence_symlinks_outside_repository(self) -> None:
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        workflows = self.root / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "outside.yml").symlink_to("/etc/hosts")
        outside_package = self.root.parent / "outside-package.json"
        outside_package.write_text(
            json.dumps({"name": "outside-name", "description": "outside evidence"}),
            encoding="utf-8",
        )
        (self.root / "package.json").symlink_to(outside_package)

        result = seeder.probe(self.root)

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["ci"], [])
        self.assertNotEqual(result["name"], "outside-name")
        self.assertNotIn("package.json", result["manifests"])

    def test_refresh_preserves_unmanaged_content(self) -> None:
        self.init_repo()
        seeder.seed(self.root, allow_untrusted=True)
        agents_path = self.root / "AGENTS.md"
        agents_path.write_text(
            agents_path.read_text(encoding="utf-8")
            + "\n## Project-specific invariants\n\n- `src/domain.ts` owns the domain state machine.\n",
            encoding="utf-8",
        )
        package = json.loads((self.root / "package.json").read_text(encoding="utf-8"))
        package["scripts"]["typecheck"] = "tsc --noEmit"
        (self.root / "package.json").write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")

        result = seeder.seed(self.root, allow_untrusted=True)
        self.assertEqual(result["status"], "updated")
        refreshed = agents_path.read_text(encoding="utf-8")
        self.assertIn("`pnpm run typecheck`", refreshed)
        self.assertIn("`src/domain.ts` owns the domain state machine", refreshed)
        self.assertTrue(seeder.validate(agents_path)["valid"])

    def test_refresh_refuses_concurrent_guidance_edit(self) -> None:
        self.init_repo()
        seeder.seed(self.root, allow_untrusted=True)
        agents_path = self.root / "AGENTS.md"
        package = json.loads((self.root / "package.json").read_text(encoding="utf-8"))
        package["scripts"]["typecheck"] = "tsc --noEmit"
        (self.root / "package.json").write_text(
            json.dumps(package, indent=2) + "\n",
            encoding="utf-8",
        )
        original_reader = seeder._read_guidance_bytes
        calls = 0

        def inject_edit(path: Path) -> bytes | None:
            nonlocal calls
            calls += 1
            value = original_reader(path)
            if calls == 2 and value is not None:
                value += b"\nCONCURRENT_USER_RULE\n"
                path.write_bytes(value)
            return value

        with mock.patch.object(seeder, "_read_guidance_bytes", side_effect=inject_edit):
            result = seeder.seed(self.root, allow_untrusted=True)

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "guidance_changed_during_seed")
        self.assertIn("CONCURRENT_USER_RULE", agents_path.read_text(encoding="utf-8"))

    def test_seed_skips_when_guidance_lock_is_busy(self) -> None:
        self.init_repo()
        with seeder.guidance_lock(self.root):
            result = seeder.seed(self.root, allow_untrusted=True)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "guidance_lock_busy")
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_existing_user_guidance_and_override_are_preserved(self) -> None:
        self.init_repo()
        agents_path = self.root / "AGENTS.md"
        agents_path.write_text("# Team rules\n\n- Run the team's checks.\n", encoding="utf-8")
        result = seeder.seed(self.root, allow_untrusted=True)
        self.assertEqual(result["reason"], "user_owned_guidance")
        self.assertEqual(agents_path.read_text(encoding="utf-8"), "# Team rules\n\n- Run the team's checks.\n")

        agents_path.unlink()
        (self.root / "AGENTS.override.md").write_text("# Override\n", encoding="utf-8")
        result = seeder.seed(self.root, allow_untrusted=True)
        self.assertEqual(result["reason"], "override_exists")
        self.assertFalse(agents_path.exists())

    def test_nested_module_requires_real_boundary(self) -> None:
        self.init_repo()
        module = self.root / "packages" / "api"
        module.mkdir(parents=True)
        (module / "pyproject.toml").write_text(
            "[project]\nname = 'sample-api'\ndescription = 'API module'\n[tool.pytest.ini_options]\n",
            encoding="utf-8",
        )
        probe = seeder.probe(self.root)
        self.assertIn("packages/api/", [item["path"] for item in probe["module_candidates"]])

        result = seeder.seed(self.root, Path("packages/api"), allow_untrusted=True)
        self.assertEqual(result["status"], "created")
        nested = module / "AGENTS.md"
        self.assertIn("applies only under `packages/api/`", nested.read_text(encoding="utf-8"))
        self.assertTrue(seeder.validate(nested)["valid"])

        invalid_target = self.root / "src"
        result = seeder.seed(self.root, invalid_target, allow_untrusted=True)
        self.assertEqual(result["reason"], "not_a_module_boundary")

    def test_hook_injects_new_guidance_but_plan_mode_does_not_write(self) -> None:
        self.init_repo()
        previous = os.environ.get("ROOTLOOM_ALLOW_UNTRUSTED")
        os.environ["ROOTLOOM_ALLOW_UNTRUSTED"] = "1"
        self.addCleanup(self._restore_env, previous)

        output = seeder._hook_output(
            {
                "source": "startup",
                "permission_mode": "default",
                "cwd": str(self.root),
            }
        )
        self.assertIsNotNone(output)
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("<seeded_project_guidance>", context)
        self.assertTrue((self.root / "AGENTS.md").exists())

        (self.root / "AGENTS.md").unlink()
        output = seeder._hook_output(
            {
                "source": "startup",
                "permission_mode": "plan",
                "cwd": str(self.root),
            }
        )
        self.assertIsNone(output)
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_validation_detects_managed_drift_and_secrets(self) -> None:
        self.init_repo()
        seeder.seed(self.root, allow_untrusted=True)
        agents_path = self.root / "AGENTS.md"
        content = agents_path.read_text(encoding="utf-8").replace("pnpm run test", "npm run invented")
        agents_path.write_text(content, encoding="utf-8")
        result = seeder.validate(agents_path)
        self.assertIn("managed_block_drift", result["errors"])

        agents_path.write_text(content + "\n- sk-abcdefghijklmnop123456789\n", encoding="utf-8")
        result = seeder.validate(agents_path)
        self.assertIn("secret_like_content_detected", result["errors"])

    @staticmethod
    def _restore_env(previous: str | None) -> None:
        if previous is None:
            os.environ.pop("ROOTLOOM_ALLOW_UNTRUSTED", None)
        else:
            os.environ["ROOTLOOM_ALLOW_UNTRUSTED"] = previous


if __name__ == "__main__":
    unittest.main()

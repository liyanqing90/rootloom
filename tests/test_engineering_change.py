from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO_ROOT
    / "plugins"
    / "rootloom"
    / "skills"
    / "engineering-change"
    / "scripts"
    / "finalize_change.py"
)
ANALYZE = SCRIPT.parent / "analyze_change.py"
PROJECT_MEMORY = (
    REPO_ROOT
    / "plugins"
    / "rootloom"
    / "skills"
    / "project-memory"
    / "scripts"
    / "project_memory.py"
)
sys.path.insert(0, str(SCRIPT.parent))
from runner.verification import split_command, verify


class EngineeringChangeTests(unittest.TestCase):
    def test_windows_command_split_preserves_backslash_paths_and_outer_quotes(self) -> None:
        raw = r"C:\hostedtoolcache\Python\python.exe -c 'assert 2 == 2'"
        self.assertEqual(
            split_command(raw, windows=True),
            [r"C:\hostedtoolcache\Python\python.exe", "-c", "assert 2 == 2"],
        )
        nested = r'''C:\hostedtoolcache\Python\python.exe -c '__import__("pathlib").Path(".env").unlink()' '''.strip()
        self.assertEqual(
            split_command(nested, windows=True),
            [
                r"C:\hostedtoolcache\Python\python.exe",
                "-c",
                '__import__("pathlib").Path(".env").unlink()',
            ],
        )

    def test_verification_output_budget_is_aggregate_and_strict(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            repo = self.make_repo(Path(temporary))
            first = f"{sys.executable} -c 'print(\"a\")'"
            second = f"{sys.executable} -c 'print(\"b\")'"
            first_chunk_size = len(f"$ {first}\n".encode("utf-8")) + 2
            budget = first_chunk_size + 6
            results, log = verify(
                [first, second],
                repo=repo,
                timeout=30,
                max_output_bytes=budget,
            )
            self.assertEqual(results[0].exit_code, 0)
            self.assertEqual(results[1].exit_code, 125)
            self.assertLessEqual(len(log), budget)

            noisy = f"{sys.executable} -c 'print(\"x\" * 1000)'"
            noisy_budget = len(f"$ {noisy}\n".encode("utf-8")) + 32
            noisy_results, noisy_log = verify(
                [noisy],
                repo=repo,
                timeout=30,
                max_output_bytes=noisy_budget,
            )
            self.assertEqual(noisy_results[0].exit_code, 125)
            self.assertLessEqual(len(noisy_log), noisy_budget)

    def test_missing_verification_executable_is_a_bounded_failed_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    "--verify",
                    "rootloom-command-that-does-not-exist",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr)
            summary = json.loads(
                (root / "run" / "summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(summary["tests"][0]["exit_code"], 126)
            self.assertFalse(summary["passed"])
            self.assertIn(
                "command could not run",
                (root / "run" / "test.log").read_text(encoding="utf-8"),
            )

    def make_repo(self, root: Path) -> Path:
        repo = root / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        (repo / "app.py").write_text("value = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)
        return repo

    def analyze(self, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ANALYZE), "--repo", str(repo), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_analyzer_keeps_docs_auth_reference_low_risk(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            repo = self.make_repo(Path(temporary))
            completed = self.analyze(
                repo,
                "--task",
                "Document the authentication flow",
                "--path",
                "docs/auth.md",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            assessment = json.loads(completed.stdout)
            self.assertEqual(assessment["detected_risk"], "low")
            self.assertEqual(assessment["minimum_tier"], 0)
            self.assertEqual(
                [item["id"] for item in assessment["signals"]],
                ["docs-or-tests-only"],
            )

    def test_analyzer_promotes_auth_source_and_explains_verification(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            repo = self.make_repo(Path(temporary))
            completed = self.analyze(
                repo,
                "--task",
                "Change login token validation",
                "--path",
                "src/auth/token.py",
                "--declared-risk",
                "low",
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            assessment = json.loads(completed.stdout)
            self.assertEqual(assessment["effective_risk"], "high")
            self.assertEqual(assessment["minimum_tier"], 2)
            self.assertTrue(assessment["risk_was_raised"])
            signal_ids = {item["id"] for item in assessment["signals"]}
            self.assertIn("authentication", signal_ids)
            behavior_ids = {
                item["id"]
                for item in assessment["verification_plan"]["required_behaviors"]
            }
            self.assertIn("auth-boundaries", behavior_ids)
            self.assertEqual(
                assessment["verification_plan"]["status"],
                "suggested-not-executed",
            )

    def test_analyzer_can_classify_a_high_risk_task_before_paths_are_known(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            repo = self.make_repo(Path(temporary))
            completed = self.analyze(repo, "--task", "新增数据库迁移并回填历史数据")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            assessment = json.loads(completed.stdout)
            self.assertEqual(assessment["detected_risk"], "high")
            self.assertEqual(assessment["minimum_tier"], 2)
            self.assertEqual(assessment["confidence"], "medium")
            behavior_ids = {
                item["id"]
                for item in assessment["verification_plan"]["required_behaviors"]
            }
            self.assertIn("primary-behavior", behavior_ids)
            self.assertIn("data-compatibility", behavior_ids)
            self.assertNotIn("documentation-contract", behavior_ids)

    def test_analyzer_ignores_unchanged_diff_context_and_detects_workflows(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            repo = self.make_repo(Path(temporary))
            service = repo / "service.py"
            service.write_text("AUTHENTICATION_ENABLED = True\nvalue = 1\n", encoding="utf-8")
            subprocess.run(["git", "add", "service.py"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "service"], cwd=repo, check=True)
            service.write_text("AUTHENTICATION_ENABLED = True\nvalue = 2\n", encoding="utf-8")
            completed = self.analyze(repo)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            assessment = json.loads(completed.stdout)
            self.assertEqual(assessment["detected_risk"], "medium")
            self.assertNotIn(
                "authentication",
                {item["id"] for item in assessment["signals"]},
            )

            subprocess.run(["git", "restore", "service.py"], cwd=repo, check=True)
            workflow = self.analyze(repo, "--path", ".github/workflows/ci.yml")
            self.assertEqual(workflow.returncode, 0, workflow.stderr)
            workflow_assessment = json.loads(workflow.stdout)
            self.assertEqual(workflow_assessment["detected_risk"], "high")
            self.assertIn(
                "infrastructure",
                {item["id"] for item in workflow_assessment["signals"]},
            )

    def test_analyzer_does_not_treat_rule_strings_as_domain_code(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            repo = self.make_repo(Path(temporary))
            rules = repo / "rules.py"
            rules.write_text("SIGNALS = set()\nTOKEN = None\n", encoding="utf-8")
            subprocess.run(["git", "add", "rules.py"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "rules"], cwd=repo, check=True)
            rules.write_text(
                (
                    'SIGNALS = {"auth", "money", "database", "lock", "state-machine"}\n'
                    'TOKEN = compile_pattern()\n'
                ),
                encoding="utf-8",
            )
            completed = self.analyze(repo)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            assessment = json.loads(completed.stdout)
            self.assertEqual(assessment["detected_risk"], "medium")
            self.assertEqual(
                {item["id"] for item in assessment["signals"]},
                {"behavioral-code"},
            )

    def test_analyzer_loads_active_memory_but_not_expired_memory_as_risk(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            repo = self.make_repo(Path(temporary))
            memory = repo / ".project-memory"
            memory.mkdir()
            collection = {
                "format": "rootloom-project-memory-v1",
                "kind": "risks",
                "entries": [
                    {
                        "id": "risk-active",
                        "date": "2026-01-01",
                        "summary": "relay reconnect ordering",
                        "mitigation": "check lifecycle transitions",
                        "paths": ["src/relay.py"],
                    },
                    {
                        "id": "risk-expired",
                        "date": "2025-01-01",
                        "summary": "retired relay transport",
                        "mitigation": "none",
                        "paths": ["src/relay.py"],
                        "expires": "2025-12-31",
                    },
                ],
            }
            (memory / "known-risks.json").write_text(json.dumps(collection), encoding="utf-8")
            completed = self.analyze(repo, "--path", "src/relay.py")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            assessment = json.loads(completed.stdout)
            self.assertEqual(
                [item["id"] for item in assessment["memory"]["matches"]],
                ["risk-active"],
            )
            self.assertEqual(
                [item["id"] for item in assessment["memory"]["stale"]],
                ["risk-expired"],
            )
            self.assertEqual(assessment["detected_risk"], "medium")

    def test_legacy_memory_identity_matches_the_memory_cli(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            repo = self.make_repo(Path(temporary))
            memory = repo / ".project-memory"
            memory.mkdir()
            collection = {
                "format": "rootloom-project-memory-v1",
                "kind": "failures",
                "entries": [
                    {
                        "date": "2026-01-01",
                        "summary": "relay reconnect race",
                        "root_cause": "transition ordering",
                        "fix": "serialize transitions",
                        "paths": ["src/relay.py"],
                    }
                ],
            }
            (memory / "failures.json").write_text(json.dumps(collection), encoding="utf-8")
            analyzed = self.analyze(repo, "--path", "src/relay.py")
            self.assertEqual(analyzed.returncode, 0, analyzed.stderr)
            analyzer_id = json.loads(analyzed.stdout)["memory"]["matches"][0]["id"]
            context = subprocess.run(
                [
                    sys.executable,
                    str(PROJECT_MEMORY),
                    "--repo",
                    str(repo),
                    "context",
                    "--path",
                    "src/relay.py",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(context.returncode, 0, context.stderr)
            memory_id = json.loads(context.stdout)["failures"][0]["id"]
            self.assertEqual(analyzer_id, memory_id)

    def test_matching_docs_memory_does_not_promote_a_docs_only_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            repo = self.make_repo(Path(temporary))
            memory = repo / ".project-memory"
            memory.mkdir()
            collection = {
                "format": "rootloom-project-memory-v1",
                "kind": "decisions",
                "entries": [
                    {
                        "id": "decision-auth-docs",
                        "date": "2026-01-01",
                        "summary": "document token boundary",
                        "record": "docs/auth.md",
                        "paths": ["docs/auth.md"],
                    }
                ],
            }
            (memory / "decisions.json").write_text(json.dumps(collection), encoding="utf-8")
            subprocess.run(["git", "add", ".project-memory/decisions.json"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "memory"], cwd=repo, check=True)
            completed = self.analyze(repo, "--path", "docs/auth.md")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            assessment = json.loads(completed.stdout)
            self.assertEqual(assessment["detected_risk"], "low")
            self.assertEqual(
                [item["id"] for item in assessment["memory"]["matches"]],
                ["decision-auth-docs"],
            )
            self.assertNotIn(
                "project-memory",
                {item["id"] for item in assessment["signals"]},
            )

    @unittest.skipIf(os.name == "nt", "symlink creation is not portable on Windows CI")
    def test_analyzer_warns_without_reading_symlinked_memory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            outside = root / "outside"
            outside.mkdir()
            (outside / "known-risks.json").write_text(
                '{"format":"rootloom-project-memory-v1","kind":"risks","entries":[]}',
                encoding="utf-8",
            )
            (repo / ".project-memory").symlink_to(outside, target_is_directory=True)
            completed = self.analyze(repo, "--path", "src/relay.py")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            assessment = json.loads(completed.stdout)
            self.assertEqual(assessment["memory"]["matches"], [])
            self.assertEqual(
                assessment["memory"]["warnings"],
                ["ignored symlinked .project-memory directory"],
            )

    def test_writes_compact_summary_and_verification_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            output = root / "run"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(output),
                    "--risk",
                    "low",
                    "--verify",
                    f"{sys.executable} -c 'assert 2 == 2'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["passed"])
            self.assertEqual(summary["changed_files"], ["app.py"])
            self.assertEqual(summary["risk"], "medium")
            self.assertTrue(summary["risk_assessment"]["risk_was_raised"])
            self.assertEqual(
                summary["verification_plan"]["status"],
                "suggested-not-executed",
            )
            self.assertIn(b"value = 2", (output / "diff.patch").read_bytes())
            self.assertIn("assert 2 == 2", (output / "test.log").read_text(encoding="utf-8"))

    def test_finalizer_refuses_in_repository_output_and_oversized_patch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            inside = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(repo / "run"),
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(inside.returncode, 0)
            self.assertIn("outside the repository", inside.stderr)
            self.assertFalse((repo / "run").exists())

            oversized = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    "--max-patch-bytes",
                    "1",
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(oversized.returncode, 0)
            self.assertIn("tracked patch exceeds", oversized.stderr)
            self.assertFalse((root / "run").exists())

    def test_finalizer_auto_risk_and_manual_high_risk_are_not_lowered(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            readme = repo / "README.md"
            readme.write_text("before\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "docs"], cwd=repo, check=True)
            readme.write_text("after\n", encoding="utf-8")

            automatic = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "automatic"),
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(automatic.returncode, 0, automatic.stderr)
            auto_summary = json.loads(
                (root / "automatic" / "summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(auto_summary["risk"], "low")
            self.assertIsNone(auto_summary["risk_assessment"]["declared_risk"])

            manual = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "manual"),
                    "--risk",
                    "high",
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(manual.returncode, 0, manual.stderr)
            manual_summary = json.loads(
                (root / "manual" / "summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manual_summary["risk"], "high")
            self.assertFalse(manual_summary["risk_assessment"]["risk_was_raised"])

    def test_sensitive_deletion_requires_exact_confirmation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            secret = repo / ".env"
            secret.write_text("TOKEN=redacted\n", encoding="utf-8")
            subprocess.run(["git", "add", ".env"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "env"], cwd=repo, check=True)
            secret.unlink()
            base = [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(repo),
                "--output",
                str(root / "run"),
                "--risk",
                "high",
                "--verify",
                f"{sys.executable} -c 'assert not __import__(\"pathlib\").Path(\".env\").exists()'",
            ]
            refused = subprocess.run(base, capture_output=True, text=True, check=False)
            self.assertEqual(refused.returncode, 10)
            self.assertIn(".env", refused.stdout)
            accepted = subprocess.run(
                [*base, "--confirm-dangerous-delete", ".env"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)

    def test_sensitive_rename_guards_the_original_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            secret = repo / ".env"
            secret.write_text("TOKEN=redacted\n", encoding="utf-8")
            subprocess.run(["git", "add", ".env"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "env"], cwd=repo, check=True)
            secret.rename(repo / "config.txt")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    "--risk",
                    "high",
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 10)
            self.assertIn(".env", completed.stdout)

    def test_verification_cannot_hide_a_sensitive_deletion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            secret = repo / ".env"
            secret.write_text("TOKEN=redacted\n", encoding="utf-8")
            subprocess.run(["git", "add", ".env"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "env"], cwd=repo, check=True)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    "--risk",
                    "high",
                    "--verify",
                    (
                        f"{sys.executable} -c "
                        "'__import__(\"pathlib\").Path(\".env\").unlink()'"
                    ),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 10)
            self.assertIn("verification introduced dangerous deletions", completed.stdout)
            self.assertFalse((root / "run" / "summary.json").exists())

    def test_verification_cannot_delete_an_untracked_sensitive_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            (repo / ".env").write_text("TOKEN=redacted\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    "--risk",
                    "high",
                    "--verify",
                    (
                        f"{sys.executable} -c "
                        "'__import__(\"pathlib\").Path(\".env\").unlink()'"
                    ),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 10)
            self.assertIn("verification introduced dangerous deletions", completed.stdout)

    def test_verification_worktree_mutation_marks_bundle_failed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            output = root / "run"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(output),
                    "--risk",
                    "medium",
                    "--verify",
                    (
                        f"{sys.executable} -c "
                        "'__import__(\"pathlib\").Path(\"app.py\").write_text(\"value = 2\\n\")'"
                    ),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertFalse(summary["passed"])
            self.assertFalse(summary["verification_preserved_capture"])
            self.assertEqual(summary["changed_files"], ["app.py"])
            self.assertIn(b"value = 2", (output / "diff.patch").read_bytes())
            self.assertIn(
                "verification changed the tracked patch or captured path set",
                (output / "test.log").read_text(encoding="utf-8"),
            )

    def test_unborn_repository_writes_a_bundle_without_head(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / "app.py").write_text("value = 1\n", encoding="utf-8")
            output = root / "run"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(output),
                    "--risk",
                    "low",
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["passed"])
            self.assertTrue(summary["verification_preserved_capture"])
            self.assertEqual(summary["changed_files"], ["app.py"])
            self.assertIn(b"# app.py", (output / "diff.patch").read_bytes())

    def test_invalid_detached_head_is_not_treated_as_an_unborn_branch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            (repo / ".git" / "HEAD").write_text("0" * 40 + "\n", encoding="ascii")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    "--risk",
                    "low",
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("bad object HEAD", completed.stderr)
            self.assertFalse((root / "run" / "summary.json").exists())

    def test_no_verification_is_not_reported_as_passed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            output = root / "run"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(output),
                    "--risk",
                    "low",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertFalse(summary["passed"])


if __name__ == "__main__":
    unittest.main()

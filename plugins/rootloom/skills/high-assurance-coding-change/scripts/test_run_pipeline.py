#!/usr/bin/env python3
"""Focused regression tests for the high-assurance runner's local gates."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).with_name("run_pipeline.py")
SPEC = importlib.util.spec_from_file_location("high_assurance_runner", MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, stdout=subprocess.DEVNULL)


class RunnerGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        (self.repo / "a.txt").write_text("baseline\n", encoding="utf-8")
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-qm", "baseline")
        self.run_dir = self.root / "artifacts"
        self.run_dir.mkdir(mode=0o700)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_allowed_paths_are_exact_or_recursive(self) -> None:
        rules = runner.normalize_allowed_paths(["src/app.py", "tests/**"])
        self.assertTrue(runner.path_is_allowed("src/app.py", rules))
        self.assertTrue(runner.path_is_allowed("tests/unit/test_app.py", rules))
        self.assertFalse(runner.path_is_allowed("src/other.py", rules))
        for unsafe in ("../secret", ".git/config", "/tmp/file", "src/*.py"):
            with self.subTest(unsafe=unsafe), self.assertRaises(runner.PipelineError):
                runner.normalize_allowed_paths([unsafe])

    def test_semantic_gates_reject_contradictions(self) -> None:
        diagnosis = {
            "decision": "GO",
            "root_cause": "cause",
            "violated_invariant": "invariant",
            "change_contract": {
                "allowed_paths": [],
                "allowed_behavior": ["fix"],
                "acceptance_criteria": ["test passes"],
            },
            "required_tests": ["test"],
        }
        with self.assertRaises(runner.PipelineError):
            runner.validate_diagnosis(diagnosis)

        review = {
            "verdict": "PASS",
            "findings": [{"severity": "HIGH"}],
            "contract_compliance": ["claimed"],
            "test_adequacy": "claimed",
        }
        with self.assertRaises(runner.PipelineError):
            runner.validate_review(review)

    def test_evidence_requires_attributable_provenance(self) -> None:
        with self.assertRaises(runner.PipelineError):
            runner.validate_evidence({"reproduction": {}, "evidence_provenance": {}})
        with self.assertRaises(runner.PipelineError):
            runner.validate_evidence({"reproduction": {}, "evidence_provenance": []})
        with self.assertRaises(runner.PipelineError):
            runner.validate_evidence(
                {
                    "observed_facts": [
                        {
                            "id": "fact-1",
                            "statement": "failure observed",
                            "provenance_ids": ["missing-source"],
                        }
                    ],
                    "reproduction": {
                        "status": "not_reproduced",
                        "evidence_ids": [],
                    },
                    "hypotheses": [],
                    "evidence_provenance": [
                        {
                            "id": "source-1",
                            "claim": "failure observed",
                            "kind": "fact",
                            "source_environment": "focused test / local",
                            "observed_at": "2026-07-12",
                            "reference": "tests/test_failure.py",
                            "freshness_redaction": "fresh",
                        }
                    ],
                }
            )

        valid = {
            "observed_facts": [
                {
                    "id": "fact-1",
                    "statement": "failure observed",
                    "provenance_ids": ["source-1"],
                }
            ],
            "evidence_provenance": [
                {
                    "id": "source-1",
                    "claim": "failure observed",
                    "kind": "fact",
                    "source_environment": "focused test / local",
                    "observed_at": "2026-07-12",
                    "reference": "tests/test_failure.py",
                    "freshness_redaction": "fresh",
                }
            ],
            "reproduction": {
                "status": "reproduced",
                "evidence_ids": ["source-1"],
            },
            "hypotheses": [
                {
                    "hypothesis": "owner invariant failed",
                    "supporting_provenance_ids": ["source-1"],
                    "contradicting_provenance_ids": [],
                }
            ],
        }
        runner.validate_evidence(valid)

    def test_go_diagnosis_requires_invariant_verification_map(self) -> None:
        diagnosis = {
            "decision": "GO",
            "root_cause": "cause",
            "violated_invariant": "invariant",
            "change_contract": {
                "allowed_paths": ["a.txt"],
                "allowed_behavior": ["fix"],
                "acceptance_criteria": ["test passes"],
            },
            "required_tests": ["test"],
        }
        with self.assertRaises(runner.PipelineError):
            runner.validate_diagnosis(diagnosis)

        diagnosis["verification_map"] = {
            "original_failure_path": {
                "requirement": "reproduce and fix the original failure",
                "command_ids": ["verify-1"],
            },
            "owning_boundary_invariant": {
                "requirement": "assert the owning invariant",
                "command_ids": ["verify-1"],
            },
            "adjacent_negative_or_alternate_path": {
                "requirement": "cover an adjacent path",
                "command_ids": ["verify-missing"],
            },
        }
        with self.assertRaises(runner.PipelineError):
            runner.validate_diagnosis(diagnosis, {"verify-0", "verify-1"})
        diagnosis["verification_map"]["adjacent_negative_or_alternate_path"][
            "command_ids"
        ] = ["verify-0"]
        runner.validate_diagnosis(diagnosis, {"verify-0", "verify-1"})
        for item in diagnosis["verification_map"].values():
            item["command_ids"] = ["verify-0"]
        with self.assertRaises(runner.PipelineError) as caught:
            runner.validate_diagnosis(diagnosis, {"verify-0", "verify-1"})
        self.assertIn("user-supplied behavior command", str(caught.exception))

    def test_completed_report_must_match_actual_delta_and_have_no_deviation(self) -> None:
        rules = runner.normalize_allowed_paths(["a.txt"])
        report = {
            "status": "completed",
            "files_changed": ["a.txt"],
            "behavioral_change": "fixed",
            "deviations": ["also changed something"],
        }
        with self.assertRaises(runner.PipelineError):
            runner.validate_implementation(report, rules, {"a.txt"})
        report["deviations"] = []
        with self.assertRaises(runner.PipelineError):
            runner.validate_implementation(report, rules, {"a.txt", "other.txt"})

    def test_full_state_detects_staged_untracked_and_dirty_baseline_changes(self) -> None:
        baseline = runner.capture_repo_state(self.repo)
        (self.repo / "a.txt").write_text("staged\n", encoding="utf-8")
        git(self.repo, "add", "a.txt")
        (self.repo / "new.bin").write_bytes(b"\x00\x01")
        current = runner.capture_repo_state(self.repo)
        self.assertEqual(
            runner.changed_paths_between(baseline, current),
            {"a.txt", "new.bin"},
        )
        with self.assertRaises(runner.PipelineError) as caught:
            runner.enforce_repository_contract(
                repo=self.repo,
                run_dir=self.run_dir,
                prefix="delta",
                baseline=baseline,
                allowed_rules=runner.normalize_allowed_paths(["a.txt", "new.bin"]),
            )
        self.assertEqual(caught.exception.exit_code, 6)

        git(self.repo, "reset", "-q", "HEAD", "--", "a.txt")
        (self.repo / "a.txt").write_text("dirty baseline\n", encoding="utf-8")
        (self.repo / "new.bin").unlink()
        dirty_baseline = runner.capture_repo_state(self.repo)
        (self.repo / "a.txt").write_text("pipeline changed dirty file\n", encoding="utf-8")
        self.assertEqual(
            runner.changed_paths_between(dirty_baseline, runner.capture_repo_state(self.repo)),
            {"a.txt"},
        )

    def test_out_of_contract_untracked_file_is_a_hard_failure(self) -> None:
        baseline = runner.capture_repo_state(self.repo)
        (self.repo / "surprise.txt").write_text("unexpected\n", encoding="utf-8")
        with self.assertRaises(runner.PipelineError) as caught:
            runner.enforce_repository_contract(
                repo=self.repo,
                run_dir=self.run_dir,
                prefix="scope",
                baseline=baseline,
                allowed_rules=runner.normalize_allowed_paths(["a.txt"]),
            )
        self.assertEqual(caught.exception.exit_code, 6)

    def test_scope_gate_precedes_delta_capture(self) -> None:
        baseline = runner.capture_repo_state(self.repo)
        (self.repo / "outside.txt").write_text("do not capture\n", encoding="utf-8")
        with mock.patch.object(runner, "capture_delta") as capture:
            with self.assertRaises(runner.PipelineError):
                runner.enforce_repository_contract(
                    repo=self.repo,
                    run_dir=self.run_dir,
                    prefix="scope-first",
                    baseline=baseline,
                    allowed_rules=runner.normalize_allowed_paths(["a.txt"]),
                )
        capture.assert_not_called()

    def test_ignored_files_and_head_changes_are_in_the_snapshot(self) -> None:
        (self.repo / ".gitignore").write_text("ignored.log\n", encoding="utf-8")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-qm", "add ignore rule")
        baseline = runner.capture_repo_state(self.repo)

        (self.repo / "ignored.log").write_text("hidden mutation\n", encoding="utf-8")
        current = runner.capture_repo_state(self.repo)
        self.assertEqual(runner.changed_paths_between(baseline, current), {"ignored.log"})
        with self.assertRaises(runner.PipelineError):
            runner.assert_repo_unchanged(baseline, current, "ignored-file reader")

        (self.repo / "ignored.log").unlink()
        clean_again = runner.capture_repo_state(self.repo)
        git(self.repo, "commit", "--allow-empty", "-qm", "empty metadata mutation")
        after_commit = runner.capture_repo_state(self.repo)
        self.assertEqual(runner.changed_paths_between(clean_again, after_commit), set())
        with self.assertRaises(runner.PipelineError):
            runner.assert_repo_unchanged(clean_again, after_commit, "empty commit")

        control_baseline = runner.capture_repo_state(self.repo)
        hook = self.repo / ".git" / "hooks" / "codex-test"
        hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        with self.assertRaises(runner.PipelineError):
            runner.assert_repo_unchanged(
                control_baseline,
                runner.capture_repo_state(self.repo),
                "hook mutation",
            )

    def test_ignored_files_use_metadata_without_content_hashing(self) -> None:
        (self.repo / ".gitignore").write_text("ignored.bin\n", encoding="utf-8")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-qm", "ignore generated binary")
        ignored = self.repo / "ignored.bin"
        ignored.write_bytes(b"x" * 1024 * 1024)
        original = runner.file_fingerprint

        def reject_ignored_content(path: Path) -> dict[str, object]:
            if path == ignored:
                raise AssertionError("ignored file content was hashed")
            return original(path)

        with mock.patch.object(runner, "file_fingerprint", side_effect=reject_ignored_content):
            state = runner.capture_repo_state(self.repo)

        self.assertEqual(state["worktree"]["ignored.bin"]["kind"], "file-metadata")

    def test_delta_never_reads_or_emits_ignored_content(self) -> None:
        (self.repo / ".gitignore").write_text(".env\n", encoding="utf-8")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-qm", "ignore local environment")
        baseline = runner.capture_repo_state(self.repo)
        marker = "ROOTLOOM_SECRET_MUST_NOT_LEAVE_FILE_91f7"
        ignored = self.repo / ".env"
        ignored.write_text(f"TOKEN={marker}\n", encoding="utf-8")

        original_fingerprint = runner.file_fingerprint

        def reject_content_read(path: Path) -> dict[str, object]:
            if path == ignored:
                raise AssertionError("ignored content fingerprint attempted")
            return original_fingerprint(path)

        with (
            mock.patch.object(
                runner,
                "file_fingerprint",
                side_effect=reject_content_read,
            ),
            mock.patch.object(
                runner,
                "untracked_patch",
                wraps=runner.untracked_patch,
            ) as patch_capture,
        ):
            delta, _ = runner.enforce_repository_contract(
                repo=self.repo,
                run_dir=self.run_dir,
                prefix="ignored-safe",
                baseline=baseline,
                allowed_rules=runner.normalize_allowed_paths([".env"]),
            )

        patch_capture.assert_called_once_with(self.repo, [])
        self.assertEqual(delta["ignored_metadata"][0]["path"], ".env")
        self.assertEqual(delta["untracked_patch"], "")
        for artifact in self.run_dir.iterdir():
            self.assertNotIn(marker, artifact.read_text(encoding="utf-8"))
        self.assertNotIn(marker, runner.compact_delta(delta))

    def test_sensitive_visible_untracked_content_is_redacted(self) -> None:
        baseline = runner.capture_repo_state(self.repo)
        marker = "VISIBLE_SECRET_127d"
        sensitive = self.repo / ".env.local"
        sensitive.write_text(marker, encoding="utf-8")
        original_fingerprint = runner.file_fingerprint

        def reject_sensitive_content(path: Path) -> dict[str, object]:
            if path == sensitive:
                raise AssertionError("sensitive untracked content was hashed")
            return original_fingerprint(path)

        with mock.patch.object(
            runner,
            "file_fingerprint",
            side_effect=reject_sensitive_content,
        ):
            delta, state = runner.enforce_repository_contract(
                repo=self.repo,
                run_dir=self.run_dir,
                prefix="redacted",
                baseline=baseline,
                allowed_rules=runner.normalize_allowed_paths([".env.local"]),
            )
        self.assertEqual(delta["visible_untracked"], [])
        redacted = delta["redacted_untracked_metadata"][0]
        self.assertEqual(redacted["path"], ".env.local")
        self.assertEqual(redacted["kind"], "file-metadata")
        self.assertNotIn("sha256", redacted)
        self.assertEqual(state["worktree"][".env.local"]["kind"], "file-metadata")
        self.assertNotIn("sha256", state["worktree"][".env.local"])
        self.assertNotIn(marker, runner.compact_delta(delta))

    def test_known_custom_and_dotfile_sensitive_paths_are_metadata_only(self) -> None:
        known_paths = (
            ".npmrc",
            ".pypirc",
            ".netrc",
            ".git-credentials",
            ".docker/config.json",
            ".kube/config",
            "kubeconfig",
            "auth.json",
            "service-account.json",
        )
        for path in known_paths:
            with self.subTest(path=path):
                self.assertTrue(runner.is_sensitive_repo_path(path))

        npmrc = self.repo / ".npmrc"
        npmrc.write_text("//registry.example/:_authToken=secret", encoding="utf-8")
        known_state = runner.capture_repo_state(self.repo)
        self.assertIn(".npmrc", known_state["sensitive_untracked_paths"])
        self.assertEqual(known_state["worktree"][".npmrc"]["kind"], "file-metadata")
        self.assertNotIn("sha256", known_state["worktree"][".npmrc"])

        custom = self.repo / "private" / "runtime.conf"
        custom.parent.mkdir()
        custom.write_text("custom-secret", encoding="utf-8")
        dotfile = self.repo / "config" / ".customrc"
        dotfile.parent.mkdir()
        dotfile.write_text("dot-secret", encoding="utf-8")
        rules = runner.normalize_sensitive_paths(["private/**"])
        state = runner.capture_repo_state(
            self.repo,
            sensitive_rules=rules,
            redact_untracked_dotfiles=True,
        )
        for path in ("private/runtime.conf", "config/.customrc"):
            with self.subTest(path=path):
                self.assertIn(path, state["sensitive_untracked_paths"])
                self.assertEqual(state["worktree"][path]["kind"], "file-metadata")
                self.assertNotIn("sha256", state["worktree"][path])

    def test_ordinary_visible_untracked_file_retains_content_patch(self) -> None:
        baseline = runner.capture_repo_state(self.repo)
        marker = "ordinary-visible-content-41c2"
        (self.repo / "ordinary.txt").write_text(marker, encoding="utf-8")
        delta, state = runner.enforce_repository_contract(
            repo=self.repo,
            run_dir=self.run_dir,
            prefix="ordinary",
            baseline=baseline,
            allowed_rules=runner.normalize_allowed_paths(["ordinary.txt"]),
        )
        self.assertEqual(state["worktree"]["ordinary.txt"]["kind"], "file")
        self.assertIn("sha256", state["worktree"]["ordinary.txt"])
        self.assertIn(marker, delta["untracked_patch"])

    def test_ignored_path_budget_fails_closed(self) -> None:
        (self.repo / ".gitignore").write_text("cache/\n", encoding="utf-8")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-qm", "ignore cache")
        cache = self.repo / "cache"
        cache.mkdir()
        for index in range(3):
            (cache / f"{index}.tmp").write_text("x", encoding="utf-8")
        with self.assertRaises(runner.PipelineError) as caught:
            runner.capture_repo_state(self.repo, max_ignored_paths=2)
        self.assertEqual(caught.exception.exit_code, 9)
        self.assertIn("budget exceeded", str(caught.exception))

    def test_verification_coverage_requires_successful_machine_records(self) -> None:
        diagnosis = {
            "verification_map": {
                field: {"requirement": field, "command_ids": ["verify-1"]}
                for field in (
                    "original_failure_path",
                    "owning_boundary_invariant",
                    "adjacent_negative_or_alternate_path",
                )
            }
        }
        with self.assertRaises(runner.PipelineError):
            runner.validate_verification_coverage(diagnosis, [])
        with self.assertRaises(runner.PipelineError):
            runner.validate_verification_coverage(
                diagnosis,
                [{"id": "verify-1", "exit_code": 1}],
            )
        runner.validate_verification_coverage(
            diagnosis,
            [{"id": "verify-1", "exit_code": 0}],
        )

    def test_platform_gate_rejects_missing_posix_lock_support(self) -> None:
        with mock.patch.object(runner, "fcntl", None):
            with self.assertRaises(runner.PipelineError) as caught:
                runner.ensure_supported_runner_platform()
        self.assertEqual(caught.exception.exit_code, 9)

    def test_read_only_gate_and_repository_lock(self) -> None:
        before = runner.capture_repo_state(self.repo)
        (self.repo / "a.txt").write_text("mutated\n", encoding="utf-8")
        with self.assertRaises(runner.PipelineError):
            runner.assert_repo_unchanged(before, runner.capture_repo_state(self.repo), "reader")

        with runner.repository_lock(self.repo):
            with self.assertRaises(runner.PipelineError) as caught:
                with runner.repository_lock(self.repo):
                    self.fail("second lock should not be acquired")
            self.assertEqual(caught.exception.exit_code, 7)

    def test_submodules_and_nested_repositories_are_rejected(self) -> None:
        runner.capture_repo_state(self.repo)
        nested = self.repo / "vendor" / "nested"
        nested.mkdir(parents=True)
        git(nested, "init", "-q")
        with self.assertRaises(runner.PipelineError) as caught:
            runner.capture_repo_state(self.repo)
        self.assertEqual(caught.exception.exit_code, 9)
        with self.assertRaises(runner.PipelineError) as caught:
            runner.ensure_supported_repository_topology(self.repo)
        self.assertEqual(caught.exception.exit_code, 9)

        gitlink_repo = self.root / "gitlink-repo"
        gitlink_repo.mkdir()
        git(gitlink_repo, "init", "-q")
        git(gitlink_repo, "config", "user.email", "test@example.com")
        git(gitlink_repo, "config", "user.name", "Test")
        (gitlink_repo / "tracked.txt").write_text("content\n", encoding="utf-8")
        git(gitlink_repo, "add", "tracked.txt")
        git(gitlink_repo, "commit", "-qm", "baseline")
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=gitlink_repo,
            text=True,
        ).strip()
        git(
            gitlink_repo,
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{head},dependency",
        )
        with self.assertRaises(runner.PipelineError) as caught:
            runner.ensure_supported_repository_topology(gitlink_repo)
        self.assertEqual(caught.exception.exit_code, 9)

    def test_timeout_terminates_spawned_process_group(self) -> None:
        marker = self.root / "grandchild-survived"
        child = self.root / "child.py"
        child.write_text(
            "import pathlib, sys, time\n"
            "time.sleep(1.5)\n"
            "pathlib.Path(sys.argv[1]).write_text('survived')\n",
            encoding="utf-8",
        )
        parent = self.root / "parent.py"
        parent.write_text(
            "import subprocess, sys, time\n"
            "subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]])\n"
            "time.sleep(10)\n",
            encoding="utf-8",
        )
        return_code, _, timed_out = runner.run_managed(
            [sys.executable, str(parent), str(child), str(marker)],
            cwd=self.root,
            timeout=1,
        )
        self.assertEqual(return_code, 124)
        self.assertTrue(timed_out)
        time.sleep(0.75)
        self.assertFalse(marker.exists())

    def test_runner_umask_produces_private_artifacts(self) -> None:
        previous = os.umask(0o077)
        try:
            secure_dir = self.root / "secure-run"
            secure_dir.mkdir(mode=0o700)
            artifact = secure_dir / "result.json"
            runner.write_json(artifact, {"result": "PASS"})
        finally:
            os.umask(previous)
        self.assertEqual(secure_dir.stat().st_mode & 0o777, 0o700)
        self.assertEqual(artifact.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main(verbosity=2)

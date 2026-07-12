#!/usr/bin/env python3
"""Focused regression tests for the high-assurance runner's local gates."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shlex
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
        self.assertIn("user-supplied verification command", str(caught.exception))

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
        marker = "ROOTLOOM_SECRET_MUST_NOT_LEAVE_FILE_91f7"
        ignored = self.repo / ".env"
        ignored.write_text(f"TOKEN={marker}\n", encoding="utf-8")
        baseline = runner.capture_repo_state(self.repo)
        ignored.unlink()

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
                allowed_protected_deletions={".env"},
            )

        patch_capture.assert_called_once_with(self.repo, [])
        self.assertEqual(delta["ignored_metadata"][0]["path"], ".env")
        self.assertEqual(delta["ignored_metadata"][0]["kind"], "missing")
        self.assertEqual(delta["protected_deletions"], [".env"])
        self.assertEqual(delta["untracked_patch"], "")
        for artifact in self.run_dir.iterdir():
            self.assertNotIn(marker, artifact.read_text(encoding="utf-8"))
        self.assertNotIn(marker, runner.compact_delta(delta))

    def test_sensitive_visible_untracked_content_is_redacted(self) -> None:
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
            state = runner.capture_repo_state(self.repo)
        visible, redacted_manifest = runner.state_untracked_manifests(state)
        self.assertEqual(visible, [])
        redacted = redacted_manifest[0]
        self.assertEqual(redacted["path"], ".env.local")
        self.assertEqual(redacted["kind"], "file-metadata")
        self.assertNotIn("sha256", redacted)
        self.assertEqual(state["worktree"][".env.local"]["kind"], "file-metadata")
        self.assertNotIn("sha256", state["worktree"][".env.local"])
        self.assertNotIn(marker, str(redacted_manifest))

    def test_protected_modification_and_creation_fail_before_delta_capture(self) -> None:
        (self.repo / ".gitignore").write_text("ignored.env\n", encoding="utf-8")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-qm", "ignore protected file")
        ignored = self.repo / "ignored.env"
        ignored.write_text("before", encoding="utf-8")
        sensitive = self.repo / ".env.local"
        sensitive.write_text("before", encoding="utf-8")
        baseline = runner.capture_repo_state(self.repo)
        ignored.write_text("after", encoding="utf-8")
        sensitive.write_text("after", encoding="utf-8")

        with mock.patch.object(runner, "capture_delta") as capture:
            with self.assertRaises(runner.PipelineError) as caught:
                runner.enforce_repository_contract(
                    repo=self.repo,
                    run_dir=self.run_dir,
                    prefix="protected-modification",
                    baseline=baseline,
                    allowed_rules=runner.normalize_allowed_paths(
                        ["ignored.env", ".env.local"]
                    ),
                )
        capture.assert_not_called()
        self.assertIn("protected metadata-only paths", str(caught.exception))

        ignored.unlink()
        sensitive.unlink()
        clean_baseline = runner.capture_repo_state(self.repo)
        (self.repo / ".env.new").write_text("created", encoding="utf-8")
        with self.assertRaises(runner.PipelineError):
            runner.enforce_repository_contract(
                repo=self.repo,
                run_dir=self.run_dir,
                prefix="protected-creation",
                baseline=clean_baseline,
                allowed_rules=runner.normalize_allowed_paths([".env.new"]),
            )

    def test_baseline_ignored_path_stays_metadata_only_after_gitignore_change(self) -> None:
        gitignore = self.repo / ".gitignore"
        gitignore.write_text("private/runtime.conf\n", encoding="utf-8")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-qm", "ignore private runtime")
        protected = self.repo / "private" / "runtime.conf"
        protected.parent.mkdir()
        protected.write_text("SECRET=before\n", encoding="utf-8")
        baseline = runner.capture_repo_state(self.repo)

        gitignore.write_text("", encoding="utf-8")
        original_fingerprint = runner.file_fingerprint

        def reject_protected_content(path: Path) -> dict[str, object]:
            if path == protected:
                raise AssertionError("baseline protected content was hashed")
            return original_fingerprint(path)

        with (
            mock.patch.object(
                runner,
                "file_fingerprint",
                side_effect=reject_protected_content,
            ),
            mock.patch.object(runner, "capture_delta") as capture,
        ):
            current = runner.capture_repo_state(
                self.repo,
                metadata_only_floor=runner.protected_metadata_paths(baseline),
            )
            self.assertEqual(
                current["worktree"]["private/runtime.conf"]["kind"],
                "file-metadata",
            )
            with self.assertRaises(runner.PipelineError) as entrypoint:
                runner._entrypoint_fingerprint(
                    self.repo,
                    "private/runtime.conf",
                    current,
                )
            self.assertIn("baseline protected metadata-only", str(entrypoint.exception))
            with self.assertRaises(runner.PipelineError) as caught:
                runner.enforce_repository_contract(
                    repo=self.repo,
                    run_dir=self.run_dir,
                    prefix="gitignore-declassification",
                    baseline=baseline,
                    allowed_rules=runner.normalize_allowed_paths(
                        [".gitignore", "private/runtime.conf"]
                    ),
                )

        capture.assert_not_called()
        self.assertIn("declassified baseline protected", str(caught.exception))

    def test_baseline_excluded_path_stays_metadata_only_after_git_control_change(self) -> None:
        exclude = self.repo / ".git" / "info" / "exclude"
        exclude.write_text("private/runtime.conf\n", encoding="utf-8")
        protected = self.repo / "private" / "runtime.conf"
        protected.parent.mkdir()
        protected.write_text("SECRET=before\n", encoding="utf-8")
        baseline = runner.capture_repo_state(self.repo)

        exclude.write_text("", encoding="utf-8")
        protected.write_text("SECRET=after\n", encoding="utf-8")
        original_fingerprint = runner.file_fingerprint

        def reject_protected_content(path: Path) -> dict[str, object]:
            if path == protected:
                raise AssertionError("baseline protected content was hashed")
            return original_fingerprint(path)

        with (
            mock.patch.object(
                runner,
                "file_fingerprint",
                side_effect=reject_protected_content,
            ),
            mock.patch.object(runner, "capture_delta") as capture,
        ):
            with self.assertRaises(runner.PipelineError) as caught:
                runner.enforce_repository_contract(
                    repo=self.repo,
                    run_dir=self.run_dir,
                    prefix="exclude-declassification",
                    baseline=baseline,
                    allowed_rules=runner.normalize_allowed_paths(
                        ["private/runtime.conf"]
                    ),
                )

        capture.assert_not_called()
        self.assertIn("Git control metadata changed", str(caught.exception))

    def test_protected_delete_authorization_is_exact_used_and_requires_human_review(self) -> None:
        for unsafe in ("private/**", "private/", "*.env"):
            with self.subTest(unsafe=unsafe), self.assertRaises(runner.PipelineError):
                runner.normalize_protected_deletions([unsafe])

        baseline = runner.capture_repo_state(self.repo)
        with self.assertRaises(runner.PipelineError) as caught:
            runner.enforce_repository_contract(
                repo=self.repo,
                run_dir=self.run_dir,
                prefix="unused-delete",
                baseline=baseline,
                allowed_rules=runner.normalize_allowed_paths(["a.txt"]),
                allowed_protected_deletions={"missing.env"},
            )
        self.assertIn("unused", str(caught.exception))
        self.assertEqual(runner.completion_outcome([]), ("PASS", 0))
        self.assertEqual(
            runner.completion_outcome([".env"]),
            ("HUMAN_REVIEW_REQUIRED", runner.HUMAN_REVIEW_REQUIRED_EXIT),
        )

    def test_protected_delete_authorization_does_not_allow_modification(self) -> None:
        protected = self.repo / ".env.local"
        protected.write_text("before", encoding="utf-8")
        baseline = runner.capture_repo_state(self.repo)
        protected.write_text("after", encoding="utf-8")
        with self.assertRaises(runner.PipelineError) as caught:
            runner.enforce_repository_contract(
                repo=self.repo,
                run_dir=self.run_dir,
                prefix="delete-only",
                baseline=baseline,
                allowed_rules=runner.normalize_allowed_paths([".env.local"]),
                allowed_protected_deletions={".env.local"},
            )
        self.assertIn("protected metadata-only paths", str(caught.exception))

    def test_protected_delete_authorization_is_deletion_only(self) -> None:
        (self.repo / ".gitignore").write_text(".env\n", encoding="utf-8")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-qm", "ignore env")
        protected = self.repo / ".env"
        protected.write_text("SECRET=do-not-copy\n", encoding="utf-8")
        baseline = runner.capture_repo_state(self.repo)
        target = self.repo / "config" / "runtime.txt"
        target.parent.mkdir()
        protected.rename(target)

        with mock.patch.object(runner, "capture_delta") as capture:
            with self.assertRaises(runner.PipelineError) as caught:
                runner.enforce_repository_contract(
                    repo=self.repo,
                    run_dir=self.run_dir,
                    prefix="protected-rename",
                    baseline=baseline,
                    allowed_rules=runner.normalize_allowed_paths(
                        [".env", "config/runtime.txt"]
                    ),
                    allowed_protected_deletions={".env"},
                )
        capture.assert_not_called()
        self.assertIn("deletion-only run", str(caught.exception))

    def test_protected_delete_preflight_rejects_invalid_authorization(self) -> None:
        protected = self.repo / ".env.local"
        protected.write_text("before", encoding="utf-8")
        ordinary = self.repo / "ordinary.txt"
        ordinary.write_text("ordinary", encoding="utf-8")
        baseline = runner.capture_repo_state(self.repo)
        rules = runner.normalize_allowed_paths([".env.local"])

        with self.assertRaises(runner.PipelineError) as missing:
            runner.validate_protected_deletion_preflight(
                repo=self.repo,
                baseline=baseline,
                allowed_rules=rules,
                allowed_deletions={"missing.env"},
            )
        self.assertIn("before writer execution", str(missing.exception))

        with self.assertRaises(runner.PipelineError) as not_protected:
            runner.validate_protected_deletion_preflight(
                repo=self.repo,
                baseline=baseline,
                allowed_rules=runner.normalize_allowed_paths(["ordinary.txt"]),
                allowed_deletions={"ordinary.txt"},
            )
        self.assertIn("not a baseline protected path", str(not_protected.exception))

        with self.assertRaises(runner.PipelineError) as outside_contract:
            runner.validate_protected_deletion_preflight(
                repo=self.repo,
                baseline=baseline,
                allowed_rules=runner.normalize_allowed_paths(["a.txt"]),
                allowed_deletions={".env.local"},
            )
        self.assertIn("not permitted", str(outside_contract.exception))

    def test_dotfile_redaction_cannot_hide_deliverable_creation(self) -> None:
        baseline = runner.capture_repo_state(
            self.repo,
            redact_untracked_dotfiles=True,
        )
        workflow = self.repo / ".github" / "workflows" / "release.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("name: release\n", encoding="utf-8")
        with self.assertRaises(runner.PipelineError) as caught:
            runner.enforce_repository_contract(
                repo=self.repo,
                run_dir=self.run_dir,
                prefix="dotfile-deliverable",
                baseline=baseline,
                allowed_rules=runner.normalize_allowed_paths(
                    [".github/workflows/release.yml"]
                ),
                redact_untracked_dotfiles=True,
            )
        self.assertIn("protected metadata-only paths", str(caught.exception))

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
        runner.capture_repo_state(self.repo, check_topology=False)
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

    def test_allowed_and_verification_paths_reject_out_of_repo_symlinks(self) -> None:
        outside = self.root / "outside"
        outside.mkdir()
        link = self.repo / "linked"
        link.symlink_to(outside, target_is_directory=True)

        with self.assertRaises(runner.PipelineError) as allowed:
            runner.validate_allowed_path_boundaries(
                self.repo,
                runner.normalize_allowed_paths(["linked/file.txt"]),
            )
        self.assertIn("outside the repository", str(allowed.exception))

        script = self.repo / "scripts" / "verify.sh"
        script.parent.mkdir()
        script.symlink_to(outside / "verify.sh")
        with self.assertRaises(runner.PipelineError) as verification:
            runner.validate_verification_command_boundaries(
                self.repo,
                [{"id": "verify-1", "argv": ["scripts/verify.sh"]}],
            )
        self.assertIn("outside the repository", str(verification.exception))

    def test_verification_entrypoint_rejects_writer_replaced_symlink(self) -> None:
        script = self.repo / "scripts" / "check.sh"
        script.parent.mkdir()
        script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        baseline = runner.discover_verification_entrypoints(
            self.repo,
            [{"id": "verify-1", "argv": ["scripts/check.sh"]}],
            runner.capture_repo_state(self.repo),
        )
        outside = self.root / "outside-check.sh"
        outside.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        script.unlink()
        script.symlink_to(outside)

        with self.assertRaises(runner.PipelineError) as caught:
            runner.validate_verification_entrypoints_unchanged(
                self.repo,
                baseline,
                runner.capture_repo_state(self.repo),
            )
        self.assertIn("outside the repository", str(caught.exception))

    def test_verification_entrypoint_rejects_writer_modified_harness_files(self) -> None:
        makefile = self.repo / "Makefile"
        package = self.repo / "package.json"
        pytest_config = self.repo / "pyproject.toml"
        makefile.write_text("check:\n\ttrue\n", encoding="utf-8")
        package.write_text('{"scripts":{"test":"node test.js"}}\n', encoding="utf-8")
        pytest_config.write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
        commands = [
            {"id": "verify-1", "argv": ["make", "check"]},
            {"id": "verify-2", "argv": ["npm", "test"]},
            {"id": "verify-3", "argv": ["pytest"]},
        ]
        baseline = runner.discover_verification_entrypoints(
            self.repo,
            commands,
            runner.capture_repo_state(self.repo),
        )
        self.assertIn("Makefile", baseline["verify-1"])
        self.assertIn("package.json", baseline["verify-2"])
        self.assertIn("pyproject.toml", baseline["verify-3"])

        makefile.write_text("check:\n\t@echo passed\n", encoding="utf-8")
        with self.assertRaises(runner.PipelineError) as caught:
            runner.validate_verification_entrypoints_unchanged(
                self.repo,
                baseline,
                runner.capture_repo_state(self.repo),
            )
        self.assertIn("verify-1:Makefile", str(caught.exception))

    def test_verification_entrypoint_tracks_missing_candidates(self) -> None:
        makefile = self.repo / "Makefile"
        makefile.write_text("check:\n\ttrue\n", encoding="utf-8")
        baseline = runner.discover_verification_entrypoints(
            self.repo,
            [{"id": "verify-1", "argv": ["make", "check"]}],
            runner.capture_repo_state(self.repo),
        )
        self.assertEqual(baseline["verify-1"]["GNUmakefile"]["entry"]["kind"], "missing")
        (self.repo / "GNUmakefile").write_text("check:\n\t@echo weak\n", encoding="utf-8")
        with self.assertRaises(runner.PipelineError) as caught:
            runner.validate_verification_entrypoints_unchanged(
                self.repo,
                baseline,
                runner.capture_repo_state(self.repo),
            )
        self.assertIn("verify-1:GNUmakefile", str(caught.exception))

        pytest_baseline = runner.discover_verification_entrypoints(
            self.repo,
            [{"id": "verify-2", "argv": ["python", "-m", "pytest"]}],
            runner.capture_repo_state(self.repo),
        )
        self.assertEqual(pytest_baseline["verify-2"]["pytest.ini"]["entry"]["kind"], "missing")
        (self.repo / "pytest.ini").write_text("[pytest]\naddopts = -q\n", encoding="utf-8")
        with self.assertRaises(runner.PipelineError) as pytest_changed:
            runner.validate_verification_entrypoints_unchanged(
                self.repo,
                pytest_baseline,
                runner.capture_repo_state(self.repo),
            )
        self.assertIn("verify-2:pytest.ini", str(pytest_changed.exception))

    def test_verification_entrypoint_recognizes_common_wrappers_and_explicit_bindings(self) -> None:
        (self.repo / "scripts").mkdir()
        (self.repo / "scripts" / "check.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (self.repo / "pytest-ci.ini").write_text("[pytest]\n", encoding="utf-8")
        (self.repo / "Makefile.ci").write_text("check:\n\ttrue\n", encoding="utf-8")
        (self.repo / "apps").mkdir()
        (self.repo / "apps" / "web").mkdir()
        (self.repo / "apps" / "web" / "package.json").write_text("{}\n", encoding="utf-8")
        commands = [
            {"id": "verify-1", "argv": ["./scripts/check.sh"]},
            {"id": "verify-2", "argv": ["uv", "run", "pytest", "-c", "pytest-ci.ini"]},
            {"id": "verify-3", "argv": ["poetry", "run", "pytest"]},
            {"id": "verify-4", "argv": ["make", "-f", "Makefile.ci", "check"]},
            {"id": "verify-5", "argv": ["npm", "--prefix", "apps/web", "test"]},
        ]
        runner.validate_verification_command_boundaries(self.repo, commands)
        baseline = runner.discover_verification_entrypoints(
            self.repo,
            commands,
            runner.capture_repo_state(self.repo),
            bound_paths={"verify-1": {"scripts/check.sh"}},
        )
        self.assertIn("scripts/check.sh", baseline["verify-1"])
        self.assertIn("pytest-ci.ini", baseline["verify-2"])
        self.assertIn("pyproject.toml", baseline["verify-3"])
        self.assertIn("Makefile.ci", baseline["verify-4"])
        self.assertIn("apps/web/package.json", baseline["verify-5"])
        self.assertEqual(
            baseline["verify-1"]["scripts/check.sh"]["source"],
            "operator-bound",
        )

    def test_verification_entrypoint_binds_repo_internal_symlink_target_content(self) -> None:
        scripts = self.repo / "scripts"
        scripts.mkdir()
        impl = scripts / "check_impl.sh"
        impl.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        link = scripts / "check.sh"
        link.symlink_to("check_impl.sh")
        baseline = runner.discover_verification_entrypoints(
            self.repo,
            [{"id": "verify-1", "argv": ["scripts/check.sh"]}],
            runner.capture_repo_state(self.repo),
        )
        self.assertEqual(
            baseline["verify-1"]["scripts/check.sh"]["chain"][0]["resolved"],
            "scripts/check_impl.sh",
        )
        impl.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        with self.assertRaises(runner.PipelineError) as caught:
            runner.validate_verification_entrypoints_unchanged(
                self.repo,
                baseline,
                runner.capture_repo_state(self.repo),
            )
        self.assertIn("verify-1:scripts/check.sh", str(caught.exception))

    def test_verification_entrypoint_does_not_bind_directory_selectors(self) -> None:
        tests_dir = self.repo / "tests" / "unit"
        tests_dir.mkdir(parents=True)
        baseline = runner.discover_verification_entrypoints(
            self.repo,
            [{"id": "verify-1", "argv": ["pytest", "tests/unit"]}],
            runner.capture_repo_state(self.repo),
        )
        self.assertNotIn("tests/unit", baseline["verify-1"])

    def test_verification_entrypoint_never_hashes_ignored_or_sensitive_paths(self) -> None:
        (self.repo / ".gitignore").write_text("Makefile\nprivate/\n", encoding="utf-8")
        ignored_makefile = self.repo / "Makefile"
        ignored_makefile.write_text("check:\n\ttrue\n", encoding="utf-8")
        private = self.repo / "private"
        private.mkdir()
        sensitive_script = private / "check.sh"
        sensitive_script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        state = runner.capture_repo_state(
            self.repo,
            sensitive_rules=runner.normalize_sensitive_paths(["private/**"]),
        )
        original = runner.file_fingerprint

        def reject_protected_content(path: Path) -> dict[str, object]:
            if path in {ignored_makefile, sensitive_script}:
                raise AssertionError("protected verification content was hashed")
            return original(path)

        with mock.patch.object(
            runner,
            "file_fingerprint",
            side_effect=reject_protected_content,
        ):
            with self.assertRaises(runner.PipelineError) as ignored:
                runner.discover_verification_entrypoints(
                    self.repo,
                    [{"id": "verify-1", "argv": ["make", "check"]}],
                    state,
                )
            self.assertIn("ignored", str(ignored.exception))
            with self.assertRaises(runner.PipelineError) as sensitive:
                runner.discover_verification_entrypoints(
                    self.repo,
                    [{"id": "verify-1", "argv": ["./private/check.sh"]}],
                    state,
                )
            self.assertIn("cannot be read or hashed", str(sensitive.exception))

    def test_bound_sensitive_missing_and_directory_harnesses_fail_closed(self) -> None:
        (self.repo / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
        (self.repo / "scripts").mkdir()
        commands = [
            {"id": runner.BUILTIN_DIFF_CHECK_ID, "argv": ["git", "diff", "HEAD", "--check"]},
            {"id": "verify-1", "argv": ["make", "check"]},
        ]
        state = runner.capture_repo_state(self.repo)
        for raw, expected in (
            (".env", "sensitive untracked"),
            ("scripts/missing.sh", "existing regular file"),
            ("scripts", "existing regular file"),
        ):
            bindings = runner.normalize_verification_bindings([raw], commands)
            with self.assertRaises(runner.PipelineError) as caught:
                runner.discover_verification_entrypoints(
                    self.repo,
                    commands,
                    state,
                    bound_paths=bindings,
                )
            self.assertIn(expected, str(caught.exception))

    def test_bound_harness_is_scoped_to_a_real_verification_command(self) -> None:
        harness = self.repo / "scripts" / "acceptance.sh"
        harness.parent.mkdir()
        harness.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        commands = [
            {"id": runner.BUILTIN_DIFF_CHECK_ID, "argv": ["git", "diff", "HEAD", "--check"]},
            {"id": "verify-1", "argv": ["make", "check"]},
            {"id": "verify-2", "argv": ["pytest"]},
        ]
        with self.assertRaises(runner.PipelineError) as ambiguous:
            runner.normalize_verification_bindings(["scripts/acceptance.sh"], commands)
        self.assertIn("verify-N:path", str(ambiguous.exception))
        bindings = runner.normalize_verification_bindings(
            ["verify-2:scripts/acceptance.sh"],
            commands,
        )
        baseline = runner.discover_verification_entrypoints(
            self.repo,
            commands,
            runner.capture_repo_state(self.repo),
            bound_paths=bindings,
        )
        self.assertNotIn("scripts/acceptance.sh", baseline["verify-1"])
        self.assertEqual(
            baseline["verify-2"]["scripts/acceptance.sh"]["source"],
            "operator-bound",
        )

    def test_pytest_new_test_selector_is_not_an_immutable_entrypoint(self) -> None:
        state = runner.capture_repo_state(self.repo)
        baseline = runner.discover_verification_entrypoints(
            self.repo,
            [{"id": "verify-1", "argv": ["pytest", "tests/test_new_regression.py"]}],
            state,
        )
        self.assertNotIn("tests/test_new_regression.py", baseline["verify-1"])
        test_path = self.repo / "tests" / "test_new_regression.py"
        test_path.parent.mkdir()
        test_path.write_text("def test_new():\n    assert True\n", encoding="utf-8")
        runner.validate_verification_entrypoints_unchanged(
            self.repo,
            baseline,
            runner.capture_repo_state(self.repo),
        )

    def test_entrypoint_fingerprint_records_parent_directory_symlinks(self) -> None:
        first = self.repo / "real-scripts"
        second = self.repo / "alternate-scripts"
        first.mkdir()
        second.mkdir()
        for directory in (first, second):
            (directory / "check.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        link = self.repo / "scripts"
        link.symlink_to("real-scripts", target_is_directory=True)
        baseline = runner.discover_verification_entrypoints(
            self.repo,
            [{"id": "verify-1", "argv": ["./scripts/check.sh"]}],
            runner.capture_repo_state(self.repo),
        )
        self.assertEqual(
            baseline["verify-1"]["scripts/check.sh"]["chain"][0]["link"],
            "scripts",
        )
        link.unlink()
        link.symlink_to("alternate-scripts", target_is_directory=True)
        with self.assertRaises(runner.PipelineError):
            runner.validate_verification_entrypoints_unchanged(
                self.repo,
                baseline,
                runner.capture_repo_state(self.repo),
            )

    def test_symlink_entrypoint_rejects_protected_target_without_hashing(self) -> None:
        (self.repo / ".gitignore").write_text("private/\n", encoding="utf-8")
        private = self.repo / "private"
        private.mkdir()
        target = private / "check_impl.sh"
        target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        scripts = self.repo / "scripts"
        scripts.mkdir()
        (scripts / "check.sh").symlink_to("../private/check_impl.sh")
        state = runner.capture_repo_state(self.repo)
        original = runner.file_fingerprint

        def reject_target(path: Path) -> dict[str, object]:
            if path == target:
                raise AssertionError("protected symlink target was hashed")
            return original(path)

        with mock.patch.object(runner, "file_fingerprint", side_effect=reject_target):
            with self.assertRaises(runner.PipelineError) as caught:
                runner.discover_verification_entrypoints(
                    self.repo,
                    [{"id": "verify-1", "argv": ["./scripts/check.sh"]}],
                    state,
                )
        self.assertIn("ignored", str(caught.exception))

    def test_verification_batch_stops_before_next_command_after_mutation(self) -> None:
        scripts = self.repo / "scripts"
        scripts.mkdir()
        second = scripts / "second.sh"
        marker = self.root / "second-ran"
        second.write_text(f"#!/bin/sh\ntouch {shlex.quote(str(marker))}\n", encoding="utf-8")
        second.chmod(0o755)
        commands = [
            {
                "id": "verify-1",
                "argv": [
                    sys.executable,
                    "-c",
                    "from pathlib import Path; Path('scripts/second.sh').write_text('changed')",
                ],
            },
            {"id": "verify-2", "argv": ["./scripts/second.sh"]},
        ]
        expected = runner.capture_repo_state(self.repo)
        entrypoints = runner.discover_verification_entrypoints(
            self.repo,
            commands,
            expected,
        )
        run_dir = self.root / "verification-run"
        run_dir.mkdir()
        with self.assertRaises(runner.PipelineError) as caught:
            runner.run_verification(
                repo=self.repo,
                run_dir=run_dir,
                prefix="04-verification",
                commands=commands,
                dry_run=False,
                timeout_seconds=5,
                expected_state=expected,
                state_supplier=lambda: runner.capture_repo_state(self.repo),
                entrypoints=entrypoints,
            )
        self.assertIn("verification command verify-1", str(caught.exception))
        self.assertFalse(marker.exists())

    def test_protected_deletion_mode_rejects_dirty_and_repair_cycles(self) -> None:
        with self.assertRaises(runner.PipelineError) as dirty:
            runner.validate_protected_deletion_runtime_options(
                allowed_deletions={".env"},
                allow_dirty=True,
                max_repair_cycles=0,
            )
        self.assertIn("clean worktree", str(dirty.exception))

        with self.assertRaises(runner.PipelineError) as repair:
            runner.validate_protected_deletion_runtime_options(
                allowed_deletions={".env"},
                allow_dirty=False,
                max_repair_cycles=1,
            )
        self.assertIn("does not support repair cycles", str(repair.exception))

        runner.validate_protected_deletion_runtime_options(
            allowed_deletions={".env"},
            allow_dirty=False,
            max_repair_cycles=0,
        )

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
        return_code, _, timed_out, leftover = runner.run_managed(
            [sys.executable, str(parent), str(child), str(marker)],
            cwd=self.root,
            timeout=1,
        )
        self.assertEqual(return_code, 124)
        self.assertTrue(timed_out)
        self.assertFalse(leftover)
        time.sleep(0.75)
        self.assertFalse(marker.exists())

    def test_timeout_reaps_direct_process_that_ignores_sigterm(self) -> None:
        command = (
            "import signal, time; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "time.sleep(20)"
        )
        return_code, _, timed_out, leftover = runner.run_managed(
            [sys.executable, "-c", command],
            cwd=self.root,
            timeout=1,
        )
        self.assertEqual(return_code, 124)
        self.assertTrue(timed_out)
        self.assertFalse(leftover)

    def test_successful_command_with_leftover_child_fails_closed(self) -> None:
        marker = self.root / "leftover-child"
        child = self.root / "linger.py"
        child.write_text(
            "import pathlib, sys, time\n"
            "time.sleep(2)\n"
            "pathlib.Path(sys.argv[1]).write_text('survived')\n",
            encoding="utf-8",
        )
        parent = self.root / "success_with_child.py"
        parent.write_text(
            "import subprocess, sys\n"
            "subprocess.Popen(\n"
            "    [sys.executable, sys.argv[1], sys.argv[2]],\n"
            "    stdin=subprocess.DEVNULL,\n"
            "    stdout=subprocess.DEVNULL,\n"
            "    stderr=subprocess.DEVNULL,\n"
            ")\n",
            encoding="utf-8",
        )
        return_code, output, timed_out, leftover = runner.run_managed(
            [sys.executable, str(parent), str(child), str(marker)],
            cwd=self.root,
            timeout=5,
        )
        self.assertEqual(return_code, 125)
        self.assertFalse(timed_out)
        self.assertTrue(leftover)
        self.assertIn("left a live process group", output)
        time.sleep(0.5)
        self.assertFalse(marker.exists())

    def test_leftover_child_ignoring_sigterm_is_killed(self) -> None:
        ready = self.root / "sigterm-ignored-ready"
        marker = self.root / "sigterm-ignored-survived"
        child = self.root / "ignore_sigterm.py"
        child.write_text(
            "import pathlib, signal, sys, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "pathlib.Path(sys.argv[1]).write_text('ready')\n"
            "time.sleep(8)\n"
            "pathlib.Path(sys.argv[2]).write_text('survived')\n",
            encoding="utf-8",
        )
        parent = self.root / "success_with_stubborn_child.py"
        parent.write_text(
            "import pathlib, subprocess, sys, time\n"
            "subprocess.Popen(\n"
            "    [sys.executable, sys.argv[1], sys.argv[2], sys.argv[3]],\n"
            "    stdin=subprocess.DEVNULL,\n"
            "    stdout=subprocess.DEVNULL,\n"
            "    stderr=subprocess.DEVNULL,\n"
            ")\n"
            "ready = pathlib.Path(sys.argv[2])\n"
            "deadline = time.monotonic() + 3\n"
            "while not ready.exists() and time.monotonic() < deadline:\n"
            "    time.sleep(0.01)\n"
            "raise SystemExit(0 if ready.exists() else 2)\n",
            encoding="utf-8",
        )
        return_code, output, timed_out, leftover = runner.run_managed(
            [
                sys.executable,
                str(parent),
                str(child),
                str(ready),
                str(marker),
            ],
            cwd=self.root,
            timeout=5,
        )
        self.assertEqual(return_code, 125)
        self.assertFalse(timed_out)
        self.assertTrue(leftover)
        self.assertIn("left a live process group", output)
        time.sleep(0.75)
        self.assertFalse(marker.exists())

    def test_failed_command_with_leftover_child_preserves_failure_and_cleans_up(self) -> None:
        marker = self.root / "failed-leftover-child"
        child = self.root / "failed-linger.py"
        child.write_text(
            "import pathlib, sys, time\n"
            "time.sleep(2)\n"
            "pathlib.Path(sys.argv[1]).write_text('survived')\n",
            encoding="utf-8",
        )
        parent = self.root / "failure_with_child.py"
        parent.write_text(
            "import subprocess, sys\n"
            "subprocess.Popen(\n"
            "    [sys.executable, sys.argv[1], sys.argv[2]],\n"
            "    stdin=subprocess.DEVNULL,\n"
            "    stdout=subprocess.DEVNULL,\n"
            "    stderr=subprocess.DEVNULL,\n"
            ")\n"
            "raise SystemExit(7)\n",
            encoding="utf-8",
        )
        return_code, output, timed_out, leftover = runner.run_managed(
            [sys.executable, str(parent), str(child), str(marker)],
            cwd=self.root,
            timeout=5,
        )
        self.assertEqual(return_code, 7)
        self.assertFalse(timed_out)
        self.assertTrue(leftover)
        self.assertIn("left a live process group", output)
        time.sleep(0.5)
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

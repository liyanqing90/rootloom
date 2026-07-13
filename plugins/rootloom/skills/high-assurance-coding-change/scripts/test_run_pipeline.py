#!/usr/bin/env python3
"""Focused regression tests for the high-assurance runner's local gates."""

from __future__ import annotations

import importlib.util
import json
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
sys.modules.setdefault("run_pipeline", runner)
REVIEW_PATH = MODULE_PATH.with_name("review_decision.py")
REVIEW_SPEC = importlib.util.spec_from_file_location("review_decision", REVIEW_PATH)
assert REVIEW_SPEC and REVIEW_SPEC.loader
review_decision = importlib.util.module_from_spec(REVIEW_SPEC)
REVIEW_SPEC.loader.exec_module(review_decision)


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
                },
            )

        valid = {
            "observed_facts": [
                {
                    "id": "fact-1",
                    "statement": "failure observed",
                    "provenance_ids": ["source-1"],
                },
            ],
            "evidence_provenance": [
                {
                    "id": "source-1",
                    "claim": "failure observed",
                    "kind": "fact",
                    "source_type": "repository",
                    "reference": "tests/test_failure.py",
                },
                {
                    "id": "source-2",
                    "claim": "sibling path preserves the owner invariant",
                    "kind": "fact",
                    "source_type": "repository",
                    "reference": "src/sibling.py:20",
                },
            ],
            "reproduction": {
                "status": "reproduced",
                "evidence_ids": ["source-1"],
            },
            "hypotheses": [
                {
                    "hypothesis": "owner invariant failed",
                    "supporting_provenance_ids": ["source-1"],
                    "contradicting_provenance_ids": ["source-2"],
                },
                {
                    "hypothesis": "all sibling paths share the defect",
                    "supporting_provenance_ids": [],
                    "contradicting_provenance_ids": ["source-2"],
                },
            ],
        }
        runner.validate_evidence(valid)
        invalid_reference = json.loads(json.dumps(valid))
        invalid_reference["hypotheses"][0]["contradicting_provenance_ids"] = [
            "fabricated-source"
        ]
        with self.assertRaises(runner.PipelineError):
            runner.validate_evidence(invalid_reference)
        one_hypothesis = json.loads(json.dumps(valid))
        one_hypothesis["hypotheses"] = one_hypothesis["hypotheses"][:1]
        with self.assertRaisesRegex(runner.PipelineError, "competing hypotheses"):
            runner.validate_evidence(one_hypothesis)
        unchallenged = json.loads(json.dumps(valid))
        for hypothesis in unchallenged["hypotheses"]:
            hypothesis["contradicting_provenance_ids"] = []
        with self.assertRaisesRegex(runner.PipelineError, "falsified or contradicted"):
            runner.validate_evidence(unchallenged)
        unattributed_runtime = json.loads(json.dumps(valid))
        unattributed_runtime["evidence_provenance"][0]["source_type"] = (
            "runtime_external"
        )
        with self.assertRaisesRegex(runner.PipelineError, "source_environment"):
            runner.validate_evidence(unattributed_runtime)
        unattributed_runtime["evidence_provenance"][0].update(
            {
                "source_environment": "local focused test",
                "observed_at": "2026-07-12T12:00:00+08:00",
                "freshness_redaction": "fresh; no secrets retained",
            }
        )
        runner.validate_evidence(unattributed_runtime)

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
            "rejected_alternatives": ["patching the caller leaves the invariant broken"],
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
        diagnosis["rejected_alternatives"] = []
        with self.assertRaisesRegex(runner.PipelineError, "rejected_alternatives"):
            runner.validate_diagnosis(diagnosis, {"verify-0", "verify-1"})
        diagnosis["rejected_alternatives"] = [
            "patching the caller leaves the invariant broken"
        ]
        diagnosis["verification_map"]["adjacent_negative_or_alternate_path"][
            "command_ids"
        ] = ["verify-0"]
        runner.validate_diagnosis(diagnosis, {"verify-0", "verify-1"})
        for item in diagnosis["verification_map"].values():
            item["command_ids"] = ["verify-0"]
        with self.assertRaises(runner.PipelineError) as caught:
            runner.validate_diagnosis(diagnosis, {"verify-0", "verify-1"})
        self.assertIn("user-supplied verification command", str(caught.exception))

    def test_review_requires_a_concrete_challenge_pass(self) -> None:
        review = {
            "verdict": "PASS",
            "findings": [],
            "contract_compliance": ["scope and invariant satisfied"],
            "test_adequacy": "original, invariant, and adjacent paths passed",
            "residual_risks": [],
        }
        with self.assertRaisesRegex(runner.PipelineError, "review challenge"):
            runner.validate_review(review)
        review["challenge"] = {
            "strongest_counterexample": "empty input preserves the invariant",
            "adjacent_analog_checked": "src/sibling.py uses the same owner boundary",
            "complexity_value": "one owner check replaces two caller checks",
        }
        runner.validate_review(review)

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
                "stream_untracked_patch",
                wraps=runner.stream_untracked_patch,
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

        patch_capture.assert_called_once()
        self.assertEqual(patch_capture.call_args.args[0], self.repo)
        self.assertEqual(patch_capture.call_args.args[1], [])
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
        self.assertTrue(delta["delta_complete"])
        self.assertGreater(delta["delta_bytes"], 0)

    def test_untracked_patch_budget_fails_closed_without_partial_patch(self) -> None:
        baseline = runner.capture_repo_state(self.repo)
        path = self.repo / "large-untracked.bin"
        path.write_bytes(os.urandom(64 * 1024))
        with self.assertRaises(runner.PipelineError) as caught:
            runner.enforce_repository_contract(
                repo=self.repo,
                run_dir=self.run_dir,
                prefix="large-untracked",
                baseline=baseline,
                allowed_rules=runner.normalize_allowed_paths([path.name]),
                max_delta_bytes=128 * 1024,
                max_untracked_patch_bytes=1024,
            )
        self.assertIn("automated review was refused", str(caught.exception))
        artifact = self.run_dir / "large-untracked-untracked.patch"
        self.assertEqual(artifact.stat().st_size, 0)

    def test_untracked_patch_commands_share_one_capture_deadline(self) -> None:
        destination = self.run_dir / "shared-deadline.patch"
        manifest = [
            {"path": "one.txt", "kind": "file"},
            {"path": "two.txt", "kind": "file"},
        ]

        def consume_deadline(*args: object, **kwargs: object) -> int:
            time.sleep(0.03)
            return 0

        with mock.patch.object(
            runner,
            "stream_command_artifact",
            side_effect=consume_deadline,
        ) as capture:
            with self.assertRaises(runner.PipelineError) as caught:
                runner.stream_untracked_patch(
                    self.repo,
                    manifest,
                    destination,
                    1024,
                    time.monotonic() + 0.01,
                )
        self.assertIn("deadline expired", str(caught.exception))
        self.assertEqual(capture.call_count, 1)

    def test_untracked_patch_failure_rolls_back_the_complete_batch(self) -> None:
        destination = self.run_dir / "transactional-untracked.patch"
        manifest = [
            {"path": "one.txt", "kind": "file"},
            {"path": "two.txt", "kind": "file"},
        ]
        calls = 0

        def capture_path(*args: object, **kwargs: object) -> int:
            nonlocal calls
            calls += 1
            artifact = kwargs["destination"]
            assert isinstance(artifact, Path)
            if calls == 1:
                with artifact.open("ab") as handle:
                    handle.write(b"complete-first-path")
                return len(b"complete-first-path")
            with artifact.open("ab") as handle:
                handle.write(b"partial-second-path")
            raise runner.PipelineError("simulated second-path failure", 9)

        with mock.patch.object(
            runner,
            "stream_command_artifact",
            side_effect=capture_path,
        ):
            with self.assertRaises(runner.PipelineError) as caught:
                runner.stream_untracked_patch(
                    self.repo,
                    manifest,
                    destination,
                    1024,
                    time.monotonic() + 5,
                )
        self.assertIn("two.txt", str(caught.exception))
        self.assertEqual(calls, 2)
        self.assertEqual(destination.read_bytes(), b"")

    def test_tracked_delta_budget_fails_closed_without_full_buffering(self) -> None:
        path = self.repo / "large-tracked.bin"
        path.write_bytes(os.urandom(64 * 1024))
        git(self.repo, "add", path.name)
        git(self.repo, "commit", "-qm", "add binary")
        baseline = runner.capture_repo_state(self.repo)
        path.write_bytes(os.urandom(64 * 1024))
        with self.assertRaises(runner.PipelineError) as caught:
            runner.enforce_repository_contract(
                repo=self.repo,
                run_dir=self.run_dir,
                prefix="large-tracked",
                baseline=baseline,
                allowed_rules=runner.normalize_allowed_paths([path.name]),
                max_delta_bytes=1024,
            )
        self.assertIn("Delta is incomplete", str(caught.exception))
        artifact = self.run_dir / "large-tracked-unstaged.patch"
        self.assertEqual(artifact.stat().st_size, 0)

    def test_large_complete_delta_retains_only_bounded_prompt_excerpt(self) -> None:
        path = self.repo / "excerpted-tracked.bin"
        path.write_bytes(os.urandom(64 * 1024))
        git(self.repo, "add", path.name)
        git(self.repo, "commit", "-qm", "add excerpt fixture")
        baseline = runner.capture_repo_state(self.repo)
        path.write_bytes(os.urandom(64 * 1024))
        delta, _ = runner.enforce_repository_contract(
            repo=self.repo,
            run_dir=self.run_dir,
            prefix="excerpted",
            baseline=baseline,
            allowed_rules=runner.normalize_allowed_paths([path.name]),
            max_delta_bytes=1024 * 1024,
        )
        state = delta["patch_prompt_excerpts"]["unstaged_patch"]
        artifact = self.run_dir / "excerpted-unstaged.patch"
        self.assertTrue(state["truncated"])
        self.assertEqual(state["artifact_bytes"], artifact.stat().st_size)
        self.assertLess(
            len(delta["unstaged_patch"].encode("utf-8")),
            artifact.stat().st_size,
        )
        self.assertLessEqual(
            state["excerpt_utf8_bytes"],
            runner.MAX_DELTA_PATCH_EXCERPT_BYTES + 200,
        )

    def test_delta_capture_disables_repository_textconv_drivers(self) -> None:
        marker = self.root / "textconv-ran"
        driver = self.repo / "textconv.py"
        driver.write_text(
            "import pathlib, sys\n"
            "pathlib.Path(sys.argv[1]).write_text('ran')\n"
            "print(pathlib.Path(sys.argv[2]).read_text())\n",
            encoding="utf-8",
        )
        (self.repo / ".gitattributes").write_text(
            "*.dat diff=malicious\n",
            encoding="utf-8",
        )
        data = self.repo / "sample.dat"
        data.write_text("before\n", encoding="utf-8")
        git(self.repo, "add", ".gitattributes", driver.name, data.name)
        git(self.repo, "commit", "-qm", "add textconv fixture")
        git(
            self.repo,
            "config",
            "diff.malicious.textconv",
            f"{shlex.quote(sys.executable)} {shlex.quote(str(driver))} "
            f"{shlex.quote(str(marker))}",
        )
        baseline = runner.capture_repo_state(self.repo)
        data.write_text("after\n", encoding="utf-8")
        runner.enforce_repository_contract(
            repo=self.repo,
            run_dir=self.run_dir,
            prefix="no-textconv",
            baseline=baseline,
            allowed_rules=runner.normalize_allowed_paths([data.name]),
        )
        self.assertFalse(marker.exists())

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

    def test_state_path_and_byte_budgets_fail_closed(self) -> None:
        (self.repo / "b.txt").write_text("b", encoding="utf-8")
        git(self.repo, "add", "b.txt")
        with self.assertRaisesRegex(runner.PipelineError, "tracked path budget"):
            runner.capture_repo_state(
                self.repo,
                max_state_paths=1,
                check_topology=False,
            )
        with self.assertRaisesRegex(runner.PipelineError, "Git status"):
            runner.capture_repo_state(
                self.repo,
                max_state_bytes=1,
                check_topology=False,
            )
        with self.assertRaisesRegex(runner.PipelineError, "tracked byte budget"):
            runner.list_git_paths(
                self.repo,
                ["ls-files", "-z", "--cached"],
                max_paths=10,
                max_bytes=1,
                budget_name="tracked",
            )
        with self.assertRaisesRegex(runner.PipelineError, "topology.*budget"):
            runner.ensure_supported_repository_topology(self.repo, max_paths=1)
        allowed = self.repo / "allowed"
        allowed.mkdir()
        (allowed / "one.txt").write_text("1", encoding="utf-8")
        (allowed / "two.txt").write_text("2", encoding="utf-8")
        with self.assertRaisesRegex(runner.PipelineError, "allowed-path.*budget"):
            runner.validate_allowed_path_boundaries(
                self.repo,
                runner.normalize_allowed_paths(["allowed/**"]),
                max_paths=1,
            )
        control = self.root / "control"
        control.mkdir()
        (control / "one").write_text("1", encoding="utf-8")
        with self.assertRaisesRegex(runner.PipelineError, "Git control tree budget"):
            runner.tree_fingerprint(control, max_entries=1)

    def test_snapshot_digest_cache_reuses_and_invalidates_file_hashes(self) -> None:
        cache: dict[str, dict[str, object]] = {}
        path = self.repo / "a.txt"
        with mock.patch.object(
            runner.hashlib,
            "sha256",
            wraps=runner.hashlib.sha256,
        ) as sha256:
            first = runner.file_fingerprint(path, cache)
            first_calls = sha256.call_count
            second = runner.file_fingerprint(path, cache)
            self.assertEqual(second, first)
            self.assertEqual(sha256.call_count, first_calls)
            path.write_text("changed\n", encoding="utf-8")
            third = runner.file_fingerprint(path, cache)
            self.assertNotEqual(third["sha256"], first["sha256"])
            self.assertGreater(sha256.call_count, first_calls)

    def test_directory_fingerprint_is_metadata_only_and_never_spawns_git(self) -> None:
        directory = self.repo / "ordinary-directory"
        directory.mkdir()
        with mock.patch.object(runner.subprocess, "run") as spawn:
            fingerprint = runner.file_fingerprint(directory)
        spawn.assert_not_called()
        self.assertEqual(fingerprint["kind"], "directory")
        self.assertNotIn("sha256", fingerprint)

    def test_stage_json_and_required_isolation_fail_before_use(self) -> None:
        output = self.root / "oversized.json"
        output.write_text('{"value":"' + ("x" * 100) + '"}', encoding="utf-8")
        with self.assertRaisesRegex(runner.PipelineError, "exceeds 32 bytes"):
            runner.read_json(output, 32)
        linked_output = self.root / "linked-output.json"
        linked_output.symlink_to(output)
        with self.assertRaisesRegex(runner.PipelineError, "missing or symlinked"):
            runner.read_json(linked_output, 1024)
        task = self.root / "oversized-task.md"
        task.write_text("x" * 100, encoding="utf-8")
        with self.assertRaisesRegex(runner.PipelineError, "task file exceeds 32 bytes"):
            runner.read_text_bounded(task, 32, "task file")
        private_target = self.root / "private-target"
        private_target.write_text("preserve", encoding="utf-8")
        private_link = self.root / "private-link"
        private_link.symlink_to(private_target)
        with self.assertRaisesRegex(runner.PipelineError, "safely openable"):
            runner.ensure_empty_private_file(private_link)
        self.assertEqual(private_target.read_text(encoding="utf-8"), "preserve")
        summary_link = self.root / "summary-link.json"
        summary_link.symlink_to(private_target)
        runner.atomic_write_json(summary_link, {"accepted": True})
        self.assertFalse(summary_link.is_symlink())
        self.assertEqual(private_target.read_text(encoding="utf-8"), "preserve")
        with self.assertRaisesRegex(runner.PipelineError, "requires --isolation-launcher"):
            runner.normalize_isolation_launcher(None, required=True)
        launcher = self.root / "launcher"
        launcher.write_text("#!/bin/sh\nexec \"$@\"\n", encoding="utf-8")
        launcher.chmod(0o755)
        argv, metadata = runner.normalize_isolation_launcher(
            str(launcher),
            required=True,
        )
        self.assertEqual(argv, [str(launcher.resolve())])
        assert metadata is not None
        self.assertEqual(metadata["executable_sha256"], runner.file_sha256(launcher))
        command, actual = runner.prepare_isolated_command(argv, metadata, ["true"])
        self.assertEqual(command, [str(launcher.resolve()), "--", "true"])
        self.assertEqual(actual, metadata["configured_executable_identity"])
        launcher.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
        launcher.chmod(0o755)
        with self.assertRaisesRegex(runner.PipelineError, "identity drifted"):
            runner.prepare_isolated_command(argv, metadata, ["true"])

        for forbidden_root, label in ((self.repo, "repository"), (self.run_dir, "run root")):
            forbidden = forbidden_root / "launcher"
            forbidden.write_text("#!/bin/sh\nexec \"$@\"\n", encoding="utf-8")
            forbidden.chmod(0o755)
            with self.subTest(label=label), self.assertRaisesRegex(
                runner.PipelineError,
                label,
            ):
                runner.normalize_isolation_launcher(
                    str(forbidden),
                    required=True,
                    repo=self.repo,
                    run_root=self.run_dir,
                )

    def test_human_review_decision_binds_artifacts_and_refuses_drift(self) -> None:
        script = MODULE_PATH.with_name("review_decision.py")
        first = self.root / "human-review-accept"
        first.mkdir()
        (first / "evidence.json").write_text("{}\n", encoding="utf-8")
        first_core = {
            "result": "HUMAN_REVIEW_REQUIRED",
            "protected_deletions": ["protected.txt"],
        }
        binding = runner.compute_human_review_binding(
            self.repo,
            first,
            runner.human_review_result_core_sha256(first_core),
            first_core["protected_deletions"],
        )
        first_result = {**first_core, "human_review_binding": binding}
        runner.write_json(
            first / "result.json",
            first_result,
        )
        tampered_result = dict(first_result)
        tampered_result["protected_deletions"] = []
        runner.write_json(first / "result.json", tampered_result)
        tampered = subprocess.run(
            [
                sys.executable,
                str(script),
                "--repo",
                str(self.repo),
                "--run-dir",
                str(first),
                "--reviewer",
                "reviewer@example.test",
                "--decision",
                "accept",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(tampered.returncode, 0)
        self.assertIn("binding drifted", tampered.stderr)
        runner.write_json(first / "result.json", first_result)
        with runner.repository_lock(self.repo):
            locked = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--repo",
                    str(self.repo),
                    "--run-dir",
                    str(first),
                    "--reviewer",
                    "reviewer@example.test",
                    "--decision",
                    "accept",
                ],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        self.assertNotEqual(locked.returncode, 0)
        self.assertIn("another high-assurance pipeline holds", locked.stderr)
        self.assertFalse((first / "human-review.ndjson").exists())
        accepted = subprocess.run(
            [
                sys.executable,
                str(script),
                "--repo",
                str(self.repo),
                "--run-dir",
                str(first),
                "--reviewer",
                "reviewer@example.test",
                "--decision",
                "accept",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        decision = json.loads((first / "human-review.ndjson").read_text())
        self.assertEqual(decision["decision"], "accept")
        duplicate = subprocess.run(
            [
                sys.executable,
                str(script),
                "--repo",
                str(self.repo),
                "--run-dir",
                str(first),
                "--reviewer",
                "reviewer@example.test",
                "--decision",
                "accept",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("terminal decision", duplicate.stderr)

        second = self.root / "human-review-drift"
        second.mkdir()
        (second / "evidence.json").write_text("{}\n", encoding="utf-8")
        second_core = {
            "result": "HUMAN_REVIEW_REQUIRED",
            "protected_deletions": [],
        }
        binding = runner.compute_human_review_binding(
            self.repo,
            second,
            runner.human_review_result_core_sha256(second_core),
            second_core["protected_deletions"],
        )
        runner.write_json(
            second / "result.json",
            {**second_core, "human_review_binding": binding},
        )
        (second / "evidence.json").write_text('{"drift":true}\n', encoding="utf-8")
        refused = subprocess.run(
            [
                sys.executable,
                str(script),
                "--repo",
                str(self.repo),
                "--run-dir",
                str(second),
                "--reviewer",
                "reviewer@example.test",
                "--decision",
                "accept",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("binding drifted", refused.stderr)

        invalid = self.root / "human-review-invalid-entry"
        invalid.mkdir()
        (invalid / "nested").mkdir()
        with self.assertRaisesRegex(runner.PipelineError, "non-file entry"):
            runner.compute_human_review_binding(self.repo, invalid, "0" * 64)

        crowded = self.root / "human-review-crowded"
        crowded.mkdir()
        for index in range(257):
            (crowded / f"{index}.json").touch()
        with self.assertRaisesRegex(runner.PipelineError, "count exceeds 256"):
            runner.compute_human_review_binding(self.repo, crowded, "0" * 64)

        full = self.root / "human-review-full-capacity"
        full.mkdir()
        for index in range(256):
            (full / f"{index}.json").touch()
        full_core = {
            "result": "HUMAN_REVIEW_REQUIRED",
            "protected_deletions": [],
        }
        core_hash = runner.human_review_result_core_sha256(full_core)
        full_binding = runner.compute_human_review_binding(self.repo, full, core_hash)
        runner.write_json(
            full / "result.json",
            {**full_core, "human_review_binding": full_binding},
        )
        self.assertEqual(
            runner.compute_human_review_binding(self.repo, full, core_hash),
            full_binding,
        )

    def test_human_review_refuses_recreated_ignored_deletion_target(self) -> None:
        (self.repo / ".gitignore").write_text(".env\n", encoding="utf-8")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-qm", "ignore env")
        review_dir = self.root / "human-review-recreated-ignored"
        review_dir.mkdir()
        core = {
            "result": "HUMAN_REVIEW_REQUIRED",
            "protected_deletions": [".env"],
        }
        binding = runner.compute_human_review_binding(
            self.repo,
            review_dir,
            runner.human_review_result_core_sha256(core),
            core["protected_deletions"],
        )
        runner.write_json(
            review_dir / "result.json",
            {**core, "human_review_binding": binding},
        )
        (self.repo / ".env").write_text("SECRET=restored\n", encoding="utf-8")
        refused = subprocess.run(
            [
                sys.executable,
                str(REVIEW_PATH),
                "--repo",
                str(self.repo),
                "--run-dir",
                str(review_dir),
                "--reviewer",
                "reviewer@example.test",
                "--decision",
                "accept",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("must remain exactly missing", refused.stderr)
        self.assertFalse((review_dir / "human-review.ndjson").exists())

    def test_human_review_v2_result_fails_closed_instead_of_upgrading(self) -> None:
        review_dir = self.root / "human-review-v2"
        review_dir.mkdir()
        core = {
            "result": "HUMAN_REVIEW_REQUIRED",
            "protected_deletions": [],
        }
        legacy_binding = {
            "format": "rootloom-human-review-binding-v2",
            "repo": str(self.repo.resolve()),
            "git_head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo,
                text=True,
            ).strip(),
        }
        runner.write_json(
            review_dir / "result.json",
            {**core, "human_review_binding": legacy_binding},
        )
        refused = subprocess.run(
            [
                sys.executable,
                str(REVIEW_PATH),
                "--repo",
                str(self.repo),
                "--run-dir",
                str(review_dir),
                "--reviewer",
                "reviewer@example.test",
                "--decision",
                "accept",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("binding drifted", refused.stderr)
        self.assertFalse((review_dir / "human-review.ndjson").exists())

    def test_human_review_post_write_drift_compensates_terminal_record(self) -> None:
        review_dir = self.root / "human-review-post-write-drift"
        review_dir.mkdir()
        core = {
            "result": "HUMAN_REVIEW_REQUIRED",
            "protected_deletions": [],
        }
        binding = runner.compute_human_review_binding(
            self.repo,
            review_dir,
            runner.human_review_result_core_sha256(core),
        )
        runner.write_json(
            review_dir / "result.json",
            {**core, "human_review_binding": binding},
        )
        with mock.patch.object(
            runner,
            "compute_human_review_binding",
            side_effect=[binding, runner.PipelineError("exact target reappeared", 9)],
        ):
            with self.assertRaisesRegex(runner.PipelineError, "was compensated"):
                review_decision.decide(
                    self.repo,
                    review_dir,
                    "reviewer@example.test",
                    "accept",
                )
        self.assertEqual((review_dir / "human-review.ndjson").read_bytes(), b"")
        self.assertFalse((review_dir / "human-review-summary.json").exists())

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
            ("scripts", "regular file, not a directory"),
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
                environment=runner.build_verification_environment([], {}),
                max_output_bytes=runner.DEFAULT_MAX_COMMAND_OUTPUT_BYTES,
                max_total_output_bytes=runner.DEFAULT_MAX_VERIFICATION_OUTPUT_BYTES,
            )
        self.assertIn("verification command verify-1", str(caught.exception))
        self.assertFalse(marker.exists())

    def test_verification_detached_delayed_mutation_cannot_auto_pass(self) -> None:
        late_mutation = self.repo / "late-mutation.txt"
        ready = self.root / "late-mutation-ready"
        child = self.root / "late_mutation_child.py"
        child.write_text(
            "import pathlib, sys, time\n"
            "target, ready = map(pathlib.Path, sys.argv[1:3])\n"
            "ready.write_text('ready')\n"
            "time.sleep(3)\n"
            "target.write_text('mutated after verification returned')\n",
            encoding="utf-8",
        )
        parent = self.root / "late_mutation_parent.py"
        parent.write_text(
            "import pathlib, subprocess, sys, time\n"
            "subprocess.Popen(\n"
            "    [sys.executable, sys.argv[1], sys.argv[2], sys.argv[3]],\n"
            "    start_new_session=True,\n"
            ")\n"
            "ready = pathlib.Path(sys.argv[3])\n"
            "deadline = time.monotonic() + 2\n"
            "while not ready.exists() and time.monotonic() < deadline:\n"
            "    time.sleep(0.01)\n"
            "raise SystemExit(0 if ready.exists() else 2)\n",
            encoding="utf-8",
        )
        commands = [
            {
                "id": "verify-1",
                "argv": [
                    sys.executable,
                    str(parent),
                    str(child),
                    str(late_mutation),
                    str(ready),
                ],
            }
        ]
        expected = runner.capture_repo_state(self.repo)
        started = time.monotonic()
        verified, records = runner.run_verification(
            repo=self.repo,
            run_dir=self.run_dir,
            prefix="detached-verification",
            commands=commands,
            dry_run=False,
            timeout_seconds=3600,
            expected_state=expected,
            state_supplier=lambda: runner.capture_repo_state(self.repo),
            entrypoints={},
            environment=runner.build_verification_environment([], {}),
            max_output_bytes=runner.DEFAULT_MAX_COMMAND_OUTPUT_BYTES,
            max_total_output_bytes=runner.DEFAULT_MAX_VERIFICATION_OUTPUT_BYTES,
        )
        self.assertLess(time.monotonic() - started, 2.5)
        self.assertFalse(verified)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["command_exit_code"], 0)
        self.assertEqual(records[0]["runner_exit_code"], 125)
        self.assertEqual(records[0]["exit_code"], 125)
        self.assertTrue(records[0]["output_drain_timed_out"])
        self.assertTrue(records[0]["detached_descendant_possible"])
        self.assertFalse(late_mutation.exists())
        deadline = time.monotonic() + 4
        while not late_mutation.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(late_mutation.exists())

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

    def test_detached_child_holding_stdout_cannot_defeat_timeout(self) -> None:
        ready = self.root / "detached-ready"
        stop = self.root / "detached-stop"
        done = self.root / "detached-done"
        child = self.root / "detached_stdout_child.py"
        child.write_text(
            "import pathlib, sys, time\n"
            "ready, stop, done = map(pathlib.Path, sys.argv[1:4])\n"
            "ready.write_text('ready')\n"
            "deadline = time.monotonic() + 15\n"
            "while not stop.exists() and time.monotonic() < deadline:\n"
            "    time.sleep(0.02)\n"
            "done.write_text('done')\n",
            encoding="utf-8",
        )
        parent = self.root / "spawn_detached_stdout_child.py"
        parent.write_text(
            "import pathlib, subprocess, sys, time\n"
            "subprocess.Popen(\n"
            "    [sys.executable, sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]],\n"
            "    start_new_session=True,\n"
            ")\n"
            "ready = pathlib.Path(sys.argv[2])\n"
            "deadline = time.monotonic() + 3\n"
            "while not ready.exists() and time.monotonic() < deadline:\n"
            "    time.sleep(0.01)\n"
            "raise SystemExit(0 if ready.exists() else 2)\n",
            encoding="utf-8",
        )

        started = time.monotonic()
        try:
            result = runner.run_managed(
                [
                    sys.executable,
                    str(parent),
                    str(child),
                    str(ready),
                    str(stop),
                    str(done),
                ],
                cwd=self.root,
                timeout=1,
            )
            elapsed = time.monotonic() - started
            self.assertEqual(result.command_exit_code, 0)
            self.assertEqual(result.exit_code, 125)
            self.assertFalse(result.timed_out)
            self.assertFalse(result.leftover_process_group)
            self.assertTrue(result.output_drain_timed_out)
            self.assertTrue(result.detached_descendant_possible)
            self.assertLess(elapsed, 5)
            self.assertIn("output pipe remained open", result.output)
            self.assertFalse(done.exists())
        finally:
            stop.write_text("stop", encoding="utf-8")
            deadline = time.monotonic() + 3
            while not done.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
        self.assertTrue(done.exists())

    def test_parent_exit_starts_detached_stdout_drain_without_waiting_for_timeout(self) -> None:
        ready = self.root / "long-timeout-detached-ready"
        stop = self.root / "long-timeout-detached-stop"
        done = self.root / "long-timeout-detached-done"
        child = self.root / "long_timeout_detached_child.py"
        child.write_text(
            "import pathlib, sys, time\n"
            "ready, stop, done = map(pathlib.Path, sys.argv[1:4])\n"
            "ready.write_text('ready')\n"
            "while not stop.exists():\n"
            "    time.sleep(0.02)\n"
            "done.write_text('done')\n",
            encoding="utf-8",
        )
        parent = self.root / "long_timeout_parent.py"
        parent.write_text(
            "import pathlib, subprocess, sys, time\n"
            "subprocess.Popen(\n"
            "    [sys.executable, sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]],\n"
            "    start_new_session=True,\n"
            ")\n"
            "ready = pathlib.Path(sys.argv[2])\n"
            "deadline = time.monotonic() + 3\n"
            "while not ready.exists() and time.monotonic() < deadline:\n"
            "    time.sleep(0.01)\n"
            "raise SystemExit(0 if ready.exists() else 2)\n",
            encoding="utf-8",
        )

        started = time.monotonic()
        try:
            result = runner.run_managed(
                [
                    sys.executable,
                    str(parent),
                    str(child),
                    str(ready),
                    str(stop),
                    str(done),
                ],
                cwd=self.root,
                timeout=3600,
            )
            elapsed = time.monotonic() - started
            self.assertEqual(result.command_exit_code, 0)
            self.assertEqual(result.exit_code, 125)
            self.assertFalse(result.timed_out)
            self.assertFalse(result.leftover_process_group)
            self.assertTrue(result.output_drain_timed_out)
            self.assertTrue(result.detached_descendant_possible)
            self.assertLess(elapsed, 5)
        finally:
            stop.write_text("stop", encoding="utf-8")
            deadline = time.monotonic() + 3
            while not done.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
        self.assertTrue(done.exists())

    def test_artifact_capture_parent_exit_starts_bounded_drain(self) -> None:
        stop = self.root / "artifact-detached-stop"
        done = self.root / "artifact-detached-done"
        child = self.root / "artifact_detached_child.py"
        child.write_text(
            "import pathlib, sys, time\n"
            "stop, done = map(pathlib.Path, sys.argv[1:3])\n"
            "while not stop.exists():\n"
            "    time.sleep(0.02)\n"
            "done.write_text('done')\n",
            encoding="utf-8",
        )
        parent = self.root / "artifact_parent.py"
        parent.write_text(
            "import subprocess, sys\n"
            "subprocess.Popen(\n"
            "    [sys.executable, sys.argv[1], sys.argv[2], sys.argv[3]],\n"
            "    start_new_session=True,\n"
            ")\n",
            encoding="utf-8",
        )
        artifact = self.root / "detached-artifact.patch"
        started = time.monotonic()
        try:
            with self.assertRaises(runner.PipelineError) as caught:
                runner.stream_command_artifact(
                    [
                        sys.executable,
                        str(parent),
                        str(child),
                        str(stop),
                        str(done),
                    ],
                    repo=self.root,
                    destination=artifact,
                    max_bytes=1024,
                    timeout_seconds=3600,
                )
            self.assertIn("output pipe remained open", str(caught.exception))
            self.assertLess(time.monotonic() - started, 5)
            self.assertEqual(artifact.stat().st_size, 0)
        finally:
            stop.write_text("stop", encoding="utf-8")
            deadline = time.monotonic() + 3
            while not done.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
        self.assertTrue(done.exists())

    def test_artifact_capture_enforces_command_timeout(self) -> None:
        artifact = self.root / "timed-artifact.patch"
        started = time.monotonic()
        with self.assertRaises(runner.PipelineError) as caught:
            runner.stream_command_artifact(
                [sys.executable, "-c", "import time; time.sleep(20)"],
                repo=self.root,
                destination=artifact,
                max_bytes=1024,
                timeout_seconds=1,
            )
        self.assertIn("timed out", str(caught.exception))
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(artifact.stat().st_size, 0)

    def test_artifact_capture_restores_prior_length_after_write_failure(self) -> None:
        artifact = self.root / "partial-write.patch"
        artifact.write_bytes(b"baseline")
        original_fdopen = runner.os.fdopen

        class FailingArtifact:
            def __init__(self, descriptor: int, mode: str) -> None:
                self.handle = original_fdopen(descriptor, mode, buffering=0)

            def __enter__(self) -> "FailingArtifact":
                return self

            def __exit__(
                self,
                exc_type: object,
                exc: object,
                traceback: object,
            ) -> None:
                self.handle.close()

            def write(self, chunk: bytes) -> int:
                self.handle.write(chunk[:5])
                raise OSError("simulated artifact write failure")

        with mock.patch.object(
            runner.os,
            "fdopen",
            side_effect=lambda descriptor, mode, buffering=0: FailingArtifact(
                descriptor,
                mode,
            ),
        ):
            with self.assertRaises(OSError):
                runner.stream_command_artifact(
                    [sys.executable, "-c", "import os; os.write(1, b'x' * 100)"],
                    repo=self.root,
                    destination=artifact,
                    max_bytes=1024,
                    timeout_seconds=5,
                    append=True,
                )
        self.assertEqual(artifact.read_bytes(), b"baseline")

    def test_artifact_capture_completes_short_writes_before_claiming_success(self) -> None:
        artifact = self.root / "short-write.patch"
        artifact.write_bytes(b"baseline")
        original_fdopen = runner.os.fdopen

        class ShortWritingArtifact:
            def __init__(self, descriptor: int, mode: str) -> None:
                self.handle = original_fdopen(descriptor, mode, buffering=0)

            def __enter__(self) -> "ShortWritingArtifact":
                return self

            def __exit__(
                self,
                exc_type: object,
                exc: object,
                traceback: object,
            ) -> None:
                self.handle.close()

            def write(self, chunk: bytes) -> int:
                return self.handle.write(chunk[:3])

        with mock.patch.object(
            runner.os,
            "fdopen",
            side_effect=lambda descriptor, mode, buffering=0: ShortWritingArtifact(
                descriptor,
                mode,
            ),
        ):
            written = runner.stream_command_artifact(
                [sys.executable, "-c", "import os; os.write(1, b'x' * 100)"],
                repo=self.root,
                destination=artifact,
                max_bytes=1024,
                timeout_seconds=5,
                append=True,
            )
        self.assertEqual(written, 100)
        self.assertEqual(artifact.read_bytes(), b"baseline" + (b"x" * 100))

    def test_artifact_capture_rejects_zero_length_write_and_restores_artifact(self) -> None:
        artifact = self.root / "zero-write.patch"
        artifact.write_bytes(b"baseline")
        original_fdopen = runner.os.fdopen

        class ZeroWritingArtifact:
            def __init__(self, descriptor: int, mode: str) -> None:
                self.handle = original_fdopen(descriptor, mode, buffering=0)

            def __enter__(self) -> "ZeroWritingArtifact":
                return self

            def __exit__(
                self,
                exc_type: object,
                exc: object,
                traceback: object,
            ) -> None:
                self.handle.close()

            def write(self, chunk: bytes) -> int:
                return 0

        with mock.patch.object(
            runner.os,
            "fdopen",
            side_effect=lambda descriptor, mode, buffering=0: ZeroWritingArtifact(
                descriptor,
                mode,
            ),
        ):
            with self.assertRaises(runner.PipelineError) as caught:
                runner.stream_command_artifact(
                    [sys.executable, "-c", "import os; os.write(1, b'x' * 100)"],
                    repo=self.root,
                    destination=artifact,
                    max_bytes=1024,
                    timeout_seconds=5,
                    append=True,
                )
        self.assertIn("short write", str(caught.exception))
        self.assertEqual(artifact.read_bytes(), b"baseline")

    def test_artifact_capture_compensates_selector_setup_failure(self) -> None:
        artifact = self.root / "selector-setup.patch"
        artifact.write_bytes(b"baseline")
        with mock.patch.object(
            runner.selectors,
            "DefaultSelector",
            side_effect=OSError("simulated selector setup failure"),
        ):
            with self.assertRaises(OSError):
                runner.stream_command_artifact(
                    [sys.executable, "-c", "import time; time.sleep(20)"],
                    repo=self.root,
                    destination=artifact,
                    max_bytes=1024,
                    timeout_seconds=5,
                    append=True,
                )
        self.assertEqual(artifact.read_bytes(), b"baseline")

    def test_output_limit_terminates_log_storm_with_bounded_tail(self) -> None:
        marker = self.root / "output-limit-command-finished"
        limit = 128 * 1024
        command = (
            "import os, pathlib, sys; "
            "chunk=b'x'*65536; "
            "[(os.write(1, chunk)) for _ in range(512)]; "
            "pathlib.Path(sys.argv[1]).write_text('finished')"
        )
        started = time.monotonic()
        result = runner.run_managed(
            [sys.executable, "-c", command, str(marker)],
            cwd=self.root,
            timeout=10,
            max_output_bytes=limit,
        )
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(result.exit_code, runner.COMMAND_OUTPUT_LIMIT_EXIT)
        self.assertTrue(result.output_limit_exceeded)
        self.assertTrue(result.output_truncated)
        self.assertGreater(result.output_bytes_observed, limit)
        self.assertLessEqual(result.output_bytes_retained, limit)
        self.assertIn("exceeded output limit", result.output)
        self.assertFalse(marker.exists())

    def test_managed_input_round_trip_and_minimal_verification_environment(self) -> None:
        source = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.root),
            "LANG": "C.UTF-8",
            "ROOTLOOM_FAKE_SECRET": "must-not-pass",
            "ROOTLOOM_ALLOWED": "allowed-value",
        }
        environment = runner.build_verification_environment(
            ["ROOTLOOM_ALLOWED"],
            source,
        )
        self.assertNotIn("ROOTLOOM_FAKE_SECRET", environment)
        self.assertEqual(environment["ROOTLOOM_ALLOWED"], "allowed-value")
        with self.assertRaises(runner.PipelineError):
            runner.build_verification_environment(["INVALID-NAME"], source)
        with self.assertRaises(runner.PipelineError):
            runner.build_verification_environment(["MISSING"], source)

        command = (
            "import json, os, sys; "
            "payload=sys.stdin.read(); "
            "print(json.dumps({'payload': payload, 'environment': dict(os.environ)}))"
        )
        result = runner.run_managed(
            [sys.executable, "-c", command],
            cwd=self.root,
            timeout=5,
            input_text="round-trip",
            environment=environment,
        )
        payload = json.loads(result.output)
        self.assertEqual(result.command_exit_code, 0)
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(payload["payload"], "round-trip")
        self.assertNotIn("ROOTLOOM_FAKE_SECRET", payload["environment"])
        self.assertEqual(
            payload["environment"]["ROOTLOOM_ALLOWED"],
            "allowed-value",
        )

    def test_interrupt_after_parent_exit_cleans_original_process_group(self) -> None:
        parent_exited = self.root / "parent-exited"
        child_done = self.root / "interrupt-child-survived"
        child = self.root / "interrupt_child.py"
        child.write_text(
            "import pathlib, sys, time\n"
            "time.sleep(1)\n"
            "pathlib.Path(sys.argv[1]).write_text('survived')\n",
            encoding="utf-8",
        )
        parent = self.root / "interrupt_parent.py"
        parent.write_text(
            "import pathlib, subprocess, sys\n"
            "subprocess.Popen([sys.executable, sys.argv[1], sys.argv[2]], "
            "stdin=subprocess.DEVNULL)\n"
            "pathlib.Path(sys.argv[3]).write_text('exited')\n",
            encoding="utf-8",
        )
        real_selector = runner.selectors.DefaultSelector

        class InterruptingSelector:
            def __init__(self) -> None:
                self.delegate = real_selector()

            def register(self, *args: object, **kwargs: object) -> object:
                return self.delegate.register(*args, **kwargs)

            def unregister(self, *args: object, **kwargs: object) -> object:
                return self.delegate.unregister(*args, **kwargs)

            def select(self, timeout: float | None = None) -> object:
                if parent_exited.exists():
                    time.sleep(0.15)
                    raise KeyboardInterrupt
                return self.delegate.select(timeout)

            def close(self) -> None:
                self.delegate.close()

        with mock.patch.object(
            runner.selectors,
            "DefaultSelector",
            InterruptingSelector,
        ):
            with self.assertRaises(KeyboardInterrupt):
                runner.run_managed(
                    [
                        sys.executable,
                        str(parent),
                        str(child),
                        str(child_done),
                        str(parent_exited),
                    ],
                    cwd=self.root,
                    timeout=5,
                )
        time.sleep(1.1)
        self.assertFalse(child_done.exists())

    def test_selector_initialization_failure_reaps_started_process(self) -> None:
        marker = self.root / "selector-init-child-survived"
        command = (
            "import pathlib, sys, time; time.sleep(0.6); "
            "pathlib.Path(sys.argv[1]).write_text('survived')"
        )
        with mock.patch.object(
            runner.selectors,
            "DefaultSelector",
            side_effect=RuntimeError("selector init failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "selector init failed"):
                runner.run_managed(
                    [sys.executable, "-c", command, str(marker)],
                    cwd=self.root,
                    timeout=5,
                )
        time.sleep(0.8)
        self.assertFalse(marker.exists())

    def test_verification_batch_output_budget_stops_remaining_commands(self) -> None:
        marker = self.root / "third-verification-ran"
        commands = [
            {
                "id": "verify-1",
                "argv": [sys.executable, "-c", "import os; os.write(1, b'x' * 100)"],
            },
            {
                "id": "verify-2",
                "argv": [sys.executable, "-c", "import os; os.write(1, b'y' * 100)"],
            },
            {
                "id": "verify-3",
                "argv": [
                    sys.executable,
                    "-c",
                    "import pathlib, sys; pathlib.Path(sys.argv[1]).write_text('ran')",
                    str(marker),
                ],
            },
        ]
        expected = runner.capture_repo_state(self.repo)
        verified, records = runner.run_verification(
            repo=self.repo,
            run_dir=self.run_dir,
            prefix="verification-budget",
            commands=commands,
            dry_run=False,
            timeout_seconds=5,
            expected_state=expected,
            state_supplier=lambda: runner.capture_repo_state(self.repo),
            entrypoints={},
            environment=runner.build_verification_environment([], {}),
            max_output_bytes=128,
            max_total_output_bytes=150,
        )
        self.assertFalse(verified)
        self.assertEqual(len(records), 2)
        self.assertEqual(
            sum(record["output_bytes_retained"] for record in records),
            150,
        )
        self.assertTrue(records[-1]["verification_output_budget_exceeded"])
        self.assertFalse(marker.exists())
        ndjson = self.run_dir / "verification-budget.ndjson"
        lines = ndjson.read_bytes().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(ndjson.stat().st_size, records[-1]["artifact_bytes_written_total"])
        summary = json.loads(
            (self.run_dir / "verification-budget-summary.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(summary["format"], "rootloom-verification-summary-v2")
        self.assertEqual(summary["record_format"], "rootloom-verification-ndjson-v2")
        self.assertEqual(summary["artifact_bytes_written"], ndjson.stat().st_size)
        self.assertFalse((self.run_dir / "verification-budget.json").exists())

    def test_verification_ndjson_budget_uses_actual_serialized_bytes(self) -> None:
        commands = [
            {
                "id": "verify-1",
                "argv": [
                    sys.executable,
                    "-c",
                    "import os; os.write(1, b'\\0' * 10000)",
                ],
            }
        ]
        expected = runner.capture_repo_state(self.repo)
        serialized_output_lengths: list[int] = []
        original_dumps = runner.json.dumps

        def tracking_dumps(value: object, *args: object, **kwargs: object) -> str:
            if isinstance(value, dict) and "output" in value:
                serialized_output_lengths.append(len(str(value["output"])))
            return original_dumps(value, *args, **kwargs)

        with mock.patch.object(runner.json, "dumps", side_effect=tracking_dumps):
            verified, records = runner.run_verification(
                repo=self.repo,
                run_dir=self.run_dir,
                prefix="verification-serialized-budget",
                commands=commands,
                dry_run=False,
                timeout_seconds=5,
                expected_state=expected,
                state_supplier=lambda: runner.capture_repo_state(self.repo),
                entrypoints={},
                environment=runner.build_verification_environment([], {}),
                max_output_bytes=20_000,
                max_total_output_bytes=20_000,
                max_artifact_bytes=1500,
            )
        self.assertFalse(verified)
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["command_exit_code"], 0)
        self.assertEqual(record["runner_exit_code"], 0)
        self.assertEqual(record["exit_code"], runner.COMMAND_OUTPUT_LIMIT_EXIT)
        self.assertEqual(record["record_schema_version"], 2)
        self.assertEqual(record["output_utf8_bytes"], 10_000)
        self.assertTrue(record["artifact_output_truncated"])
        self.assertTrue(record["verification_artifact_budget_exceeded"])
        ndjson = self.run_dir / "verification-serialized-budget.ndjson"
        self.assertLessEqual(ndjson.stat().st_size, 1500)
        persisted = json.loads(ndjson.read_text(encoding="utf-8"))
        self.assertEqual(persisted["record_json_bytes"], ndjson.stat().st_size)
        self.assertEqual(
            persisted["artifact_bytes_written_total"],
            ndjson.stat().st_size,
        )
        self.assertLess(max(serialized_output_lengths), 10_000)

    def test_verification_json_byte_prediction_matches_encoded_payload(self) -> None:
        outputs = [
            "plain ascii",
            'quotes " and slash \\',
            "controls\x00\b\f\n\r\t\x1f",
            "中文与 emoji 😀",
            "surrogate \udcff",
        ]
        for output in outputs:
            with self.subTest(output=repr(output)):
                record, payload = runner.verification_record_line(
                    {
                        **runner.empty_verification_record("verify-1", ["true"]),
                        "output": output,
                        "exit_code": 0,
                    },
                    max_bytes=100_000,
                    artifact_bytes_written=17,
                )
                self.assertEqual(record["record_json_bytes"], len(payload))
                self.assertEqual(
                    record["artifact_bytes_written_total"],
                    17 + len(payload),
                )
                decoded = json.loads(payload.decode("utf-8"))
                self.assertEqual(decoded["output"], output)

    def test_log_sized_control_output_is_not_expanded_before_rejection(self) -> None:
        output = "\x00" * runner.DEFAULT_MAX_COMMAND_OUTPUT_BYTES
        serialized_output_lengths: list[int] = []
        original_dumps = runner.json.dumps

        def tracking_dumps(value: object, *args: object, **kwargs: object) -> str:
            if isinstance(value, dict) and "output" in value:
                serialized_output_lengths.append(len(str(value["output"])))
            return original_dumps(value, *args, **kwargs)

        with mock.patch.object(runner.json, "dumps", side_effect=tracking_dumps):
            record, payload = runner.verification_record_line(
                {
                    **runner.empty_verification_record("verify-1", ["true"]),
                    "output": output,
                    "exit_code": 0,
                },
                max_bytes=1500,
                artifact_bytes_written=0,
            )
        self.assertTrue(record["artifact_output_truncated"])
        self.assertEqual(
            record["output_utf8_bytes"],
            runner.DEFAULT_MAX_COMMAND_OUTPUT_BYTES,
        )
        self.assertLessEqual(len(payload), 1500)
        self.assertLess(max(serialized_output_lengths), 1000)

    def test_verification_artifact_metadata_is_preflighted_before_command(self) -> None:
        marker = self.root / "preflight-command-ran"
        commands = [
            {
                "id": "verify-1",
                "argv": [
                    sys.executable,
                    "-c",
                    "import pathlib, sys; pathlib.Path(sys.argv[1]).write_text('ran')",
                    str(marker),
                ],
            }
        ]
        expected = runner.capture_repo_state(self.repo)
        with self.assertRaises(runner.PipelineError) as caught:
            runner.run_verification(
                repo=self.repo,
                run_dir=self.run_dir,
                prefix="verification-preflight",
                commands=commands,
                dry_run=False,
                timeout_seconds=5,
                expected_state=expected,
                state_supplier=lambda: runner.capture_repo_state(self.repo),
                entrypoints={},
                environment=runner.build_verification_environment([], {}),
                max_output_bytes=1024,
                max_total_output_bytes=1024,
                max_artifact_bytes=100,
            )
        self.assertIn("too small for required structured metadata", str(caught.exception))
        self.assertFalse(marker.exists())

    def test_verification_ndjson_partial_write_is_rolled_back(self) -> None:
        def partial_write(artifact: object, payload: bytes) -> int:
            written = artifact.write(payload[:7])
            assert written == 7
            raise OSError("simulated NDJSON append failure")

        ndjson = self.run_dir / "verification-partial-append.ndjson"
        ndjson.write_bytes(b"")
        with mock.patch.object(runner, "write_all", side_effect=partial_write):
            with self.assertRaises(OSError):
                runner.append_complete_artifact(
                    ndjson,
                    b"complete-record\n",
                    expected_starting_size=0,
                )
        self.assertEqual(ndjson.read_bytes(), b"")

        target = self.run_dir / "append-target.ndjson"
        target.write_bytes(b"")
        linked = self.run_dir / "append-linked.ndjson"
        linked.symlink_to(target)
        with self.assertRaisesRegex(runner.PipelineError, "open Artifact safely"):
            runner.append_complete_artifact(
                linked,
                b"must-not-follow\n",
                expected_starting_size=0,
            )
        self.assertEqual(target.read_bytes(), b"")

    def test_verification_batch_rejects_more_than_command_ceiling(self) -> None:
        args = mock.Mock(verify=["true"] * runner.MAX_VERIFICATION_COMMANDS)
        with self.assertRaises(runner.PipelineError):
            runner.verification_commands(args)

    def test_model_stage_persists_structured_command_sidecar_on_failure(self) -> None:
        args = mock.Mock(
            dry_run=False,
            codex_bin="codex",
            stage_timeout=5,
            max_command_output_bytes=128,
        )
        result = runner.ManagedResult(
            command_exit_code=0,
            exit_code=runner.COMMAND_OUTPUT_LIMIT_EXIT,
            output="bounded tail\n",
            timed_out=False,
            leftover_process_group=False,
            output_bytes_observed=192,
            output_bytes_retained=128,
            output_truncated=True,
            output_limit_exceeded=True,
            output_drain_timed_out=False,
            detached_descendant_possible=False,
        )
        role = {
            "model": "test-model",
            "model_reasoning_effort": "high",
            "sandbox_mode": "read-only",
            "developer_instructions": "test",
        }
        with mock.patch.object(runner, "run_managed", return_value=result):
            with self.assertRaises(runner.PipelineError):
                runner.run_stage(
                    args=args,
                    repo=self.repo,
                    run_dir=self.run_dir,
                    stage_name="evidence",
                    artifact_prefix="01-evidence",
                    role=role,
                    schema={},
                    prompt="inspect",
                )
        sidecar = json.loads(
            (self.run_dir / "01-evidence-command.json").read_text(encoding="utf-8")
        )
        self.assertEqual(sidecar["stage"], "evidence")
        self.assertEqual(sidecar["output_bytes_observed"], 192)
        self.assertEqual(sidecar["output_bytes_retained"], 128)
        self.assertTrue(sidecar["output_limit_exceeded"])
        self.assertEqual(sidecar["command_exit_code"], 0)
        self.assertEqual(sidecar["runner_exit_code"], runner.COMMAND_OUTPUT_LIMIT_EXIT)

    def test_every_model_stage_rejects_detached_lifecycle_uncertainty(self) -> None:
        args = mock.Mock(
            dry_run=False,
            codex_bin="codex",
            stage_timeout=5,
            max_command_output_bytes=128,
        )
        result = runner.ManagedResult(
            command_exit_code=0,
            exit_code=runner.COMMAND_LIFECYCLE_UNCERTAIN_EXIT,
            output="detached descendant may still be running\n",
            timed_out=False,
            leftover_process_group=False,
            output_bytes_observed=0,
            output_bytes_retained=0,
            output_truncated=False,
            output_limit_exceeded=False,
            output_drain_timed_out=True,
            detached_descendant_possible=True,
        )
        with mock.patch.object(runner, "run_managed", return_value=result):
            for stage in ("evidence", "diagnosis", "implementation", "review"):
                with self.subTest(stage=stage), self.assertRaises(
                    runner.PipelineError
                ) as caught:
                    runner.run_stage(
                        args=args,
                        repo=self.repo,
                        run_dir=self.run_dir,
                        stage_name=stage,
                        artifact_prefix=f"detached-{stage}",
                        role={
                            "model": "test-model",
                            "model_reasoning_effort": "high",
                            "sandbox_mode": runner.ROLE_SANDBOXES[stage],
                            "developer_instructions": "test",
                        },
                        schema={},
                        prompt="inspect",
                    )
                self.assertIn("exit code 125", str(caught.exception))
                sidecar = json.loads(
                    (self.run_dir / f"detached-{stage}-command.json").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(sidecar["command_exit_code"], 0)
                self.assertEqual(
                    sidecar["runner_exit_code"],
                    runner.COMMAND_LIFECYCLE_UNCERTAIN_EXIT,
                )
                self.assertTrue(sidecar["detached_descendant_possible"])

    def test_compact_verification_preserves_structured_output_state(self) -> None:
        compact = json.loads(
            runner.compact_verification(
                [
                    {
                        "id": "verify-1",
                        "command": "python noisy_test.py",
                        "command_exit_code": 0,
                        "runner_exit_code": runner.COMMAND_OUTPUT_LIMIT_EXIT,
                        "exit_code": runner.COMMAND_OUTPUT_LIMIT_EXIT,
                        "output": "x" * 13000,
                        "leftover_process_group": False,
                        "timed_out": False,
                        "output_bytes_observed": 9_000_000,
                        "output_bytes_retained": 8_388_608,
                        "output_truncated": True,
                        "output_limit_exceeded": True,
                        "output_drain_timed_out": True,
                        "detached_descendant_possible": True,
                    }
                ]
            )
        )[0]
        self.assertEqual(compact["command_exit_code"], 0)
        self.assertEqual(compact["runner_exit_code"], runner.COMMAND_OUTPUT_LIMIT_EXIT)
        self.assertEqual(compact["exit_code"], runner.COMMAND_OUTPUT_LIMIT_EXIT)
        self.assertEqual(compact["output_bytes_observed"], 9_000_000)
        self.assertEqual(compact["output_bytes_retained"], 8_388_608)
        self.assertTrue(compact["output_truncated"])
        self.assertTrue(compact["output_limit_exceeded"])
        self.assertTrue(compact["output_drain_timed_out"])
        self.assertTrue(compact["detached_descendant_possible"])
        self.assertEqual(len(compact["output_tail"]), 12000)

    def test_compact_verification_has_a_global_prompt_limit(self) -> None:
        records = [
            {
                "id": f"verify-{index}",
                "command": "python noisy_test.py",
                "exit_code": 0,
                "output": "x" * 12000,
            }
            for index in range(runner.MAX_VERIFICATION_COMMANDS)
        ]
        compact = runner.compact_verification(records)
        self.assertLessEqual(len(compact), runner.MAX_VERIFICATION_PROMPT_CHARS)
        self.assertIn("verification summary truncated", compact)

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

    def test_failed_command_with_leftover_child_preserves_raw_failure_and_fails_closed(
        self,
    ) -> None:
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
        result = runner.run_managed(
            [sys.executable, str(parent), str(child), str(marker)],
            cwd=self.root,
            timeout=5,
        )
        self.assertEqual(result.command_exit_code, 7)
        self.assertEqual(result.exit_code, runner.COMMAND_LIFECYCLE_UNCERTAIN_EXIT)
        self.assertFalse(result.timed_out)
        self.assertTrue(result.leftover_process_group)
        self.assertIn("left a live process group", result.output)
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

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
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
BEGIN_REVIEW = SCRIPT.parent / "begin_review.py"
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
    ALL_CLAIM_IDS = (
        "primary-behavior",
        "owning-invariant",
        "adjacent-path",
        "auth-boundaries",
        "data-compatibility",
        "financial-boundaries",
        "ordering-and-races",
        "deployment-contract",
        "consumer-compatibility",
        "destructive-effect",
        "historical-counterexample",
    )

    @staticmethod
    def contract_sha256(payload: dict[str, object]) -> str:
        normalized = dict(payload)
        normalized.pop("contract_sha256", None)
        encoded = json.dumps(
            normalized, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("ascii")
        return hashlib.sha256(encoded).hexdigest()
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
            self.assertTrue(noisy_results[0].output_limit_exceeded)
            self.assertGreater(
                noisy_results[0].output_bytes_observed,
                noisy_results[0].output_bytes_retained,
            )
            self.assertLessEqual(len(noisy_log), noisy_budget)

    @unittest.skipIf(os.name == "nt", "POSIX process-group regression")
    def test_verification_terminates_a_leaked_descendant_process_group(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            repo = self.make_repo(Path(temporary))
            command = (
                f"{sys.executable} -c 'import subprocess,sys; "
                "subprocess.Popen([sys.executable,\"-c\",\"import time; time.sleep(30)\"],"
                "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)'"
            )
            started = time.monotonic()
            results, _log = verify(
                [command], repo=repo, timeout=10, max_output_bytes=4096
            )
            self.assertLess(time.monotonic() - started, 5)
            self.assertEqual(results[0].exit_code, 125)
            self.assertTrue(results[0].process_tree_converged)
            self.assertFalse(results[0].passed)

    def test_missing_verification_executable_is_a_bounded_failed_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            command = "rootloom-command-that-does-not-exist"
            governed = self.prepare_governed_change(
                root, repo, command=command, name="missing-command"
            )
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    *governed,
                    "--verify",
                    command,
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

    def prepare_governed_change(
        self,
        root: Path,
        repo: Path,
        *,
        command: str,
        task: str = "change product behavior",
        allowed_paths: list[str] | None = None,
        claims: tuple[str, ...] | None = None,
        name: str = "change",
    ) -> list[str]:
        review_dir = root / f"{name}-review"
        baseline = review_dir / "baseline.json"
        begun = subprocess.run(
            [
                sys.executable,
                str(BEGIN_REVIEW),
                "--repo",
                str(repo),
                "--task",
                task,
                "--output",
                str(review_dir),
                *[
                    part
                    for path in (allowed_paths or ["**"])
                    for part in ("--path", path)
                ],
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(begun.returncode, 0, begun.stderr)
        baseline_payload = json.loads(baseline.read_text(encoding="ascii"))
        baseline_sha256 = hashlib.sha256(baseline.read_bytes()).hexdigest()
        contract = review_dir / "change-contract.json"
        payload = {
            "format": "rootloom-change-contract-v1",
            "run_id": baseline_payload["run_id"],
            "nonce": baseline_payload["nonce"],
            "baseline_sha256": baseline_sha256,
            "task_sha256": baseline_payload["task_sha256"],
            "allowed_paths": allowed_paths or ["**"],
            "forbidden_paths": [],
            "root_cause_alignment": "PASS",
            "verification_commands": {"verify-1": command},
            "verification_claims": {
                claim: ["verify-1"]
                for claim in (claims or self.ALL_CLAIM_IDS)
            },
        }
        payload["contract_sha256"] = self.contract_sha256(payload)
        contract.write_text(json.dumps(payload), encoding="utf-8")
        (review_dir / "review.json").write_text(
            json.dumps(
                {
                    "format": "rootloom-review-run-v1",
                    "run_id": baseline_payload["run_id"],
                    "nonce": baseline_payload["nonce"],
                    "task_sha256": baseline_payload["task_sha256"],
                    "baseline": baseline.name,
                    "baseline_sha256": baseline_sha256,
                    "change_contract": contract.name,
                    "change_contract_sha256": payload["contract_sha256"],
                }
            ),
            encoding="ascii",
        )
        return [
            "--task",
            task,
            "--baseline",
            str(baseline),
            "--change-contract",
            str(contract),
        ]

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

    def test_begin_review_creates_operator_sealed_intake_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            output = root / "review"
            created = subprocess.run(
                [
                    sys.executable,
                    str(BEGIN_REVIEW),
                    "--repo",
                    str(repo),
                    "--task",
                    "change product behavior",
                    "--output",
                    str(output),
                    "--path",
                    "app.py",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            manifest = json.loads((output / "review.json").read_text(encoding="ascii"))
            baseline = json.loads((output / "baseline.json").read_text(encoding="ascii"))
            contract = json.loads(
                (output / "change-contract.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["run_id"], baseline["run_id"])
            self.assertEqual(manifest["nonce"], baseline["nonce"])
            self.assertEqual(manifest["baseline"], "baseline.json")
            self.assertEqual(manifest["change_contract"], "change-contract.json")
            self.assertEqual(contract["run_id"], baseline["run_id"])
            self.assertEqual(contract["nonce"], baseline["nonce"])
            self.assertEqual(
                contract["baseline_sha256"],
                hashlib.sha256((output / "baseline.json").read_bytes()).hexdigest(),
            )
            self.assertEqual(manifest["baseline_sha256"], contract["baseline_sha256"])
            self.assertEqual(
                manifest["change_contract_sha256"], contract["contract_sha256"]
            )
            refused = subprocess.run(
                [
                    sys.executable,
                    str(BEGIN_REVIEW),
                    "--repo",
                    str(repo),
                    "--task",
                    "change product behavior",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("already exists", refused.stderr)

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

    def test_analyzer_treats_dependency_manifests_and_split_stems_as_product_risk(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            repo = self.make_repo(Path(temporary))
            dependency = self.analyze(
                repo,
                "--task",
                "upgrade cryptography and fix authentication dependency",
                "--path",
                "requirements.txt",
            )
            self.assertEqual(dependency.returncode, 0, dependency.stderr)
            payload = json.loads(dependency.stdout)
            self.assertEqual(payload["minimum_tier"], 2)
            self.assertIn(
                "dependency-supply-chain", {item["id"] for item in payload["signals"]}
            )
            stemmed = self.analyze(repo, "--path", "src/auth_service.py")
            self.assertEqual(stemmed.returncode, 0, stemmed.stderr)
            self.assertIn(
                "authentication",
                {item["id"] for item in json.loads(stemmed.stdout)["signals"]},
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

    def test_analyzer_and_memory_cli_share_the_entry_limit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            repo = self.make_repo(Path(temporary))
            memory = repo / ".project-memory"
            memory.mkdir()
            collection = {
                "format": "rootloom-project-memory-v1",
                "kind": "risks",
                "entries": [
                    {
                        "summary": f"risk {index}",
                        "mitigation": "inspect current source",
                        "paths": ["src/relay.py"],
                    }
                    for index in range(1001)
                ],
            }
            (memory / "known-risks.json").write_text(
                json.dumps(collection), encoding="utf-8"
            )
            analyzed = self.analyze(repo, "--path", "src/relay.py")
            self.assertEqual(analyzed.returncode, 0, analyzed.stderr)
            payload = json.loads(analyzed.stdout)
            self.assertEqual(payload["memory"]["matches"], [])
            self.assertIn("entries exceed 1000", payload["memory"]["warnings"][0])
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
            self.assertNotEqual(context.returncode, 0)
            self.assertIn("entries exceed 1000", context.stderr)

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
            command = f"{sys.executable} -c 'assert 2 == 2'"
            governed = self.prepare_governed_change(
                root, repo, command=command, name="bundle"
            )
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
                    *governed,
                    "--verify",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["passed"])
            self.assertEqual(summary["schema_revision"], 2)
            self.assertEqual(summary["quality_status"], "VERIFIED_CHANGE")
            self.assertEqual(summary["verification_coverage"], "complete")
            self.assertEqual(summary["claim_binding"], "complete")
            self.assertEqual(summary["semantic_coverage"], "unknown")
            self.assertEqual(summary["evidence_provenance"]["baseline"], "operator-sealed")
            self.assertEqual(
                summary["evidence_provenance"]["change_contract"], "operator-sealed"
            )
            self.assertEqual(summary["evidence_provenance"]["verification_claims"], "self-declared")
            self.assertTrue(summary["hash_chain"]["valid"])
            self.assertEqual(summary["process_convergence"], "complete")
            self.assertTrue(summary["detached_descendant_possible"])
            self.assertEqual(summary["isolation"], "process-group-only")
            self.assertTrue(summary["review_manifest"]["valid"])
            self.assertEqual(summary["exit_policy"], "bundle")
            self.assertEqual(summary["process_exit_code"], 0)
            self.assertEqual(summary["changed_files"], ["app.py"])
            self.assertEqual(summary["risk"], "medium")
            self.assertTrue(summary["risk_assessment"]["risk_was_raised"])
            self.assertEqual(
                summary["verification_plan"]["status"],
                "suggested-not-executed",
            )
            self.assertIn(b"value = 2", (output / "diff.patch").read_bytes())
            self.assertIn("assert 2 == 2", (output / "test.log").read_text(encoding="utf-8"))

    def test_unrelated_passing_command_is_partial_not_verified(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            command = f"{sys.executable} -c 'assert 2 == 2'"
            governed = self.prepare_governed_change(
                root,
                repo,
                command=command,
                claims=("primary",),
                name="partial",
            )
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    *governed,
                    "--strict",
                    "--verify",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads((root / "run" / "summary.json").read_text())
            self.assertTrue(summary["commands_passed"])
            self.assertTrue(summary["capture_preserved"])
            self.assertEqual(summary["claim_binding"], "partial")
            self.assertEqual(summary["verification_coverage"], "partial")
            self.assertEqual(summary["quality_status"], "COMMANDS_PASSED")
            self.assertFalse(summary["passed"])

    def test_advisory_finalizer_does_not_block_without_governed_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            command = f"{sys.executable} -c 'assert 2 == 2'"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    "--task",
                    "change product behavior",
                    "--verify",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads((root / "run" / "summary.json").read_text())
            self.assertEqual(summary["mode"], "advisory")
            self.assertTrue(summary["commands_passed"])
            self.assertEqual(summary["verification_coverage"], "unverified")
            self.assertEqual(summary["quality_status"], "UNVERIFIED")
            self.assertEqual(summary["claim_binding"], "unverified")
            self.assertFalse(summary["baseline"]["required"])
            self.assertFalse(summary["baseline"]["provided"])
            self.assertFalse(summary["change_contract"]["required"])
            self.assertFalse(summary["passed"])

    def test_require_verified_returns_quality_exit_for_unverified_advisory(self) -> None:
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
                    "--task",
                    "change product behavior",
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                    "--require-verified",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 4, completed.stderr)
            summary = json.loads((root / "run" / "summary.json").read_text())
            self.assertEqual(summary["exit_policy"], "quality")
            self.assertEqual(summary["process_exit_code"], 4)
            self.assertEqual(summary["quality_status"], "UNVERIFIED")

    def test_quality_exit_policy_distinguishes_no_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    "--allow-no-change",
                    "--exit-policy",
                    "quality",
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 3, completed.stderr)
            summary = json.loads((root / "run" / "summary.json").read_text())
            self.assertEqual(summary["quality_status"], "NO_CHANGE")
            self.assertEqual(summary["process_exit_code"], 3)

    def test_self_declared_strict_evidence_is_mechanically_verified_not_passed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            baseline = root / "baseline.json"
            analyzed = self.analyze(repo, "--task", "change product behavior", "--write-baseline", str(baseline))
            self.assertEqual(analyzed.returncode, 0, analyzed.stderr)
            contract = root / "contract.json"
            command = f"{sys.executable} -c 'assert True'"
            baseline_payload = json.loads(baseline.read_text(encoding="ascii"))
            payload = {
                "format": "rootloom-change-contract-v1",
                "run_id": baseline_payload["run_id"],
                "nonce": baseline_payload["nonce"],
                "baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
                "task_sha256": baseline_payload["task_sha256"],
                "allowed_paths": ["**"],
                "forbidden_paths": [],
                "root_cause_alignment": "PASS",
                "verification_commands": {"verify-1": command},
                "verification_claims": {
                    claim: ["verify-1"] for claim in self.ALL_CLAIM_IDS
                },
            }
            payload["contract_sha256"] = self.contract_sha256(payload)
            contract.write_text(json.dumps(payload), encoding="utf-8")
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    "--task",
                    "change product behavior",
                    "--baseline",
                    str(baseline),
                    "--change-contract",
                    str(contract),
                    "--verify",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads((root / "run" / "summary.json").read_text())
            self.assertEqual(summary["quality_status"], "MECHANICALLY_VERIFIED")
            self.assertFalse(summary["passed"])
            self.assertEqual(summary["evidence_provenance"]["baseline"], "self-declared")
            self.assertEqual(summary["evidence_provenance"]["change_contract"], "self-declared")
            self.assertFalse(summary["review_manifest"]["valid"])

    def test_symlinked_baseline_is_rejected_before_hashing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            target = root / "target-baseline.json"
            target.write_text("{}", encoding="ascii")
            baseline = root / "baseline-link.json"
            try:
                baseline.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    "--task",
                    "change product behavior",
                    "--strict",
                    "--baseline",
                    str(baseline),
                    "--change-contract",
                    str(root / "missing-contract.json"),
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("baseline must not be a symlink", completed.stderr)
            self.assertFalse((root / "run" / "summary.json").exists())

    def test_structured_claim_binding_requires_target_in_command(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            baseline = root / "baseline.json"
            analyzed = self.analyze(repo, "--task", "change product behavior", "--write-baseline", str(baseline))
            self.assertEqual(analyzed.returncode, 0, analyzed.stderr)
            baseline_payload = json.loads(baseline.read_text(encoding="ascii"))
            payload = {
                "format": "rootloom-change-contract-v1",
                "run_id": baseline_payload["run_id"],
                "nonce": baseline_payload["nonce"],
                "baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
                "task_sha256": baseline_payload["task_sha256"],
                "allowed_paths": ["**"],
                "forbidden_paths": [],
                "root_cause_alignment": "PASS",
                "verification_commands": {
                    "verify-1": f"{sys.executable} -m unittest tests.test_engineering_change"
                },
                "verification_claims": {
                    "primary": [
                        {
                            "id": "primary-behavior",
                            "command_ids": ["verify-1"],
                            "target": "tests/test_missing.py::test_missing",
                            "expected_evidence": "targeted regression executes",
                            "evidence_kind": "regression-test",
                        }
                    ]
                },
            }
            payload["contract_sha256"] = self.contract_sha256(payload)
            contract = root / "contract.json"
            contract.write_text(json.dumps(payload), encoding="utf-8")
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    "--task",
                    "change product behavior",
                    "--baseline",
                    str(baseline),
                    "--change-contract",
                    str(contract),
                    "--verify",
                    payload["verification_commands"]["verify-1"],
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("target is not present", completed.stderr)

    def test_strict_finalizer_requires_governed_evidence(self) -> None:
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
                    "--task",
                    "change product behavior",
                    "--strict",
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("requires --baseline", completed.stderr)
            self.assertFalse((root / "run" / "summary.json").exists())

    def test_untracked_content_rewrite_changes_capture_and_patch_contains_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            command = (
                f"{sys.executable} -c "
                "'__import__(\"pathlib\").Path(\"new_service.py\").write_text(\"value = \\\"B\\\"\\n\")'"
            )
            governed = self.prepare_governed_change(
                root,
                repo,
                command=command,
                allowed_paths=["new_service.py"],
                name="untracked-rewrite",
            )
            (repo / "new_service.py").write_text('value = "A"\n', encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    *governed,
                    "--verify",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr)
            summary = json.loads((root / "run" / "summary.json").read_text())
            self.assertFalse(summary["capture_preserved"])
            self.assertEqual(summary["quality_status"], "FAILED")
            fingerprint = summary["repository_capture"]["untracked"][0]
            self.assertEqual(fingerprint["kind"], "file")
            self.assertEqual(len(fingerprint["sha256"]), 64)
            self.assertIn(b'value = "B"', (root / "run" / "diff.patch").read_bytes())

    def test_ignored_sensitive_baseline_is_metadata_only_and_guards_deletion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
            subprocess.run(["git", "add", ".gitignore"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "ignore env"], cwd=repo, check=True)
            secret = repo / ".env"
            secret.write_text("SECRET_VALUE=never-read\n", encoding="utf-8")
            command = f"{sys.executable} -c 'assert True'"
            governed = self.prepare_governed_change(
                root, repo, command=command, name="ignored-secret"
            )
            baseline_path = root / "ignored-secret-review" / "baseline.json"
            baseline = json.loads(baseline_path.read_text())
            metadata = next(
                item
                for item in baseline["snapshot"]["sensitive_paths"]
                if item["path"] == ".env"
            )
            self.assertFalse(metadata["content_read"])
            self.assertNotIn("sha256", metadata)
            self.assertNotIn("never-read", baseline_path.read_text())
            secret.unlink()
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    *governed,
                    "--verify",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 10, completed.stderr)
            self.assertIn(".env", completed.stdout)

    def test_ignored_file_below_secret_like_directory_is_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            (repo / ".gitignore").write_text("private-secrets/\n", encoding="utf-8")
            subprocess.run(["git", "add", ".gitignore"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "ignore secrets"], cwd=repo, check=True)
            secrets = repo / "private-secrets"
            secrets.mkdir()
            (secrets / "runtime.json").write_text(
                '{"value":"never-read-nested-secret"}\n', encoding="utf-8"
            )
            baseline = root / "nested-secret-baseline.json"
            completed = self.analyze(repo, "--write-baseline", str(baseline))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(baseline.read_text())
            metadata = next(
                item
                for item in payload["snapshot"]["sensitive_paths"]
                if item["path"] == "private-secrets/runtime.json"
            )
            self.assertFalse(metadata["content_read"])
            self.assertNotIn("sha256", metadata)
            self.assertNotIn("never-read-nested-secret", baseline.read_text())

    def test_sensitive_directory_and_symlink_are_metadata_only_without_recursion(self) -> None:
        if os.name == "nt":
            self.skipTest("symlink creation is not portable on Windows CI")
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            private = repo / "private-config"
            private.mkdir()
            (private / "nested.txt").write_text("never capture this text", encoding="utf-8")
            (repo / "credential-link").symlink_to(
                "private-config", target_is_directory=True
            )
            baseline = root / "metadata-baseline.json"
            completed = self.analyze(
                repo,
                "--sensitive-path",
                "private-config",
                "--sensitive-path",
                "credential-link",
                "--write-baseline",
                str(baseline),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(baseline.read_text())
            metadata = {
                item["path"]: item for item in payload["snapshot"]["sensitive_paths"]
            }
            self.assertEqual(metadata["private-config"]["kind"], "directory")
            self.assertEqual(metadata["credential-link"]["kind"], "symlink")
            self.assertEqual(metadata["credential-link"]["target"], "private-config")
            self.assertNotIn("never capture this text", baseline.read_text())

    def test_untracked_binary_is_hashed_without_entering_text_patch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            command = f"{sys.executable} -c 'assert __import__(\"pathlib\").Path(\"asset.bin\").exists()'"
            governed = self.prepare_governed_change(
                root,
                repo,
                command=command,
                allowed_paths=["asset.bin"],
                name="binary",
            )
            (repo / "asset.bin").write_bytes(b"binary\x00payload")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    *governed,
                    "--verify",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = json.loads((root / "run" / "summary.json").read_text())
            fingerprint = summary["repository_capture"]["untracked"][0]
            self.assertEqual(fingerprint["size"], len(b"binary\x00payload"))
            self.assertEqual(len(fingerprint["sha256"]), 64)
            self.assertEqual(fingerprint["text_patch"], "not-text-or-over-limit")
            self.assertNotIn(b"binary\x00payload", (root / "run" / "diff.patch").read_bytes())

    @unittest.skipIf(os.name == "nt", "non-UTF-8 paths are a POSIX filesystem contract")
    def test_non_utf8_git_path_is_serialized_with_ascii_escapes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            command = f"{sys.executable} -c 'assert True'"
            governed = self.prepare_governed_change(
                root, repo, command=command, name="non-utf8"
            )
            raw_path = os.path.join(os.fsencode(repo), b"bad-\xff.py")
            try:
                descriptor = os.open(raw_path, os.O_CREAT | os.O_WRONLY, 0o600)
            except OSError as exc:
                self.skipTest(f"filesystem rejects non-UTF-8 names: {exc}")
            try:
                os.write(descriptor, b"value = 1\n")
            finally:
                os.close(descriptor)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    *governed,
                    "--verify",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            encoded = (root / "run" / "summary.json").read_bytes()
            self.assertIn(b"bad-\\udcff.py", encoded)
            json.loads(encoded.decode("ascii"))

    def test_change_contract_blocks_out_of_scope_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            command = f"{sys.executable} -c 'assert True'"
            governed = self.prepare_governed_change(
                root,
                repo,
                command=command,
                allowed_paths=["src/**"],
                name="scope",
            )
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    *governed,
                    "--verify",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr)
            summary = json.loads((root / "run" / "summary.json").read_text())
            self.assertFalse(summary["change_contract"]["scope_valid"])
            self.assertEqual(summary["tests"], [])
            self.assertEqual(summary["quality_status"], "FAILED")

    def test_output_directory_requires_ownership_and_no_change_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            occupied = root / "occupied"
            occupied.mkdir()
            (occupied / "personal.txt").write_text("mine", encoding="utf-8")
            refused = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(occupied),
                    "--allow-no-change",
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("ownership marker", refused.stderr)
            self.assertEqual((occupied / "personal.txt").read_text(), "mine")

            allowed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "empty"),
                    "--allow-no-change",
                    "--verify",
                    f"{sys.executable} -c 'assert True'",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            summary = json.loads((root / "empty" / "summary.json").read_text())
            self.assertEqual(summary["quality_status"], "NO_CHANGE")
            self.assertEqual(summary["process_exit_code"], 0)
            self.assertFalse(summary["passed"])
            self.assertTrue((root / "empty" / ".rootloom-engineering-bundle.json").is_file())

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
            self.assertIn("exceeds configured 1-byte budget", oversized.stderr)
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
            command = (
                f"{sys.executable} -c "
                "'assert not __import__(\"pathlib\").Path(\".env\").exists()'"
            )
            governed = self.prepare_governed_change(
                root,
                repo,
                command=command,
                task="remove obsolete secret file",
                name="delete-secret",
            )
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
                *governed,
                "--verify",
                command,
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
            command = f"{sys.executable} -c 'assert True'"
            governed = self.prepare_governed_change(
                root,
                repo,
                command=command,
                task="rename secret configuration",
                name="rename-secret",
            )
            secret.rename(repo / "config.txt")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    *governed,
                    "--risk",
                    "high",
                    "--verify",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                completed.returncode, 10, f"stdout={completed.stdout}\nstderr={completed.stderr}"
            )
            self.assertIn(".env", completed.stdout)

    def test_verification_cannot_hide_a_sensitive_deletion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            secret = repo / ".env"
            secret.write_text("TOKEN=redacted\n", encoding="utf-8")
            subprocess.run(["git", "add", ".env"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "env"], cwd=repo, check=True)
            command = (
                f"{sys.executable} -c "
                "'__import__(\"pathlib\").Path(\".env\").unlink()'"
            )
            governed = self.prepare_governed_change(
                root,
                repo,
                command=command,
                task="change product behavior",
                name="verification-delete",
            )
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    *governed,
                    "--risk",
                    "high",
                    "--verify",
                    command,
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
            command = (
                f"{sys.executable} -c "
                "'__import__(\"pathlib\").Path(\".env\").unlink()'"
            )
            governed = self.prepare_governed_change(
                root,
                repo,
                command=command,
                task="change product behavior",
                name="untracked-secret",
            )
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(root / "run"),
                    *governed,
                    "--risk",
                    "high",
                    "--verify",
                    command,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                completed.returncode, 10, f"stdout={completed.stdout}\nstderr={completed.stderr}"
            )
            self.assertIn("verification introduced dangerous deletions", completed.stdout)

    def test_verification_worktree_mutation_marks_bundle_failed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = self.make_repo(root)
            output = root / "run"
            command = (
                f"{sys.executable} -c "
                "'__import__(\"pathlib\").Path(\"app.py\").write_text(\"value = 3\\n\")'"
            )
            governed = self.prepare_governed_change(
                root, repo, command=command, name="verification-mutation"
            )
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--output",
                    str(output),
                    *governed,
                    "--risk",
                    "medium",
                    "--verify",
                    command,
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
            self.assertIn(b"value = 3", (output / "diff.patch").read_bytes())
            self.assertIn(
                "verification changed the tracked patch or captured path/content set",
                (output / "test.log").read_text(encoding="utf-8"),
            )

    def test_unborn_repository_writes_a_bundle_without_head(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-change-", dir=Path.home()) as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            command = f"{sys.executable} -c 'assert True'"
            governed = self.prepare_governed_change(
                root, repo, command=command, name="unborn"
            )
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
                    *governed,
                    "--risk",
                    "low",
                    "--verify",
                    command,
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
            self.assertIn(b"value = 1", (output / "diff.patch").read_bytes())

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
            governed = self.prepare_governed_change(
                root,
                repo,
                command=f"{sys.executable} -c 'assert True'",
                name="no-verification",
            )
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
                    *governed,
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

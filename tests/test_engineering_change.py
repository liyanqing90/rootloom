from __future__ import annotations

import json
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
sys.path.insert(0, str(SCRIPT.parent))
from runner.verification import split_command


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
            self.assertIn(b"value = 2", (output / "diff.patch").read_bytes())
            self.assertIn("assert 2 == 2", (output / "test.log").read_text(encoding="utf-8"))

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

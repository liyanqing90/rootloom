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
    / "project-memory"
    / "scripts"
    / "project_memory.py"
)


class ProjectMemoryTests(unittest.TestCase):
    def test_context_does_not_initialize_missing_memory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-memory-", dir=Path.home()) as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            context = subprocess.run(
                [sys.executable, str(SCRIPT), "--repo", str(repo), "context"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(context.returncode, 0, context.stderr)
            self.assertEqual(json.loads(context.stdout)["failures"], [])
            self.assertFalse((repo / ".project-memory").exists())

    def test_init_and_record_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rootloom-memory-", dir=Path.home()) as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            initialized = subprocess.run(
                [sys.executable, str(SCRIPT), "--repo", str(repo), "init"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(initialized.returncode, 0, initialized.stderr)
            recorded = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "record-failure",
                    "--summary",
                    "reconnect failed",
                    "--root-cause",
                    "state race",
                    "--fix",
                    "serialize transitions",
                    "--path",
                    "src/relay.py",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            payload = json.loads(
                (repo / ".project-memory" / "failures.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["entries"][0]["root_cause"], "state race")
            context = subprocess.run(
                [sys.executable, str(SCRIPT), "--repo", str(repo), "context"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(context.returncode, 0, context.stderr)
            self.assertEqual(json.loads(context.stdout)["failures"][0]["fix"], "serialize transitions")


if __name__ == "__main__":
    unittest.main()

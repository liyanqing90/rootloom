#!/usr/bin/env python3
"""Run an optional live Personal Core Hook smoke test."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile


PLUGIN_ID = "rootloom@rootloom"
REPO_ROOT = Path(__file__).resolve().parents[1]


def run(argv: list[str], *, env: dict[str, str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="rootloom-live-", dir=Path.home()) as temporary:
        root = Path(temporary)
        codex_home = root / "codex-home"
        codex_home.mkdir()
        auth = Path.home() / ".codex" / "auth.json"
        if auth.is_file():
            (codex_home / "auth.json").symlink_to(auth)
        repo = root / "sample"
        repo.mkdir()
        run(["git", "init", "-q"], env=os.environ.copy(), cwd=repo)
        (repo / "README.md").write_text("# Live sample\n", encoding="utf-8")

        env = os.environ.copy()
        env["CODEX_HOME"] = str(codex_home)
        env["ROOTLOOM_ALLOW_UNTRUSTED"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        marketplace = run(
            ["codex", "plugin", "marketplace", "add", str(REPO_ROOT), "--json"],
            env=env,
            cwd=REPO_ROOT,
        )
        install = run(
            ["codex", "plugin", "add", PLUGIN_ID, "--json"], env=env, cwd=REPO_ROOT
        )
        plugin_list = run(
            ["codex", "plugin", "list", "--json"], env=env, cwd=REPO_ROOT
        )
        plugin_path: Path | None = None
        if plugin_list.returncode == 0:
            for item in json.loads(plugin_list.stdout).get("installed", []):
                if item.get("pluginId") == PLUGIN_ID and item.get("source", {}).get("path"):
                    plugin_path = Path(item["source"]["path"])
                    break
        setup = (
            plugin_path / "skills" / "setup-rootloom" / "scripts" / "setup_rootloom.py"
            if plugin_path
            else Path("missing")
        )
        base = ["python3", str(setup), "--codex-home", str(codex_home), "--json"]
        applied = run([*base, "apply", "--preset", "personal"], env=env, cwd=REPO_ROOT)
        model = run(
            [
                "codex",
                "exec",
                "--dangerously-bypass-hook-trust",
                "--ephemeral",
                "-C",
                str(repo),
                "Read AGENTS.md without editing files and reply exactly SEEDED_OK when it contains rootloom:managed-start.",
            ],
            env=env,
            cwd=repo,
            timeout=180,
        )
        seeded = repo / "AGENTS.md"
        rolled_back = run([*base, "rollback"], env=env, cwd=REPO_ROOT)
        passed = (
            marketplace.returncode == 0
            and install.returncode == 0
            and plugin_list.returncode == 0
            and plugin_path is not None
            and applied.returncode == 0
            and model.returncode == 0
            and seeded.is_file()
            and "rootloom:managed-start" in seeded.read_text(encoding="utf-8")
            and "SEEDED_OK" in model.stdout
            and rolled_back.returncode == 0
            and not (codex_home / "AGENTS.md").exists()
        )
        print(
            json.dumps(
                {
                    "passed": passed,
                    "plugin_path": str(plugin_path) if plugin_path else None,
                    "model_returncode": model.returncode,
                    "model_stdout_tail": model.stdout[-500:],
                    "model_stderr_tail": model.stderr[-500:],
                },
                indent=2,
            )
        )
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Exercise Rootloom Personal Core against the installed Codex CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any


PLUGIN_ID = "rootloom@rootloom"
REPO_ROOT = Path(__file__).resolve().parents[1]


def run(argv: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def installed_plugin_path(payload: dict[str, Any]) -> Path | None:
    for item in payload.get("installed", []):
        if item.get("pluginId") == PLUGIN_ID:
            raw = item.get("source", {}).get("path")
            return Path(raw) if raw else None
    return None


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="rootloom-compatibility-", dir=Path.home()) as temporary:
        codex_home = Path(temporary) / "codex-home"
        codex_home.mkdir()
        env = os.environ.copy()
        env["CODEX_HOME"] = str(codex_home)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        commands: dict[str, subprocess.CompletedProcess[str]] = {
            "version": run(["codex", "--version"], env=env),
            "marketplace": run(
                ["codex", "plugin", "marketplace", "add", str(REPO_ROOT), "--json"],
                env=env,
            ),
            "install": run(["codex", "plugin", "add", PLUGIN_ID, "--json"], env=env),
            "plugin_list": run(["codex", "plugin", "list", "--json"], env=env),
        }
        plugin_path: Path | None = None
        if commands["plugin_list"].returncode == 0:
            try:
                plugin_path = installed_plugin_path(json.loads(commands["plugin_list"].stdout))
            except json.JSONDecodeError:
                pass
        setup_script = (
            plugin_path / "skills" / "setup-rootloom" / "scripts" / "setup_rootloom.py"
            if plugin_path
            else Path("missing")
        )
        setup_base = [
            "python3",
            str(setup_script),
            "--codex-home",
            str(codex_home),
            "--json",
        ]
        plugin_install_side_effects = [
            path
            for path in (
                "AGENTS.md",
                "rules/rootloom.rules",
                ".rootloom/components.json",
                ".rootloom/state.json",
            )
            if (codex_home / path).exists()
        ]
        commands["setup_install"] = run(
            [*setup_base, "install", "--preset", "personal"], env=env
        )
        commands["setup_status"] = run([*setup_base, "status"], env=env)
        commands["setup_upgrade"] = run([*setup_base, "upgrade"], env=env)

        rules = codex_home / "rules" / "rootloom.rules"
        decisions: dict[str, str | None] = {}
        for name, argv in (
            ("commit", ["git", "commit", "-m", "compatibility"]),
            ("push", ["git", "push", "origin", "main"]),
            ("reset", ["git", "reset", "--hard"]),
        ):
            completed = run(
                ["codex", "execpolicy", "check", "--rules", str(rules), "--", *argv],
                env=env,
            )
            commands[f"rule_{name}"] = completed
            try:
                decisions[name] = json.loads(completed.stdout).get("decision")
            except json.JSONDecodeError:
                decisions[name] = None

        commands["rollback"] = run([*setup_base, "rollback"], env=env)
        leftovers = [
            path
            for path in ("AGENTS.md", "rules/rootloom.rules", ".rootloom/components.json")
            if (codex_home / path).exists()
        ]
        failed = {
            name: {
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-500:],
                "stderr_tail": completed.stderr[-500:],
            }
            for name, completed in commands.items()
            if completed.returncode != 0
        }
        passed = (
            plugin_path is not None
            and not failed
            and not plugin_install_side_effects
            and decisions == {"commit": "allow", "push": "prompt", "reset": "forbidden"}
            and not leftovers
            and not (codex_home / "agents").exists()
            and not (codex_home / "high-assurance.config.toml").exists()
        )
        print(
            json.dumps(
                {
                    "passed": passed,
                    "codex_version": commands["version"].stdout.strip(),
                    "plugin_path": str(plugin_path) if plugin_path else None,
                    "plugin_install_side_effects": plugin_install_side_effects,
                    "rule_decisions": decisions,
                    "managed_leftovers_after_rollback": leftovers,
                    "failed_commands": failed,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

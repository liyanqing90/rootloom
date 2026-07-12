#!/usr/bin/env python3
"""Exercise Rootloom's offline plugin and setup contracts against the active Codex CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any


PLUGIN_ID = "rootloom@rootloom"
REPO_ROOT = Path(__file__).resolve().parents[1]


def run(
    argv: list[str],
    *,
    env: dict[str, str],
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def installed_plugin_path(payload: dict[str, Any]) -> Path | None:
    for item in payload.get("installed", []):
        if item.get("pluginId") != PLUGIN_ID:
            continue
        raw = item.get("source", {}).get("path")
        return Path(raw) if raw else None
    return None


def main() -> int:
    with tempfile.TemporaryDirectory(
        prefix="rootloom-compatibility-",
        dir=Path.home(),
    ) as temporary:
        codex_home = Path(temporary) / "codex-home"
        codex_home.mkdir()
        env = os.environ.copy()
        env["CODEX_HOME"] = str(codex_home)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        commands: dict[str, subprocess.CompletedProcess[str]] = {}
        commands["version"] = run(["codex", "--version"], env=env)
        commands["marketplace"] = run(
            ["codex", "plugin", "marketplace", "add", str(REPO_ROOT), "--json"],
            env=env,
        )
        commands["install"] = run(
            ["codex", "plugin", "add", PLUGIN_ID, "--json"],
            env=env,
        )
        commands["plugin_list"] = run(
            ["codex", "plugin", "list", "--json"],
            env=env,
        )

        plugin_path: Path | None = None
        if commands["plugin_list"].returncode == 0:
            try:
                plugin_path = installed_plugin_path(json.loads(commands["plugin_list"].stdout))
            except json.JSONDecodeError:
                plugin_path = None

        if plugin_path is None:
            setup_script = Path("missing")
            validate_setup = Path("missing")
        else:
            setup_script = (
                plugin_path
                / "skills"
                / "setup-rootloom"
                / "scripts"
                / "setup_rootloom.py"
            )
            validate_setup = (
                plugin_path
                / "skills"
                / "high-assurance-coding-change"
                / "scripts"
                / "validate_setup.py"
            )

        setup_base = [
            "python3",
            str(setup_script),
            "--codex-home",
            str(codex_home),
            "--json",
        ]
        config_path = codex_home / "config.toml"
        config_before_setup = config_path.read_bytes() if config_path.is_file() else None
        commands["setup_apply"] = run([*setup_base, "apply", "--preset", "full"], env=env)
        commands["setup_status"] = run([*setup_base, "status"], env=env)
        commands["routing_validate"] = run(["python3", str(validate_setup)], env=env)
        commands["profile_parse"] = run(
            ["codex", "--profile", "high-assurance", "exec", "--help"],
            env=env,
        )

        rules = codex_home / "rules" / "rootloom.rules"
        rule_results: dict[str, str | None] = {}
        for name, expected, argv in (
            ("commit", "allow", ["git", "commit", "-m", "compatibility"]),
            ("push", "prompt", ["git", "push", "origin", "main"]),
            ("reset", "forbidden", ["git", "reset", "--hard"]),
        ):
            completed = run(
                ["codex", "execpolicy", "check", "--rules", str(rules), "--", *argv],
                env=env,
            )
            commands[f"rule_{name}"] = completed
            try:
                decision = json.loads(completed.stdout).get("decision")
            except json.JSONDecodeError:
                decision = None
            rule_results[name] = decision
            if decision != expected:
                break

        commands["rollback"] = run([*setup_base, "rollback", "--all"], env=env)
        managed_paths = (
            "AGENTS.md",
            "high-assurance.config.toml",
            "agents/evidence_explorer.toml",
            "agents/root_cause_reviewer.toml",
            "agents/implementation_worker.toml",
            "agents/verification_reviewer.toml",
            "rules/rootloom.rules",
            ".rootloom/components.json",
        )
        leftovers = [path for path in managed_paths if (codex_home / path).exists()]
        config_after_rollback = config_path.read_bytes() if config_path.is_file() else None
        config_restored = config_after_rollback == config_before_setup
        failed_commands = {
            name: {
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-800:],
                "stderr_tail": completed.stderr[-800:],
            }
            for name, completed in commands.items()
            if completed.returncode != 0
        }
        passed = (
            plugin_path is not None
            and not failed_commands
            and rule_results
            == {"commit": "allow", "push": "prompt", "reset": "forbidden"}
            and not leftovers
            and config_restored
        )
        print(
            json.dumps(
                {
                    "passed": passed,
                    "codex_version": commands["version"].stdout.strip(),
                    "plugin_path": str(plugin_path) if plugin_path else None,
                    "rule_decisions": rule_results,
                    "managed_leftovers_after_rollback": leftovers,
                    "preexisting_config_restored": config_restored,
                    "failed_commands": failed_commands,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

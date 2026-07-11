from __future__ import annotations

import difflib
import json
import os
import subprocess
import tempfile
import tomllib
from pathlib import Path


PLUGIN_ID = "rootloom@rootloom"
REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="rootloom-live-", dir=Path.home()) as temp_dir:
        codex_home = Path(temp_dir) / "codex-home"
        codex_home.mkdir()
        auth_source = Path.home() / ".codex" / "auth.json"
        if auth_source.is_file():
            (codex_home / "auth.json").symlink_to(auth_source)

        root = Path(temp_dir) / "live-sample"
        root.mkdir()
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / "README.md").write_text(
            "# Live Seeder Sample\n\nA live Codex hook verification repository.\n",
            encoding="utf-8",
        )
        (root / "package.json").write_text(
            json.dumps(
                {
                    "name": "live-seeder-sample",
                    "description": "A live hook verification repository.",
                    "scripts": {"test": "node --test", "lint": "eslint ."},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / "package-lock.json").write_text(
            json.dumps({"name": "live-seeder-sample", "lockfileVersion": 3}) + "\n",
            encoding="utf-8",
        )
        (root / "src").mkdir()

        env = os.environ.copy()
        env["CODEX_HOME"] = str(codex_home)
        env["ROOTLOOM_ALLOW_UNTRUSTED"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        marketplace = subprocess.run(
            ["codex", "plugin", "marketplace", "add", str(REPO_ROOT), "--json"],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        install = subprocess.run(
            ["codex", "plugin", "add", PLUGIN_ID, "--json"],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        plugin_list = subprocess.run(
            ["codex", "plugin", "list", "--json"],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        plugin_path: Path | None = None
        if plugin_list.returncode == 0:
            payload = json.loads(plugin_list.stdout)
            for item in payload.get("installed", []):
                if item.get("pluginId") == PLUGIN_ID:
                    source_path = item.get("source", {}).get("path")
                    if source_path:
                        plugin_path = Path(source_path)
                    break

        setup_script = (
            plugin_path
            / "skills"
            / "setup-rootloom"
            / "scripts"
            / "setup_rootloom.py"
            if plugin_path
            else Path("missing")
        )
        setup_base = ["python3", str(setup_script), "--codex-home", str(codex_home), "--json"]
        component_catalog = subprocess.run(
            [*setup_base, "list-components"],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        engineering_plan = subprocess.run(
            [*setup_base, "plan", "--preset", "engineering"],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        engineering_apply = subprocess.run(
            [*setup_base, "apply", "--preset", "engineering"],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        engineering_policy_path = (
            codex_home / ".rootloom" / "components.json"
        )
        engineering_policy = (
            json.loads(engineering_policy_path.read_text(encoding="utf-8"))
            if engineering_policy_path.is_file()
            else {}
        )
        engineering_config_path = codex_home / "config.toml"
        if engineering_config_path.is_file():
            with engineering_config_path.open("rb") as handle:
                engineering_config = tomllib.load(handle)
        else:
            engineering_config = {}
        engineering_agents = engineering_config.get("agents", {})
        managed_agent_limits_absent = all(
            key not in engineering_agents
            for key in ("max_threads", "max_depth", "interrupt_message")
        )
        delegation_roles_absent = all(
            not (codex_home / "agents" / f"{name}.toml").exists()
            for name in (
                "evidence_explorer",
                "root_cause_reviewer",
                "implementation_worker",
                "verification_reviewer",
            )
        )
        engineering_ready = (
            (codex_home / "AGENTS.md").is_file()
            and (codex_home / "rules" / "rootloom.rules").is_file()
            and managed_agent_limits_absent
            and delegation_roles_absent
            and not (codex_home / "high-assurance.config.toml").exists()
            and engineering_policy.get("hooks", {}).get("project-guidance-hook") is True
            and engineering_policy.get("hooks", {}).get("subagent-audit-hook") is False
        )
        engineering_rollback = subprocess.run(
            [*setup_base, "rollback"],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        setup_plan = subprocess.run(
            [*setup_base, "plan"], capture_output=True, text=True, env=env, timeout=30
        )
        setup_apply = subprocess.run(
            [*setup_base, "apply"], capture_output=True, text=True, env=env, timeout=30
        )
        setup_status = subprocess.run(
            [*setup_base, "status"], capture_output=True, text=True, env=env, timeout=30
        )
        rules_path = codex_home / "rules" / "rootloom.rules"
        rule_check = subprocess.run(
            [
                "codex",
                "execpolicy",
                "check",
                "--rules",
                str(rules_path),
                "--",
                "git",
                "commit",
                "-m",
                "smoke",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        managed_paths = [
            codex_home / "AGENTS.md",
            codex_home / "config.toml",
            codex_home / "high-assurance.config.toml",
            *(codex_home / "agents" / f"{name}.toml" for name in (
                "evidence_explorer",
                "root_cause_reviewer",
                "implementation_worker",
                "verification_reviewer",
            )),
            rules_path,
        ]
        before_runtime = {
            str(path.relative_to(codex_home)): path.read_bytes()
            for path in managed_paths
            if path.is_file()
        }
        command = [
            "codex",
            "--profile",
            "high-assurance",
            "exec",
            "--dangerously-bypass-hook-trust",
            "--ephemeral",
            "-C",
            str(root),
            "This is a read-only hook smoke test. Do not modify files. Read AGENTS.md and reply exactly SEEDED_OK if it contains the rootloom managed marker.",
        ]
        result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=180)
        runtime_changed = [
            relative
            for relative, value in before_runtime.items()
            if not (codex_home / relative).is_file()
            or (codex_home / relative).read_bytes() != value
        ]
        config_before = before_runtime.get("config.toml", b"").decode("utf-8")
        config_after = (codex_home / "config.toml").read_text(encoding="utf-8")
        config_runtime_diff = "".join(
            difflib.unified_diff(
                config_before.splitlines(keepends=True),
                config_after.splitlines(keepends=True),
                fromfile="config.toml.before-runtime",
                tofile="config.toml.after-runtime",
            )
        )
        agents_path = root / "AGENTS.md"
        content = agents_path.read_text(encoding="utf-8") if agents_path.exists() else ""
        global_guidance = codex_home / "AGENTS.md"
        profile_path = codex_home / "high-assurance.config.toml"
        profile_ready = profile_path.is_file()
        global_ready = (
            global_guidance.is_file()
            and "rootloom:managed-start"
            in global_guidance.read_text(encoding="utf-8")
        )
        roles_ready = all(
            (codex_home / "agents" / f"{name}.toml").is_file()
            for name in (
                "evidence_explorer",
                "root_cause_reviewer",
                "implementation_worker",
                "verification_reviewer",
            )
        )
        rule_decision = None
        if rule_check.returncode == 0:
            rule_decision = json.loads(rule_check.stdout).get("decision")
        setup_rollback = subprocess.run(
            [*setup_base, "rollback"], capture_output=True, text=True, env=env, timeout=30
        )
        passed = (
            marketplace.returncode == 0
            and install.returncode == 0
            and plugin_list.returncode == 0
            and plugin_path is not None
            and component_catalog.returncode == 0
            and engineering_plan.returncode == 0
            and engineering_apply.returncode == 0
            and engineering_ready
            and engineering_rollback.returncode == 0
            and setup_plan.returncode == 0
            and setup_apply.returncode == 0
            and setup_status.returncode == 0
            and global_ready
            and profile_ready
            and roles_ready
            and rule_decision == "allow"
            and result.returncode == 0
            and "rootloom:managed-start" in content
            and "SEEDED_OK" in result.stdout
            and setup_rollback.returncode == 0
            and not global_guidance.exists()
        )
        print(
            json.dumps(
                {
                    "passed": passed,
                    "isolated_codex_home": True,
                    "marketplace_returncode": marketplace.returncode,
                    "install_returncode": install.returncode,
                    "plugin_list_returncode": plugin_list.returncode,
                    "plugin_path": str(plugin_path) if plugin_path else None,
                    "component_catalog_returncode": component_catalog.returncode,
                    "engineering_plan_returncode": engineering_plan.returncode,
                    "engineering_apply_returncode": engineering_apply.returncode,
                    "engineering_rollback_returncode": engineering_rollback.returncode,
                    "engineering_ready": engineering_ready,
                    "setup_plan_returncode": setup_plan.returncode,
                    "setup_apply_returncode": setup_apply.returncode,
                    "setup_status_returncode": setup_status.returncode,
                    "setup_rollback_returncode": setup_rollback.returncode,
                    "global_ready_before_rollback": global_ready,
                    "profile_ready_before_rollback": profile_ready,
                    "roles_ready_before_rollback": roles_ready,
                    "commit_rule_decision": rule_decision,
                    "returncode": result.returncode,
                    "agents_created": agents_path.exists(),
                    "managed_marker": "rootloom:managed-start" in content,
                    "model_acknowledged": "SEEDED_OK" in result.stdout,
                    "marketplace_stderr_tail": marketplace.stderr[-600:],
                    "install_stderr_tail": install.stderr[-600:],
                    "setup_stderr_tail": setup_apply.stderr[-600:],
                    "rollback_stderr_tail": setup_rollback.stderr[-600:],
                    "rollback_stdout_tail": setup_rollback.stdout[-1200:],
                    "managed_files_changed_by_runtime": runtime_changed,
                    "config_runtime_diff": config_runtime_diff,
                    "stderr_tail": result.stderr[-1200:],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

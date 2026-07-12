#!/usr/bin/env python3
"""Validate the repository's public plugin, documentation, and release contract."""

from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
PLUGIN = ROOT / "plugins" / "rootloom"
MANIFEST = PLUGIN / ".codex-plugin" / "plugin.json"
HOOKS = PLUGIN / "hooks" / "hooks.json"
SKILLS_DIR = PLUGIN / "skills"
SYSTEM_ASSETS = PLUGIN / "assets" / "system"
SCANNER = (
    PLUGIN
    / "skills"
    / "seed-project-guidance"
    / "scripts"
    / "seed_project_guidance.py"
)
COMPONENT_HOOK = PLUGIN / "hooks" / "run_component_hook.py"
REQUIRED_SKILLS = {
    "setup-rootloom",
    "seed-project-guidance",
    "refine-project-guidance",
    "record-engineering-decision",
    "operating-coding-change",
    "operating-code-review",
    "operating-high-risk-change",
    "high-assurance-coding-change",
}

WORKFLOW_CONTRACTS = {
    SYSTEM_ASSETS / "AGENTS.md": (
        "Tier 0 Direct",
        "Tier 1 Scoped",
        "Tier 2 Governed",
        "Intent",
        "Context",
        "Tools",
        "Constraints",
        "Verification",
    ),
    SKILLS_DIR / "operating-coding-change" / "SKILL.md": (
        "Software 3.0 = Intent + Context + Tools + Constraints + Verification",
        "Tier 0 Direct",
        "Tier 1 Scoped",
        "ROOT_CAUSE_ALIGNMENT",
        "MITIGATION",
        "provenance record",
        "adjacent negative",
    ),
    SKILLS_DIR / "operating-code-review" / "SKILL.md": (
        "ROOT_CAUSE_ALIGNMENT: PASS | FAIL | NOT_APPLICABLE",
        "false fix",
        "original failure path",
        "unattributed model summary",
        "adjacent negative",
    ),
    SKILLS_DIR / "operating-high-risk-change" / "SKILL.md": (
        "Tier 2 Governed",
        "Intent + Context + Tools + Constraints + Verification",
        "competing hypotheses",
        "ROOT_CAUSE_ALIGNMENT: PASS",
        "MITIGATION",
        "material runtime or external evidence",
        "adjacent negative",
    ),
    SKILLS_DIR / "high-assurance-coding-change" / "SKILL.md": (
        "Tier 1 Scoped",
        "Tier 2 Governed",
        "ROOT_CAUSE_ALIGNMENT: PASS",
        "do not establish factual truth",
        "evidence provenance",
        "existing provenance ID",
    ),
    SKILLS_DIR / "record-engineering-decision" / "SKILL.md": (
        "durable repository-owned engineering decision",
        "fact, inference, or unresolved uncertainty",
        "does not prove the conclusion true",
    ),
}

SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
LOCAL_LINK = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
HTML_SOURCE = re.compile(r"(?:src|href)=[\"']([^\"']+)[\"']")
ACTION_USE = re.compile(r"^\s*uses:\s*[^\s@]+@([^\s#]+)", re.MULTILINE)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[opusr]_[A-Za-z0-9]{20,}\b"),
)
TODO_MARKER = "[TO" + "DO:"


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path.relative_to(ROOT)}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON: {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"expected JSON object: {path.relative_to(ROOT)}")
        return {}
    return value


def validate_marketplace(errors: list[str]) -> None:
    payload = load_json(MARKETPLACE, errors)
    if payload.get("name") != "rootloom":
        errors.append("marketplace name must be rootloom")
    if payload.get("interface", {}).get("displayName") != "Rootloom":
        errors.append("marketplace displayName must be Rootloom")
    plugins = payload.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        errors.append("marketplace must contain exactly one plugin entry")
        return
    entry = plugins[0]
    if not isinstance(entry, dict):
        errors.append("marketplace plugin entry must be an object")
        return
    if entry.get("name") != "rootloom":
        errors.append("marketplace plugin name mismatch")
    source = entry.get("source")
    if source != {"source": "local", "path": "./plugins/rootloom"}:
        errors.append("marketplace source must target ./plugins/rootloom")
    policy = entry.get("policy")
    if policy != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}:
        errors.append("marketplace policy must be AVAILABLE/ON_INSTALL")


def validate_manifest(errors: list[str]) -> None:
    payload = load_json(MANIFEST, errors)
    if payload.get("name") != PLUGIN.name:
        errors.append("plugin folder and manifest name must match")
    version = payload.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        errors.append("plugin version must be strict semver")
    elif f"## [{version}]" not in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"):
        errors.append("plugin version must have a CHANGELOG release section")
    for field in ("description", "license", "repository", "homepage"):
        if not payload.get(field):
            errors.append(f"plugin manifest is missing {field}")
    if "hooks" in payload:
        errors.append("hooks must be discovered from hooks/hooks.json, not declared in plugin.json")
    interface = payload.get("interface")
    if not isinstance(interface, dict):
        errors.append("plugin manifest is missing interface metadata")
        return
    for field in (
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "capabilities",
        "defaultPrompt",
    ):
        if not interface.get(field):
            errors.append(f"plugin interface is missing {field}")
    if interface.get("displayName") != "Rootloom":
        errors.append("plugin displayName must be Rootloom")
    prompts = interface.get("defaultPrompt")
    if isinstance(prompts, list):
        if len(prompts) > 3:
            errors.append("plugin defaultPrompt supports at most three entries")
        if any(not isinstance(item, str) or len(item) > 128 for item in prompts):
            errors.append("plugin defaultPrompt entries must be strings of at most 128 characters")
    for field in ("composerIcon", "logo", "logoDark"):
        raw_path = interface.get(field)
        if not isinstance(raw_path, str) or not raw_path.startswith("./"):
            errors.append(f"plugin interface {field} must be a relative path")
            continue
        target = (PLUGIN / raw_path).resolve()
        if not target.is_relative_to(PLUGIN.resolve()) or not target.is_file():
            errors.append(f"plugin interface {field} does not resolve to a file")


def validate_hooks(errors: list[str]) -> None:
    payload = load_json(HOOKS, errors)
    session_hooks = payload.get("hooks", {}).get("SessionStart") if payload else None
    if not isinstance(session_hooks, list) or len(session_hooks) != 1:
        errors.append("hooks must define exactly one SessionStart entry")
        return
    entry = session_hooks[0]
    if entry.get("matcher") != "startup|resume|clear":
        errors.append("SessionStart matcher must remain startup|resume|clear")
    commands = entry.get("hooks")
    if not isinstance(commands, list) or len(commands) != 1:
        errors.append("SessionStart must contain exactly one command hook")
        return
    command = commands[0]
    if command.get("type") != "command":
        errors.append("SessionStart hook must be a command hook")
    raw_command = command.get("command", "")
    if (
        "$PLUGIN_ROOT" not in raw_command
        or "run_component_hook.py" not in raw_command
        or "project-guidance-hook" not in raw_command
    ):
        errors.append("SessionStart must resolve its selectable component gate through $PLUGIN_ROOT")
    timeout = command.get("timeout")
    if not isinstance(timeout, int) or timeout < 1 or timeout > 30:
        errors.append("SessionStart timeout must be between 1 and 30 seconds")
    if not SCANNER.is_file():
        errors.append("SessionStart scanner is missing")
    if not COMPONENT_HOOK.is_file():
        errors.append("selectable component Hook gate is missing")

    subagent_hooks = payload.get("hooks", {}).get("SubagentStart") if payload else None
    if not isinstance(subagent_hooks, list) or len(subagent_hooks) != 1:
        errors.append("hooks must define exactly one SubagentStart entry")
        return
    subagent_entry = subagent_hooks[0]
    if subagent_entry.get("matcher") != "*":
        errors.append("SubagentStart matcher must cover every child agent")
    handlers = subagent_entry.get("hooks")
    if not isinstance(handlers, list) or len(handlers) != 1:
        errors.append("SubagentStart must contain exactly one command hook")
        return
    subagent_command = handlers[0].get("command", "")
    if (
        "$PLUGIN_ROOT" not in subagent_command
        or "run_component_hook.py" not in subagent_command
        or "subagent-audit-hook" not in subagent_command
    ):
        errors.append("SubagentStart must resolve its selectable component gate through $PLUGIN_ROOT")
    if not (PLUGIN / "hooks" / "subagent_budget.py").is_file():
        errors.append("Subagent budget Hook script is missing")


def validate_skills(errors: list[str]) -> None:
    discovered = {path.parent.name for path in SKILLS_DIR.glob("*/SKILL.md")}
    missing = REQUIRED_SKILLS - discovered
    extra = discovered - REQUIRED_SKILLS
    if missing:
        errors.append(f"missing required Skills: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"unexpected unvalidated Skills: {', '.join(sorted(extra))}")
    for name in sorted(discovered):
        skill = SKILLS_DIR / name / "SKILL.md"
        content = skill.read_text(encoding="utf-8")
        if not content.startswith("---\n") or f"name: {name}" not in content[:800]:
            errors.append(f"Skill frontmatter name is invalid: {name}")
        if TODO_MARKER in content:
            errors.append(f"Skill contains an unresolved TODO placeholder: {name}")
        metadata = skill.parent / "agents" / "openai.yaml"
        if not metadata.is_file():
            errors.append(f"Skill UI metadata is missing: {name}")
        else:
            metadata_text = metadata.read_text(encoding="utf-8")
            if f"${name}" not in metadata_text or "default_prompt:" not in metadata_text:
                errors.append(f"Skill UI metadata default prompt is invalid: {name}")


def load_toml(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            payload = tomllib.load(handle)
    except FileNotFoundError:
        errors.append(f"missing file: {path.relative_to(ROOT)}")
        return {}
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"invalid TOML: {path.relative_to(ROOT)}: {exc}")
        return {}
    return payload


def validate_system_assets(errors: list[str]) -> None:
    guidance = SYSTEM_ASSETS / "AGENTS.md"
    if not guidance.is_file():
        errors.append("managed global AGENTS.md template is missing")
    else:
        text = guidance.read_text(encoding="utf-8")
        if "rootloom:managed-start" not in text:
            errors.append("global AGENTS.md template is not managed")
        if "rootloom:managed-end" not in text:
            errors.append("global AGENTS.md template has no managed end marker")
        if len(text.encode("utf-8")) > 16_384:
            errors.append("global AGENTS.md template exceeds the 16 KiB suite budget")

    expected_agents = {
        "evidence_explorer": "read-only",
        "root_cause_reviewer": "read-only",
        "implementation_worker": "workspace-write",
        "verification_reviewer": "read-only",
    }
    for name, sandbox in expected_agents.items():
        path = SYSTEM_ASSETS / "agents" / f"{name}.toml"
        payload = load_toml(path, errors)
        if not payload:
            continue
        for field in ("name", "description", "model", "model_reasoning_effort", "developer_instructions"):
            if not payload.get(field):
                errors.append(f"custom agent {name} is missing {field}")
        if payload.get("name") != name:
            errors.append(f"custom agent filename/name mismatch: {name}")
        if payload.get("sandbox_mode") != sandbox:
            errors.append(f"custom agent {name} must use {sandbox}")

    profile = load_toml(SYSTEM_ASSETS / "profiles" / "high-assurance.config.toml", errors)
    if profile:
        if profile.get("approval_policy") != "on-request":
            errors.append("high-assurance profile must use on-request approval")
        if profile.get("sandbox_mode") != "workspace-write":
            errors.append("high-assurance profile must use workspace-write")
        if profile.get("agents", {}).get("max_threads") != 4:
            errors.append("high-assurance profile max_threads must be 4")
        if profile.get("agents", {}).get("max_depth") != 1:
            errors.append("high-assurance profile max_depth must be 1")

    rules = SYSTEM_ASSETS / "rules" / "rootloom.rules"
    if not rules.is_file():
        errors.append("Rootloom Rules template is missing")
    else:
        rules_text = rules.read_text(encoding="utf-8")
        for expected in (
            'pattern = ["git", "commit"]',
            'pattern = ["git", "push"]',
            'pattern = ["git", "reset", "--hard"]',
        ):
            if expected not in rules_text:
                errors.append(f"Rules template is missing contract: {expected}")

    setup_script = (
        SKILLS_DIR
        / "setup-rootloom"
        / "scripts"
        / "setup_rootloom.py"
    )
    if not setup_script.is_file():
        errors.append("setup script is missing")
    else:
        setup_text = setup_script.read_text(encoding="utf-8")
        for contract in (
            '"skills-only"',
            '"guidance"',
            '"engineering"',
            '"delegated"',
            '"full"',
            '"delegation-control"',
            '"high-assurance"',
            '"project-guidance-hook"',
            '"subagent-audit-hook"',
            "setup_lock",
            '"before_mode"',
            "setup failed and compensation was incomplete",
            "rollback failed and compensation was incomplete",
        ):
            if contract not in setup_text:
                errors.append(f"setup script is missing capability contract: {contract}")

    scanner_text = SCANNER.read_text(encoding="utf-8") if SCANNER.is_file() else ""
    for contract in (
        "guidance_lock",
        "guidance_changed_during_seed",
        "_safe_repo_file",
    ):
        if contract not in scanner_text:
            errors.append(f"project seeder is missing safety contract: {contract}")

    runner = (
        SKILLS_DIR
        / "high-assurance-coding-change"
        / "scripts"
        / "run_pipeline.py"
    )
    if not runner.is_file():
        errors.append("high-assurance runner is missing")
    else:
        runner_text = runner.read_text(encoding="utf-8")
        for contract in (
            'RUNNER_VERSION = "2.5"',
            "file_metadata_fingerprint",
            "sensitive_untracked_paths",
            "state_untracked_manifests",
            "redacted_untracked_metadata",
            '"--sensitive-path"',
            '"--redact-untracked-dotfiles"',
            '"--allow-protected-path-delete"',
            "validate_protected_changes",
            '"HUMAN_REVIEW_REQUIRED"',
            "post_implementation_state = capture_state(check_topology=True)",
            "post_review_state = capture_state(check_topology=True)",
            "max_ignored_paths",
            "validate_verification_coverage",
            '"provenance_ids"',
            '"evidence_ids"',
        ):
            if contract not in runner_text:
                errors.append(f"high-assurance runner is missing contract: {contract}")


def validate_workflow_contracts(errors: list[str]) -> None:
    legacy_tier = re.compile(r"\bR[1-4]\b")
    for path, contracts in WORKFLOW_CONTRACTS.items():
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            errors.append(f"missing workflow contract file: {path.relative_to(ROOT)}")
            continue
        for contract in contracts:
            if contract not in content:
                errors.append(
                    f"workflow contract missing in {path.relative_to(ROOT)}: {contract}"
                )
        if legacy_tier.search(content):
            errors.append(
                f"legacy R1-R4 tier vocabulary remains in {path.relative_to(ROOT)}"
            )

    for path in (
        ROOT / "README.md",
        ROOT / "README.zh-CN.md",
        ROOT / "docs" / "architecture.md",
        ROOT / "docs" / "architecture.zh-CN.md",
    ):
        content = path.read_text(encoding="utf-8")
        for tier in ("Tier 0 Direct", "Tier 1 Scoped", "Tier 2 Governed"):
            if tier not in content:
                errors.append(
                    f"public tier documentation missing in {path.relative_to(ROOT)}: {tier}"
                )
        if legacy_tier.search(content):
            errors.append(
                f"legacy R1-R4 tier vocabulary remains in {path.relative_to(ROOT)}"
            )


def iter_public_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() in {
            ".md",
            ".json",
            ".yml",
            ".yaml",
            ".toml",
            ".rules",
            ".py",
            ".sh",
        }:
            files.append(path)
    return sorted(files)


def validate_links(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        links = [*LOCAL_LINK.findall(content), *HTML_SOURCE.findall(content)]
        for raw in links:
            target_text = raw.strip().split(maxsplit=1)[0].strip("<>\"'")
            if not target_text or target_text.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target_text = target_text.split("#", 1)[0].split("?", 1)[0]
            if not target_text:
                continue
            target = (path.parent / target_text).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not target.exists():
                errors.append(
                    f"broken local link in {path.relative_to(ROOT)}: {raw}"
                )


def validate_source_files(errors: list[str]) -> None:
    for path in sorted(ROOT.rglob("*.py")):
        if ".git" in path.parts:
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"Python syntax error in {path.relative_to(ROOT)}: {exc}")
    for path in sorted(ROOT.rglob("*.svg")):
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            errors.append(f"invalid SVG XML in {path.relative_to(ROOT)}: {exc}")


def validate_workflows(errors: list[str]) -> None:
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        content = path.read_text(encoding="utf-8")
        for ref in ACTION_USE.findall(content):
            if not re.fullmatch(r"[0-9a-f]{40}", ref):
                errors.append(
                    f"GitHub Action is not pinned to a full commit SHA in {path.relative_to(ROOT)}: {ref}"
                )


def validate_repository_hygiene(errors: list[str]) -> None:
    required = (
        ROOT / "README.md",
        ROOT / "README.zh-CN.md",
        ROOT / "LICENSE",
        ROOT / "CONTRIBUTING.md",
        ROOT / "CONTRIBUTING.zh-CN.md",
        ROOT / "SECURITY.md",
        ROOT / "CODE_OF_CONDUCT.md",
        ROOT / "CHANGELOG.md",
        ROOT / "AGENTS.md",
        ROOT / "docs" / "architecture.md",
        ROOT / "docs" / "architecture.zh-CN.md",
        ROOT / "docs" / "guidance-design.md",
        ROOT / "docs" / "guidance-design.zh-CN.md",
        ROOT / "docs" / "maturity.md",
        ROOT / "docs" / "maturity.zh-CN.md",
        ROOT / "docs" / "setup.md",
        ROOT / "docs" / "setup.zh-CN.md",
        ROOT / "examples" / "AGENTS.project.md",
        ROOT / "tests" / "compatibility_smoke.py",
    )
    for path in required:
        if not path.is_file():
            errors.append(f"missing project file: {path.relative_to(ROOT)}")
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.stat().st_size > 1_000_000:
            errors.append(f"unexpected file larger than 1 MB: {path.relative_to(ROOT)}")
    for path in iter_public_text_files():
        content = path.read_text(encoding="utf-8")
        if TODO_MARKER in content:
            errors.append(f"unresolved TODO placeholder in {path.relative_to(ROOT)}")
        if path.is_relative_to(ROOT / "tests"):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                errors.append(f"secret-like content in {path.relative_to(ROOT)}")


def validate_maturity_contract(errors: list[str]) -> None:
    contracts = {
        ROOT / "docs" / "maturity.md": (
            "early-stage, single-maintainer",
            "do not yet demonstrate broad adoption",
            "does not prove the conclusion true",
            "scheduled latest-version probe",
            "does not collect telemetry from user repositories",
            "Do not turn a process-conformance rate into a product-quality claim",
            "GEB article is acknowledged as informal design inspiration",
        ),
        ROOT / "docs" / "maturity.zh-CN.md": (
            "早期、单维护者",
            "尚不能证明广泛采用",
            "不能证明模型陈述为真",
            "定时使用最新版本探测",
            "不从用户仓库收集遥测",
            "不能把流程遵从率包装成产品质量结论",
            "GEB 文章仅作为",
        ),
    }
    for path, expected in contracts.items():
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        for contract in expected:
            if contract not in content:
                errors.append(
                    f"maturity boundary missing in {path.relative_to(ROOT)}: {contract}"
                )

    workflow = ROOT / ".github" / "workflows" / "codex-compatibility.yml"
    try:
        content = workflow.read_text(encoding="utf-8")
    except FileNotFoundError:
        errors.append("missing Codex latest-version compatibility probe")
        return
    for contract in (
        "schedule:",
        "workflow_dispatch:",
        "@openai/codex@latest",
        "make check",
        "make compatibility-smoke",
    ):
        if contract not in content:
            errors.append(f"Codex compatibility probe is missing contract: {contract}")


def main() -> int:
    errors: list[str] = []
    validate_marketplace(errors)
    validate_manifest(errors)
    validate_hooks(errors)
    validate_skills(errors)
    validate_system_assets(errors)
    validate_workflow_contracts(errors)
    validate_links(errors)
    validate_source_files(errors)
    validate_workflows(errors)
    validate_repository_hygiene(errors)
    validate_maturity_contract(errors)
    if errors:
        print("Repository validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

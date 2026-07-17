#!/usr/bin/env python3
"""Validate Rootloom Personal Core's public repository contract."""

from __future__ import annotations

import ast
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
PLUGIN = ROOT / "plugins" / "rootloom"
MANIFEST = PLUGIN / ".codex-plugin" / "plugin.json"
HOOKS = PLUGIN / "hooks" / "hooks.json"
SKILLS = PLUGIN / "skills"
SYSTEM = PLUGIN / "assets" / "system"
EXPECTED_SKILLS = {
    "engineering-change",
    "operating-code-review",
    "operating-coding-change",
    "operating-high-risk-change",
    "project-memory",
    "record-engineering-decision",
    "refine-project-guidance",
    "seed-project-guidance",
    "setup-rootloom",
}
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
ACTION_USE = re.compile(r"^\s*uses:\s*[^\s@]+@([^\s#]+)", re.MULTILINE)
LOCAL_LINK = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
HTML_SRC = re.compile(r'<(?:img|source)\b[^>]*\bsrc="([^"]+)"', re.IGNORECASE)
HTML_REF = re.compile(
    r'<(?:a|img|link|script|source)\b[^>]*\b(?:href|src)="([^"]+)"',
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[opusr]_[A-Za-z0-9]{20,}\b"),
)


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing file: {path.relative_to(ROOT)}")
        return {}
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON: {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"expected JSON object: {path.relative_to(ROOT)}")
        return {}
    return payload


def validate_marketplace(errors: list[str]) -> None:
    payload = load_json(MARKETPLACE, errors)
    if payload.get("name") != "rootloom":
        errors.append("marketplace name must be rootloom")
    plugins = payload.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        errors.append("marketplace must contain exactly one plugin")
        return
    entry = plugins[0]
    if not isinstance(entry, dict) or entry.get("name") != "rootloom":
        errors.append("marketplace plugin name must be rootloom")
        return
    if entry.get("source") != {"source": "local", "path": "./plugins/rootloom"}:
        errors.append("marketplace must point to ./plugins/rootloom")


def validate_manifest(errors: list[str]) -> None:
    payload = load_json(MANIFEST, errors)
    if payload.get("name") != "rootloom":
        errors.append("plugin name must be rootloom")
    version = payload.get("version")
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        errors.append("plugin version must be strict semver")
    elif f"## [{version}]" not in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"):
        errors.append("plugin version must have a CHANGELOG section")
    else:
        producer_contracts = {
            SKILLS / "engineering-change" / "scripts" / "runner" / "baseline.py": (
                f'PRODUCER_VERSION = "{version}"'
            ),
            SKILLS / "engineering-change" / "scripts" / "finalize_change.py": (
                f'"producer_version": "{version}"'
            ),
        }
        for path, marker in producer_contracts.items():
            if marker not in path.read_text(encoding="utf-8"):
                errors.append(
                    f"plugin and evidence producer versions differ: {path.relative_to(ROOT)}"
                )
    for field in ("description", "author", "homepage", "repository", "license", "skills"):
        if not payload.get(field):
            errors.append(f"plugin manifest is missing {field}")
    interface = payload.get("interface")
    if not isinstance(interface, dict):
        errors.append("plugin interface metadata is missing")
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
    prompts = interface.get("defaultPrompt")
    if not isinstance(prompts, list) or len(prompts) > 3:
        errors.append("plugin defaultPrompt must be a list with at most three entries")
    elif any(not isinstance(item, str) or len(item) > 128 for item in prompts):
        errors.append("plugin defaultPrompt entries must be strings <= 128 chars")
    public_copy = " ".join(
        str(value)
        for value in (
            payload.get("description", ""),
            interface.get("shortDescription", ""),
            interface.get("longDescription", ""),
        )
    ).casefold()
    if "inspectable" not in public_copy:
        errors.append("plugin positioning must describe an inspectable workflow")
    for overclaim in ("quality layer", "verifiable", "verified change"):
        if overclaim in public_copy:
            errors.append(f"plugin positioning overclaims assurance: {overclaim}")
    for field in ("composerIcon", "logo", "logoDark"):
        raw = interface.get(field)
        if not isinstance(raw, str) or not raw.startswith("./"):
            errors.append(f"plugin interface {field} must be relative")
            continue
        target = (PLUGIN / raw).resolve()
        if not target.is_relative_to(PLUGIN.resolve()) or not target.is_file():
            errors.append(f"plugin interface {field} does not resolve to a file")


def frontmatter_name(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\n(?P<body>.*?)\n---\n", text, re.DOTALL)
    if not match:
        return None
    name = re.search(r"^name:\s*([^\n]+)$", match.group("body"), re.MULTILINE)
    return name.group(1).strip() if name else None


def validate_skills(errors: list[str]) -> None:
    actual = {path.parent.name for path in SKILLS.glob("*/SKILL.md")}
    if actual != EXPECTED_SKILLS:
        errors.append(
            "skill catalog mismatch: expected "
            + ", ".join(sorted(EXPECTED_SKILLS))
            + "; found "
            + ", ".join(sorted(actual))
        )
    for name in sorted(actual):
        path = SKILLS / name / "SKILL.md"
        if frontmatter_name(path) != name:
            errors.append(f"Skill frontmatter name mismatch: {path.relative_to(ROOT)}")
        agent = SKILLS / name / "agents" / "openai.yaml"
        if not agent.is_file():
            errors.append(f"Skill is missing agents/openai.yaml: {name}")
    forbidden = (
        SKILLS / "high-assurance-coding-change" / "SKILL.md",
        SYSTEM / "profiles" / "high-assurance.config.toml",
    )
    for path in forbidden:
        if path.exists():
            errors.append(f"Assurance artifact must not ship on main: {path.relative_to(ROOT)}")
    if any((SYSTEM / "agents").glob("*.toml")):
        errors.append("Personal Core must not ship custom-agent TOMLs")


def validate_hooks(errors: list[str]) -> None:
    payload = load_json(HOOKS, errors)
    hooks = payload.get("hooks")
    if not isinstance(hooks, dict) or set(hooks) != {"SessionStart"}:
        errors.append("Personal Core must expose exactly one SessionStart Hook type")
        return
    entries = hooks["SessionStart"]
    if not isinstance(entries, list) or len(entries) != 1:
        errors.append("SessionStart must contain exactly one entry")
        return
    entry = entries[0]
    handlers = entry.get("hooks") if isinstance(entry, dict) else None
    if entry.get("matcher") != "startup|resume|clear":
        errors.append("SessionStart matcher must remain startup|resume|clear")
    if not isinstance(handlers, list) or len(handlers) != 1:
        errors.append("SessionStart must contain exactly one command")
        return
    command = handlers[0]
    raw = command.get("command", "") if isinstance(command, dict) else ""
    if "$PLUGIN_ROOT" not in raw or "run_component_hook.py" not in raw or "project-guidance-hook" not in raw:
        errors.append("SessionStart must route through the managed component gate")


def validate_personal_contracts(errors: list[str]) -> None:
    global_guidance = SYSTEM / "AGENTS.md"
    global_text = global_guidance.read_text(encoding="utf-8")
    global_lines = len(global_text.splitlines())
    global_bytes = len(global_text.encode("utf-8"))
    if not 30 <= global_lines <= 45 or not 3_000 <= global_bytes <= 4_096:
        errors.append(
            "global AGENTS.md must remain approximately 3-4 KiB and 30-45 lines"
        )
    seeder_text = (
        SKILLS / "seed-project-guidance" / "scripts" / "seed_project_guidance.py"
    ).read_text(encoding="utf-8")
    if "MAX_SESSION_CONTEXT_BYTES = 4 * 1024" not in seeder_text:
        errors.append("SessionStart additional context must remain capped at 4 KiB")
    if 'permission_mode == "plan"' not in seeder_text:
        errors.append("SessionStart project context must remain disabled in Plan sessions")
    intelligence_text = (
        SKILLS / "engineering-change" / "scripts" / "runner" / "intelligence.py"
    ).read_text(encoding="utf-8")
    if "include_project_memory: bool = False" not in intelligence_text:
        errors.append("Analyzer Project Memory must remain an explicit default-off input")
    for path, label in (
        (
            SKILLS / "engineering-change" / "scripts" / "analyze_change.py",
            "Analyzer",
        ),
        (
            SKILLS / "engineering-change" / "scripts" / "finalize_change.py",
            "Finalizer",
        ),
    ):
        if '"--include-project-memory"' not in path.read_text(encoding="utf-8"):
            errors.append(f"{label} must expose explicit Project Memory opt-in")
    root_guidance = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    root_rules = [line for line in root_guidance.splitlines() if line.startswith("- ")]
    if not 5 <= len(root_rules) <= 8:
        errors.append("root AGENTS.md must contain only 5-8 repository-wide rules")
    for directory, label in (
        (ROOT / ".codex" / "plans", "one-time task plans"),
        (ROOT / "docs" / "releases", "repository publication records"),
    ):
        if directory.exists() and any(path.is_file() for path in directory.rglob("*")):
            errors.append(f"repository must not retain {label}: {directory.relative_to(ROOT)}")

    contracts = {
        PLUGIN / "hooks" / "run_component_hook.py": (
            "type(version) is not int",
            "version != 1",
            "component policy version must be the integer 1",
        ),
        SKILLS / "seed-project-guidance" / "scripts" / "seed_project_guidance.py": (
            "temporary_project_context",
            "MAX_SESSION_CONTEXT_BYTES",
            "_render_session_context",
            'permission_mode == "plan"',
            "creating or updating AGENTS.md",
            "guidance only when the user explicitly invokes",
        ),
        SKILLS / "engineering-change" / "SKILL.md": (
            "Evidence → Diagnosis → Change Contract → Implementation → Verification",
            "ROOT_CAUSE_ALIGNMENT: PASS",
            "Final Review Summary",
            "analyze_change.py",
            "suggested-not-executed",
            "--write-baseline",
            "rootloom-change-contract-v1",
            "opt-in",
            "--strict",
            "--confirm-dangerous-delete",
            "REVIEW_EVIDENCE_COMPLETE",
            "REVIEW_REQUIRED_WITH_REDACTIONS",
            "--max-capture-seconds",
            "--max-git-seconds",
            "--max-sensitive-paths",
            "--reviewable-path",
        ),
        SKILLS / "engineering-change" / "scripts" / "analyze_change.py": (
            "analyze_change",
            "--declared-risk",
            "--include-project-memory",
            "--write-baseline",
            "tracked_patch",
            "--max-capture-seconds",
            "--max-git-seconds",
            "--max-sensitive-paths",
        ),
        SKILLS / "engineering-change" / "scripts" / "begin_review.py": (
            "REVIEW_MANIFEST_FORMAT",
            "change-contract.draft.json",
            "--allow-all-paths",
            "--allow-dirty-baseline",
            "--reviewable-path",
            "baseline_sha256",
            "rename_directory_no_replace",
            "CONTRACT_DRAFT_SENTINEL",
            "--max-capture-seconds",
            "--max-git-seconds",
            "--max-sensitive-paths",
        ),
        SKILLS / "engineering-change" / "scripts" / "seal_contract.py": (
            "contract.seal.json",
            "change-contract.json",
            "contains_contract_placeholder",
            "CONTRACT_HASH_BASIS",
            "--recover",
            "validate_contract_seal",
        ),
        SKILLS / "engineering-change" / "scripts" / "runner" / "intelligence.py": (
            "rootloom-change-assessment-v1",
            "dependency-supply-chain",
            "suggested-not-executed",
            "Static signals cannot prove semantic risk",
            "include_project_memory: bool = False",
            "allow_repository_reads",
            "read_bounded_repository_text",
        ),
        SKILLS / "engineering-change" / "scripts" / "runner" / "baseline.py": (
            "rootloom-change-baseline-v1",
            "rootloom-change-baseline-v2",
            "rootloom-change-baseline-v3",
            "rootloom-change-baseline-v4",
            "reviewable_paths",
            "intake-sealed",
            "run_id",
            "task_sha256",
            "sensitive_preservation",
            "write_new_baseline",
            "head_ref",
        ),
        SKILLS / "engineering-change" / "scripts" / "runner" / "change_contract.py": (
            "rootloom-change-contract-v1",
            "allowed_paths",
            "verification_claim_bindings",
            "structured_contract_claimed_commands",
            "segment",
            "verification_coverage",
        ),
        SKILLS / "engineering-change" / "scripts" / "runner" / "review_run.py": (
            "rootloom-review-run-v2",
            "rootloom-contract-seal-v1",
            "canonical-json-without-contract_sha256",
            "review_manifest_sha256",
            "unexpected or missing fields",
            "CONTRACT_DRAFT_SENTINEL",
        ),
        SKILLS / "engineering-change" / "scripts" / "runner" / "evidence_paths.py": (
            "validate_no_symlink_chain",
            "validate_outside_repository_storage",
            "Git common directory",
            "lstat",
            "fsync_directory",
            "rename_directory_no_replace",
        ),
        SKILLS / "engineering-change" / "scripts" / "runner" / "strict_json.py": (
            "duplicate JSON key",
            "non-standard JSON constant",
            "out-of-range JSON number",
        ),
        SKILLS / "engineering-change" / "scripts" / "runner" / "state.py": (
            "stable_repository_capture",
            "canonical_reviewable_paths",
            "git_index_path_tags",
            "reviewable_path_metadata",
            "reviewable path is ignored and cannot be captured reliably",
            "reviewable path is hidden by Git index flags",
            "reviewable path must have link count one",
            "reference_sensitive_metadata",
            "sensitive_change_quarantine",
            "target_sha256",
            "repository path traverses a symlink parent",
            "DEFAULT_MAX_GIT_SECONDS",
            "DEFAULT_MAX_CAPTURE_SECONDS",
            "DEFAULT_MAX_SENSITIVE_PATHS",
            "MAX_REVIEWABLE_PATHS",
            "sensitive_material_git_pathspecs",
            "CaptureDeadline",
            "run_command",
        ),
        SKILLS / "engineering-change" / "scripts" / "runner" / "process.py": (
            "output_bytes_observed",
            "process_tree_converged",
            "TerminateJobObject",
            "_controlled_tree_active",
        ),
        SKILLS / "engineering-change" / "scripts" / "finalize_change.py": (
            "diff.patch",
            "test.log",
            "summary.json",
            '"risk_assessment"',
            '"verification_plan"',
            '"quality_status"',
            '"evidence_complete"',
            '"verification_coverage"',
            '"claim_binding"',
            '"evidence_provenance"',
            '"exit_policy"',
            '"mode"',
            "--strict",
            "--include-project-memory",
            "--strict-bundle-only",
            "--require-verified",
            '"sensitive_integrity"',
            '"declared_claim_binding"',
            '"removed_preexisting_paths"',
            '"evidence_files_preserved"',
            '"repository_base_preserved_during_verification"',
            '"sensitive_change_quarantine"',
            '"verification_sensitive_change_quarantine"',
            "invalidate_previous_summary",
            "validate_outside_repository_storage",
            "--max-patch-bytes",
            "--max-capture-seconds",
            "--max-git-seconds",
            "--max-sensitive-paths",
            '"capture_limits"',
            '"capture_duration_seconds"',
            '"reviewability_policy"',
            '"policy_provenance"',
            '"captured_files_provenance"',
            '"semantic_review"',
            "REVIEW_EVIDENCE_COMPLETE",
            "REVIEW_REQUIRED_WITH_REDACTIONS",
            "SEMANTIC_REVIEW_ASSERTED",
            "DANGEROUS_DELETE_EXIT",
            "REINTAKE_REQUIRED_EXIT",
            "reintake-required",
        ),
        SKILLS / "project-memory" / "SKILL.md": (
            ".project-memory/",
            "current source",
            "record-failure",
            "set-status",
            "--include-stale",
        ),
        SKILLS / "project-memory" / "scripts" / "project_memory.py": (
            "rootloom-project-context-v1",
            "deduplicated",
            "memory.lock",
            "project-memory directory must not be a symlink",
        ),
        PLUGIN / "lib" / "rootloom_memory.py": (
            "rootloom-project-memory-v1",
            "O_NOFOLLOW",
            "entries exceed",
        ),
        PLUGIN / "lib" / "rootloom_paths.py": (
            "REVIEWABLE_ENV_TEMPLATE_NAMES",
            "PUBLIC_CERTIFICATE_SUFFIXES",
            "AMBIGUOUS_SENSITIVE_MATERIAL_SUFFIXES",
            "AMBIGUOUS_STRONG_KEY_CONTEXTS",
            "STRONG_SENSITIVE_MATERIAL_SUFFIXES",
            "MAX_REVIEWABLE_PATHS",
            "privkey.pem",
            "privatekey.pem",
            "ed25519-key.pem",
            "service-account.json",
            "is_sensitive_material_path",
            "is_security_domain_path",
            "is_protected_deletion_path",
            "validate_reviewable_paths",
            "normalize_reviewable_paths",
            "PROTECTED_STATE_SUFFIXES",
            "sensitive_material_git_pathspecs",
        ),
        SKILLS / "setup-rootloom" / "scripts" / "setup_rootloom.py": (
            '"personal": FULL_CAPABILITIES',
            '"autonomy"',
            'CAPABILITY_ALIASES = {"command-safety": "autonomy"}',
            'PRESET_ALIASES = {"engineering": "personal"}',
            "simple_lock",
            "rootloom-simple-backup-v1",
            "refusing rollback because",
            'operation="upgrade"',
            "drifted_paths",
            'selected.add("global-policy")',
        ),
        SKILLS / "setup-rootloom" / "SKILL.md": (
            "three authorization modes",
            "persistent cross-task default",
            "Full covers high-risk steps only in the current task",
            "Rules avoid duplicating that semantic decision",
        ),
        SYSTEM / "AGENTS.md": (
            "Diagnose the observable path",
            "Preserve unrelated user changes",
            "Tier 0 Direct",
            "proportional evidence",
            "deep `engineering-change` workflow",
            "Single action",
            "Standard",
            "Full",
            "Never infer Full",
        ),
        SYSTEM / "rules" / "rootloom.rules": (
            "never grants task authority",
            "persistent Standard",
            'pattern = ["git", "push"]',
            'pattern = ["gh", "pr", ["create", "merge"]]',
            'pattern = ["gh", "release", "create"]',
            'pattern = ["gh", "release", "delete"]',
        ),
        ROOT / "README.md": (
            "Rootloom Personal Core",
            "An inspectable personal engineering workflow for Codex.",
            "codex/enterprise-assurance",
            "Archived Assurance Edition",
            "Optional Autonomy",
            "Optional Evidence",
            "Experimental Project Memory",
            "$engineering-change",
            "$project-memory",
            "analyze_change.py",
            "quality_status",
            "--write-baseline",
            "--strict",
            "seal_contract.py",
            "two consecutive bounded captures",
            "material metadata change",
            "newly discovered ignored addition",
            "Git common directory",
            "Installation is complete after those two commands",
            "Persistent across tasks",
            "Full is never inferred",
            "REVIEW_EVIDENCE_COMPLETE",
            "REVIEW_REQUIRED_WITH_REDACTIONS",
            "evidence_complete",
            "--max-capture-seconds",
            "is_sensitive_material_path",
            "--reviewable-path",
            "reviewability_policy",
            "policy_provenance",
            "reintake-required",
            "assume-unchanged",
            "not a content-aware secret scanner",
        ),
        ROOT / "README.zh-CN.md": (
            "Rootloom Personal Core",
            "面向 Codex 的可检查个人工程工作流。",
            "codex/enterprise-assurance",
            "Archived Assurance Edition",
            "Optional Autonomy",
            "Optional Evidence",
            "Experimental Project Memory",
            "$engineering-change",
            "$project-memory",
            "analyze_change.py",
            "Engineering Memory",
            "quality_status",
            "--write-baseline",
            "--strict",
            "seal_contract.py",
            "连续两次有界采集",
            "材料元数据变化",
            "新发现的 Ignored 新增",
            "Git Common Directory",
            "两条命令完成后插件即安装完毕",
            "跨任务持久",
            "所有权限绝不会被自动推断",
            "REVIEW_EVIDENCE_COMPLETE",
            "REVIEW_REQUIRED_WITH_REDACTIONS",
            "evidence_complete",
            "--max-capture-seconds",
            "is_sensitive_material_path",
            "--reviewable-path",
            "reviewability_policy",
            "policy_provenance",
            "reintake-required",
            "assume-unchanged",
            "不是内容感知型 Secret Scanner",
        ),
        ROOT / "index.html": (
            "Make code changes you can explain.",
            "data-language-toggle",
            "data-workflow-image",
            "rootloom-loom-en.webp",
            "rootloom-loom-zh.webp",
            "codex plugin marketplace add liyanqing90/rootloom",
            "codex plugin add rootloom@rootloom",
            "$operating-coding-change",
            "Completion should say what happened.",
        ),
        ROOT / "site" / "styles.css": (
            "--canvas:",
            "--font-sans:",
            ".workflow-rail",
            ".evidence-section",
            ".copy-status",
            "@media (prefers-reduced-motion: reduce)",
        ),
        ROOT / "site" / "main.js": (
            'rootloom-language',
            "navigator.clipboard",
            "setLocalizedText",
            "让每一次代码修改",
            "data-workflow-image",
            "data-copy",
        ),
        ROOT / ".github" / "workflows" / "pages.yml": (
            "actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b",
            "actions/upload-pages-artifact@7b1f4a764d45c48632c6b24a0339c27f5614fb0b",
            "actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e",
            "pages: write",
            "id-token: write",
            "GitHub Pages artifact must not contain symlinks",
        ),
        ROOT / "PRODUCT.md": (
            "## Register",
            "brand",
            "Tactile, rigorous, candid",
            "## Accessibility & Inclusion",
        ),
        ROOT / "DESIGN.md": (
            "Creative North Star: \"The Working Loom\"",
            "## 1. Overview",
            "## 2. Colors",
            "## 3. Typography",
            "## 4. Elevation",
            "## 5. Components",
            "## 6. Do's and Don'ts",
        ),
        ROOT / "docs" / "setup.md": (
            "gh pr merge 123 --merge",
            "gh release create v1.0.0",
            "Standard persists across tasks",
            "catastrophic recursive-deletion hard deny",
        ),
        ROOT / "docs" / "setup.zh-CN.md": (
            "gh pr merge 123 --merge",
            "gh release create v1.0.0",
            "普通权限跨任务持久",
            "灾难性递归删除的硬拒绝",
        ),
        ROOT / "docs" / "architecture.md": (
            "intelligence.py",
            "risk_assessment",
            "relevant entries",
            "rootloom-change-baseline-v3",
            "rootloom-change-baseline-v4",
            "schema_revision: 5",
            "is_sensitive_material_path",
            "--max-capture-seconds",
            "strict_json.py",
            "symbolic HEAD ref",
            "Git common directory",
            "tiered authorization decision",
            "reviewability_policy",
            "policy_provenance",
            "reintake-required",
            "skip-worktree",
        ),
        ROOT / "docs" / "architecture.zh-CN.md": (
            "intelligence.py",
            "risk_assessment",
            "相关性选择",
            "rootloom-change-baseline-v3",
            "rootloom-change-baseline-v4",
            "schema_revision: 5",
            "is_sensitive_material_path",
            "--max-capture-seconds",
            "strict_json.py",
            "符号 HEAD Ref",
            "Git Common Directory",
            "分级授权决策",
            "reviewability_policy",
            "policy_provenance",
            "reintake-required",
            "skip-worktree",
        ),
        ROOT / "docs" / "decisions" / "2026-07-14-tiered-authorization-modes.md": (
            "Status: accepted",
            "Single action",
            "Standard",
            "Full",
            "persistent cross-task default",
            "catastrophic recursive deletion",
        ),
        ROOT / "docs" / "decisions" / "2026-07-15-evidence-honest-strict-review.md": (
            "Status: accepted",
            "REVIEW_EVIDENCE_COMPLETE",
            "REVIEW_REQUIRED_WITH_REDACTIONS",
            "SEMANTIC_REVIEW_ASSERTED",
            "--max-git-seconds",
            "--max-sensitive-paths",
            "--recover",
        ),
        ROOT / "docs" / "decisions" / "2026-07-15-sensitive-material-and-capture-bounds.md": (
            "Status: accepted",
            "is_sensitive_material_path",
            "is_security_domain_path",
            "CaptureDeadline",
            "rootloom-change-baseline-v3",
            "rootloom-change-baseline-v4",
            "Summary revision 5",
            "--reviewable-path",
            "ignored reviewable files",
            "assume-unchanged",
            "OpenSSL",
            "evidence_complete",
        ),
        ROOT / "docs" / "decisions" / "2026-07-16-personal-core-product-boundaries.md": (
            "Status: accepted",
            "Core — Change, Review, Guidance",
            "Optional Autonomy",
            "Optional Evidence",
            "Experimental Project Memory",
            "Archived Assurance Edition",
            "reintake-required",
            "verified-quality layer",
        ),
        PLUGIN / "AGENTS.md": (
            "exact integer `version: 1`",
            "SessionStart project-context Hook is read-only",
        ),
        SKILLS / "engineering-change" / "AGENTS.md": (
            "wire formats are frozen",
            "reintake-required",
        ),
        SKILLS / "setup-rootloom" / "AGENTS.md": (
            "Public presets are only",
            "`autonomy` is the canonical",
        ),
        SKILLS / "project-memory" / "AGENTS.md": (
            "Project Memory is experimental",
        ),
        ROOT / "CONTRIBUTING.md": (
            "Versioning public contracts",
            "Patch:",
            "Minor:",
            "Major:",
            "evidence_complete",
            "Published tags and Releases are immutable",
        ),
        ROOT / "CONTRIBUTING.zh-CN.md": (
            "公共契约版本规则",
            "Patch：",
            "Minor：",
            "Major：",
            "evidence_complete",
            "Tag 与 Release 保持不可变",
        ),
        ROOT / "docs" / "diagram" / "architecture-en.svg": (
            "Authorization Modes",
            "Single Action",
            "Standard",
            "Full",
            "Personal Core",
            "Archived Assurance Edition",
            "Inspectable",
        ),
        ROOT / "docs" / "diagram" / "architecture-zh.svg": (
            "授权模式",
            "本条命令",
            "普通权限",
            "所有权限",
            "个人核心",
            "已归档保障版",
            "可检查",
        ),
    }
    for path, needles in contracts.items():
        if not path.is_file():
            errors.append(f"missing contract file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                errors.append(f"missing contract {needle!r} in {path.relative_to(ROOT)}")
    rules_text = (SYSTEM / "rules" / "rootloom.rules").read_text(encoding="utf-8")
    if 'decision = "prompt"' in rules_text:
        errors.append("Rootloom Rules must not duplicate semantic authorization with prompt decisions")
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for forbidden in ("macos-strict-runner", "high-assurance-coding-change"):
        if forbidden in ci:
            errors.append(f"CI retains Assurance-only surface: {forbidden}")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("check:", "validate:", "test:", "compatibility-smoke:"):
        if target not in makefile:
            errors.append(f"Makefile is missing {target}")


def validate_python(errors: list[str]) -> None:
    for path in sorted((PLUGIN, ROOT / "tests", ROOT / "scripts"), key=str):
        candidates = path.rglob("*.py") if path.is_dir() else ()
        for candidate in candidates:
            if "__pycache__" in candidate.parts:
                continue
            try:
                ast.parse(candidate.read_text(encoding="utf-8"), filename=str(candidate))
            except (OSError, SyntaxError, UnicodeDecodeError) as exc:
                errors.append(f"invalid Python: {candidate.relative_to(ROOT)}: {exc}")


def validate_links(errors: list[str]) -> None:
    documents = [ROOT / "README.md", ROOT / "README.zh-CN.md", ROOT / "index.html"] + sorted(
        (ROOT / "docs").glob("*.md")
    )
    for path in documents:
        text = path.read_text(encoding="utf-8")
        references = (
            HTML_REF.findall(text)
            if path.suffix == ".html"
            else LOCAL_LINK.findall(text) + HTML_SRC.findall(text)
        )
        for raw in references:
            target = raw.strip().strip("<>").split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            target = target.replace("%20", " ")
            if not (path.parent / target).resolve().exists():
                errors.append(f"broken local link in {path.relative_to(ROOT)}: {raw}")


def validate_workflows(errors: list[str]) -> None:
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        for reference in ACTION_USE.findall(text):
            if not re.fullmatch(r"[0-9a-f]{40}", reference):
                errors.append(f"workflow action is not pinned to a commit: {path.relative_to(ROOT)}: {reference}")


def validate_assets(errors: list[str]) -> None:
    svg_paths = (
        sorted(PLUGIN.rglob("*.svg"))
        + sorted((ROOT / "assets").glob("*.svg"))
        + sorted((ROOT / "docs" / "diagram").glob("*.svg"))
    )
    for path in svg_paths:
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            errors.append(f"invalid SVG: {path.relative_to(ROOT)}: {exc}")
    architecture_diagrams = {
        ROOT / "docs" / "diagram" / "architecture-en.svg": "en",
        ROOT / "docs" / "diagram" / "architecture-zh.svg": "zh",
    }
    version_label = re.compile(r"(?i)\bv?\d+\.\d+(?:\.\d+)?\b")
    for path, language in architecture_diagrams.items():
        try:
            root = ET.parse(path).getroot()
        except (FileNotFoundError, ET.ParseError):
            continue
        visible_text = " ".join(
            "".join(element.itertext())
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] in {"title", "desc", "text"}
        )
        if version_label.search(visible_text):
            errors.append(f"architecture diagram must not bind a version: {path.relative_to(ROOT)}")
        if language == "en" and re.search(r"[\u3400-\u9fff]", visible_text):
            errors.append(f"English architecture diagram contains Chinese text: {path.relative_to(ROOT)}")
        if language == "zh" and re.search(r"[A-Za-z]", visible_text):
            errors.append(f"Chinese architecture diagram contains English text: {path.relative_to(ROOT)}")
    required_images = {
        ROOT / "assets" / "rootloom-brand.webp": b"RIFF",
        ROOT / "site" / "assets" / "rootloom-loom.webp": b"RIFF",
        ROOT / "site" / "assets" / "rootloom-loom-en.webp": b"RIFF",
        ROOT / "site" / "assets" / "rootloom-loom-zh.webp": b"RIFF",
        ROOT / "docs" / "diagram" / "architecture-en.svg": b"<svg",
        ROOT / "docs" / "diagram" / "architecture-en@2x.png": b"\x89PNG\r\n\x1a\n",
        ROOT / "docs" / "diagram" / "architecture-zh.svg": b"<svg",
        ROOT / "docs" / "diagram" / "architecture-zh@2x.png": b"\x89PNG\r\n\x1a\n",
    }
    for path, signature in required_images.items():
        try:
            header = path.read_bytes()[: max(12, len(signature))]
        except FileNotFoundError:
            errors.append(f"missing public image: {path.relative_to(ROOT)}")
            continue
        if not header.startswith(signature):
            errors.append(f"invalid public image: {path.relative_to(ROOT)}")
        if path.suffix == ".webp" and header[8:12] != b"WEBP":
            errors.append(f"invalid WebP image: {path.relative_to(ROOT)}")


def validate_secrets(errors: list[str]) -> None:
    suffixes = {
        ".css",
        ".html",
        ".js",
        ".json",
        ".md",
        ".py",
        ".rules",
        ".toml",
        ".yaml",
        ".yml",
    }
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if "tests" in path.parts:
            continue
        if path.suffix.lower() not in suffixes and path.name not in {"Makefile", "AGENTS.md"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"possible secret in {path.relative_to(ROOT)}")
                break


def main() -> int:
    errors: list[str] = []
    validate_marketplace(errors)
    validate_manifest(errors)
    validate_skills(errors)
    validate_hooks(errors)
    validate_personal_contracts(errors)
    validate_python(errors)
    validate_links(errors)
    validate_workflows(errors)
    validate_assets(errors)
    validate_secrets(errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Rootloom Personal Core repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
    contracts = {
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
            "reference_sensitive_metadata",
            "sensitive_change_quarantine",
            "target_sha256",
            "repository path traverses a symlink parent",
            "DEFAULT_MAX_GIT_SECONDS",
            "DEFAULT_MAX_CAPTURE_SECONDS",
            "DEFAULT_MAX_SENSITIVE_PATHS",
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
            '"semantic_review"',
            "REVIEW_EVIDENCE_COMPLETE",
            "REVIEW_REQUIRED_WITH_REDACTIONS",
            "SEMANTIC_REVIEW_ASSERTED",
            "DANGEROUS_DELETE_EXIT",
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
            "STRONG_SENSITIVE_MATERIAL_SUFFIXES",
            "service-account.json",
            "is_sensitive_material_path",
            "is_security_domain_path",
            "is_protected_deletion_path",
            "validate_reviewable_paths",
            "PROTECTED_STATE_SUFFIXES",
            "sensitive_material_git_pathspecs",
        ),
        SKILLS / "setup-rootloom" / "scripts" / "setup_rootloom.py": (
            '"personal": FULL_CAPABILITIES',
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
            "Personal risk analyzer",
            "engineering-change",
            "Verification Intelligence",
            ".project-memory/",
            "Installing or upgrading Rootloom does not authorize automatic",
            "Do not turn optional assurance into a universal precondition",
            "persistent cross-task default",
            "Single action",
            "Standard",
            "Full",
            "Never infer **Full**",
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
            "codex/enterprise-assurance",
            "$engineering-change",
            "$project-memory",
            "analyze_change.py",
            "Engineering memory",
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
        ),
        ROOT / "README.zh-CN.md": (
            "Rootloom Personal Core",
            "codex/enterprise-assurance",
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
            "evidence_complete",
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
        ROOT / "docs" / "releases" / "2.2.0.md": (
            "Status: published",
            "7018c317e59a6e44081e07c1d68d277c469f0cfb",
            "RE_kwDOTVQo6M4VEtd1",
        ),
        ROOT / "docs" / "releases" / "2.2.1.md": (
            "Status: published",
            "da1c174f524c61f53d1ff3cc8650165eb10246ab",
            "RE_kwDOTVQo6M4VE4K1",
        ),
        ROOT / "docs" / "releases" / "2.2.2.md": (
            "Status: published",
            "a8e3fdf5592781d455683c61b26bc36351213c4d",
            "RE_kwDOTVQo6M4VFYr5",
        ),
        ROOT / "docs" / "releases" / "2.3.0.md": (
            "Status: published",
            "bb35433fb938ac3bfdff5339954dff6b44472fc8",
            "RE_kwDOTVQo6M4VFlGv",
        ),
        ROOT / "docs" / "releases" / "2.4.0.md": (
            "Status: published",
            "e434654958109ef6f6a3878ef8a3db36226cec54",
            "df0bb82d8253724b362988a8540e099e903df627",
            "RE_kwDOTVQo6M4VHEQf",
            "29383392662",
            "29383564033",
            "29385444153",
        ),
        ROOT / "docs" / "releases" / "3.0.0.md": (
            "Status: published",
            "61c1d8202350442721644345678e1525461c7d08",
            "72091416819a5b16436f2be0b7862dc965856f49",
            "RE_kwDOTVQo6M4VHOPs",
            "29390214510",
            "29390437387",
            "29390839339",
        ),
        ROOT / "docs" / "releases" / "3.1.0.md": (
            "Status: published",
            "4e010ea26c871a603a955b88ede8c5cea5066572",
            "fe8c834d5e9d450210cfdb33de0d6e8f688a7ae3",
            "RE_kwDOTVQo6M4VH8wK",
            "29408409629",
            "29408654603",
            "29413872318",
        ),
        ROOT / "docs" / "diagram" / "architecture-en.svg": (
            "Authorization Modes",
            "Single Action",
            "Standard",
            "Full",
            "Personal Core",
            "Enterprise Assurance",
        ),
        ROOT / "docs" / "diagram" / "architecture-zh.svg": (
            "授权模式",
            "本条命令",
            "普通权限",
            "所有权限",
            "个人核心",
            "企业保障",
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
    documents = [ROOT / "README.md", ROOT / "README.zh-CN.md"] + sorted(
        (ROOT / "docs").glob("*.md")
    )
    for path in documents:
        text = path.read_text(encoding="utf-8")
        for raw in LOCAL_LINK.findall(text) + HTML_SRC.findall(text):
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
        ROOT / "assets" / "rootloom-xiaohei-loom-en.png": b"\x89PNG\r\n\x1a\n",
        ROOT / "assets" / "rootloom-xiaohei-loom-zh.png": b"\x89PNG\r\n\x1a\n",
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
    suffixes = {".md", ".py", ".json", ".toml", ".yml", ".yaml", ".rules"}
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

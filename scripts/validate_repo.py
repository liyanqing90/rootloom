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
            "--confirm-dangerous-delete",
        ),
        SKILLS / "engineering-change" / "scripts" / "analyze_change.py": (
            "analyze_change",
            "--declared-risk",
            "tracked_patch",
        ),
        SKILLS / "engineering-change" / "scripts" / "runner" / "intelligence.py": (
            "rootloom-change-assessment-v1",
            "rootloom-project-memory-v1",
            "suggested-not-executed",
            "Static signals cannot prove semantic risk",
        ),
        SKILLS / "engineering-change" / "scripts" / "finalize_change.py": (
            "diff.patch",
            "test.log",
            "summary.json",
            '"risk_assessment"',
            '"verification_plan"',
            "output directory must be outside",
            "--max-patch-bytes",
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
            "rootloom-project-memory-v1",
            "rootloom-project-context-v1",
            "deduplicated",
            "project-memory directory must not be a symlink",
        ),
        SKILLS / "setup-rootloom" / "scripts" / "setup_rootloom.py": (
            '"personal": FULL_CAPABILITIES',
            "simple_lock",
            "rootloom-simple-backup-v1",
            "refusing rollback because",
        ),
        SYSTEM / "AGENTS.md": (
            "Personal risk analyzer",
            "engineering-change",
            "Verification Intelligence",
            ".project-memory/",
        ),
        ROOT / "README.md": (
            "Rootloom Personal Core",
            "codex/enterprise-assurance",
            "$engineering-change",
            "$project-memory",
            "analyze_change.py",
            "Engineering memory",
        ),
        ROOT / "README.zh-CN.md": (
            "Rootloom Personal Core",
            "codex/enterprise-assurance",
            "$engineering-change",
            "$project-memory",
            "analyze_change.py",
            "Engineering Memory",
        ),
        ROOT / "docs" / "architecture.md": (
            "intelligence.py",
            "risk_assessment",
            "relevant entries",
        ),
        ROOT / "docs" / "architecture.zh-CN.md": (
            "intelligence.py",
            "risk_assessment",
            "相关性选择",
        ),
        ROOT / "docs" / "diagram" / "architecture.svg": (
            "PERSONAL CORE 2.1",
            "Risk Scanner",
            "Engineering Memory",
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
    required_images = {
        ROOT / "assets" / "rootloom-brand.webp": b"RIFF",
        ROOT / "docs" / "diagram" / "architecture.svg": b"<svg",
        ROOT / "docs" / "diagram" / "architecture@2x.png": b"\x89PNG\r\n\x1a\n",
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

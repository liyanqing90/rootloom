"""Versioned setup-recovery target schemas and manifest validation."""

from __future__ import annotations

from typing import Any


RECOVERY_SCHEMA_VERSION = 2
# Schema 1 is the implicit manifest contract emitted through Rootloom 1.2.12.
# Keep snapshots literal so future target catalog changes cannot orphan recovery.
RECOVERY_TARGET_SCHEMAS: dict[int, dict[str, str]] = {
    1: {
        "AGENTS.md": "file",
        "config.toml": "config",
        "high-assurance.config.toml": "file",
        "agents/evidence_explorer.toml": "file",
        "agents/root_cause_reviewer.toml": "file",
        "agents/implementation_worker.toml": "file",
        "agents/verification_reviewer.toml": "file",
        "rules/rootloom.rules": "file",
        ".rootloom/components.json": "hook-policy",
    },
    2: {
        "AGENTS.md": "file",
        "config.toml": "config",
        "high-assurance.config.toml": "file",
        "agents/evidence_explorer.toml": "file",
        "agents/root_cause_reviewer.toml": "file",
        "agents/implementation_worker.toml": "file",
        "agents/verification_reviewer.toml": "file",
        "rules/rootloom.rules": "file",
        ".rootloom/components.json": "hook-policy",
    },
}


def recovery_target_schema(manifest: dict[str, Any]) -> tuple[int, dict[str, str]]:
    raw_schema = manifest.get("recovery_schema_version", 1)
    if isinstance(raw_schema, bool) or not isinstance(raw_schema, int):
        raise ValueError("invalid setup recovery schema version")
    targets = RECOVERY_TARGET_SCHEMAS.get(raw_schema)
    if targets is None:
        raise ValueError(f"unsupported setup recovery schema version: {raw_schema}")
    producer_version = manifest.get("producer_version", manifest.get("version"))
    if not isinstance(producer_version, str) or not producer_version.strip():
        raise ValueError("setup recovery manifest has no producer version")
    return raw_schema, targets


def validate_recovery_target_entry(
    entry: dict[str, Any],
    *,
    schema_version: int,
    targets: dict[str, str],
    seen: set[str],
    label: str,
) -> tuple[str, str]:
    relative = entry.get("path")
    if not isinstance(relative, str) or relative not in targets or relative in seen:
        raise ValueError(f"invalid {label} target: {relative!r}")
    seen.add(relative)
    target_type = targets[relative]
    recorded_type = entry.get("target_type")
    if schema_version >= 2:
        if recorded_type != target_type:
            raise ValueError(f"invalid {label} target type for {relative}")
    elif recorded_type is not None and recorded_type != target_type:
        raise ValueError(f"invalid legacy {label} target type for {relative}")
    return relative, target_type

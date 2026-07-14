"""Machine-checkable scope and verification declarations for Tier 1/2 changes."""

from __future__ import annotations

import fnmatch
import json
import os
from pathlib import Path
import stat
from typing import Any


CHANGE_CONTRACT_FORMAT = "rootloom-change-contract-v1"
MAX_CONTRACT_BYTES = 1024 * 1024
MAX_PATTERNS = 200
MAX_VERIFICATIONS = 20
MAX_COMMAND_CHARS = 8192
CLAIM_ALIASES = {
    "primary": "primary-behavior",
    "invariant": "owning-invariant",
    "adjacent": "adjacent-path",
}
ROOT_CAUSE_VALUES = {"PASS", "NOT_APPLICABLE"}


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError(f"change contract must not be a symlink: {path}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError(f"change contract must be a regular file: {path}")
        raw = bytearray()
        while len(raw) <= MAX_CONTRACT_BYTES:
            chunk = os.read(descriptor, min(64 * 1024, MAX_CONTRACT_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        after = os.fstat(descriptor)
        if (
            (opened.st_dev, opened.st_ino, opened.st_size)
            != (after.st_dev, after.st_ino, after.st_size)
        ):
            raise ValueError(f"change contract changed during read: {path}")
        if len(raw) > MAX_CONTRACT_BYTES or after.st_size > MAX_CONTRACT_BYTES:
            raise ValueError(f"change contract exceeds {MAX_CONTRACT_BYTES} bytes: {path}")
    finally:
        os.close(descriptor)
    try:
        payload = json.loads(bytes(raw).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid change contract JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("change contract must be a JSON object")
    return payload


def _normalize_pattern(raw: str, *, field: str) -> str:
    value = raw.strip().replace("\\", "/")
    parts = value.split("/")
    if (
        not value
        or value.startswith("/")
        or any(part in {"", ".", ".."} for part in parts)
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError(f"{field} contains an unsafe repository-relative glob: {raw!r}")
    return value


def _string_list(payload: dict[str, Any], field: str, *, required: bool) -> list[str]:
    raw = payload.get(field)
    if raw is None and not required:
        return []
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise ValueError(f"change contract {field} must be a string list")
    if required and not raw:
        raise ValueError(f"change contract {field} must not be empty")
    if len(raw) > MAX_PATTERNS:
        raise ValueError(f"change contract {field} exceeds {MAX_PATTERNS} entries")
    normalized = [_normalize_pattern(item, field=field) for item in raw]
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"change contract {field} must not contain duplicates")
    return normalized


def load_change_contract(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if payload.get("format") != CHANGE_CONTRACT_FORMAT:
        raise ValueError(f"change contract format must be {CHANGE_CONTRACT_FORMAT}")
    allowed = _string_list(payload, "allowed_paths", required=True)
    forbidden = _string_list(payload, "forbidden_paths", required=False)
    alignment = payload.get("root_cause_alignment")
    if alignment not in ROOT_CAUSE_VALUES:
        raise ValueError(
            "change contract root_cause_alignment must be PASS or NOT_APPLICABLE"
        )
    commands = payload.get("verification_commands", {})
    if not isinstance(commands, dict) or any(
        not isinstance(key, str)
        or not key.strip()
        or not isinstance(value, str)
        or not value.strip()
        or len(value) > MAX_COMMAND_CHARS
        for key, value in commands.items()
    ):
        raise ValueError("change contract verification_commands must map IDs to commands")
    if len(commands) > MAX_VERIFICATIONS:
        raise ValueError(
            f"change contract supports at most {MAX_VERIFICATIONS} verification commands"
        )
    claims = payload.get("verification_claims")
    if not isinstance(claims, dict) or not claims:
        raise ValueError("change contract verification_claims must not be empty")
    normalized_claims: dict[str, list[str]] = {}
    for raw_claim, references in claims.items():
        if not isinstance(raw_claim, str) or not raw_claim.strip():
            raise ValueError("change contract claim IDs must be nonempty strings")
        if not isinstance(references, list) or not references or any(
            not isinstance(item, str) or not item.strip() for item in references
        ):
            raise ValueError("change contract claims must contain verification IDs")
        missing = sorted(set(references) - set(commands))
        if missing:
            raise ValueError(
                f"change contract claim {raw_claim} references unknown verifications: "
                + ", ".join(missing)
            )
        normalized_claims[CLAIM_ALIASES.get(raw_claim, raw_claim)] = list(references)
    return {
        **payload,
        "allowed_paths": allowed,
        "forbidden_paths": forbidden,
        "verification_commands": dict(commands),
        "verification_claims": normalized_claims,
    }


def path_matches(path: str, pattern: str) -> bool:
    if fnmatch.fnmatchcase(path, pattern):
        return True
    if pattern.endswith("/**") and path == pattern[:-3].rstrip("/"):
        return True
    return False


def scope_violations(
    contract: dict[str, Any], changes: list[dict[str, str]]
) -> dict[str, list[str]]:
    paths = {
        item[field]
        for item in changes
        for field in ("path", "original_path")
        if item.get(field)
    }
    outside = sorted(
        path
        for path in paths
        if not any(path_matches(path, pattern) for pattern in contract["allowed_paths"])
    )
    forbidden = sorted(
        path
        for path in paths
        if any(path_matches(path, pattern) for pattern in contract["forbidden_paths"])
    )
    return {"outside_allowed_paths": outside, "forbidden_paths_changed": forbidden}


def parse_cli_claim(raw: str) -> tuple[str, str]:
    claim, separator, command = raw.partition(":")
    if not separator or not claim.strip() or not command.strip():
        raise ValueError("--verify-claim must use CLAIM:COMMAND")
    if len(command) > MAX_COMMAND_CHARS:
        raise ValueError(f"verification command exceeds {MAX_COMMAND_CHARS} characters")
    return CLAIM_ALIASES.get(claim.strip(), claim.strip()), command.strip()


def claimed_commands(
    contract: dict[str, Any] | None, cli_claims: list[tuple[str, str]]
) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    if contract is not None:
        commands = contract["verification_commands"]
        for claim, references in contract["verification_claims"].items():
            result.setdefault(claim, set()).update(commands[item] for item in references)
    for claim, command in cli_claims:
        result.setdefault(claim, set()).add(command)
    return result


def verification_coverage(
    required_behaviors: list[dict[str, str]],
    claims: dict[str, set[str]],
    passed_commands: set[str],
    *,
    tier: int,
) -> tuple[str, dict[str, Any]]:
    required = [item["id"] for item in required_behaviors]
    if tier == 0:
        coverage = "complete" if passed_commands else "unverified"
        return coverage, {
            "required": required,
            "covered": required if coverage == "complete" else [],
            "missing": [] if coverage == "complete" else required,
            "claims": {},
        }
    covered = sorted(
        behavior
        for behavior in required
        if claims.get(behavior, set()) & passed_commands
    )
    missing = sorted(set(required) - set(covered))
    coverage = "complete" if not missing else "partial" if covered else "unverified"
    return coverage, {
        "required": required,
        "covered": covered,
        "missing": missing,
        "claims": {key: sorted(value) for key, value in sorted(claims.items())},
    }

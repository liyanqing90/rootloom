#!/usr/bin/env python3
"""Plan, install, inspect, and roll back Rootloom."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import tomllib
from typing import Any, Iterator

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from setup.recovery import (
    RECOVERY_SCHEMA_VERSION,
    recovery_target_schema,
    validate_recovery_target_entry,
)
from setup.transaction import atomic_write as _transaction_atomic_write


MANAGED_TOKEN = "rootloom:managed"
LIMITS_START = "# rootloom:agent-limits-start version=1"
LIMITS_END = "# rootloom:agent-limits-end"
STATE_DIRNAME = ".rootloom"
COMPONENT_POLICY_PATH = f"{STATE_DIRNAME}/components.json"
POSIX_MODE_CONTRACT = os.name != "nt" and hasattr(os, "fchmod")
MANAGED_AGENT_LIMITS: tuple[tuple[str, str], ...] = (
    ("max_threads", "4"),
    ("max_depth", "1"),
    ("interrupt_message", "true"),
)
MANAGED_AGENT_KEYS = tuple(key for key, _value in MANAGED_AGENT_LIMITS)
COMPONENT_DESCRIPTIONS = {
    "global-guidance": "Install the refined global AGENTS.md working agreement.",
    "project-guidance-hook": "Enable automatic evidence-backed project AGENTS.md seeding.",
    "agent-limits": "Manage the concurrent thread cap, nesting depth, and interrupt visibility.",
    "command-rules": "Install tested local Git, publication, infrastructure, and destructive-command policy.",
    "quality-profile": "Install the high-assurance Sol/high CLI profile.",
    "custom-agents": "Install the atomic four-role Terra/Sol custom-agent set.",
    "subagent-audit-hook": "Enable advisory cumulative child-budget and role/model auditing.",
}
FULL_COMPONENTS = tuple(COMPONENT_DESCRIPTIONS)
CAPABILITY_DESCRIPTIONS = {
    "global-policy": "Apply the lean cross-project working agreement.",
    "project-context": "Automatically seed and refresh repository-specific guidance.",
    "command-safety": "Separate reversible local work from publication and destructive commands.",
    "delegation-control": "Install and audit the atomic four-role subagent system and runtime limits.",
    "high-assurance": "Add the quality-first profile used by deterministic controlled delivery.",
}
CAPABILITY_COMPONENTS = {
    "global-policy": ("global-guidance",),
    "project-context": ("project-guidance-hook",),
    "command-safety": ("command-rules",),
    "delegation-control": (
        "agent-limits",
        "custom-agents",
        "subagent-audit-hook",
    ),
    "high-assurance": ("quality-profile",),
}
CAPABILITY_DEPENDENCIES = {
    "high-assurance": ("delegation-control",),
}
FULL_CAPABILITIES = tuple(CAPABILITY_DESCRIPTIONS)
PRESETS = {
    "skills-only": (),
    "guidance": (
        "global-policy",
        "project-context",
    ),
    "engineering": (
        "global-policy",
        "project-context",
        "command-safety",
    ),
    "delegated": (
        "global-policy",
        "project-context",
        "command-safety",
        "delegation-control",
    ),
    "full": FULL_CAPABILITIES,
}


@dataclass(frozen=True)
class Target:
    relative_path: str
    source: Path | None
    component: str
    kind: str = "file"


@dataclass(frozen=True)
class Action:
    path: str
    action: str
    reason: str
    before_hash: str | None
    after_hash: str


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def file_mode(path: Path, fallback: int = 0o600) -> int:
    try:
        return stat.S_IMODE(path.stat(follow_symlinks=False).st_mode)
    except FileNotFoundError:
        return fallback


@contextmanager
def setup_lock(codex_home: Path) -> Iterator[Path]:
    """Serialize setup mutations for one Codex home without waiting indefinitely."""

    state_root = codex_home / STATE_DIRNAME
    if state_root.is_symlink():
        raise ValueError("refusing symlinked setup state directory")
    state_root.mkdir(parents=True, exist_ok=True)
    os.chmod(state_root, 0o700)
    lock_path = state_root / "setup.lock"
    if lock_path.is_symlink():
        raise ValueError("refusing symlinked setup lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    locked = False
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(descriptor, 0o600)
        elif os.name != "nt":  # pragma: no cover - unknown non-POSIX runtime
            raise RuntimeError("setup lock permissions cannot be hardened on this platform")
        if os.name == "nt":  # pragma: no cover - exercised on Windows CI when available
            import msvcrt

            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"\0")
            os.lseek(descriptor, 0, os.SEEK_SET)
            try:
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError(
                    f"another Rootloom setup transaction holds {lock_path}"
                ) from exc
        else:
            import fcntl

            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError(
                    f"another Rootloom setup transaction holds {lock_path}"
                ) from exc
        locked = True
        yield lock_path
    finally:
        if locked:
            if os.name == "nt":  # pragma: no cover - exercised on Windows CI when available
                import msvcrt

                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[3]


def plugin_version(root: Path) -> str:
    manifest = root / ".codex-plugin" / "plugin.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    version = payload.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("plugin manifest has no version")
    return version


def normalize_components(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    unknown = sorted(set(values) - set(COMPONENT_DESCRIPTIONS))
    if unknown:
        raise ValueError(f"unknown setup components: {', '.join(unknown)}")
    selected = set(values)
    return tuple(name for name in FULL_COMPONENTS if name in selected)


def normalize_capabilities(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    unknown = sorted(set(values) - set(CAPABILITY_DESCRIPTIONS))
    if unknown:
        raise ValueError(f"unknown setup capabilities: {', '.join(unknown)}")
    selected = set(values)
    pending = list(values)
    while pending:
        capability = pending.pop()
        for dependency in CAPABILITY_DEPENDENCIES.get(capability, ()):
            if dependency not in selected:
                selected.add(dependency)
                pending.append(dependency)
    return tuple(name for name in FULL_CAPABILITIES if name in selected)


def components_for_capabilities(capabilities: tuple[str, ...]) -> tuple[str, ...]:
    selected: list[str] = []
    for capability in normalize_capabilities(capabilities):
        selected.extend(CAPABILITY_COMPONENTS[capability])
    return normalize_components(selected)


def all_targets(root: Path) -> list[Target]:
    assets = root / "assets" / "system"
    return [
        Target("AGENTS.md", assets / "AGENTS.md", "global-guidance"),
        Target("config.toml", None, "agent-limits", kind="config"),
        Target(
            "high-assurance.config.toml",
            assets / "profiles" / "high-assurance.config.toml",
            "quality-profile",
        ),
        *[
            Target(
                f"agents/{name}.toml",
                assets / "agents" / f"{name}.toml",
                "custom-agents",
            )
            for name in (
                "evidence_explorer",
                "root_cause_reviewer",
                "implementation_worker",
                "verification_reviewer",
            )
        ],
        Target(
            "rules/rootloom.rules",
            assets / "rules" / "rootloom.rules",
            "command-rules",
        ),
        Target(COMPONENT_POLICY_PATH, None, "hook-policy", kind="hook-policy"),
    ]


def target_catalog(root: Path, components: tuple[str, ...]) -> list[Target]:
    selected = set(normalize_components(components))
    return [
        target
        for target in all_targets(root)
        if target.kind == "hook-policy" or target.component in selected
    ]


def render_component_policy(
    capabilities: tuple[str, ...],
    components: tuple[str, ...],
) -> bytes:
    selected_capabilities = normalize_capabilities(capabilities)
    selected = normalize_components(components)
    payload = {
        "hooks": {
            "project-guidance-hook": "project-guidance-hook" in selected,
            "subagent-audit-hook": "subagent-audit-hook" in selected,
        },
        "managed_by": MANAGED_TOKEN,
        "schema_version": 1,
        "selected_capabilities": list(selected_capabilities),
        "selected_components": list(selected),
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()


def validate_toml(text: str, label: str) -> None:
    try:
        tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"invalid TOML in {label}: {exc}") from exc


def table_bounds(lines: list[str], name: str) -> tuple[int, int] | None:
    header = re.compile(rf"\s*\[{re.escape(name)}\]\s*(?:#.*)?")
    for index, line in enumerate(lines):
        if not header.fullmatch(line):
            continue
        end = len(lines)
        for later in range(index + 1, len(lines)):
            if re.match(r"\s*\[", lines[later]):
                end = later
                break
        return index, end
    return None


def is_managed_agent_key(line: str) -> bool:
    keys = "|".join(re.escape(key) for key in MANAGED_AGENT_KEYS)
    return re.match(rf"\s*(?:{keys})\s*=", line) is not None


def remove_legacy_limit_markers(lines: list[str]) -> list[str]:
    markers = {LIMITS_START, LIMITS_END}
    return [line for line in lines if line.strip() not in markers]


def render_agent_limits(existing: str) -> str:
    if existing.strip():
        validate_toml(existing, "config.toml before setup")

    newline = "\r\n" if "\r\n" in existing else "\n"
    existing = existing.replace("\r\n", "\n").replace("\r", "\n")
    lines = remove_legacy_limit_markers(existing.splitlines())
    bounds = table_bounds(lines, "agents")
    managed_lines = [
        f"{key} = {value} # {MANAGED_TOKEN}"
        for key, value in MANAGED_AGENT_LIMITS
    ]
    if bounds is None:
        prefix = existing.rstrip()
        rendered = (
            (prefix + "\n\n" if prefix else "")
            + "[agents]\n"
            + "\n".join(managed_lines)
            + "\n"
        )
    else:
        section_start, section_end = bounds
        section_body = [
            line
            for line in lines[section_start + 1 : section_end]
            if not is_managed_agent_key(line)
        ]
        replacement = [lines[section_start], *managed_lines, *section_body]
        rendered = "\n".join(
            [*lines[:section_start], *replacement, *lines[section_end:]]
        ).rstrip() + "\n"

    validate_toml(rendered, "config.toml after setup")
    return rendered if newline == "\n" else rendered.replace("\n", newline)


def managed_agent_limits_intact(text: str) -> bool:
    try:
        payload = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return False
    agents = payload.get("agents")
    if not isinstance(agents, dict):
        return False
    return (
        type(agents.get("max_threads")) is int
        and agents["max_threads"] == 4
        and type(agents.get("max_depth")) is int
        and agents["max_depth"] == 1
        and agents.get("interrupt_message") is True
    )


def restore_agent_limits(current: str, previous: str) -> str:
    """Restore only setup-owned agent keys while preserving later unrelated config."""

    validate_toml(current, "config.toml before rollback")
    if previous.strip():
        validate_toml(previous, "config.toml backup")
    if not managed_agent_limits_intact(current):
        raise RuntimeError("managed [agents] limits changed after setup")

    newline = "\r\n" if "\r\n" in current else "\n"
    current_lines = remove_legacy_limit_markers(current.splitlines())
    current_bounds = table_bounds(current_lines, "agents")
    if current_bounds is None:
        raise RuntimeError("managed [agents] table is missing after setup")
    current_start, current_end = current_bounds
    remaining_body = [
        line
        for line in current_lines[current_start + 1 : current_end]
        if not is_managed_agent_key(line)
    ]

    previous_lines = remove_legacy_limit_markers(previous.splitlines())
    previous_bounds = table_bounds(previous_lines, "agents")
    previous_key_lines: list[str] = []
    if previous_bounds is not None:
        previous_start, previous_end = previous_bounds
        previous_section = previous_lines[previous_start + 1 : previous_end]
        for key in MANAGED_AGENT_KEYS:
            match = next(
                (
                    line
                    for line in previous_section
                    if re.match(rf"\s*{re.escape(key)}\s*=", line)
                ),
                None,
            )
            if match is not None:
                previous_key_lines.append(match)

    meaningful_remaining = any(line.strip() for line in remaining_body)
    if previous_bounds is None and not previous_key_lines and not meaningful_remaining:
        replacement: list[str] = []
    else:
        replacement = [
            current_lines[current_start],
            *previous_key_lines,
            *remaining_body,
        ]

    rendered = "\n".join(
        [*current_lines[:current_start], *replacement, *current_lines[current_end:]]
    ).rstrip()
    if rendered:
        rendered += "\n"
        validate_toml(rendered, "config.toml after rollback")
    return rendered if newline == "\n" else rendered.replace("\n", newline)


def has_symlink_component(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def desired_bytes(
    target: Target,
    destination: Path,
    codex_home: Path,
    capabilities: tuple[str, ...],
    components: tuple[str, ...],
) -> bytes:
    if target.kind == "config":
        current = None if has_symlink_component(destination, codex_home) else read_bytes(destination)
        text = current.decode("utf-8") if current is not None else ""
        return render_agent_limits(text).encode("utf-8")
    if target.kind == "hook-policy":
        return render_component_policy(capabilities, components)
    if target.source is None or not target.source.is_file():
        raise FileNotFoundError(f"missing setup asset for {target.relative_path}")
    return target.source.read_bytes()


def managed_equivalent(current: bytes, desired: bytes) -> bool:
    current_text = current.decode("utf-8", errors="replace")
    desired_text = desired.decode("utf-8", errors="replace")
    desired_without_markers = "\n".join(
        line
        for line in desired_text.splitlines()
        if MANAGED_TOKEN not in line
    ).strip()
    return current_text.strip() == desired_without_markers


def load_state(codex_home: Path) -> dict[str, Any]:
    state_root = codex_home / STATE_DIRNAME
    if state_root.is_symlink():
        raise ValueError("refusing symlinked setup state directory")
    path = state_root / "state.json"
    if path.is_symlink():
        raise ValueError("refusing symlinked setup state file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid setup state: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"invalid setup state object: {path}")
    return payload


def classify_action(
    target: Target,
    destination: Path,
    desired: bytes,
    state: dict[str, Any],
    codex_home: Path,
) -> Action:
    after_hash = sha256_bytes(desired)
    if has_symlink_component(destination, codex_home):
        return Action(
            target.relative_path,
            "conflict",
            "target or one of its managed parent directories is a symlink",
            None,
            after_hash,
        )
    current = read_bytes(destination)
    if current is None:
        return Action(target.relative_path, "create", "target is absent", None, after_hash)

    before_hash = sha256_bytes(current)
    if before_hash == after_hash:
        return Action(
            target.relative_path,
            "unchanged",
            "already matches this release",
            before_hash,
            after_hash,
        )

    if target.kind == "config":
        return Action(
            target.relative_path,
            "update",
            "preserve config and manage only [agents] limits",
            before_hash,
            after_hash,
        )

    current_text = current.decode("utf-8", errors="replace")
    recorded = state.get("files", {}).get(target.relative_path, {})
    recorded_hash = recorded.get("after_hash") if isinstance(recorded, dict) else None
    if recorded_hash and recorded_hash != before_hash:
        return Action(
            target.relative_path,
            "conflict",
            "managed target changed after the last apply",
            before_hash,
            after_hash,
        )
    if MANAGED_TOKEN in current_text:
        return Action(
            target.relative_path,
            "update",
            "managed target has a newer template",
            before_hash,
            after_hash,
        )
    if managed_equivalent(current, desired):
        return Action(
            target.relative_path,
            "adopt",
            "content matches the template before ownership markers",
            before_hash,
            after_hash,
        )
    return Action(
        target.relative_path,
        "conflict",
        "existing file is user-owned",
        before_hash,
        after_hash,
    )


def installed_capabilities(state: dict[str, Any]) -> tuple[str, ...] | None:
    if state.get("status") != "installed":
        return None
    raw = state.get("capabilities")
    if raw is None:
        return FULL_CAPABILITIES
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise ValueError("invalid installed capability selection in setup state")
    return normalize_capabilities(raw)


def build_plan(
    codex_home: Path,
    capabilities: tuple[str, ...] = FULL_CAPABILITIES,
) -> tuple[str, list[Target], list[Action], dict[str, bytes]]:
    root = plugin_root()
    version = plugin_version(root)
    state = load_state(codex_home)
    selected_capabilities = normalize_capabilities(capabilities)
    selected_components = components_for_capabilities(selected_capabilities)
    targets = target_catalog(root, selected_components)
    desired: dict[str, bytes] = {}
    actions: list[Action] = []
    for target in targets:
        destination = codex_home / target.relative_path
        value = desired_bytes(
            target,
            destination,
            codex_home,
            selected_capabilities,
            selected_components,
        )
        desired[target.relative_path] = value
        actions.append(classify_action(target, destination, value, state, codex_home))
    return version, targets, actions, desired


def atomic_write(path: Path, value: bytes, mode: int = 0o600) -> None:
    _transaction_atomic_write(path, value, mode)


def make_transaction_dir(codex_home: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = codex_home / STATE_DIRNAME / "backups"
    if (codex_home / STATE_DIRNAME).is_symlink():
        raise ValueError("refusing symlinked setup state directory")
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(codex_home / STATE_DIRNAME, 0o700)
    path = Path(tempfile.mkdtemp(prefix=f"{stamp}-{os.getpid()}-", dir=root))
    os.chmod(path, 0o700)
    return path


RECOVERY_FORMAT = "rootloom-setup-recovery-v2"
TERMINAL_RECOVERY_PHASES = {"committed", "compensated", "recovered"}


def write_recovery_journal(
    transaction: Path,
    phase: str,
    applied_paths: list[str],
) -> None:
    manifest_path = transaction / "manifest.json"
    if has_symlink_component(manifest_path, transaction) or not manifest_path.is_file():
        raise ValueError("setup recovery manifest is missing or symlinked")
    manifest_sha256 = sha256_bytes(manifest_path.read_bytes())
    atomic_write(
        transaction / "recovery.json",
        (
            json.dumps(
                {
                    "format": RECOVERY_FORMAT,
                    "phase": phase,
                    "applied_paths": applied_paths,
                    "manifest_sha256": manifest_sha256,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode(),
    )


def unresolved_transactions(codex_home: Path) -> list[Path]:
    root = codex_home / STATE_DIRNAME / "backups"
    if not root.exists():
        return []
    if root.is_symlink():
        raise ValueError("refusing symlinked setup backup directory")
    unresolved: list[Path] = []
    for journal_path in sorted(root.glob("*/recovery.json")):
        transaction = journal_path.parent
        if (
            transaction.is_symlink()
            or not transaction.resolve().is_relative_to(root.resolve())
            or journal_path.is_symlink()
        ):
            raise ValueError("refusing symlinked setup recovery journal")
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        if not isinstance(journal, dict):
            raise ValueError(f"invalid setup recovery journal: {journal_path}")
        if journal.get("format") != RECOVERY_FORMAT:
            if journal.get("phase") in TERMINAL_RECOVERY_PHASES:
                continue
            raise ValueError(f"invalid setup recovery journal: {journal_path}")
        if journal.get("phase") not in TERMINAL_RECOVERY_PHASES:
            unresolved.append(journal_path.parent)
    return unresolved


def ensure_no_unresolved_transaction(codex_home: Path) -> None:
    unresolved = unresolved_transactions(codex_home)
    if unresolved:
        raise RuntimeError(
            "unresolved Rootloom setup transaction requires 'recover': "
            + ", ".join(str(path) for path in unresolved)
        )


def _valid_recovery_hash(value: Any, *, allow_missing: bool) -> bool:
    if value is None:
        return allow_missing
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _recovery_backup_bytes(
    transaction: Path,
    raw_relative: Any,
    expected_hash: str,
    label: str,
) -> bytes:
    if not isinstance(raw_relative, str):
        raise ValueError(f"invalid {label} backup path")
    relative = Path(raw_relative)
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"invalid {label} backup path")
    backup = transaction / relative
    if (
        has_symlink_component(backup, transaction)
        or not backup.resolve().is_relative_to(transaction.resolve())
        or not backup.is_file()
    ):
        raise ValueError(f"invalid {label} recovery backup")
    payload = backup.read_bytes()
    if sha256_bytes(payload) != expected_hash:
        raise RuntimeError(f"{label} recovery backup hash does not match its manifest")
    return payload


def _recovery_mode(value: Any, label: str) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > 0o7777
    ):
        raise ValueError(f"invalid {label} recovery mode")
    return value


def build_recovery_plan(
    codex_home: Path,
    transaction: Path,
    manifest: dict[str, Any],
) -> tuple[list[tuple[Path, bytes | None, int | None]], Path, bytes | None, int | None]:
    raw_home = manifest.get("codex_home")
    if not isinstance(raw_home, str) or Path(raw_home).resolve() != codex_home.resolve():
        raise ValueError("setup recovery manifest targets a different Codex home")
    if manifest.get("operation") not in {"apply", "rollback"}:
        raise ValueError("invalid setup recovery operation")
    entries = manifest.get("files")
    state_contract = manifest.get("state_recovery")
    if not isinstance(entries, list) or not isinstance(state_contract, dict):
        raise ValueError("setup transaction has no complete recovery contract")

    schema_version, recovery_targets = recovery_target_schema(manifest)
    seen: set[str] = set()
    plan: list[tuple[Path, bytes | None, int | None]] = []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            raise ValueError("invalid setup recovery entry")
        relative, _target_type = validate_recovery_target_entry(
            raw_entry,
            schema_version=schema_version,
            targets=recovery_targets,
            seen=seen,
            label="recovery",
        )
        destination = codex_home / relative
        if has_symlink_component(destination, codex_home):
            raise ValueError(f"refusing symlinked recovery target: {relative}")

        before_exists = raw_entry.get("before_exists")
        before_hash = raw_entry.get("before_hash")
        after_hash = raw_entry.get("after_hash")
        if not isinstance(before_exists, bool):
            raise ValueError(f"invalid recovery existence contract for {relative}")
        if not _valid_recovery_hash(before_hash, allow_missing=not before_exists):
            raise ValueError(f"invalid before hash for recovery target {relative}")
        if not _valid_recovery_hash(after_hash, allow_missing=True):
            raise ValueError(f"invalid after hash for recovery target {relative}")
        if after_hash is not None and POSIX_MODE_CONTRACT:
            after_mode = _recovery_mode(raw_entry.get("after_mode"), relative)
        else:
            if after_hash is None and raw_entry.get("after_mode") is not None:
                raise ValueError(f"inconsistent deleted-file recovery contract: {relative}")
            after_mode = None
        if before_exists:
            assert isinstance(before_hash, str)
            before = _recovery_backup_bytes(
                transaction,
                raw_entry.get("backup"),
                before_hash,
                relative,
            )
            mode = _recovery_mode(raw_entry.get("before_mode"), relative)
        else:
            if (
                before_hash is not None
                or raw_entry.get("backup") is not None
                or raw_entry.get("before_mode") is not None
            ):
                raise ValueError(f"inconsistent missing-file recovery contract: {relative}")
            before = None
            mode = None
        current = read_bytes(destination)
        current_hash = sha256_bytes(current) if current is not None else None
        if current_hash not in {before_hash, after_hash}:
            raise RuntimeError(f"recovery refused because {relative} changed after interruption")
        if POSIX_MODE_CONTRACT and current is not None:
            current_mode = file_mode(destination)
            allowed_modes: set[int] = set()
            if current_hash == before_hash and before_exists:
                assert mode is not None
                allowed_modes.add(mode)
            if current_hash == after_hash and after_mode is not None:
                allowed_modes.add(after_mode)
            if current_mode not in allowed_modes:
                raise RuntimeError(
                    f"recovery refused because {relative} mode changed after interruption"
                )
        plan.append((destination, before, mode))

    state_path = codex_home / STATE_DIRNAME / "state.json"
    state_before_exists = state_contract.get("before_exists")
    state_before_hash = state_contract.get("before_hash")
    state_after_hash = state_contract.get("after_hash")
    if not isinstance(state_before_exists, bool):
        raise ValueError("invalid setup-state recovery existence contract")
    if not _valid_recovery_hash(
        state_before_hash,
        allow_missing=not state_before_exists,
    ) or not _valid_recovery_hash(state_after_hash, allow_missing=True):
        raise ValueError("invalid setup-state recovery hash contract")
    if state_after_hash is not None and POSIX_MODE_CONTRACT:
        state_after_mode = _recovery_mode(
            state_contract.get("after_mode"),
            "setup state",
        )
    else:
        if state_after_hash is None and state_contract.get("after_mode") is not None:
            raise ValueError("inconsistent deleted setup-state recovery contract")
        state_after_mode = None
    if state_before_exists:
        assert isinstance(state_before_hash, str)
        state_before = _recovery_backup_bytes(
            transaction,
            "state.before",
            state_before_hash,
            "setup state",
        )
        state_mode = _recovery_mode(state_contract.get("before_mode"), "setup state")
    else:
        if state_before_hash is not None or state_contract.get("before_mode") is not None:
            raise ValueError("inconsistent missing setup-state recovery contract")
        state_before = None
        state_mode = None
    state_current = read_bytes(state_path)
    state_hash = sha256_bytes(state_current) if state_current is not None else None
    if state_hash not in {state_before_hash, state_after_hash}:
        raise RuntimeError("recovery refused because setup state changed after interruption")
    if POSIX_MODE_CONTRACT and state_current is not None:
        current_state_mode = file_mode(state_path)
        allowed_state_modes: set[int] = set()
        if state_hash == state_before_hash and state_before_exists:
            assert state_mode is not None
            allowed_state_modes.add(state_mode)
        if state_hash == state_after_hash and state_after_mode is not None:
            allowed_state_modes.add(state_after_mode)
        if current_state_mode not in allowed_state_modes:
            raise RuntimeError(
                "recovery refused because setup state mode changed after interruption"
            )
    return plan, state_path, state_before, state_mode


def _recover_locked(codex_home: Path) -> dict[str, Any]:
    unresolved = unresolved_transactions(codex_home)
    if not unresolved:
        return {"status": "no_recovery_required", "codex_home": str(codex_home)}
    if len(unresolved) != 1:
        raise RuntimeError("multiple unresolved setup transactions require manual recovery")
    transaction = unresolved[0]
    manifest_path = transaction / "manifest.json"
    if manifest_path.is_symlink():
        raise ValueError("refusing symlinked transaction manifest")
    manifest_payload = manifest_path.read_bytes()
    journal = json.loads((transaction / "recovery.json").read_text(encoding="utf-8"))
    if journal.get("manifest_sha256") != sha256_bytes(manifest_payload):
        raise RuntimeError("setup recovery manifest changed after journal preparation")
    manifest = json.loads(manifest_payload)
    if not isinstance(manifest, dict):
        raise ValueError("invalid setup recovery manifest")
    plan, state_path, state_before, state_mode = build_recovery_plan(
        codex_home,
        transaction,
        manifest,
    )
    for destination, before, mode in reversed(plan):
        if before is not None:
            assert mode is not None
            atomic_write(destination, before, mode=mode)
        else:
            destination.unlink(missing_ok=True)
    if state_before is not None:
        assert state_mode is not None
        atomic_write(state_path, state_before, mode=state_mode)
    else:
        state_path.unlink(missing_ok=True)
    write_recovery_journal(transaction, "recovered", [])
    return {"status": "recovered", "transaction": str(transaction)}


def recover(codex_home: Path) -> dict[str, Any]:
    with setup_lock(codex_home):
        return _recover_locked(codex_home)


def _apply_plan_locked(
    codex_home: Path,
    replace_conflicts: bool,
    capabilities: tuple[str, ...] = FULL_CAPABILITIES,
) -> dict[str, Any]:
    ensure_no_unresolved_transaction(codex_home)
    selected_capabilities = normalize_capabilities(capabilities)
    selected_components = components_for_capabilities(selected_capabilities)
    previous_state = load_state(codex_home)
    current_selection = installed_capabilities(previous_state)
    if current_selection is not None and current_selection != selected_capabilities:
        raise RuntimeError(
            "capability selection differs from the installed transaction; run rollback "
            "first, then apply the new preset or capability set"
        )
    version, targets, actions, desired = build_plan(codex_home, selected_capabilities)
    conflicts = [item for item in actions if item.action == "conflict"]
    unsafe_conflicts = [item for item in conflicts if "symlink" in item.reason]
    if unsafe_conflicts:
        paths = ", ".join(item.path for item in unsafe_conflicts)
        raise RuntimeError(f"setup refuses symlinked targets: {paths}")
    if conflicts and not replace_conflicts:
        raise RuntimeError(
            "setup has user-owned conflicts; review plan and rerun with "
            "--replace-conflicts only after explicit authorization"
        )

    changed = [item for item in actions if item.action != "unchanged"]
    if not changed:
        return {
            "status": "unchanged",
            "version": version,
            "codex_home": str(codex_home),
            "capabilities": list(selected_capabilities),
            "components": list(selected_components),
            "actions": [asdict(item) for item in actions],
        }

    transaction = make_transaction_dir(codex_home)
    target_types = {target.relative_path: target.kind for target in targets}
    manifest_entries: list[dict[str, Any]] = []
    for action in changed:
        destination = codex_home / action.path
        if has_symlink_component(destination, codex_home):
            raise ValueError(f"refusing symlinked setup target: {action.path}")
        before = read_bytes(destination)
        backup_relative: str | None = None
        before_mode: int | None = None
        if before is not None:
            backup = transaction / action.path
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, backup, follow_symlinks=False)
            backup_relative = action.path
            before_mode = file_mode(destination)
        manifest_entries.append(
            {
                "path": action.path,
                "target_type": target_types[action.path],
                "before_exists": before is not None,
                "before_hash": sha256_bytes(before) if before is not None else None,
                "before_mode": before_mode,
                "after_hash": sha256_bytes(desired[action.path]),
                "after_mode": 0o600 if POSIX_MODE_CONTRACT else None,
                "backup": backup_relative,
            }
        )
    transaction_manifest = {
        "operation": "apply",
        "version": version,
        "producer_version": version,
        "recovery_schema_version": RECOVERY_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "codex_home": str(codex_home),
        "capabilities": list(selected_capabilities),
        "components": list(selected_components),
        "previous_state": previous_state,
        "files": manifest_entries,
    }
    atomic_write(
        transaction / "manifest.json",
        (json.dumps(transaction_manifest, indent=2, sort_keys=True) + "\n").encode(),
    )
    state_path = codex_home / STATE_DIRNAME / "state.json"
    state_before = read_bytes(state_path)
    state_before_mode = file_mode(state_path) if state_before is not None else None
    state = {
        "status": "installed",
        "version": version,
        "capabilities": list(selected_capabilities),
        "components": list(selected_components),
        "latest_transaction": str(transaction.relative_to(codex_home / STATE_DIRNAME)),
        "files": {
            action.path: {"after_hash": action.after_hash}
            for action in actions
        },
    }
    state_payload = (json.dumps(state, indent=2, sort_keys=True) + "\n").encode()
    if state_before is not None:
        atomic_write(transaction / "state.before", state_before, mode=state_before_mode or 0o600)
    transaction_manifest["state_recovery"] = {
        "before_exists": state_before is not None,
        "before_hash": sha256_bytes(state_before) if state_before is not None else None,
        "before_mode": state_before_mode,
        "after_hash": sha256_bytes(state_payload),
        "after_mode": 0o600 if POSIX_MODE_CONTRACT else None,
    }
    atomic_write(
        transaction / "manifest.json",
        (json.dumps(transaction_manifest, indent=2, sort_keys=True) + "\n").encode(),
    )
    write_recovery_journal(transaction, "prepared", [])
    mutated_entries: list[dict[str, Any]] = []
    try:
        for entry in manifest_entries:
            destination = codex_home / entry["path"]
            mutated_entries.append(entry)
            atomic_write(destination, desired[entry["path"]])
            write_recovery_journal(
                transaction,
                "applying",
                [item["path"] for item in mutated_entries],
            )
        atomic_write(
            state_path,
            state_payload,
        )
        write_recovery_journal(
            transaction,
            "committed",
            [item["path"] for item in mutated_entries],
        )
    except Exception as exc:
        restore_errors: list[str] = []
        for entry in reversed(mutated_entries):
            destination = codex_home / entry["path"]
            try:
                if entry["before_exists"]:
                    backup = transaction / entry["backup"]
                    atomic_write(
                        destination,
                        backup.read_bytes(),
                        mode=entry.get("before_mode") or file_mode(backup),
                    )
                else:
                    destination.unlink(missing_ok=True)
            except Exception as restore_exc:  # pragma: no cover - catastrophic double fault
                restore_errors.append(f"{entry['path']}: {restore_exc}")
        try:
            if state_before is None:
                state_path.unlink(missing_ok=True)
            else:
                atomic_write(
                    state_path,
                    state_before,
                    mode=state_before_mode or 0o600,
                )
        except Exception as restore_exc:  # pragma: no cover - catastrophic double fault
            restore_errors.append(f"{STATE_DIRNAME}/state.json: {restore_exc}")
        if restore_errors:
            raise RuntimeError(
                "setup failed and compensation was incomplete: "
                + "; ".join(restore_errors)
            ) from exc
        write_recovery_journal(transaction, "compensated", [])
        raise
    return {
        "status": "applied",
        "version": version,
        "codex_home": str(codex_home),
        "capabilities": list(selected_capabilities),
        "components": list(selected_components),
        "transaction": str(transaction),
        "actions": [asdict(item) for item in actions],
    }


def apply_plan(
    codex_home: Path,
    replace_conflicts: bool,
    capabilities: tuple[str, ...] = FULL_CAPABILITIES,
) -> dict[str, Any]:
    with setup_lock(codex_home):
        return _apply_plan_locked(codex_home, replace_conflicts, capabilities)


def _rollback_locked(codex_home: Path) -> dict[str, Any]:
    ensure_no_unresolved_transaction(codex_home)
    state = load_state(codex_home)
    if state.get("status") != "installed" or not state.get("latest_transaction"):
        raise RuntimeError("no installed transaction is available to roll back")
    selected_capabilities = installed_capabilities(state)
    if selected_capabilities is None:
        selected_capabilities = FULL_CAPABILITIES
    transaction_relative = Path(str(state["latest_transaction"]))
    if transaction_relative.is_absolute() or ".." in transaction_relative.parts:
        raise ValueError("invalid setup transaction path")
    state_root = codex_home / STATE_DIRNAME
    if state_root.is_symlink():
        raise ValueError("refusing symlinked setup state directory")
    transaction = (state_root / transaction_relative).resolve()
    if not transaction.is_relative_to((state_root / "backups").resolve()):
        raise ValueError("setup transaction escaped the backup directory")
    manifest_path = transaction / "manifest.json"
    if manifest_path.is_symlink():
        raise ValueError("refusing symlinked transaction manifest")
    manifest_payload = manifest_path.read_bytes()
    journal_path = transaction / "recovery.json"
    if journal_path.exists():
        if journal_path.is_symlink():
            raise ValueError("refusing symlinked transaction recovery journal")
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        if not isinstance(journal, dict):
            raise ValueError("invalid transaction recovery journal")
        if (
            journal.get("format") == RECOVERY_FORMAT
            and journal.get("manifest_sha256") != sha256_bytes(manifest_payload)
        ):
            raise RuntimeError("setup transaction manifest changed after journal commit")
    manifest = json.loads(manifest_payload)
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ValueError(f"invalid transaction manifest: {manifest_path}")
    previous_state = manifest.get("previous_state")
    if previous_state is not None and not isinstance(previous_state, dict):
        raise ValueError("invalid previous setup state in transaction manifest")
    if isinstance(previous_state, dict) and previous_state.get("status") == "installed":
        active_capabilities = installed_capabilities(previous_state)
        if active_capabilities is None:
            raise ValueError("invalid previous installed setup state")
        previous_transaction = Path(str(previous_state.get("latest_transaction", "")))
        if (
            not previous_transaction.parts
            or previous_transaction.is_absolute()
            or ".." in previous_transaction.parts
        ):
            raise ValueError("invalid previous setup transaction path")
    else:
        active_capabilities = None

    schema_version, recovery_targets = recovery_target_schema(manifest)
    rollback_snapshots: list[tuple[str, bytes | None, int | None]] = []
    rollback_mutations: list[tuple[str, bytes | None, int | None]] = []
    seen_paths: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("invalid transaction manifest entry")
        relative_path, _target_type = validate_recovery_target_entry(
            entry,
            schema_version=schema_version,
            targets=recovery_targets,
            seen=seen_paths,
            label="transaction",
        )
        destination = codex_home / relative_path
        if has_symlink_component(destination, codex_home):
            raise ValueError(f"refusing symlinked rollback target: {relative_path}")
        current = read_bytes(destination)
        current_mode = file_mode(destination) if current is not None else None
        rollback_snapshots.append(
            (
                relative_path,
                current,
                current_mode,
            )
        )
        current_hash = sha256_bytes(current) if current is not None else None
        after_hash = entry.get("after_hash")
        before_hash = entry.get("before_hash")
        before_exists = entry.get("before_exists")
        if not _valid_recovery_hash(after_hash, allow_missing=True):
            raise ValueError(f"invalid transaction after hash: {relative_path}")
        raw_after_mode = entry.get("after_mode")
        if raw_after_mode is None:
            expected_after_mode = None
        elif after_hash is None:
            raise ValueError(f"invalid transaction after mode: {relative_path}")
        else:
            expected_after_mode = _recovery_mode(raw_after_mode, relative_path)
        if not isinstance(before_exists, bool) or not _valid_recovery_hash(
            before_hash,
            allow_missing=not before_exists,
        ):
            raise ValueError(f"invalid transaction before contract: {relative_path}")
        content_drift = current_hash != after_hash
        mode_drift = (
            expected_after_mode is not None
            and current is not None
            and current_mode != expected_after_mode
        )
        managed_config_drift = False
        if content_drift or mode_drift:
            if relative_path == "config.toml" and current is not None:
                if managed_agent_limits_intact(current.decode("utf-8")):
                    managed_config_drift = True
                else:
                    raise RuntimeError(
                        f"refusing rollback because {entry['path']} changed after setup"
                    )
            else:
                raise RuntimeError(
                    f"refusing rollback because {entry['path']} changed after setup"
                )

        previous = b""
        previous_mode: int | None = None
        if before_exists:
            assert isinstance(before_hash, str)
            previous = _recovery_backup_bytes(
                transaction,
                entry.get("backup"),
                before_hash,
                relative_path,
            )
            previous_mode = _recovery_mode(entry.get("before_mode"), relative_path)
        elif before_hash is not None or entry.get("backup") is not None:
            raise ValueError(f"inconsistent missing transaction target: {relative_path}")

        if managed_config_drift:
            assert current is not None and current_mode is not None
            restored = restore_agent_limits(
                current.decode("utf-8"),
                previous.decode("utf-8"),
            ).encode()
            rollback_mutations.append(
                (relative_path, restored or None, current_mode if restored else None)
            )
        else:
            rollback_mutations.append(
                (relative_path, previous if before_exists else None, previous_mode)
            )

    if isinstance(previous_state, dict) and previous_state.get("status") == "installed":
        next_state = previous_state
        rollback_status = "rolled_back_to_previous"
    else:
        next_state = {
            **state,
            "status": "rolled_back",
            "rolled_back_at": datetime.now(timezone.utc).isoformat(),
        }
        rollback_status = "rolled_back"
    state_path = codex_home / STATE_DIRNAME / "state.json"
    state_before = read_bytes(state_path)
    state_before_mode = file_mode(state_path) if state_before is not None else None
    if state_before is None or state_before_mode is None:
        raise RuntimeError("installed setup state disappeared before rollback")
    next_state_payload = (json.dumps(next_state, indent=2, sort_keys=True) + "\n").encode()

    rollback_recovery = make_transaction_dir(codex_home)
    recovery_entries: list[dict[str, Any]] = []
    snapshots_by_path = {
        relative: (before, mode)
        for relative, before, mode in rollback_snapshots
    }
    for relative, desired, _desired_mode in rollback_mutations:
        before, before_mode = snapshots_by_path[relative]
        backup_relative: str | None = None
        if before is not None:
            assert before_mode is not None
            backup_relative = (Path("before") / relative).as_posix()
            atomic_write(
                rollback_recovery / backup_relative,
                before,
                mode=before_mode,
            )
        recovery_entries.append(
            {
                "path": relative,
                "target_type": recovery_targets[relative],
                "before_exists": before is not None,
                "before_hash": sha256_bytes(before) if before is not None else None,
                "before_mode": before_mode,
                "after_hash": sha256_bytes(desired) if desired is not None else None,
                "after_mode": _desired_mode if POSIX_MODE_CONTRACT else None,
                "backup": backup_relative,
            }
        )
    atomic_write(
        rollback_recovery / "state.before",
        state_before,
        mode=state_before_mode,
    )
    rollback_manifest = {
        "operation": "rollback",
        "version": plugin_version(plugin_root()),
        "producer_version": plugin_version(plugin_root()),
        "recovery_schema_version": RECOVERY_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "codex_home": str(codex_home),
        "files": recovery_entries,
        "state_recovery": {
            "before_exists": True,
            "before_hash": sha256_bytes(state_before),
            "before_mode": state_before_mode,
            "after_hash": sha256_bytes(next_state_payload),
            "after_mode": 0o600 if POSIX_MODE_CONTRACT else None,
        },
    }
    atomic_write(
        rollback_recovery / "manifest.json",
        (json.dumps(rollback_manifest, indent=2, sort_keys=True) + "\n").encode(),
    )
    write_recovery_journal(rollback_recovery, "prepared", [])
    mutated_paths: list[str] = []
    try:
        for relative, desired, desired_mode in reversed(rollback_mutations):
            destination = codex_home / relative
            if desired is not None:
                assert desired_mode is not None
                atomic_write(destination, desired, mode=desired_mode)
            else:
                destination.unlink(missing_ok=True)
            mutated_paths.append(relative)
            write_recovery_journal(
                rollback_recovery,
                "applying",
                list(mutated_paths),
            )

        atomic_write(state_path, next_state_payload)
        write_recovery_journal(
            rollback_recovery,
            "committed",
            list(mutated_paths),
        )
    except Exception as exc:
        restore_errors: list[str] = []
        for relative_path, before, before_mode in reversed(rollback_snapshots):
            destination = codex_home / relative_path
            try:
                if before is None:
                    destination.unlink(missing_ok=True)
                else:
                    atomic_write(destination, before, mode=before_mode or 0o600)
            except Exception as restore_exc:  # pragma: no cover - catastrophic double fault
                restore_errors.append(f"{relative_path}: {restore_exc}")
        try:
            if state_before is None:
                state_path.unlink(missing_ok=True)
            else:
                atomic_write(
                    state_path,
                    state_before,
                    mode=state_before_mode or 0o600,
                )
        except Exception as restore_exc:  # pragma: no cover - catastrophic double fault
            restore_errors.append(f"{STATE_DIRNAME}/state.json: {restore_exc}")
        if restore_errors:
            raise RuntimeError(
                "rollback failed and compensation was incomplete: "
                + "; ".join(restore_errors)
            ) from exc
        write_recovery_journal(rollback_recovery, "compensated", [])
        raise
    return {
        "status": rollback_status,
        "codex_home": str(codex_home),
        "rolled_back_capabilities": list(selected_capabilities),
        "active_capabilities": list(active_capabilities or ()),
        "transaction": str(transaction),
        "files": [entry["path"] for entry in entries],
    }


def rollback(codex_home: Path) -> dict[str, Any]:
    with setup_lock(codex_home):
        return _rollback_locked(codex_home)


def rollback_all(codex_home: Path) -> dict[str, Any]:
    with setup_lock(codex_home):
        return _rollback_all_locked(codex_home)


def _rollback_all_locked(codex_home: Path) -> dict[str, Any]:
    transactions: list[dict[str, Any]] = []
    for _attempt in range(100):
        state = load_state(codex_home)
        if state.get("status") != "installed":
            if not transactions:
                raise RuntimeError("no installed transaction is available to roll back")
            return {
                "status": "rolled_back_all",
                "codex_home": str(codex_home),
                "active_capabilities": [],
                "transactions": transactions,
            }
        transactions.append(_rollback_locked(codex_home))
    raise RuntimeError("rollback chain exceeded 100 transactions")


def status_payload(
    codex_home: Path,
    capabilities: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    state = load_state(codex_home)
    selected_capabilities = capabilities
    if selected_capabilities is None:
        selected_capabilities = installed_capabilities(state)
        if selected_capabilities is None:
            selected_capabilities = FULL_CAPABILITIES
    selected_capabilities = normalize_capabilities(selected_capabilities)
    selected_components = components_for_capabilities(selected_capabilities)
    version, _targets, actions, _desired = build_plan(
        codex_home, selected_capabilities
    )
    return {
        "status": state.get("status", "not_installed"),
        "version": version,
        "installed_version": state.get("version"),
        "codex_home": str(codex_home),
        "capabilities": list(selected_capabilities),
        "components": list(selected_components),
        "actions": [asdict(item) for item in actions],
    }


def catalog_payload() -> dict[str, Any]:
    return {
        "status": "catalog",
        "default_preset": "full",
        "recommended_preset": "engineering",
        "capabilities": {
            name: {
                "description": description,
                "components": list(CAPABILITY_COMPONENTS[name]),
                "requires": list(CAPABILITY_DEPENDENCIES.get(name, ())),
            }
            for name, description in CAPABILITY_DESCRIPTIONS.items()
        },
        "components": COMPONENT_DESCRIPTIONS,
        "presets": {name: list(values) for name, values in PRESETS.items()},
        "note": (
            "Skills ship with the plugin. Select capability layers; components are the "
            "auditable implementation mapping. Change an installed selection by rolling it "
            "back first."
        ),
    }


def emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if payload.get("status") == "catalog":
        print("Rootloom capability levels")
        print(
            f"Recommended: {payload['recommended_preset']}  "
            f"Complete: {payload['default_preset']}"
        )
        for preset, capabilities in payload["presets"].items():
            label = ", ".join(capabilities) if capabilities else "Skills only"
            print(f"  {preset:12} {label}")
        print("\nCapability to artifact mapping")
        for name, detail in payload["capabilities"].items():
            requires = detail["requires"]
            suffix = f" (requires {', '.join(requires)})" if requires else ""
            print(f"  {name}: {detail['description']}{suffix}")
            print(f"    artifacts: {', '.join(detail['components'])}")
        return
    print(f"Rootloom: {payload['status']}")
    print(f"Codex home: {payload['codex_home']}")
    if payload.get("version"):
        print(f"Template version: {payload['version']}")
    if payload.get("installed_version"):
        print(f"Installed version: {payload['installed_version']}")
    if "capabilities" in payload and isinstance(payload["capabilities"], list):
        capabilities = payload["capabilities"]
        print(
            f"Capabilities: {', '.join(capabilities) if capabilities else 'skills-only'}"
        )
    if "components" in payload and isinstance(payload["components"], list):
        components = payload["components"]
        print(f"Artifacts: {', '.join(components) if components else 'hook policy only'}")
    for action in payload.get("actions", []):
        print(f"  {action['action'].upper():9} {action['path']} — {action['reason']}")
    if payload.get("transaction"):
        print(f"Transaction: {payload['transaction']}")


def add_selection_args(parser: argparse.ArgumentParser) -> None:
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--preset",
        choices=sorted(PRESETS),
        help="install a valid predefined component set",
    )
    selection.add_argument(
        "--capabilities",
        help=(
            "install an exact comma-separated capability set; use 'none' for Skills only"
        ),
    )


def parse_capability_argument(raw: str) -> tuple[str, ...]:
    if raw.strip().lower() == "none":
        return ()
    values = tuple(item.strip() for item in raw.split(",") if item.strip())
    if not values:
        raise ValueError("--capabilities requires a comma-separated list or 'none'")
    return normalize_capabilities(values)


def selected_capabilities_from_args(
    args: argparse.Namespace,
    codex_home: Path,
) -> tuple[str, ...]:
    if getattr(args, "preset", None):
        return PRESETS[args.preset]
    raw = getattr(args, "capabilities", None)
    if raw is not None:
        return parse_capability_argument(raw)
    if args.command == "status":
        selected = installed_capabilities(load_state(codex_home))
        return FULL_CAPABILITIES if selected is None else selected
    return FULL_CAPABILITIES


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
        help="Codex home to inspect or modify",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-components", help="show component and preset catalog")
    plan_parser = subparsers.add_parser("plan", help="preview every action without writing")
    add_selection_args(plan_parser)
    status_parser = subparsers.add_parser(
        "status", help="compare installed files with this release"
    )
    add_selection_args(status_parser)
    apply_parser = subparsers.add_parser("apply", help="apply the reviewed plan")
    add_selection_args(apply_parser)
    apply_parser.add_argument(
        "--replace-conflicts",
        action="store_true",
        help="replace user-owned conflicts after explicit authorization",
    )
    rollback_parser = subparsers.add_parser(
        "rollback", help="restore the most recent setup transaction"
    )
    rollback_parser.add_argument(
        "--all",
        action="store_true",
        help="unwind every setup transaction to the pre-install baseline",
    )
    subparsers.add_parser(
        "recover",
        help="recover one interrupted setup transaction after validating no user drift",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    codex_home = args.codex_home.expanduser().resolve()
    try:
        if args.command == "list-components":
            payload = catalog_payload()
        elif args.command == "plan":
            selected = selected_capabilities_from_args(args, codex_home)
            payload = status_payload(codex_home, selected)
            payload["status"] = "plan"
        elif args.command == "status":
            selected = selected_capabilities_from_args(args, codex_home)
            payload = status_payload(codex_home, selected)
        elif args.command == "apply":
            selected = selected_capabilities_from_args(args, codex_home)
            payload = apply_plan(codex_home, args.replace_conflicts, selected)
        elif args.command == "recover":
            payload = recover(codex_home)
        else:
            payload = rollback_all(codex_home) if args.all else rollback(codex_home)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        if args.json:
            print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    emit(payload, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

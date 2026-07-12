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


MANAGED_TOKEN = "rootloom:managed"
LIMITS_START = "# rootloom:agent-limits-start version=1"
LIMITS_END = "# rootloom:agent-limits-end"
STATE_DIRNAME = ".rootloom"
COMPONENT_POLICY_PATH = f"{STATE_DIRNAME}/components.json"
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
        os.fchmod(descriptor, 0o600)
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
    return rendered


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
    return rendered


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
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"refusing to write symlink: {path}")
    file_descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(file_descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


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


def _apply_plan_locked(
    codex_home: Path,
    replace_conflicts: bool,
    capabilities: tuple[str, ...] = FULL_CAPABILITIES,
) -> dict[str, Any]:
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
                "before_exists": before is not None,
                "before_hash": sha256_bytes(before) if before is not None else None,
                "before_mode": before_mode,
                "after_hash": sha256_bytes(desired[action.path]),
                "backup": backup_relative,
            }
        )
    transaction_manifest = {
        "version": version,
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
    mutated_entries: list[dict[str, Any]] = []
    try:
        for entry in manifest_entries:
            destination = codex_home / entry["path"]
            mutated_entries.append(entry)
            atomic_write(destination, desired[entry["path"]])
        atomic_write(
            state_path,
            (json.dumps(state, indent=2, sort_keys=True) + "\n").encode(),
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
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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

    allowed_paths = {target.relative_path for target in all_targets(plugin_root())}
    rollback_snapshots: list[tuple[str, bytes | None, int | None]] = []
    for entry in entries:
        relative_path = entry.get("path")
        if relative_path not in allowed_paths:
            raise ValueError(f"invalid transaction target: {relative_path!r}")
        destination = codex_home / relative_path
        if has_symlink_component(destination, codex_home):
            raise ValueError(f"refusing symlinked rollback target: {relative_path}")
        current = read_bytes(destination)
        rollback_snapshots.append(
            (
                relative_path,
                current,
                file_mode(destination) if current is not None else None,
            )
        )
        current_hash = sha256_bytes(current) if current is not None else None
        if current_hash != entry["after_hash"]:
            if relative_path == "config.toml" and current is not None:
                if managed_agent_limits_intact(current.decode("utf-8")):
                    continue
            raise RuntimeError(
                f"refusing rollback because {entry['path']} changed after setup"
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
    try:
        for entry in reversed(entries):
            destination = codex_home / entry["path"]
            current = read_bytes(destination)
            current_hash = sha256_bytes(current) if current is not None else None
            if entry["path"] == "config.toml" and current_hash != entry["after_hash"]:
                assert current is not None
                previous = b""
                if entry["before_exists"]:
                    backup_relative = Path(str(entry["backup"]))
                    if backup_relative.is_absolute() or ".." in backup_relative.parts:
                        raise ValueError("invalid transaction backup path")
                    backup_path = transaction / backup_relative
                    if backup_path.is_symlink():
                        raise ValueError("refusing symlinked transaction backup")
                    backup = backup_path.resolve()
                    if not backup.is_relative_to(transaction):
                        raise ValueError("transaction backup escaped its directory")
                    previous = backup.read_bytes()
                restored = restore_agent_limits(
                    current.decode("utf-8"),
                    previous.decode("utf-8"),
                ).encode()
                if restored:
                    atomic_write(destination, restored, mode=file_mode(destination))
                else:
                    destination.unlink(missing_ok=True)
                continue
            if entry["before_exists"]:
                backup_relative = Path(str(entry["backup"]))
                if backup_relative.is_absolute() or ".." in backup_relative.parts:
                    raise ValueError("invalid transaction backup path")
                backup_path = transaction / backup_relative
                if backup_path.is_symlink():
                    raise ValueError("refusing symlinked transaction backup")
                backup = backup_path.resolve()
                if not backup.is_relative_to(transaction):
                    raise ValueError("transaction backup escaped its directory")
                raw_mode = entry.get("before_mode")
                mode = raw_mode if isinstance(raw_mode, int) else file_mode(backup)
                atomic_write(destination, backup.read_bytes(), mode=mode)
            else:
                destination.unlink(missing_ok=True)

        atomic_write(
            state_path,
            (json.dumps(next_state, indent=2, sort_keys=True) + "\n").encode(),
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

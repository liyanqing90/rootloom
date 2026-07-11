#!/usr/bin/env python3
"""Track an advisory per-session child-agent budget and audit named role models."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any


DEFAULT_MAX_CHILDREN = 4
EXPECTED_MODELS = {
    "evidence_explorer": {"gpt-5.6-terra"},
    "root_cause_reviewer": {"gpt-5.6", "gpt-5.6-sol"},
    "implementation_worker": {"gpt-5.6", "gpt-5.6-sol"},
    "verification_reviewer": {"gpt-5.6", "gpt-5.6-sol"},
}


def _safe_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def _acquire_lock(path: Path) -> int | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for _attempt in range(25):
        try:
            return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > 10:
                    path.unlink(missing_ok=True)
                    continue
            except FileNotFoundError:
                continue
            time.sleep(0.01)
    return None


def _load_state(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"agent_ids": []}
    if not isinstance(payload, dict) or not isinstance(payload.get("agent_ids"), list):
        return {"agent_ids": []}
    return payload


def _unsafe_state_location(plugin_data: Path, state_dir: Path) -> str | None:
    """Reject state roots that could redirect writes through a symbolic link."""

    for candidate in (plugin_data, state_dir):
        if candidate.is_symlink():
            return str(candidate)
    return None


def audit_event(
    event: dict[str, Any],
    plugin_data: Path,
    max_children: int = DEFAULT_MAX_CHILDREN,
) -> dict[str, Any] | None:
    session_id = event.get("session_id")
    agent_id = event.get("agent_id")
    if not isinstance(session_id, str) or not session_id:
        return None
    if not isinstance(agent_id, str) or not agent_id:
        return None

    state_dir = plugin_data / "subagent-budget"
    unsafe_location = _unsafe_state_location(plugin_data, state_dir)
    if unsafe_location is not None:
        return {
            "systemMessage": (
                "Subagent budget audit skipped because its state location is a symbolic link: "
                f"{unsafe_location}"
            )
        }
    key = _safe_key(session_id)
    state_path = state_dir / f"{key}.json"
    lock_path = state_dir / f"{key}.lock"
    lock_descriptor = _acquire_lock(lock_path)
    if lock_descriptor is None:
        return {
            "systemMessage": "Subagent budget audit skipped because its state lock was busy."
        }
    try:
        os.close(lock_descriptor)
        state = _load_state(state_path)
        agent_ids = [item for item in state["agent_ids"] if isinstance(item, str)]
        if agent_id not in agent_ids:
            agent_ids.append(agent_id)
        state.update(
            {
                "agent_ids": agent_ids,
                "count": len(agent_ids),
                "updated_at": time.time(),
            }
        )
        _atomic_json(state_path, state)
    finally:
        lock_path.unlink(missing_ok=True)

    warnings: list[str] = []
    additional: list[str] = []
    count = len(agent_ids)
    if count > max_children:
        warnings.append(
            f"Advisory child-agent budget exceeded: started {count}, configured total is {max_children}."
        )
        additional.append(
            "This task has exceeded its advisory cumulative child-agent budget. "
            "SubagentStart Hooks cannot cancel a child. Do not modify files or spawn more agents; "
            "return a concise budget-exceeded notice to the parent so it can reuse or close existing threads."
        )

    agent_type = event.get("agent_type")
    actual_model = event.get("model")
    expected = EXPECTED_MODELS.get(str(agent_type))
    if expected and isinstance(actual_model, str) and actual_model not in expected:
        expected_text = " or ".join(sorted(expected))
        warnings.append(
            f"Custom-agent model mismatch: {agent_type} expected {expected_text}, observed {actual_model}."
        )
        additional.append(
            "Treat the observed custom-agent model mismatch as a routing configuration error. "
            "Remain within the role's least-privilege behavior and report the mismatch to the parent."
        )

    if not warnings:
        return None
    return {
        "systemMessage": " ".join(warnings),
        "hookSpecificOutput": {
            "hookEventName": "SubagentStart",
            "additionalContext": " ".join(additional),
        },
    }


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"systemMessage": f"Subagent audit input error: {exc}"}))
        return 0
    if not isinstance(event, dict):
        return 0
    plugin_data = Path(
        os.environ.get(
            "PLUGIN_DATA",
            Path.home() / ".codex" / ".rootloom" / "plugin-data",
        )
    ).expanduser()
    try:
        limit = int(os.environ.get("CODEX_ENGINEERING_MAX_CHILDREN", DEFAULT_MAX_CHILDREN))
    except ValueError:
        limit = DEFAULT_MAX_CHILDREN
    output = audit_event(event, plugin_data, max(1, limit))
    if output is not None:
        print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

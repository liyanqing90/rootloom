"""Canonical bounded-state commitment helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def commitment_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {
            "kind": "bytes",
            "size": len(value),
            "sha256": hashlib.sha256(value).hexdigest(),
        }
    if isinstance(value, set):
        return sorted(commitment_value(item) for item in value)
    if isinstance(value, dict):
        return {
            str(key): commitment_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [commitment_value(item) for item in value]
    return value


def commitment_sha256(value: Any) -> str:
    payload = json.dumps(
        commitment_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def repository_state_commitment(state: dict[str, Any]) -> dict[str, Any]:
    """Commit to every bounded repository-state component without expanding Result."""

    components = {
        "status": state["status_raw"],
        "paths": state["paths"],
        "ignored_paths": state["ignored_paths"],
        "untracked_paths": state["untracked_paths"],
        "sensitive_untracked_paths": state["sensitive_untracked_paths"],
        "metadata_only_paths": state["metadata_only_paths"],
        "worktree": state["worktree"],
        "index": state["index"],
        "git_control": state["git_control"],
    }
    component_hashes = {
        name: commitment_sha256(value) for name, value in components.items()
    }
    commitment = {
        "format": "rootloom-repository-state-commitment-v1",
        "path_count": len(state["paths"]),
        "worktree_entry_count": len(state["worktree"]),
        "component_sha256": component_hashes,
    }
    commitment["sha256"] = commitment_sha256(commitment)
    return commitment

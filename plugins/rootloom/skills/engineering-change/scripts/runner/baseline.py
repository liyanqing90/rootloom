"""Producer/consumer contract for pre-change repository baselines."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any

from .state import git_bounded


BASELINE_FORMAT = "rootloom-change-baseline-v1"
MAX_BASELINE_BYTES = 16 * 1024 * 1024


def repository_identity(repo: Path) -> dict[str, str]:
    raw = git_bounded(repo, "rev-parse", "--git-common-dir", max_bytes=4096)
    git_common = Path(raw.decode("utf-8", errors="surrogateescape").strip())
    if not git_common.is_absolute():
        git_common = repo / git_common
    return {"worktree": str(repo), "git_common_dir": str(git_common.resolve())}


def baseline_payload(
    repo: Path,
    *,
    snapshot: dict[str, Any],
    tracked_patch: bytes,
    extra_sensitive: list[str],
) -> dict[str, Any]:
    return {
        "format": BASELINE_FORMAT,
        "repository": repository_identity(repo),
        "snapshot": snapshot,
        "tracked_patch_sha256": hashlib.sha256(tracked_patch).hexdigest(),
        "sensitive_paths": sorted(extra_sensitive),
    }


def write_new_baseline(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise ValueError(f"baseline output already exists: {path}")
    encoded = (
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")
    if len(encoded) > MAX_BASELINE_BYTES:
        raise ValueError(f"baseline exceeds {MAX_BASELINE_BYTES}-byte budget")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def load_baseline(path: Path, repo: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError(f"baseline must not be a symlink: {path}")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError(f"baseline must be a regular file: {path}")
        raw = bytearray()
        while len(raw) <= MAX_BASELINE_BYTES:
            chunk = os.read(descriptor, min(64 * 1024, MAX_BASELINE_BYTES + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        after = os.fstat(descriptor)
        if (
            (opened.st_dev, opened.st_ino, opened.st_size)
            != (after.st_dev, after.st_ino, after.st_size)
        ):
            raise ValueError(f"baseline changed during read: {path}")
        if len(raw) > MAX_BASELINE_BYTES or after.st_size > MAX_BASELINE_BYTES:
            raise ValueError(f"baseline exceeds {MAX_BASELINE_BYTES} bytes: {path}")
    finally:
        os.close(descriptor)
    try:
        payload = json.loads(bytes(raw).decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid baseline JSON: {path}") from exc
    if not isinstance(payload, dict) or payload.get("format") != BASELINE_FORMAT:
        raise ValueError(f"baseline format must be {BASELINE_FORMAT}")
    if payload.get("repository") != repository_identity(repo):
        raise ValueError("baseline belongs to a different repository/worktree")
    snapshot = payload.get("snapshot")
    if not isinstance(snapshot, dict) or not isinstance(
        snapshot.get("sensitive_paths"), list
    ):
        raise ValueError("baseline snapshot is malformed")
    extra = payload.get("sensitive_paths", [])
    if not isinstance(extra, list) or any(not isinstance(item, str) for item in extra):
        raise ValueError("baseline sensitive_paths must be a string list")
    return payload


def sensitive_preservation(
    baseline: dict[str, Any], current_snapshot: dict[str, Any]
) -> dict[str, Any]:
    before = {
        item["path"]: item
        for item in baseline["snapshot"]["sensitive_paths"]
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    after = {
        item["path"]: item
        for item in current_snapshot["sensitive_paths"]
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    missing = sorted(
        path
        for path, metadata in before.items()
        if metadata.get("exists") and not after.get(path, {}).get("exists")
    )
    changed = sorted(
        path
        for path, metadata in before.items()
        if metadata.get("exists")
        and after.get(path, {}).get("exists")
        and metadata != after[path]
    )
    return {"preserved": not missing and not changed, "missing": missing, "changed": changed}

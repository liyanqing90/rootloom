"""Producer/consumer contract for pre-change repository baselines."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from datetime import UTC, datetime
from typing import Any
import uuid

from .state import git_bounded


BASELINE_FORMAT = "rootloom-change-baseline-v1"
BASELINE_FORMAT_V2 = "rootloom-change-baseline-v2"
MAX_BASELINE_BYTES = 16 * 1024 * 1024
PRODUCER_VERSION = "2.2.1"


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    ).encode("ascii")


def payload_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def task_sha256(task: str) -> str:
    return hashlib.sha256(task.encode("utf-8", errors="surrogateescape")).hexdigest()


def repository_identity(repo: Path) -> dict[str, str]:
    raw = git_bounded(repo, "rev-parse", "--git-common-dir", max_bytes=4096)
    git_common = Path(raw.decode("utf-8", errors="surrogateescape").strip())
    if not git_common.is_absolute():
        git_common = repo / git_common
    return {"worktree": str(repo), "git_common_dir": str(git_common.resolve())}


def git_identity(repo: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, args in {
        "head": ("rev-parse", "HEAD"),
        "index_sha256": ("write-tree",),
    }.items():
        try:
            raw = git_bounded(repo, *args, max_bytes=4096)
            result[key] = raw.decode("utf-8", errors="surrogateescape").strip()
        except Exception:
            result[key] = ""
    return result


def baseline_payload(
    repo: Path,
    *,
    snapshot: dict[str, Any],
    tracked_patch: bytes,
    extra_sensitive: list[str],
    task: str = "",
    provenance: str = "self-declared",
) -> dict[str, Any]:
    if provenance not in {"self-declared", "operator-sealed"}:
        raise ValueError("baseline provenance must be self-declared or operator-sealed")
    run_id = str(uuid.uuid4())
    nonce = uuid.uuid4().hex
    sensitive_policy = {
        "extra_sensitive": sorted(extra_sensitive),
        "snapshot_sensitive_paths": snapshot.get("sensitive_paths", []),
    }
    return {
        "format": BASELINE_FORMAT_V2,
        "run_id": run_id,
        "nonce": nonce,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "producer_version": PRODUCER_VERSION,
        "evidence_provenance": provenance,
        "repository": repository_identity(repo),
        "git": git_identity(repo),
        "task_sha256": task_sha256(task),
        "sensitive_policy_sha256": payload_sha256(sensitive_policy),
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


def _read_baseline_bytes(path: Path) -> bytes:
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
    return bytes(raw)


def read_baseline_with_hash(path: Path, repo: Path) -> tuple[dict[str, Any], str]:
    raw = _read_baseline_bytes(path)
    digest = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid baseline JSON: {path}") from exc
    if not isinstance(payload, dict) or payload.get("format") not in {
        BASELINE_FORMAT,
        BASELINE_FORMAT_V2,
    }:
        raise ValueError(f"baseline format must be {BASELINE_FORMAT} or {BASELINE_FORMAT_V2}")
    if payload.get("repository") != repository_identity(repo):
        raise ValueError("baseline belongs to a different repository/worktree")
    if payload.get("format") == BASELINE_FORMAT_V2:
        for field in (
            "run_id",
            "nonce",
            "created_at",
            "producer_version",
            "task_sha256",
            "sensitive_policy_sha256",
        ):
            if not isinstance(payload.get(field), str) or not payload[field].strip():
                raise ValueError(f"baseline {field} must be a nonempty string")
        if not isinstance(payload.get("git"), dict):
            raise ValueError("baseline git identity is malformed")
        provenance = payload.get("evidence_provenance")
        if provenance not in {"self-declared", "operator-sealed"}:
            raise ValueError("baseline evidence_provenance is malformed")
    snapshot = payload.get("snapshot")
    if not isinstance(snapshot, dict) or not isinstance(
        snapshot.get("sensitive_paths"), list
    ):
        raise ValueError("baseline snapshot is malformed")
    extra = payload.get("sensitive_paths", [])
    if not isinstance(extra, list) or any(not isinstance(item, str) for item in extra):
        raise ValueError("baseline sensitive_paths must be a string list")
    return payload, digest


def load_baseline(path: Path, repo: Path) -> dict[str, Any]:
    payload, _digest = read_baseline_with_hash(path, repo)
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

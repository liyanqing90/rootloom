"""Producer/consumer contract for pre-change repository baselines."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import stat
import tempfile
from datetime import UTC, datetime
from typing import Any
import uuid

from .state import git_bounded, git_identity
from .strict_json import parse_json_object


BASELINE_FORMAT = "rootloom-change-baseline-v1"
BASELINE_FORMAT_V2 = "rootloom-change-baseline-v2"
MAX_BASELINE_BYTES = 16 * 1024 * 1024
PRODUCER_VERSION = "2.2.1"
MAX_FUTURE_CLOCK_SKEW_SECONDS = 300
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
GIT_OBJECT_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
NONCE_PATTERN = re.compile(r"[0-9a-f]{32}")
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
BASELINE_V2_FIELDS = {
    "format",
    "run_id",
    "nonce",
    "created_at",
    "producer_version",
    "evidence_provenance",
    "repository",
    "git",
    "task_sha256",
    "sensitive_policy_sha256",
    "snapshot",
    "tracked_patch_sha256",
    "sensitive_paths",
    "allow_dirty_baseline",
    "preexisting_changes",
}
SNAPSHOT_FIELDS = {"changes", "untracked", "sensitive_paths", "bounds"}
MISSING_METADATA_FIELDS = {
    "path",
    "kind",
    "exists",
    "sensitive",
    "content_read",
}
EXISTING_METADATA_FIELDS = {
    "path",
    "kind",
    "exists",
    "device",
    "inode",
    "link_count",
    "size",
    "mode",
    "mtime_ns",
    "ctime_ns",
    "sensitive",
    "content_read",
}
FINGERPRINT_FIELDS = {
    "path",
    "kind",
    "exists",
    "size",
    "mode",
    "sha256",
    "sensitive",
    "content_read",
    "text_patch",
}


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    ).encode("ascii")


def payload_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def task_sha256(task: str) -> str:
    return hashlib.sha256(task.encode("utf-8", errors="surrogateescape")).hexdigest()


def _normalized_repo_path(raw: str, *, field: str) -> str:
    value = raw.strip().replace("\\", "/")
    parsed = PurePosixPath(value)
    if (
        not value
        or parsed.is_absolute()
        or any(part in {"", ".", ".."} for part in parsed.parts)
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError(f"baseline {field} contains an unsafe repository path")
    return parsed.as_posix()


def _validated_repo_path(raw: Any, *, field: str) -> str:
    if not isinstance(raw, str):
        raise ValueError(f"baseline {field} path must be a string")
    normalized = _normalized_repo_path(raw, field=field)
    if normalized != raw:
        raise ValueError(f"baseline {field} path must be normalized")
    return normalized


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


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
    task: str = "",
    provenance: str = "self-declared",
    allow_dirty_baseline: bool = False,
    captured_git: dict[str, str] | None = None,
) -> dict[str, Any]:
    if provenance not in {"self-declared", "operator-sealed"}:
        raise ValueError("baseline provenance must be self-declared or operator-sealed")
    run_id = str(uuid.uuid4())
    nonce = uuid.uuid4().hex
    normalized_sensitive = sorted(
        {
            _normalized_repo_path(path, field="sensitive_paths")
            for path in extra_sensitive
        }
    )
    sensitive_policy = {
        "extra_sensitive": normalized_sensitive,
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
        "git": dict(captured_git) if captured_git is not None else git_identity(repo),
        "task_sha256": task_sha256(task),
        "sensitive_policy_sha256": payload_sha256(sensitive_policy),
        "snapshot": snapshot,
        "tracked_patch_sha256": hashlib.sha256(tracked_patch).hexdigest(),
        "sensitive_paths": normalized_sensitive,
        "allow_dirty_baseline": allow_dirty_baseline,
        "preexisting_changes": list(snapshot.get("changes", [])),
    }


def write_new_baseline(path: Path, payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("baseline must be a JSON object")
    if payload.get("format") == BASELINE_FORMAT_V2:
        _validate_v2_baseline(payload)
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
            (
                opened.st_dev,
                opened.st_ino,
                opened.st_size,
                opened.st_mtime_ns,
                opened.st_ctime_ns,
            )
            != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            )
        ):
            raise ValueError(f"baseline changed during read: {path}")
        if len(raw) > MAX_BASELINE_BYTES or after.st_size > MAX_BASELINE_BYTES:
            raise ValueError(f"baseline exceeds {MAX_BASELINE_BYTES} bytes: {path}")
    finally:
        os.close(descriptor)
    return bytes(raw)


def _validate_sha256(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(f"baseline {field} must be 64 lowercase hexadecimal characters")
    return value


def _validate_snapshot_record(
    item: dict[str, Any],
    *,
    field: str,
    require_sensitive: bool,
) -> None:
    path = _validated_repo_path(item.get("path"), field=field)
    del path
    exists = item.get("exists")
    sensitive = item.get("sensitive")
    content_read = item.get("content_read")
    if not isinstance(exists, bool) or not isinstance(sensitive, bool) or not isinstance(
        content_read, bool
    ):
        raise ValueError(f"baseline snapshot {field} metadata is malformed")
    if require_sensitive and (not sensitive or content_read):
        raise ValueError("baseline sensitive metadata must remain content-unread")
    kind = item.get("kind")
    if not isinstance(kind, str):
        raise ValueError(f"baseline snapshot {field} metadata is malformed")
    if not exists:
        if set(item) != MISSING_METADATA_FIELDS or kind != "missing" or content_read:
            raise ValueError(f"baseline snapshot {field} missing metadata is malformed")
        return
    if content_read:
        if (
            set(item) != FINGERPRINT_FIELDS
            or kind != "file"
            or sensitive
            or not _is_nonnegative_int(item.get("size"))
            or not _is_nonnegative_int(item.get("mode"))
            or not isinstance(item.get("sha256"), str)
            or SHA256_PATTERN.fullmatch(item["sha256"]) is None
            or item.get("text_patch") not in {"included", "not-text-or-over-limit"}
        ):
            raise ValueError(f"baseline snapshot {field} fingerprint is malformed")
        return
    expected_fields = set(EXISTING_METADATA_FIELDS)
    if kind == "symlink":
        expected_fields.update({"target_bytes", "target_sha256"})
    if (
        set(item) != expected_fields
        or kind not in {"file", "directory", "symlink", "other"}
        or any(
            not _is_nonnegative_int(item.get(name))
            for name in (
                "device",
                "inode",
                "link_count",
                "size",
                "mode",
                "mtime_ns",
                "ctime_ns",
            )
        )
        or (
            kind == "symlink"
            and (
                not _is_nonnegative_int(item.get("target_bytes"))
                or not isinstance(item.get("target_sha256"), str)
                or SHA256_PATTERN.fullmatch(item["target_sha256"]) is None
            )
        )
    ):
        raise ValueError(f"baseline snapshot {field} metadata is malformed")
    if require_sensitive and "sha256" in item:
        raise ValueError("baseline sensitive metadata must remain content-unread")


def _validate_v2_baseline(payload: dict[str, Any]) -> None:
    if set(payload) != BASELINE_V2_FIELDS:
        raise ValueError("baseline v2 has unexpected or missing fields")
    run_id = payload.get("run_id")
    try:
        parsed_run_id = uuid.UUID(str(run_id))
    except (ValueError, AttributeError) as exc:
        raise ValueError("baseline run_id must be a canonical UUID") from exc
    if str(parsed_run_id) != run_id:
        raise ValueError("baseline run_id must be a canonical UUID")
    nonce = payload.get("nonce")
    if not isinstance(nonce, str) or NONCE_PATTERN.fullmatch(nonce) is None:
        raise ValueError("baseline nonce must be 32 lowercase hexadecimal characters")
    for field in ("task_sha256", "sensitive_policy_sha256", "tracked_patch_sha256"):
        _validate_sha256(payload.get(field), field=field)
    producer_version = payload.get("producer_version")
    if not isinstance(producer_version, str) or not producer_version.strip():
        raise ValueError("baseline producer_version must be a nonempty string")
    created_at = payload.get("created_at")
    if not isinstance(created_at, str) or not created_at.endswith("Z"):
        raise ValueError("baseline created_at must be canonical UTC ending in Z")
    try:
        created = datetime.fromisoformat(created_at[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("baseline created_at must be canonical UTC ending in Z") from exc
    if created.isoformat().replace("+00:00", "Z") != created_at:
        raise ValueError("baseline created_at must be canonical UTC ending in Z")
    age = (datetime.now(UTC) - created).total_seconds()
    if age < -MAX_FUTURE_CLOCK_SKEW_SECONDS:
        raise ValueError("baseline created_at exceeds allowed future clock skew")
    git = payload.get("git")
    if not isinstance(git, dict) or set(git) != {
        "head",
        "head_ref",
        "index_sha256",
    }:
        raise ValueError("baseline git identity is malformed")
    for field in ("head", "index_sha256"):
        value = git.get(field)
        if not isinstance(value, str) or (
            value and GIT_OBJECT_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(f"baseline git {field} is malformed")
    if not git["index_sha256"]:
        raise ValueError("baseline git index_sha256 must not be empty")
    head_ref = git.get("head_ref")
    if not isinstance(head_ref, str) or (
        head_ref
        and (
            not head_ref.startswith("refs/")
            or any(ord(character) < 33 for character in head_ref)
            or any(token in head_ref for token in ("..", "//", "@{", "\\"))
        )
    ):
        raise ValueError("baseline git head_ref is malformed")
    if not git["head"] and not head_ref:
        raise ValueError("baseline git identity must name a commit or unborn branch")
    repository = payload.get("repository")
    if not isinstance(repository, dict) or set(repository) != {
        "worktree",
        "git_common_dir",
    }:
        raise ValueError("baseline repository identity is malformed")
    if any(
        not isinstance(repository.get(field), str) or not repository[field]
        for field in ("worktree", "git_common_dir")
    ):
        raise ValueError("baseline repository identity is malformed")
    snapshot = payload.get("snapshot")
    if not isinstance(snapshot, dict) or set(snapshot) != SNAPSHOT_FIELDS:
        raise ValueError("baseline snapshot is malformed")
    for field in ("changes", "untracked", "sensitive_paths"):
        if not isinstance(snapshot.get(field), list) or any(
            not isinstance(item, dict) for item in snapshot[field]
        ):
            raise ValueError(f"baseline snapshot {field} must be an object list")
    for item in snapshot["changes"]:
        if (
            set(item) != {"status", "path", "original_path"}
            or not isinstance(item.get("status"), str)
            or len(item["status"]) != 2
            or not isinstance(item.get("path"), str)
            or not isinstance(item.get("original_path"), str)
        ):
            raise ValueError("baseline snapshot changes are malformed")
        _validated_repo_path(item["path"], field="snapshot changes")
        if item["original_path"]:
            _validated_repo_path(item["original_path"], field="snapshot changes")
    for field in ("untracked", "sensitive_paths"):
        for item in snapshot[field]:
            _validate_snapshot_record(
                item,
                field=field,
                require_sensitive=field == "sensitive_paths",
            )
        paths = [item["path"] for item in snapshot[field]]
        if paths != sorted(set(paths)):
            raise ValueError(
                f"baseline snapshot {field} paths must be unique and sorted"
            )
    bounds = snapshot.get("bounds")
    if (
        not isinstance(bounds, dict)
        or set(bounds)
        != {
            "fingerprint_bytes_observed",
            "untracked_patch_bytes",
            "sensitive_change_quarantine",
        }
        or any(
            not _is_nonnegative_int(bounds.get(field))
            for field in ("fingerprint_bytes_observed", "untracked_patch_bytes")
        )
        or not isinstance(bounds.get("sensitive_change_quarantine"), bool)
    ):
        raise ValueError("baseline snapshot bounds must be an object")
    if not isinstance(payload.get("allow_dirty_baseline"), bool):
        raise ValueError("baseline allow_dirty_baseline must be a boolean")
    preexisting = payload.get("preexisting_changes")
    if not isinstance(preexisting, list) or any(
        not isinstance(item, dict)
        or set(item) != {"status", "path", "original_path"}
        or any(not isinstance(item[field], str) for field in item)
        for item in preexisting
    ):
        raise ValueError("baseline preexisting_changes must be an object list")
    if preexisting != snapshot["changes"]:
        raise ValueError("baseline preexisting_changes must equal snapshot changes")
    if snapshot["changes"] and not payload["allow_dirty_baseline"]:
        raise ValueError("baseline with pre-existing changes must declare dirty capture")
    if not snapshot["changes"] and payload["tracked_patch_sha256"] != EMPTY_SHA256:
        raise ValueError("clean baseline cannot contain a tracked patch")
    extra_sensitive = payload.get("sensitive_paths")
    if not isinstance(extra_sensitive, list) or any(
        not isinstance(item, str) for item in extra_sensitive
    ):
        raise ValueError("baseline sensitive_paths must be a string list")
    normalized_sensitive = [
        _validated_repo_path(item, field="sensitive_paths") for item in extra_sensitive
    ]
    if normalized_sensitive != sorted(set(normalized_sensitive)):
        raise ValueError("baseline sensitive_paths must be normalized, unique, and sorted")
    sensitive_policy = {
        "extra_sensitive": normalized_sensitive,
        "snapshot_sensitive_paths": snapshot["sensitive_paths"],
    }
    if payload_sha256(sensitive_policy) != payload["sensitive_policy_sha256"]:
        raise ValueError("baseline sensitive_policy_sha256 does not match content")
    provenance = payload.get("evidence_provenance")
    if provenance not in {"self-declared", "operator-sealed"}:
        raise ValueError("baseline evidence_provenance is malformed")


def read_baseline_payload_with_hash(path: Path) -> tuple[dict[str, Any], str]:
    raw = _read_baseline_bytes(path)
    digest = hashlib.sha256(raw).hexdigest()
    payload = parse_json_object(raw, label="baseline", encoding="ascii")
    if payload.get("format") not in {
        BASELINE_FORMAT,
        BASELINE_FORMAT_V2,
    }:
        raise ValueError(f"baseline format must be {BASELINE_FORMAT} or {BASELINE_FORMAT_V2}")
    if payload.get("format") == BASELINE_FORMAT_V2:
        _validate_v2_baseline(payload)
    snapshot = payload.get("snapshot")
    if not isinstance(snapshot, dict) or not isinstance(
        snapshot.get("sensitive_paths"), list
    ):
        raise ValueError("baseline snapshot is malformed")
    extra = payload.get("sensitive_paths", [])
    if not isinstance(extra, list) or any(not isinstance(item, str) for item in extra):
        raise ValueError("baseline sensitive_paths must be a string list")
    return payload, digest


def read_baseline_with_hash(path: Path, repo: Path) -> tuple[dict[str, Any], str]:
    payload, digest = read_baseline_payload_with_hash(path)
    if payload.get("repository") != repository_identity(repo):
        raise ValueError("baseline belongs to a different repository/worktree")
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
    added = sorted(
        path
        for path, metadata in after.items()
        if metadata.get("exists") and not before.get(path, {}).get("exists")
    )
    changed = sorted(
        path
        for path, metadata in before.items()
        if metadata.get("exists")
        and after.get(path, {}).get("exists")
        and metadata != after[path]
    )
    return {
        "preserved": not missing and not changed,
        "missing": missing,
        "changed": changed,
        "added": added,
    }

"""Bounded Git and worktree capture for Personal Core."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any


PLUGIN_LIB = Path(__file__).resolve().parents[4] / "lib"
sys.path.insert(0, str(PLUGIN_LIB))
from rootloom_paths import (
    is_sensitive_path,
    normalize_repo_path,
    sensitive_git_pathspecs,
)


DEFAULT_MAX_GIT_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_STATUS_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_STATUS_PATHS = 10_000
DEFAULT_MAX_LISTED_PATHS = 50_000
DEFAULT_MAX_FINGERPRINT_FILE_BYTES = 256 * 1024 * 1024
DEFAULT_MAX_FINGERPRINT_TOTAL_BYTES = 1024 * 1024 * 1024
DEFAULT_MAX_TEXT_PATCH_FILE_BYTES = 256 * 1024


def git_bounded(
    repo: Path,
    *args: str,
    max_bytes: int,
    accepted_codes: tuple[int, ...] = (0,),
    input_data: bytes | None = None,
) -> bytes:
    if max_bytes <= 0:
        raise ValueError("Git capture budget must be positive")
    process = subprocess.Popen(
        ["git", "--no-pager", *args],
        cwd=repo,
        stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if input_data is not None and process.stdin is not None:
        process.stdin.write(input_data)
        process.stdin.close()
    output = bytearray()
    assert process.stdout is not None
    while True:
        chunk = process.stdout.read(64 * 1024)
        if not chunk:
            break
        if len(output) + len(chunk) > max_bytes:
            process.kill()
            process.wait()
            raise ValueError(
                f"git {' '.join(args)} exceeds configured {max_bytes}-byte budget"
            )
        output.extend(chunk)
    returncode = process.wait()
    if returncode not in accepted_codes:
        reason = bytes(output).decode("utf-8", errors="replace").strip()
        raise ValueError(f"git {' '.join(args)} failed: {reason}")
    return bytes(output)


def repository_changes(
    repo: Path,
    *,
    max_bytes: int = DEFAULT_MAX_STATUS_BYTES,
    max_paths: int = DEFAULT_MAX_STATUS_PATHS,
) -> tuple[list[dict[str, str]], list[str]]:
    raw = git_bounded(
        repo,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
        max_bytes=max_bytes,
    )
    records = raw.split(b"\0")
    changes: list[dict[str, str]] = []
    untracked: list[str] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        decoded = record.decode("utf-8", errors="surrogateescape")
        status = decoded[:2]
        path = normalize_repo_path(decoded[3:], label="Git status path")
        original = ""
        if "R" in status or "C" in status:
            if index >= len(records):
                raise ValueError("incomplete Git rename/copy status record")
            original = normalize_repo_path(
                records[index].decode("utf-8", errors="surrogateescape"),
                label="Git status original path",
            )
            index += 1
        changes.append({"status": status, "path": path, "original_path": original})
        if len(changes) > max_paths:
            raise ValueError(f"Git status exceeds configured {max_paths}-path budget")
        if status == "??":
            untracked.append(path)
    return changes, untracked


def git_list_paths(
    repo: Path,
    args: list[str],
    *,
    max_bytes: int = DEFAULT_MAX_STATUS_BYTES,
    max_paths: int = DEFAULT_MAX_LISTED_PATHS,
) -> list[str]:
    raw = git_bounded(repo, *args, max_bytes=max_bytes)
    values = [
        normalize_repo_path(
            item.decode("utf-8", errors="surrogateescape"),
            label="Git listed path",
        )
        for item in raw.split(b"\0")
        if item
    ]
    if len(values) > max_paths:
        raise ValueError(f"Git path listing exceeds configured {max_paths}-path budget")
    return sorted(set(values))


def discover_sensitive_paths(repo: Path, extra_sensitive: set[str]) -> list[str]:
    pathspecs = sensitive_git_pathspecs()
    tracked = git_list_paths(repo, ["ls-files", "-z", "--", *pathspecs])
    ignored = git_list_paths(
        repo,
        ["ls-files", "-z", "--others", "--ignored", "--exclude-standard", "--", *pathspecs],
    )
    return sorted(set(tracked) | set(ignored) | set(extra_sensitive))


def _empty_tree(repo: Path) -> str:
    return git_bounded(
        repo,
        "hash-object",
        "-t",
        "tree",
        "--stdin",
        max_bytes=1024,
        input_data=b"",
    ).decode("ascii").strip()


def tracked_patch(
    repo: Path,
    *,
    max_bytes: int = DEFAULT_MAX_GIT_BYTES,
    sensitive_paths: list[str] | None = None,
) -> bytes:
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "HEAD"],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    if head.returncode == 0:
        baseline = "HEAD"
    else:
        symbolic = subprocess.run(
            ["git", "symbolic-ref", "--quiet", "HEAD"],
            cwd=repo,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
        if symbolic.returncode != 0:
            reason = head.stderr.decode("utf-8", errors="replace").strip()
            raise ValueError(f"git HEAD is invalid: {reason or 'not an unborn branch'}")
        baseline = _empty_tree(repo)
    exclusions = [f":(exclude,literal){path}" for path in sorted(sensitive_paths or [])]
    return git_bounded(
        repo,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--binary",
        baseline,
        "--",
        ".",
        *exclusions,
        max_bytes=max_bytes,
    )


def _metadata_for_missing(path: str, *, sensitive: bool) -> dict[str, Any]:
    return {
        "path": path,
        "kind": "missing",
        "exists": False,
        "sensitive": sensitive,
        "content_read": False,
    }


def metadata_only(repo: Path, path: str, *, sensitive: bool = True) -> dict[str, Any]:
    normalized = normalize_repo_path(path)
    candidate = repo / normalized
    try:
        info = candidate.lstat()
    except FileNotFoundError:
        return _metadata_for_missing(normalized, sensitive=sensitive)
    result: dict[str, Any] = {
        "path": normalized,
        "exists": True,
        "size": info.st_size,
        "mode": stat.S_IMODE(info.st_mode),
        "sensitive": sensitive,
        "content_read": False,
    }
    if stat.S_ISLNK(info.st_mode):
        result["kind"] = "symlink"
        result["target"] = os.readlink(candidate)
    elif stat.S_ISDIR(info.st_mode):
        result["kind"] = "directory"
    elif stat.S_ISREG(info.st_mode):
        result["kind"] = "file"
    else:
        result["kind"] = "other"
    return result


def _regular_file_fingerprint(
    repo: Path,
    path: str,
    *,
    remaining_total: int,
    max_file_bytes: int,
    max_text_patch_file_bytes: int,
) -> tuple[dict[str, Any], bytes | None, int]:
    candidate = repo / path
    before = candidate.lstat()
    if before.st_size > max_file_bytes:
        raise ValueError(
            f"untracked file exceeds configured {max_file_bytes}-byte fingerprint budget: {path}"
        )
    if before.st_size > remaining_total:
        raise ValueError("untracked files exceed the aggregate fingerprint byte budget")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(candidate, flags)
    digest = hashlib.sha256()
    retained = bytearray()
    observed = 0
    try:
        opened = os.fstat(descriptor)
        identity = (opened.st_dev, opened.st_ino, stat.S_IFMT(opened.st_mode))
        expected = (before.st_dev, before.st_ino, stat.S_IFMT(before.st_mode))
        if identity != expected or not stat.S_ISREG(opened.st_mode):
            raise ValueError(f"untracked file identity changed before fingerprint: {path}")
        while True:
            chunk = os.read(descriptor, 64 * 1024)
            if not chunk:
                break
            observed += len(chunk)
            if observed > max_file_bytes or observed > remaining_total:
                raise ValueError(f"untracked file changed beyond fingerprint budget: {path}")
            digest.update(chunk)
            if opened.st_size <= max_text_patch_file_bytes:
                retained.extend(chunk)
        after = os.fstat(descriptor)
        if (
            (after.st_dev, after.st_ino, stat.S_IFMT(after.st_mode)) != identity
            or after.st_size != opened.st_size
            or observed != opened.st_size
        ):
            raise ValueError(f"untracked file changed during fingerprint: {path}")
    finally:
        os.close(descriptor)
    content = bytes(retained) if retained else b"" if before.st_size == 0 else None
    is_text = False
    if content is not None and b"\0" not in content:
        try:
            content.decode("utf-8")
            is_text = True
        except UnicodeDecodeError:
            pass
    result = {
        "path": path,
        "kind": "file",
        "exists": True,
        "size": before.st_size,
        "mode": stat.S_IMODE(before.st_mode),
        "sha256": digest.hexdigest(),
        "sensitive": False,
        "content_read": True,
        "text_patch": "included" if is_text else "not-text-or-over-limit",
    }
    return result, content if is_text else None, observed


def _new_file_patch(path: str, content: bytes) -> bytes:
    encoded_path = path.encode("utf-8", errors="surrogateescape")
    header = (
        b"diff --git a/"
        + encoded_path
        + b" b/"
        + encoded_path
        + b"\nnew file mode 100644\n--- /dev/null\n+++ b/"
        + encoded_path
        + b"\n"
    )
    lines = content.splitlines(keepends=True)
    if not lines and not content:
        return header + b"@@ -0,0 +1,0 @@\n"
    body = b"".join(b"+" + line for line in lines)
    if content and not content.endswith((b"\n", b"\r")):
        body += b"\n\\ No newline at end of file\n"
    return header + f"@@ -0,0 +1,{len(lines)} @@\n".encode("ascii") + body


def repository_snapshot(
    repo: Path,
    *,
    extra_sensitive: list[str] | None = None,
    max_untracked_patch_bytes: int = DEFAULT_MAX_GIT_BYTES,
    max_fingerprint_file_bytes: int = DEFAULT_MAX_FINGERPRINT_FILE_BYTES,
    max_fingerprint_total_bytes: int = DEFAULT_MAX_FINGERPRINT_TOTAL_BYTES,
    max_text_patch_file_bytes: int = DEFAULT_MAX_TEXT_PATCH_FILE_BYTES,
) -> tuple[dict[str, Any], bytes]:
    normalized_extra = {
        normalize_repo_path(path, label="sensitive path") for path in extra_sensitive or []
    }
    changes, untracked = repository_changes(repo)
    sensitive_paths = discover_sensitive_paths(repo, normalized_extra)
    sensitive_set = set(sensitive_paths)
    fingerprints: list[dict[str, Any]] = []
    patch_parts: list[bytes] = []
    patch_bytes = 0
    hashed_bytes = 0
    for path in sorted(untracked):
        sensitive = path in sensitive_set or is_sensitive_path(
            path, extra_sensitive=normalized_extra
        )
        if sensitive:
            sensitive_set.add(path)
        candidate = repo / path
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            raise ValueError(f"untracked path disappeared during capture: {path}")
        if sensitive or not stat.S_ISREG(info.st_mode):
            fingerprints.append(metadata_only(repo, path, sensitive=sensitive))
            continue
        fingerprint, content, observed = _regular_file_fingerprint(
            repo,
            path,
            remaining_total=max_fingerprint_total_bytes - hashed_bytes,
            max_file_bytes=max_fingerprint_file_bytes,
            max_text_patch_file_bytes=max_text_patch_file_bytes,
        )
        hashed_bytes += observed
        fingerprints.append(fingerprint)
        if content is not None:
            part = _new_file_patch(path, content)
            if patch_bytes + len(part) > max_untracked_patch_bytes:
                raise ValueError(
                    "untracked text patches exceed the configured aggregate patch budget"
                )
            patch_parts.append(part)
            patch_bytes += len(part)
    sensitive_metadata = [metadata_only(repo, path) for path in sorted(sensitive_set)]
    return (
        {
            "changes": changes,
            "untracked": fingerprints,
            "sensitive_paths": sensitive_metadata,
            "bounds": {
                "fingerprint_bytes_observed": hashed_bytes,
                "untracked_patch_bytes": patch_bytes,
            },
        },
        b"\n".join(patch_parts),
    )


def snapshot_identity(snapshot: dict[str, Any]) -> str:
    encoded = json.dumps(
        snapshot, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()

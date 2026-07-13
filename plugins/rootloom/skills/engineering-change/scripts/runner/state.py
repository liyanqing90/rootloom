"""Read the small Git state needed by the personal summary."""

from __future__ import annotations

from pathlib import Path
import subprocess


def git(repo: Path, *args: str, input_data: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        reason = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"git {' '.join(args)} failed: {reason}")
    return completed.stdout


def repository_changes(repo: Path) -> tuple[list[dict[str, str]], list[str]]:
    raw = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
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
        path = decoded[3:]
        original = ""
        if "R" in status or "C" in status:
            if index >= len(records):
                raise ValueError("incomplete Git rename/copy status record")
            original = records[index].decode("utf-8", errors="surrogateescape")
            index += 1
        changes.append({"status": status, "path": path, "original_path": original})
        if status == "??":
            untracked.append(path)
    return changes, untracked


def tracked_patch(repo: Path) -> bytes:
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
        baseline = git(repo, "hash-object", "-t", "tree", "--stdin", input_data=b"").decode(
            "ascii"
        ).strip()
    return git(
        repo,
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--binary",
        baseline,
        "--",
    )

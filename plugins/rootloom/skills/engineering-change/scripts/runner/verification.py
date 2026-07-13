"""Verification command parsing and execution."""

from __future__ import annotations

import os
from pathlib import Path
import shlex

from .contracts import VerificationResult
from .process import run_command


def split_command(raw: str, *, windows: bool | None = None) -> list[str]:
    if windows is None:
        windows = os.name == "nt"
    argv = shlex.split(raw, posix=not windows)
    if windows:
        argv = [
            token[1:-1]
            if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}
            else token
            for token in argv
        ]
    if not argv:
        raise ValueError("verification command cannot be empty")
    return argv


def verify(
    commands: list[str],
    *,
    repo: Path,
    timeout: int,
    max_output_bytes: int,
) -> tuple[list[VerificationResult], bytes]:
    results: list[VerificationResult] = []
    chunks: list[bytes] = []
    for raw in commands:
        argv = split_command(raw)
        result, output = run_command(
            argv,
            cwd=repo,
            timeout=timeout,
            max_output_bytes=max_output_bytes,
        )
        results.append(result)
        chunks.append((f"$ {raw}\n").encode("utf-8") + output.rstrip() + b"\n")
        if not result.passed:
            break
    return results, b"\n".join(chunks)

"""Verification command parsing and execution."""

from __future__ import annotations

from pathlib import Path
import shlex

from .contracts import VerificationResult
from .process import run_command


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
        argv = shlex.split(raw)
        if not argv:
            raise ValueError("verification command cannot be empty")
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

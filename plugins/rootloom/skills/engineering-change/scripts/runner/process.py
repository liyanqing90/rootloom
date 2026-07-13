"""Bounded subprocess execution without a shell."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import time

from .contracts import VerificationResult


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int,
    max_output_bytes: int,
) -> tuple[VerificationResult, bytes]:
    started = time.monotonic()
    with tempfile.TemporaryFile() as captured:
        try:
            completed = subprocess.run(
                argv,
                cwd=cwd,
                stdout=captured,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=timeout,
            )
            exit_code = completed.returncode
        except subprocess.TimeoutExpired:
            captured.write(b"\nRootloom: command timed out\n")
            exit_code = 124
        size = captured.tell()
        truncated = size > max_output_bytes
        captured.seek(max(0, size - max_output_bytes))
        output = captured.read()
    if truncated:
        output = b"Rootloom: output truncated to the configured tail\n" + output
        exit_code = 125
    result = VerificationResult(
        command=argv,
        exit_code=exit_code,
        duration_seconds=round(time.monotonic() - started, 3),
        passed=exit_code == 0,
    )
    return result, output

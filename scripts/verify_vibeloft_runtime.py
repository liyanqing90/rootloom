#!/usr/bin/env python3
"""Verify the published VibeLoft browser runtime contract without emitting events."""

from __future__ import annotations

import sys
import shutil
import subprocess


SCRIPT_URL = "https://vibeloft.ai/telemetry/v1.js"
EVENT_ENDPOINT = "https://api.vibeloft.ai/api/v1/telemetry/events"
REQUIRED_TOKENS = (
    EVENT_ENDPOINT,
    'credentials:"omit"',
    "globalPrivacyControl",
    "doNotTrack",
    "pushState",
    "replaceState",
    "popstate",
    "retryDelay",
    'e.protocol!=="https:"',
)
FORBIDDEN_TOKENS = (
    "supabase",
    "document.cookie",
    "AudioContext",
    "canvas",
)


def main() -> int:
    curl = shutil.which("curl")
    if curl is None:
        print("ERROR: curl is required for the TLS-verified runtime check", file=sys.stderr)
        return 1
    try:
        completed = subprocess.run(
            [
                curl,
                "--fail",
                "--silent",
                "--show-error",
                "--location",
                "--proto",
                "=https",
                "--tlsv1.2",
                "--max-time",
                "15",
                "--max-filesize",
                "1000000",
                SCRIPT_URL,
            ],
            check=False,
            capture_output=True,
            timeout=20,
        )
        if completed.returncode != 0:
            raise OSError(completed.stderr.decode("utf-8", errors="replace").strip())
        source = completed.stdout[:1_000_001].decode("utf-8")
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError) as exc:
        print(f"ERROR: unable to read official VibeLoft runtime: {exc}", file=sys.stderr)
        return 1

    errors = [f"missing runtime contract token: {token}" for token in REQUIRED_TOKENS if token not in source]
    errors.extend(
        f"forbidden runtime capability present: {token}"
        for token in FORBIDDEN_TOKENS
        if token.casefold() in source.casefold()
    )
    if source.count(EVENT_ENDPOINT) != 1:
        errors.append("official runtime must contain exactly one VibeLoft event endpoint")
    if len(source.encode("utf-8")) > 1_000_000:
        errors.append("official runtime exceeds the bounded verification size")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Official VibeLoft runtime contract verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

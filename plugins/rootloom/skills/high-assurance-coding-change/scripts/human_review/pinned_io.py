"""Bounded pinned-descriptor reads for Human Review Decision Pair files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import MAX_HUMAN_REVIEW_DECISION_BYTES


def read_decision_pair_payloads(
    runtime: Any,
    run_dir: Path,
    directory_descriptor: int,
) -> tuple[bytes, bytes]:
    terminal_payload = runtime.read_pinned_private_artifact(
        run_dir / "human-review.ndjson",
        max_bytes=MAX_HUMAN_REVIEW_DECISION_BYTES,
        directory_descriptor=directory_descriptor,
    )
    summary_payload = runtime.read_pinned_private_artifact(
        run_dir / "human-review-summary.json",
        max_bytes=MAX_HUMAN_REVIEW_DECISION_BYTES,
        directory_descriptor=directory_descriptor,
    )
    return terminal_payload, summary_payload

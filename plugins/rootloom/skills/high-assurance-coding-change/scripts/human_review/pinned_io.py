"""Bounded pinned-descriptor reads for Human Review Decision Pair files."""

from __future__ import annotations

from pathlib import Path

import run_pipeline as runner

from .constants import MAX_HUMAN_REVIEW_DECISION_BYTES


def read_decision_pair_payloads(
    run_dir: Path,
    directory_descriptor: int,
) -> tuple[bytes, bytes]:
    terminal_payload = runner.read_pinned_private_artifact(
        run_dir / "human-review.ndjson",
        max_bytes=MAX_HUMAN_REVIEW_DECISION_BYTES,
        directory_descriptor=directory_descriptor,
    )
    summary_payload = runner.read_pinned_private_artifact(
        run_dir / "human-review-summary.json",
        max_bytes=MAX_HUMAN_REVIEW_DECISION_BYTES,
        directory_descriptor=directory_descriptor,
    )
    return terminal_payload, summary_payload

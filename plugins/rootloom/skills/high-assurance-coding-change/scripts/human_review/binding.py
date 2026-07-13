"""Current-state recomputation for a structurally valid Human Review Binding."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import run_pipeline as runner


def recompute_human_review_binding(
    repo: Path,
    run_dir: Path,
    result: dict[str, Any],
    expected: dict[str, Any],
    protected_deletions: list[str],
) -> dict[str, Any]:
    """Recapture current state only after the caller validates persisted schema."""

    return runner.compute_human_review_binding(
        repo,
        run_dir,
        runner.human_review_result_core_sha256(result),
        protected_deletions,
        state_policy=expected["state_policy"],
        metadata_only_floor=expected["final_metadata_only_floor_paths"],
        expected_repository_state_commitment=expected["repository_state"],
    )

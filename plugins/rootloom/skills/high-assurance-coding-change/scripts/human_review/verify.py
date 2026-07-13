"""Read-only Decision Pair verification and stale-state classification."""

from __future__ import annotations

import hashlib
from pathlib import Path

import run_pipeline as runner

from .binding import recompute_human_review_binding
from .constants import VERIFY_STALE_EXIT
from .decision import binding_sha256, read_decision_pair
from .schema import normalize_review_scope, validate_review_result


class StaleDecisionPair(runner.PipelineError):
    """A structurally valid Decision Pair no longer matches current reviewed state."""

    def __init__(self, message: str) -> None:
        super().__init__(message, VERIFY_STALE_EXIT)


def verify_decision_pair(repo: Path, run_dir: Path) -> dict[str, object]:
    """Verify one Decision Pair without acquiring a writer lock or changing files."""

    repo, run_dir = normalize_review_scope(repo, run_dir)
    run_descriptor, run_identity = runner._safe_run_directory_descriptor(run_dir)
    try:
        result = runner.read_human_review_result(run_dir)
        expected, protected_deletions = validate_review_result(repo, run_dir, result)
        initial_result_sha256 = runner.human_review_full_result_sha256(result)
        record, terminal_payload, summary_payload = read_decision_pair(
            run_dir,
            run_descriptor,
        )
        if record["binding_sha256"] != binding_sha256(expected):
            raise runner.PipelineError(
                "human review Terminal binding does not match Result",
                9,
            )
        try:
            current = recompute_human_review_binding(
                repo,
                run_dir,
                result,
                expected,
                protected_deletions,
            )
        except runner.PipelineError as exc:
            raise StaleDecisionPair(
                f"human review repository or Artifact state is stale: {exc}"
            ) from exc
        if current != expected:
            raise StaleDecisionPair(
                "human review binding no longer matches current reviewed state"
            )
        final_result = runner.read_human_review_result(run_dir)
        final_record, final_terminal, final_summary = read_decision_pair(
            run_dir,
            run_descriptor,
        )
        if (
            runner.human_review_full_result_sha256(final_result)
            != initial_result_sha256
            or final_record != record
            or final_terminal != terminal_payload
            or final_summary != summary_payload
        ):
            raise runner.PipelineError(
                "human review Result or Decision Pair changed during verification",
                9,
            )
        final_identity = runner.validate_run_directory_descriptor(
            run_dir,
            run_descriptor,
        )
        if final_identity != run_identity:
            raise runner.PipelineError(
                "human review Run Directory changed during verification",
                9,
            )
        return {
            "status": "VALID",
            "decision": record["decision"],
            "reviewer": record["reviewer"],
            "binding_sha256": record["binding_sha256"],
            "decision_record_sha256": hashlib.sha256(terminal_payload).hexdigest(),
        }
    finally:
        runner.close_descriptor_quietly(run_descriptor)

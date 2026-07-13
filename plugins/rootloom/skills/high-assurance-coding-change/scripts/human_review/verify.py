"""Read-only Decision Pair verification with typed public outcomes."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from runner.contracts import VerificationLimits
from runner.errors import (
    BindingDriftError,
    EvidenceInvalidError,
    PipelineError,
    VerificationError,
)

from .binding import recompute_human_review_binding
from .decision import binding_sha256, read_decision_pair
from .schema import normalize_review_scope, validate_review_result


StaleDecisionPair = BindingDriftError


def _invalid_runtime_read(message: str, operation: Any) -> Any:
    try:
        return operation()
    except EvidenceInvalidError:
        raise
    except (OSError, PipelineError, ValueError) as exc:
        detail = str(exc).strip()
        raise EvidenceInvalidError(detail or message) from exc


def verify_decision_pair(
    runtime: Any,
    repo: Path,
    run_dir: Path,
    limits: VerificationLimits | None = None,
) -> dict[str, object]:
    """Verify one Decision Pair without acquiring a writer lock or changing files."""

    repo, run_dir = normalize_review_scope(repo, run_dir)
    limits = (limits or VerificationLimits()).validate()
    try:
        run_descriptor, run_identity = runtime._safe_run_directory_descriptor(run_dir)
    except (OSError, PipelineError, ValueError) as exc:
        raise EvidenceInvalidError("human review Run Directory is unsafe") from exc
    try:
        result = _invalid_runtime_read(
            "human review Result is invalid or unsafe",
            lambda: runtime.read_human_review_result(run_dir),
        )
        expected, protected_deletions = validate_review_result(
            runtime,
            repo,
            run_dir,
            result,
        )
        initial_result_sha256 = runtime.human_review_full_result_sha256(result)
        record, terminal_payload, summary_payload = _invalid_runtime_read(
            "human review Decision Pair is invalid or unsafe",
            lambda: read_decision_pair(runtime, run_dir, run_descriptor),
        )
        if record["binding_sha256"] != binding_sha256(expected):
            raise EvidenceInvalidError(
                "human review Terminal binding does not match Result"
            )
        effective_policy = limits.constrain_policy(expected["state_policy"])
        effective_expected = {**expected, "state_policy": effective_policy}
        try:
            current = recompute_human_review_binding(
                runtime,
                repo,
                run_dir,
                result,
                effective_expected,
                protected_deletions,
            )
        except EvidenceInvalidError:
            raise
        except BindingDriftError:
            raise
        except (OSError, PipelineError, ValueError) as exc:
            raise VerificationError(
                f"human review current state could not be verified: {exc}"
            ) from exc
        if current != expected:
            raise BindingDriftError(
                "human review binding is stale and no longer matches current reviewed state"
            )
        final_result = _invalid_runtime_read(
            "human review Result became invalid during verification",
            lambda: runtime.read_human_review_result(run_dir),
        )
        final_record, final_terminal, final_summary = _invalid_runtime_read(
            "human review Decision Pair became invalid during verification",
            lambda: read_decision_pair(runtime, run_dir, run_descriptor),
        )
        if (
            runtime.human_review_full_result_sha256(final_result)
            != initial_result_sha256
            or final_record != record
            or final_terminal != terminal_payload
            or final_summary != summary_payload
        ):
            raise EvidenceInvalidError(
                "human review Result or Decision Pair changed during verification"
            )
        try:
            final_identity = runtime.validate_run_directory_descriptor(
                run_dir,
                run_descriptor,
            )
        except (OSError, PipelineError, ValueError) as exc:
            raise EvidenceInvalidError(
                "human review Run Directory changed during verification"
            ) from exc
        if final_identity != run_identity:
            raise EvidenceInvalidError(
                "human review Run Directory changed during verification"
            )
        return {
            "status": "VALID",
            "decision": record["decision"],
            "reviewer": record["reviewer"],
            "binding_sha256": record["binding_sha256"],
            "decision_record_sha256": hashlib.sha256(terminal_payload).hexdigest(),
        }
    finally:
        runtime.close_descriptor_quietly(run_descriptor)

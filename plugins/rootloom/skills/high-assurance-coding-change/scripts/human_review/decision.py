"""Human Review Decision Pair production, parsing, and transaction ownership."""

from __future__ import annotations

from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata
from typing import Any

from runner.errors import EvidenceInvalidError, PipelineError

from .binding import recompute_human_review_binding
from .constants import (
    MAX_HUMAN_REVIEW_DECISION_BYTES,
    MAX_HUMAN_REVIEW_IDENTITY_BYTES,
)
from .pinned_io import read_decision_pair_payloads
from .schema import normalize_review_scope, validate_review_result


def validate_identity_text(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise EvidenceInvalidError(f"{label} identity must be text")
    normalized = value.strip()
    if not normalized:
        raise EvidenceInvalidError(f"{label} identity must not be empty")
    if normalized != value:
        raise EvidenceInvalidError(f"{label} identity must be canonical")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise EvidenceInvalidError(f"{label} identity contains a control character")
    try:
        observed_bytes = len(normalized.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise EvidenceInvalidError(f"{label} identity is not valid UTF-8") from exc
    if observed_bytes > MAX_HUMAN_REVIEW_IDENTITY_BYTES:
        raise EvidenceInvalidError(
            f"{label} identity byte budget exceeded "
            f"({observed_bytes} > {MAX_HUMAN_REVIEW_IDENTITY_BYTES})"
        )
    return normalized


def validate_decision_payload_budget(payload: bytes, label: str) -> None:
    if len(payload) > MAX_HUMAN_REVIEW_DECISION_BYTES:
        raise EvidenceInvalidError(
            f"human review {label} byte budget exceeded "
            f"({len(payload)} > {MAX_HUMAN_REVIEW_DECISION_BYTES})"
        )


def canonical_decision_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds")


def decision_summary(
    record: dict[str, object],
    terminal_payload: bytes,
) -> dict[str, object]:
    return {
        **record,
        "accepted": record["decision"] == "accept",
        "decision_record_sha256": hashlib.sha256(terminal_payload).hexdigest(),
    }


def decision_summary_payload(summary: dict[str, object]) -> bytes:
    return (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def binding_sha256(binding: dict[str, Any]) -> str:
    payload = json.dumps(
        binding,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def read_decision_pair(
    runtime: Any,
    run_dir: Path,
    directory_descriptor: int,
) -> tuple[dict[str, object], bytes, bytes]:
    terminal_payload, summary_payload = read_decision_pair_payloads(
        runtime,
        run_dir,
        directory_descriptor,
    )
    try:
        record = json.loads(terminal_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceInvalidError(
            "human review Terminal is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(record, dict) or runtime.encode_ndjson_value(record) != terminal_payload:
        raise EvidenceInvalidError(
            "human review Terminal is not one canonical NDJSON record"
        )
    required_fields = {
        "format",
        "decision",
        "reviewer",
        "local_account",
        "local_uid",
        "decided_at",
        "binding_sha256",
    }
    if set(record) != required_fields:
        raise EvidenceInvalidError("human review Terminal fields are invalid")
    if record.get("format") != "rootloom-human-review-decision-v4":
        raise EvidenceInvalidError("human review Terminal format is invalid")
    if record.get("decision") not in {"accept", "reject"}:
        raise EvidenceInvalidError("human review Terminal decision is invalid")
    reviewer = record.get("reviewer")
    local_account = record.get("local_account")
    if not isinstance(reviewer, str):
        raise EvidenceInvalidError("human review Terminal reviewer is invalid")
    if not isinstance(local_account, str):
        raise EvidenceInvalidError("human review Terminal local account is invalid")
    if validate_identity_text(reviewer, "reviewer") != reviewer:
        raise EvidenceInvalidError("human review Terminal reviewer is not canonical")
    if validate_identity_text(local_account, "local_account") != local_account:
        raise EvidenceInvalidError("human review Terminal local account is not canonical")
    local_uid = record.get("local_uid")
    if local_uid is not None and (
        isinstance(local_uid, bool) or not isinstance(local_uid, int) or local_uid < 0
    ):
        raise EvidenceInvalidError("human review Terminal local uid is invalid")
    decided_at = record.get("decided_at")
    if not isinstance(decided_at, str):
        raise EvidenceInvalidError("human review Terminal decision time is invalid")
    try:
        parsed_time = datetime.fromisoformat(decided_at)
    except ValueError as exc:
        raise EvidenceInvalidError(
            "human review Terminal decision time is invalid"
        ) from exc
    if parsed_time.tzinfo is None or canonical_decision_time(parsed_time) != decided_at:
        raise EvidenceInvalidError(
            "human review Terminal decision time is not canonical UTC"
        )
    record_binding_sha256 = record.get("binding_sha256")
    if not isinstance(record_binding_sha256, str) or re.fullmatch(
        r"[0-9a-f]{64}",
        record_binding_sha256,
    ) is None:
        raise EvidenceInvalidError("human review Terminal binding hash is invalid")
    expected_summary = decision_summary(record, terminal_payload)
    if decision_summary_payload(expected_summary) != summary_payload:
        raise EvidenceInvalidError(
            "human review Summary does not match the canonical Terminal record"
        )
    return record, terminal_payload, summary_payload


def decide(
    runtime: Any,
    repo: Path,
    run_dir: Path,
    reviewer: str,
    decision: str,
) -> dict[str, object]:
    repo, run_dir = normalize_review_scope(repo, run_dir)
    if decision not in {"accept", "reject"}:
        raise EvidenceInvalidError("human review decision is invalid")
    reviewer_identity = validate_identity_text(reviewer, "reviewer")
    local_account = validate_identity_text(getpass.getuser(), "local_account")

    with runtime.repository_lock(repo):
        result = runtime.read_human_review_result(run_dir)
        expected, protected_deletions = validate_review_result(
            runtime, repo, run_dir, result
        )
        initial_result_sha256 = runtime.human_review_full_result_sha256(result)
        current = recompute_human_review_binding(
            runtime,
            repo,
            run_dir,
            result,
            expected,
            protected_deletions,
        )
        if expected != current:
            raise PipelineError("human review binding drifted; decision refused", 9)
        decisions = run_dir / "human-review.ndjson"
        summary_path = run_dir / "human-review-summary.json"
        record = {
            "format": "rootloom-human-review-decision-v4",
            "decision": decision,
            "reviewer": reviewer_identity,
            "local_account": local_account,
            "local_uid": os.getuid() if hasattr(os, "getuid") else None,
            "decided_at": canonical_decision_time(datetime.now(timezone.utc)),
            "binding_sha256": binding_sha256(expected),
        }
        payload = runtime.encode_ndjson_value(record)
        validate_decision_payload_budget(payload, "Terminal")
        terminal_sha256 = hashlib.sha256(payload).hexdigest()
        summary = decision_summary(record, payload)
        summary_payload = decision_summary_payload(summary)
        validate_decision_payload_budget(summary_payload, "Summary")
        summary_sha256 = hashlib.sha256(summary_payload).hexdigest()

        def validate_unchanged_result(
            value: dict[str, Any],
            *,
            phase: str,
        ) -> tuple[dict[str, Any], list[str]]:
            observed_expected, observed_deletions = validate_review_result(
                runtime,
                repo,
                run_dir,
                value,
            )
            if (
                runtime.human_review_full_result_sha256(value)
                != initial_result_sha256
                or observed_expected != expected
                or observed_deletions != protected_deletions
            ):
                raise PipelineError(
                    f"human review Result changed {phase}",
                    9,
                )
            return observed_expected, observed_deletions

        def recompute_binding(value: dict[str, Any], *, phase: str) -> None:
            observed_expected, observed_deletions = validate_unchanged_result(
                value,
                phase=phase,
            )
            observed = recompute_human_review_binding(
                runtime,
                repo,
                run_dir,
                value,
                observed_expected,
                observed_deletions,
            )
            if observed != current:
                raise PipelineError(
                    f"repository state drifted {phase}",
                    9,
                )

        run_descriptor, _ = runtime._safe_run_directory_descriptor(run_dir)
        try:
            with runtime.pinned_empty_private_artifact(
                decisions,
                directory_descriptor=run_descriptor,
            ) as terminal, runtime.pinned_empty_private_artifact(
                summary_path,
                directory_descriptor=run_descriptor,
                nonempty_error="human review summary already exists",
            ) as pinned_summary:
                terminal_size = 0
                summary_size = 0
                try:
                    terminal_size = runtime.append_pinned_private_artifact(
                        terminal,
                        payload,
                        expected_starting_size=0,
                    )
                    post_terminal_result = runtime.read_human_review_result(run_dir)
                    recompute_binding(
                        post_terminal_result,
                        phase="while the terminal decision was written",
                    )
                    validate_unchanged_result(
                        runtime.read_human_review_result(run_dir),
                        phase="during post-terminal validation",
                    )
                    runtime.validate_pinned_private_artifact(
                        terminal,
                        expected_size=terminal_size,
                    )

                    summary_size = runtime.append_pinned_private_artifact(
                        pinned_summary,
                        summary_payload,
                        expected_starting_size=0,
                    )

                    final_result = runtime.read_human_review_result(run_dir)
                    recompute_binding(
                        final_result,
                        phase="during final decision validation",
                    )
                    validate_unchanged_result(
                        runtime.read_human_review_result(run_dir),
                        phase="during final Result validation",
                    )
                    runtime.validate_run_directory_descriptor(
                        run_dir,
                        run_descriptor,
                    )
                    runtime.validate_pinned_private_artifact(
                        terminal,
                        expected_size=terminal_size,
                        expected_sha256=terminal_sha256,
                    )
                    runtime.validate_pinned_private_artifact(
                        pinned_summary,
                        expected_size=summary_size,
                        expected_sha256=summary_sha256,
                    )
                    return summary
                except BaseException as exc:
                    compensation_errors: list[str] = []
                    for pinned, expected_size in (
                        (pinned_summary, summary_size),
                        (terminal, terminal_size),
                    ):
                        if expected_size == 0:
                            continue
                        try:
                            runtime.truncate_pinned_private_artifact(
                                pinned,
                                expected_size=expected_size,
                            )
                        except BaseException as compensation_exc:
                            compensation_errors.append(str(compensation_exc))
                    if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                        raise
                    detail = (
                        "; compensation detail: " + "; ".join(compensation_errors)
                        if compensation_errors
                        else ""
                    )
                    raise PipelineError(
                        "human review decision commit failed; decision was compensated "
                        f"through pinned Terminal and Summary: {exc}{detail}",
                        9,
                    ) from exc
        finally:
            runtime.close_descriptor_quietly(run_descriptor)

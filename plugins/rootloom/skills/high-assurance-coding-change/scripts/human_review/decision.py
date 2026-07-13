"""Human Review Decision Pair production, parsing, and transaction ownership."""

from __future__ import annotations

from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

import run_pipeline as runner

from .binding import recompute_human_review_binding
from .constants import (
    MAX_HUMAN_REVIEW_DECISION_BYTES,
    MAX_HUMAN_REVIEW_IDENTITY_BYTES,
)
from .pinned_io import read_decision_pair_payloads
from .schema import normalize_review_scope, validate_review_result


def validate_identity_text(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise runner.PipelineError(f"{label} identity must be text", 9)
    normalized = value.strip()
    if not normalized:
        raise runner.PipelineError(f"{label} identity must not be empty", 9)
    try:
        observed_bytes = len(normalized.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise runner.PipelineError(f"{label} identity is not valid UTF-8", 9) from exc
    if observed_bytes > MAX_HUMAN_REVIEW_IDENTITY_BYTES:
        raise runner.PipelineError(
            f"{label} identity byte budget exceeded "
            f"({observed_bytes} > {MAX_HUMAN_REVIEW_IDENTITY_BYTES})",
            9,
        )
    return normalized


def validate_decision_payload_budget(payload: bytes, label: str) -> None:
    if len(payload) > MAX_HUMAN_REVIEW_DECISION_BYTES:
        raise runner.PipelineError(
            f"human review {label} byte budget exceeded "
            f"({len(payload)} > {MAX_HUMAN_REVIEW_DECISION_BYTES})",
            9,
        )


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
    run_dir: Path,
    directory_descriptor: int,
) -> tuple[dict[str, object], bytes, bytes]:
    terminal_payload, summary_payload = read_decision_pair_payloads(
        run_dir,
        directory_descriptor,
    )
    try:
        record = json.loads(terminal_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise runner.PipelineError(
            "human review Terminal is not valid UTF-8 JSON",
            9,
        ) from exc
    if not isinstance(record, dict) or runner.encode_ndjson_value(record) != terminal_payload:
        raise runner.PipelineError(
            "human review Terminal is not one canonical NDJSON record",
            9,
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
        raise runner.PipelineError("human review Terminal fields are invalid", 9)
    if record.get("format") != "rootloom-human-review-decision-v4":
        raise runner.PipelineError("human review Terminal format is invalid", 9)
    if record.get("decision") not in {"accept", "reject"}:
        raise runner.PipelineError("human review Terminal decision is invalid", 9)
    reviewer = record.get("reviewer")
    local_account = record.get("local_account")
    if not isinstance(reviewer, str):
        raise runner.PipelineError("human review Terminal reviewer is invalid", 9)
    if not isinstance(local_account, str):
        raise runner.PipelineError("human review Terminal local account is invalid", 9)
    validate_identity_text(reviewer, "reviewer")
    validate_identity_text(local_account, "local_account")
    local_uid = record.get("local_uid")
    if local_uid is not None and (
        isinstance(local_uid, bool) or not isinstance(local_uid, int)
    ):
        raise runner.PipelineError("human review Terminal local uid is invalid", 9)
    decided_at = record.get("decided_at")
    if not isinstance(decided_at, str):
        raise runner.PipelineError("human review Terminal decision time is invalid", 9)
    try:
        parsed_time = datetime.fromisoformat(decided_at)
    except ValueError as exc:
        raise runner.PipelineError(
            "human review Terminal decision time is invalid",
            9,
        ) from exc
    if parsed_time.tzinfo is None:
        raise runner.PipelineError("human review Terminal decision time lacks timezone", 9)
    record_binding_sha256 = record.get("binding_sha256")
    if not isinstance(record_binding_sha256, str) or re.fullmatch(
        r"[0-9a-f]{64}",
        record_binding_sha256,
    ) is None:
        raise runner.PipelineError("human review Terminal binding hash is invalid", 9)
    expected_summary = decision_summary(record, terminal_payload)
    if decision_summary_payload(expected_summary) != summary_payload:
        raise runner.PipelineError(
            "human review Summary does not match the canonical Terminal record",
            9,
        )
    return record, terminal_payload, summary_payload


def decide(repo: Path, run_dir: Path, reviewer: str, decision: str) -> dict[str, object]:
    repo, run_dir = normalize_review_scope(repo, run_dir)
    if decision not in {"accept", "reject"}:
        raise runner.PipelineError("human review decision is invalid", 9)
    reviewer_identity = validate_identity_text(reviewer, "reviewer")
    local_account = validate_identity_text(getpass.getuser(), "local_account")

    with runner.repository_lock(repo):
        result = runner.read_human_review_result(run_dir)
        expected, protected_deletions = validate_review_result(repo, run_dir, result)
        initial_result_sha256 = runner.human_review_full_result_sha256(result)
        current = recompute_human_review_binding(
            repo,
            run_dir,
            result,
            expected,
            protected_deletions,
        )
        if expected != current:
            raise runner.PipelineError("human review binding drifted; decision refused", 9)
        decisions = run_dir / "human-review.ndjson"
        summary_path = run_dir / "human-review-summary.json"
        record = {
            "format": "rootloom-human-review-decision-v4",
            "decision": decision,
            "reviewer": reviewer_identity,
            "local_account": local_account,
            "local_uid": os.getuid() if hasattr(os, "getuid") else None,
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "binding_sha256": binding_sha256(expected),
        }
        payload = runner.encode_ndjson_value(record)
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
                repo,
                run_dir,
                value,
            )
            if (
                runner.human_review_full_result_sha256(value)
                != initial_result_sha256
                or observed_expected != expected
                or observed_deletions != protected_deletions
            ):
                raise runner.PipelineError(
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
                repo,
                run_dir,
                value,
                observed_expected,
                observed_deletions,
            )
            if observed != current:
                raise runner.PipelineError(
                    f"repository state drifted {phase}",
                    9,
                )

        run_descriptor, _ = runner._safe_run_directory_descriptor(run_dir)
        try:
            with runner.pinned_empty_private_artifact(
                decisions,
                directory_descriptor=run_descriptor,
            ) as terminal, runner.pinned_empty_private_artifact(
                summary_path,
                directory_descriptor=run_descriptor,
                nonempty_error="human review summary already exists",
            ) as pinned_summary:
                terminal_size = 0
                summary_size = 0
                try:
                    terminal_size = runner.append_pinned_private_artifact(
                        terminal,
                        payload,
                        expected_starting_size=0,
                    )
                    post_terminal_result = runner.read_human_review_result(run_dir)
                    recompute_binding(
                        post_terminal_result,
                        phase="while the terminal decision was written",
                    )
                    validate_unchanged_result(
                        runner.read_human_review_result(run_dir),
                        phase="during post-terminal validation",
                    )
                    runner.validate_pinned_private_artifact(
                        terminal,
                        expected_size=terminal_size,
                    )

                    summary_size = runner.append_pinned_private_artifact(
                        pinned_summary,
                        summary_payload,
                        expected_starting_size=0,
                    )

                    final_result = runner.read_human_review_result(run_dir)
                    recompute_binding(
                        final_result,
                        phase="during final decision validation",
                    )
                    validate_unchanged_result(
                        runner.read_human_review_result(run_dir),
                        phase="during final Result validation",
                    )
                    runner.validate_run_directory_descriptor(
                        run_dir,
                        run_descriptor,
                    )
                    runner.validate_pinned_private_artifact(
                        terminal,
                        expected_size=terminal_size,
                        expected_sha256=terminal_sha256,
                    )
                    runner.validate_pinned_private_artifact(
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
                            runner.truncate_pinned_private_artifact(
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
                    raise runner.PipelineError(
                        "human review decision commit failed; decision was compensated "
                        f"through pinned Terminal and Summary: {exc}{detail}",
                        9,
                    ) from exc
        finally:
            runner.close_descriptor_quietly(run_descriptor)

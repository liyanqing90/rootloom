#!/usr/bin/env python3
"""Decide or read-only verify one Rootloom HUMAN_REVIEW_REQUIRED result."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import sys

import run_pipeline as runner


VERIFY_STALE_EXIT = 12


class StaleDecisionPair(runner.PipelineError):
    """A structurally valid Decision Pair no longer matches current reviewed state."""

    def __init__(self, message: str) -> None:
        super().__init__(message, VERIFY_STALE_EXIT)


def normalize_review_scope(repo: Path, run_dir: Path) -> tuple[Path, Path]:
    repo = repo.expanduser().resolve()
    supplied_run_dir = run_dir.expanduser()
    if supplied_run_dir.is_symlink() or not supplied_run_dir.is_dir():
        raise runner.PipelineError("review run directory is missing or symlinked", 9)
    return repo, supplied_run_dir.resolve()


def validate_review_result(
    run_dir: Path,
    value: dict[str, object],
) -> tuple[dict[str, object], list[str]]:
    if value.get("result") != "HUMAN_REVIEW_REQUIRED":
        raise runner.PipelineError("run is not awaiting human review", 9)
    declared_run_dir = value.get("run_dir")
    if not isinstance(declared_run_dir, str) or not Path(declared_run_dir).is_absolute():
        raise runner.PipelineError("Result run_dir is missing or invalid", 9)
    if Path(declared_run_dir).expanduser().resolve() != run_dir:
        raise runner.PipelineError(
            "Result run_dir does not match the supplied review directory",
            9,
        )
    expected_value = value.get("human_review_binding")
    if not isinstance(expected_value, dict):
        raise runner.PipelineError("human review binding is missing or invalid", 9)
    if expected_value.get("format") != "rootloom-human-review-binding-v4":
        raise runner.PipelineError(
            "unsupported human review binding version; rerun with Human Review v4",
            9,
        )
    state_policy = expected_value.get("state_policy")
    metadata_floor = expected_value.get("final_metadata_only_floor_paths")
    repository_state = expected_value.get("repository_state")
    run_identity = expected_value.get("run_directory")
    if not isinstance(state_policy, dict):
        raise runner.PipelineError("human review state policy is missing or invalid", 9)
    normalized_policy, _ = runner.normalize_human_review_state_policy(state_policy)
    if not isinstance(metadata_floor, list) or not all(
        isinstance(path, str) for path in metadata_floor
    ):
        raise runner.PipelineError(
            "human review metadata-only floor is missing or invalid",
            9,
        )
    runner.normalize_human_review_metadata_floor(
        metadata_floor,
        max_paths=normalized_policy["max_state_paths"],
        max_path_bytes=normalized_policy["max_state_bytes"],
    )
    if not isinstance(repository_state, dict):
        raise runner.PipelineError(
            "human review repository commitment is missing or invalid",
            9,
        )
    if not isinstance(run_identity, dict):
        raise runner.PipelineError(
            "human review Run Directory commitment is missing or invalid",
            9,
        )
    protected = value.get("protected_deletions")
    if not isinstance(protected, list) or not all(
        isinstance(path, str) for path in protected
    ):
        raise runner.PipelineError("protected_deletions is missing or invalid", 9)
    return expected_value, protected


def parse_args(argv: list[str]) -> argparse.Namespace:
    verify = bool(argv and argv[0] == "verify")
    parser = argparse.ArgumentParser(
        description=(
            "Verify one committed Rootloom Human Review Decision Pair without writes."
            if verify
            else __doc__
        )
    )
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    if verify:
        parsed = parser.parse_args(argv[1:])
        parsed.command = "verify"
        return parsed
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--decision", required=True, choices=("accept", "reject"))
    parsed = parser.parse_args(argv)
    parsed.command = "decide"
    return parsed


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


def read_decision_pair(
    run_dir: Path,
    directory_descriptor: int,
) -> tuple[dict[str, object], bytes, bytes]:
    terminal_payload = runner.read_pinned_private_artifact(
        run_dir / "human-review.ndjson",
        max_bytes=runner.MAX_HUMAN_REVIEW_DECISION_BYTES,
        directory_descriptor=directory_descriptor,
    )
    summary_payload = runner.read_pinned_private_artifact(
        run_dir / "human-review-summary.json",
        max_bytes=runner.MAX_HUMAN_REVIEW_DECISION_BYTES,
        directory_descriptor=directory_descriptor,
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
    if not isinstance(record.get("reviewer"), str) or not record["reviewer"].strip():
        raise runner.PipelineError("human review Terminal reviewer is invalid", 9)
    if (
        not isinstance(record.get("local_account"), str)
        or not record["local_account"].strip()
    ):
        raise runner.PipelineError("human review Terminal local account is invalid", 9)
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
    binding_sha256 = record.get("binding_sha256")
    if not isinstance(binding_sha256, str) or re.fullmatch(
        r"[0-9a-f]{64}",
        binding_sha256,
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
    if not reviewer.strip():
        raise runner.PipelineError("reviewer identity must not be empty", 9)

    with runner.repository_lock(repo):
        result = runner.read_human_review_result(run_dir)
        expected, protected_deletions = validate_review_result(run_dir, result)
        initial_result_sha256 = runner.human_review_full_result_sha256(result)
        current = runner.compute_human_review_binding(
            repo,
            run_dir,
            runner.human_review_result_core_sha256(result),
            protected_deletions,
            state_policy=expected.get("state_policy"),
            metadata_only_floor=expected.get("final_metadata_only_floor_paths"),
            expected_repository_state_commitment=expected.get("repository_state"),
        )
        if expected != current:
            raise runner.PipelineError("human review binding drifted; decision refused", 9)
        decisions = run_dir / "human-review.ndjson"
        summary_path = run_dir / "human-review-summary.json"
        binding_payload = json.dumps(
            expected,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        record = {
            "format": "rootloom-human-review-decision-v4",
            "decision": decision,
            "reviewer": reviewer.strip(),
            "local_account": getpass.getuser(),
            "local_uid": os.getuid() if hasattr(os, "getuid") else None,
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "binding_sha256": hashlib.sha256(binding_payload).hexdigest(),
        }
        payload = runner.encode_ndjson_value(record)
        terminal_sha256 = hashlib.sha256(payload).hexdigest()
        summary = decision_summary(record, payload)
        summary_payload = decision_summary_payload(summary)
        summary_sha256 = hashlib.sha256(summary_payload).hexdigest()

        def validate_unchanged_result(
            value: dict[str, object],
            *,
            phase: str,
        ) -> tuple[dict[str, object], list[str]]:
            observed_expected, observed_deletions = validate_review_result(
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

        def recompute_binding(value: dict[str, object], *, phase: str) -> None:
            observed_expected, observed_deletions = validate_unchanged_result(
                value,
                phase=phase,
            )
            observed = runner.compute_human_review_binding(
                repo,
                run_dir,
                runner.human_review_result_core_sha256(value),
                observed_deletions,
                state_policy=observed_expected.get("state_policy"),
                metadata_only_floor=observed_expected.get(
                    "final_metadata_only_floor_paths"
                ),
                expected_repository_state_commitment=observed_expected.get(
                    "repository_state"
                ),
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


def verify_decision_pair(repo: Path, run_dir: Path) -> dict[str, object]:
    """Verify one Decision Pair without acquiring a writer lock or changing files."""

    repo, run_dir = normalize_review_scope(repo, run_dir)
    run_descriptor, run_identity = runner._safe_run_directory_descriptor(run_dir)
    try:
        result = runner.read_human_review_result(run_dir)
        expected, protected_deletions = validate_review_result(run_dir, result)
        initial_result_sha256 = runner.human_review_full_result_sha256(result)
        record, terminal_payload, summary_payload = read_decision_pair(
            run_dir,
            run_descriptor,
        )
        binding_payload = json.dumps(
            expected,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        if record["binding_sha256"] != hashlib.sha256(binding_payload).hexdigest():
            raise runner.PipelineError(
                "human review Terminal binding does not match Result",
                9,
            )
        try:
            current = runner.compute_human_review_binding(
                repo,
                run_dir,
                runner.human_review_result_core_sha256(result),
                protected_deletions,
                state_policy=expected.get("state_policy"),
                metadata_only_floor=expected.get("final_metadata_only_floor_paths"),
                expected_repository_state_commitment=expected.get("repository_state"),
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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.command == "verify":
        try:
            verify_decision_pair(args.repo, args.run_dir)
        except StaleDecisionPair:
            print("STALE")
            return VERIFY_STALE_EXIT
        except (OSError, ValueError, runner.PipelineError, json.JSONDecodeError) as exc:
            print("INVALID")
            return getattr(exc, "exit_code", 9)
        print("VALID")
        return 0
    try:
        summary = decide(args.repo, args.run_dir, args.reviewer, args.decision)
    except (OSError, ValueError, runner.PipelineError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return getattr(exc, "exit_code", 2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["accepted"] else 11


if __name__ == "__main__":
    raise SystemExit(main())

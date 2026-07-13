#!/usr/bin/env python3
"""Decide or read-only verify one Rootloom HUMAN_REVIEW_REQUIRED result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import run_pipeline as runner
from human_review import decision as decision_module
from human_review import schema as schema_module
from human_review import verify as verify_module
from runner.contracts import (
    DEFAULT_VERIFY_MAX_ARTIFACT_BYTES,
    DEFAULT_VERIFY_MAX_IGNORED_PATHS,
    DEFAULT_VERIFY_MAX_STATE_BYTES,
    DEFAULT_VERIFY_MAX_STATE_PATHS,
    DEFAULT_VERIFY_MAX_TOTAL_BYTES,
    DEFAULT_VERIFY_TIMEOUT_SECONDS,
    MAX_HUMAN_REVIEW_DIAGNOSTIC_BYTES,
    MAX_HUMAN_REVIEW_IDENTITY_BYTES,
    VerificationLimits,
    VERIFY_INVALID_EXIT,
    VERIFY_STALE_EXIT,
    VERIFY_UNVERIFIED_EXIT,
)
from runner.errors import (
    BindingDriftError,
    EvidenceInvalidError,
    VerificationError,
)


decision_summary = decision_module.decision_summary
decision_summary_payload = decision_module.decision_summary_payload
validate_decision_payload_budget = decision_module.validate_decision_payload_budget
normalize_review_scope = schema_module.normalize_review_scope
StaleDecisionPair = BindingDriftError


def decide(repo: Path, run_dir: Path, reviewer: str, decision: str) -> dict[str, object]:
    return decision_module.decide(runner, repo, run_dir, reviewer, decision)


def read_decision_pair(
    run_dir: Path,
    directory_descriptor: int,
) -> tuple[dict[str, object], bytes, bytes]:
    return decision_module.read_decision_pair(runner, run_dir, directory_descriptor)


def validate_human_review_binding_v4_schema(
    binding: object,
    *,
    repo: Path,
    run_dir: Path,
    protected_deletions: list[str],
) -> dict[str, object]:
    return schema_module.validate_human_review_binding_v4_schema(
        runner,
        binding,
        repo=repo,
        run_dir=run_dir,
        protected_deletions=protected_deletions,
    )


def validate_review_result(
    repo: Path,
    run_dir: Path,
    value: dict[str, object],
) -> tuple[dict[str, object], list[str]]:
    return schema_module.validate_review_result(runner, repo, run_dir, value)


def verify_decision_pair(
    repo: Path,
    run_dir: Path,
    limits: VerificationLimits | None = None,
) -> dict[str, object]:
    return verify_module.verify_decision_pair(runner, repo, run_dir, limits)


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
        parser.add_argument(
            "--max-artifact-bytes",
            type=int,
            default=DEFAULT_VERIFY_MAX_ARTIFACT_BYTES,
        )
        parser.add_argument(
            "--max-total-bytes",
            type=int,
            default=DEFAULT_VERIFY_MAX_TOTAL_BYTES,
        )
        parser.add_argument(
            "--max-state-paths",
            type=int,
            default=DEFAULT_VERIFY_MAX_STATE_PATHS,
        )
        parser.add_argument(
            "--max-state-bytes",
            type=int,
            default=DEFAULT_VERIFY_MAX_STATE_BYTES,
        )
        parser.add_argument(
            "--max-ignored-paths",
            type=int,
            default=DEFAULT_VERIFY_MAX_IGNORED_PATHS,
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=DEFAULT_VERIFY_TIMEOUT_SECONDS,
        )
        parsed = parser.parse_args(argv[1:])
        parsed.command = "verify"
        return parsed
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--decision", required=True, choices=("accept", "reject"))
    parsed = parser.parse_args(argv)
    parsed.command = "decide"
    return parsed


def bounded_diagnostic(exc: BaseException) -> str:
    message = " ".join(str(exc).splitlines()).strip()
    if not message:
        message = "human review verification failed"
    payload = message.encode("utf-8", errors="replace")
    if len(payload) <= MAX_HUMAN_REVIEW_DIAGNOSTIC_BYTES:
        return message
    return payload[:MAX_HUMAN_REVIEW_DIAGNOSTIC_BYTES].decode(
        "utf-8",
        errors="ignore",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.command == "verify":
        limits = VerificationLimits(
            max_ignored_paths=args.max_ignored_paths,
            max_state_paths=args.max_state_paths,
            max_state_bytes=args.max_state_bytes,
            max_artifact_bytes=args.max_artifact_bytes,
            max_total_bytes=args.max_total_bytes,
            timeout_seconds=args.timeout,
        )
        try:
            verify_decision_pair(args.repo, args.run_dir, limits)
        except BindingDriftError as exc:
            print("STALE")
            print(bounded_diagnostic(exc), file=sys.stderr)
            return VERIFY_STALE_EXIT
        except VerificationError as exc:
            print("UNVERIFIED")
            print(bounded_diagnostic(exc), file=sys.stderr)
            return VERIFY_UNVERIFIED_EXIT
        except (
            EvidenceInvalidError,
            OSError,
            ValueError,
            runner.PipelineError,
            json.JSONDecodeError,
        ) as exc:
            print("INVALID")
            print(bounded_diagnostic(exc), file=sys.stderr)
            return VERIFY_INVALID_EXIT
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

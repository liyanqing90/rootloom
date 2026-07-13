#!/usr/bin/env python3
"""Decide or read-only verify one Rootloom HUMAN_REVIEW_REQUIRED result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import run_pipeline as runner
from human_review import decision as decision_module
from human_review.constants import (
    MAX_HUMAN_REVIEW_DIAGNOSTIC_BYTES,
    MAX_HUMAN_REVIEW_IDENTITY_BYTES,
    VERIFY_INVALID_EXIT,
    VERIFY_STALE_EXIT,
)
from human_review.decision import (
    decide,
    decision_summary,
    decision_summary_payload,
    read_decision_pair,
    validate_decision_payload_budget,
)
from human_review.schema import (
    normalize_review_scope,
    validate_human_review_binding_v4_schema,
    validate_review_result,
)
from human_review.verify import StaleDecisionPair, verify_decision_pair


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
        try:
            verify_decision_pair(args.repo, args.run_dir)
        except StaleDecisionPair as exc:
            print("STALE")
            print(bounded_diagnostic(exc), file=sys.stderr)
            return VERIFY_STALE_EXIT
        except (OSError, ValueError, runner.PipelineError, json.JSONDecodeError) as exc:
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

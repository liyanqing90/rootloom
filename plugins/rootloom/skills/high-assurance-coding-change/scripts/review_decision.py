#!/usr/bin/env python3
"""Accept or reject one Rootloom HUMAN_REVIEW_REQUIRED result without drift."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys

import run_pipeline as runner


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--decision", required=True, choices=("accept", "reject"))
    return parser.parse_args(argv)


def decide(repo: Path, run_dir: Path, reviewer: str, decision: str) -> dict[str, object]:
    repo = repo.expanduser().resolve()
    supplied_run_dir = run_dir.expanduser()
    if not reviewer.strip():
        raise runner.PipelineError("reviewer identity must not be empty", 9)
    if supplied_run_dir.is_symlink() or not supplied_run_dir.is_dir():
        raise runner.PipelineError("review run directory is missing or symlinked", 9)
    run_dir = supplied_run_dir.resolve()
    with runner.repository_lock(repo):
        result_path = run_dir / "result.json"
        result = runner.read_json(result_path, 4 * 1024 * 1024)
        if result.get("result") != "HUMAN_REVIEW_REQUIRED":
            raise runner.PipelineError("run is not awaiting human review", 9)
        expected = result.get("human_review_binding")
        if not isinstance(expected, dict):
            raise runner.PipelineError("human review binding is missing or invalid", 9)
        protected_deletions = result.get("protected_deletions")
        if not isinstance(protected_deletions, list) or not all(
            isinstance(path, str) for path in protected_deletions
        ):
            raise runner.PipelineError("protected_deletions is missing or invalid", 9)
        current = runner.compute_human_review_binding(
            repo,
            run_dir,
            runner.human_review_result_core_sha256(result),
            protected_deletions,
            state_policy=expected.get("state_policy"),
        )
        if expected != current:
            raise runner.PipelineError("human review binding drifted; decision refused", 9)
        decisions = run_dir / "human-review.ndjson"
        summary_path = run_dir / "human-review-summary.json"
        if decisions.exists() and not decisions.is_symlink() and decisions.stat().st_size:
            raise runner.PipelineError("human review already has a terminal decision", 9)
        if summary_path.exists() or summary_path.is_symlink():
            raise runner.PipelineError("human review summary already exists", 9)
        runner.ensure_empty_private_file(decisions)
        binding_payload = json.dumps(
            expected,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        record = {
            "format": "rootloom-human-review-decision-v3",
            "decision": decision,
            "reviewer": reviewer.strip(),
            "local_account": getpass.getuser(),
            "local_uid": os.getuid() if hasattr(os, "getuid") else None,
            "decided_at": datetime.now(timezone.utc).isoformat(),
            "binding_sha256": hashlib.sha256(binding_payload).hexdigest(),
        }
        payload = runner.encode_ndjson_value(record)
        runner.append_complete_artifact(decisions, payload, expected_starting_size=0)
        try:
            post_write = runner.compute_human_review_binding(
                repo,
                run_dir,
                runner.human_review_result_core_sha256(result),
                protected_deletions,
                state_policy=expected.get("state_policy"),
            )
        except BaseException as exc:
            runner.truncate_private_artifact(decisions, len(payload))
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise runner.PipelineError(
                "post-write human review validation failed; decision was compensated: "
                f"{exc}",
                9,
            ) from exc
        if post_write != current:
            runner.truncate_private_artifact(decisions, len(payload))
            raise runner.PipelineError(
                "repository state drifted while the human review decision was written; "
                "decision was compensated",
                9,
            )
        summary = {
            **record,
            "accepted": decision == "accept",
            "decision_record_sha256": hashlib.sha256(payload).hexdigest(),
        }
        runner.atomic_write_json(summary_path, summary)
        return summary


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv or sys.argv[1:])
        summary = decide(args.repo, args.run_dir, args.reviewer, args.decision)
    except (OSError, ValueError, runner.PipelineError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return getattr(exc, "exit_code", 2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["accepted"] else 11


if __name__ == "__main__":
    raise SystemExit(main())

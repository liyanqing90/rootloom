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

    def validate_result(value: dict[str, object]) -> tuple[dict[str, object], list[str]]:
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
        if not isinstance(state_policy, dict):
            raise runner.PipelineError("human review state policy is missing or invalid", 9)
        if not isinstance(metadata_floor, list) or not all(
            isinstance(path, str) for path in metadata_floor
        ):
            raise runner.PipelineError(
                "human review metadata-only floor is missing or invalid",
                9,
            )
        protected = value.get("protected_deletions")
        if not isinstance(protected, list) or not all(
            isinstance(path, str) for path in protected
        ):
            raise runner.PipelineError("protected_deletions is missing or invalid", 9)
        return expected_value, protected

    with runner.repository_lock(repo):
        result = runner.read_human_review_result(run_dir)
        expected, protected_deletions = validate_result(result)
        initial_result_sha256 = runner.human_review_full_result_sha256(result)
        current = runner.compute_human_review_binding(
            repo,
            run_dir,
            runner.human_review_result_core_sha256(result),
            protected_deletions,
            state_policy=expected.get("state_policy"),
            metadata_only_floor=expected.get("final_metadata_only_floor_paths"),
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
            "format": "rootloom-human-review-decision-v4",
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
            post_write_result = runner.read_human_review_result(run_dir)
            post_write_expected, post_write_deletions = validate_result(post_write_result)
            if (
                runner.human_review_full_result_sha256(post_write_result)
                != initial_result_sha256
                or post_write_expected != expected
                or post_write_deletions != protected_deletions
            ):
                raise runner.PipelineError(
                    "human review Result changed while the decision was written",
                    9,
                )
            post_write = runner.compute_human_review_binding(
                repo,
                run_dir,
                runner.human_review_result_core_sha256(post_write_result),
                post_write_deletions,
                state_policy=post_write_expected.get("state_policy"),
                metadata_only_floor=post_write_expected.get(
                    "final_metadata_only_floor_paths"
                ),
            )
            final_result = runner.read_human_review_result(run_dir)
            if runner.human_review_full_result_sha256(final_result) != initial_result_sha256:
                raise runner.PipelineError(
                    "human review Result changed during post-write validation",
                    9,
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

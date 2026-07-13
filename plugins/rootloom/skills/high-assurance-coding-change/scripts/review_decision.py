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
        repository_state = expected_value.get("repository_state")
        if not isinstance(state_policy, dict):
            raise runner.PipelineError("human review state policy is missing or invalid", 9)
        if not isinstance(metadata_floor, list) or not all(
            isinstance(path, str) for path in metadata_floor
        ):
            raise runner.PipelineError(
                "human review metadata-only floor is missing or invalid",
                9,
            )
        if not isinstance(repository_state, dict):
            raise runner.PipelineError(
                "human review repository commitment is missing or invalid",
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
        summary = {
            **record,
            "accepted": decision == "accept",
            "decision_record_sha256": hashlib.sha256(payload).hexdigest(),
        }
        summary_payload = (
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")

        def validate_unchanged_result(
            value: dict[str, object],
            *,
            phase: str,
        ) -> tuple[dict[str, object], list[str]]:
            observed_expected, observed_deletions = validate_result(value)
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
                    )
                    runner.validate_pinned_private_artifact(
                        pinned_summary,
                        expected_size=summary_size,
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

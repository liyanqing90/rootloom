#!/usr/bin/env python3
"""Analyze a planned or current change for risk and verification needs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from runner.contracts import RISK_LEVELS
from runner.baseline import baseline_payload, write_new_baseline
from runner.intelligence import analyze_change
from runner.state import repository_snapshot, tracked_patch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--task", default="")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--declared-risk", choices=RISK_LEVELS)
    parser.add_argument("--sensitive-path", action="append", default=[])
    parser.add_argument("--write-baseline", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = args.repo.expanduser().resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"not a Git repository: {repo}")
    if args.write_baseline:
        baseline_path = args.write_baseline.expanduser().resolve()
        if baseline_path == repo or baseline_path.is_relative_to(repo):
            raise SystemExit("baseline output must be outside the repository")
    snapshot, _untracked_patch = repository_snapshot(
        repo, extra_sensitive=args.sensitive_path
    )
    sensitive = [item["path"] for item in snapshot["sensitive_paths"]]
    patch = tracked_patch(repo, sensitive_paths=sensitive)
    assessment = analyze_change(
        repo,
        task=args.task,
        anticipated_paths=args.path,
        changes=snapshot["changes"],
        tracked_patch=patch,
        declared_risk=args.declared_risk,
    )
    if args.write_baseline:
        write_new_baseline(
            baseline_path,
            baseline_payload(
                repo,
                snapshot=snapshot,
                tracked_patch=patch,
                extra_sensitive=args.sensitive_path,
                task=args.task,
            ),
        )
    print(json.dumps(assessment, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

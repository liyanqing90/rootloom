#!/usr/bin/env python3
"""Analyze a planned or current change for risk and verification needs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from runner.contracts import RISK_LEVELS
from runner.intelligence import analyze_change
from runner.state import repository_changes, tracked_patch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--task", default="")
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--declared-risk", choices=RISK_LEVELS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = args.repo.expanduser().resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"not a Git repository: {repo}")
    changes, _untracked = repository_changes(repo)
    assessment = analyze_change(
        repo,
        task=args.task,
        anticipated_paths=args.path,
        changes=changes,
        tracked_patch=tracked_patch(repo),
        declared_risk=args.declared_risk,
    )
    print(json.dumps(assessment, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Create an operator-sealed Rootloom review intake directory."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from runner.baseline import baseline_payload, file_sha256, write_new_baseline
from runner.change_contract import contract_sha256
from runner.state import repository_snapshot, tracked_patch


def atomic_write_new(path: Path, payload: dict[str, object]) -> None:
    encoded = (
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("ascii")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--sensitive-path", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = args.repo.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"not a Git repository: {repo}")
    if output == repo or output.is_relative_to(repo):
        raise SystemExit("review output must be outside the repository")
    try:
        os.mkdir(output, 0o700)
    except FileExistsError as exc:
        raise SystemExit(f"review output already exists: {output}") from exc
    snapshot, _untracked_patch = repository_snapshot(
        repo, extra_sensitive=args.sensitive_path
    )
    sensitive = [item["path"] for item in snapshot["sensitive_paths"]]
    patch = tracked_patch(repo, sensitive_paths=sensitive)
    baseline = baseline_payload(
        repo,
        snapshot=snapshot,
        tracked_patch=patch,
        extra_sensitive=args.sensitive_path,
        task=args.task,
        provenance="operator-sealed",
    )
    baseline_path = output / "baseline.json"
    write_new_baseline(baseline_path, baseline)
    command = "TODO replace with repository test command for TODO"
    contract = {
        "format": "rootloom-change-contract-v1",
        "run_id": baseline["run_id"],
        "nonce": baseline["nonce"],
        "baseline_sha256": file_sha256(baseline_path),
        "task_sha256": baseline["task_sha256"],
        "allowed_paths": args.path or ["**"],
        "forbidden_paths": [],
        "root_cause_alignment": "NOT_APPLICABLE",
        "verification_commands": {"verify-primary": command},
        "verification_claims": {
            "primary-behavior": [
                {
                    "id": "primary-behavior",
                    "command_ids": ["verify-primary"],
                    "target": "TODO",
                    "expected_evidence": "TODO replace before finalization",
                    "evidence_kind": "manual-review",
                }
            ]
        },
    }
    contract["contract_sha256"] = contract_sha256(contract)
    atomic_write_new(output / "change-contract.json", contract)
    manifest = {
        "format": "rootloom-review-run-v1",
        "run_id": baseline["run_id"],
        "baseline": "baseline.json",
        "baseline_sha256": contract["baseline_sha256"],
        "change_contract": "change-contract.json",
        "change_contract_sha256": contract["contract_sha256"],
        "nonce": baseline["nonce"],
        "task_sha256": baseline["task_sha256"],
        "next_step": "Edit change-contract.json before running finalize_change.py.",
    }
    atomic_write_new(output / "review.json", manifest)
    print(json.dumps(manifest, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

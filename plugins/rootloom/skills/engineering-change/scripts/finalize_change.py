#!/usr/bin/env python3
"""Verify a personal engineering change and write a compact review bundle."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import tempfile

from runner.contracts import DANGEROUS_DELETE_EXIT, RISK_LEVELS, SUMMARY_FORMAT
from runner.errors import DangerousDeletionError
from runner.intelligence import analyze_change
from runner.state import repository_changes, tracked_patch
from runner.verification import verify


DANGEROUS_PARTS = {".env", "secret", "secrets", "migration", "migrations", "database", "db"}
DEFAULT_MAX_PATCH_BYTES = 16 * 1024 * 1024
MAX_VERIFY_COMMANDS = 20
MAX_COMMAND_CHARS = 8192
MAX_REMAINING_RISKS = 20
MAX_REMAINING_RISK_CHARS = 4096


def is_dangerous_path(path: str) -> bool:
    parts = {part.lower() for part in Path(path).parts}
    name = Path(path).name.lower()
    return bool(parts & DANGEROUS_PARTS) or bool(
        re.search(r"(?:^|[._-])(secret|credential|token|database|migration)(?:[._-]|$)", name)
    )


def dangerous_deletions(changes: list[dict[str, str]]) -> list[str]:
    dangerous: set[str] = set()
    for item in changes:
        if "D" in item["status"] and is_dangerous_path(item["path"]):
            dangerous.add(item["path"])
        if (
            "R" in item["status"]
            and item["original_path"]
            and is_dangerous_path(item["original_path"])
        ):
            dangerous.add(item["original_path"])
    return sorted(dangerous)


def atomic_write(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", default="")
    parser.add_argument("--risk", choices=RISK_LEVELS)
    parser.add_argument("--verify", action="append", default=[])
    parser.add_argument("--remaining-risk", action="append", default=[])
    parser.add_argument("--confirm-dangerous-delete", action="append", default=[])
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--max-output-bytes", type=int, default=4 * 1024 * 1024)
    parser.add_argument("--max-patch-bytes", type=int, default=DEFAULT_MAX_PATCH_BYTES)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = args.repo.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"not a Git repository: {repo}")
    if output == repo or output.is_relative_to(repo):
        raise SystemExit("output directory must be outside the repository being captured")
    if args.timeout <= 0 or args.max_output_bytes <= 0 or args.max_patch_bytes <= 0:
        raise SystemExit("timeout, output budget, and patch budget must be positive")
    if len(args.verify) > MAX_VERIFY_COMMANDS:
        raise SystemExit(f"at most {MAX_VERIFY_COMMANDS} verification commands are supported")
    if any(len(command) > MAX_COMMAND_CHARS for command in args.verify):
        raise SystemExit(f"verification commands must be at most {MAX_COMMAND_CHARS} characters")
    if len(args.remaining_risk) > MAX_REMAINING_RISKS or any(
        len(value) > MAX_REMAINING_RISK_CHARS for value in args.remaining_risk
    ):
        raise SystemExit(
            f"at most {MAX_REMAINING_RISKS} remaining risks of "
            f"{MAX_REMAINING_RISK_CHARS} characters are supported"
        )
    changes_before, untracked_before = repository_changes(repo)
    patch_before = tracked_patch(repo)
    if len(patch_before) > args.max_patch_bytes:
        raise SystemExit(
            f"tracked patch exceeds configured {args.max_patch_bytes}-byte budget"
        )
    assessment = analyze_change(
        repo,
        task=args.task,
        anticipated_paths=[],
        changes=changes_before,
        tracked_patch=patch_before,
        declared_risk=args.risk,
    )
    dangerous = dangerous_deletions(changes_before)
    confirmed = sorted(set(args.confirm_dangerous_delete))
    missing = sorted(set(dangerous) - set(confirmed))
    if missing:
        error = DangerousDeletionError(
            "dangerous deletions require exact confirmation: " + ", ".join(missing)
        )
        print(str(error))
        return DANGEROUS_DELETE_EXIT

    results, log = verify(
        args.verify,
        repo=repo,
        timeout=args.timeout,
        max_output_bytes=args.max_output_bytes,
    )
    changes, untracked = repository_changes(repo)
    patch = tracked_patch(repo)
    verification_preserved_capture = (
        changes == changes_before
        and untracked == untracked_before
        and patch == patch_before
    )
    if not verification_preserved_capture:
        log += (
            b"\nRootloom: verification changed the tracked patch or captured path set; "
            b"result is not PASS.\n"
        )
    dangerous_after = set(dangerous_deletions(changes))
    dangerous_after.update(
        path
        for path in set(untracked_before) - set(untracked)
        if is_dangerous_path(path)
    )
    missing_after = sorted(set(dangerous_after) - set(confirmed))
    if missing_after:
        error = DangerousDeletionError(
            "verification introduced dangerous deletions requiring exact confirmation: "
            + ", ".join(missing_after)
        )
        print(str(error))
        return DANGEROUS_DELETE_EXIT
    if untracked:
        patch += b"\n# Untracked paths (content intentionally omitted)\n"
        patch += "".join(f"# {path}\n" for path in sorted(untracked)).encode(
            "utf-8", errors="surrogateescape"
        )
    risk_assessment = {
        key: value
        for key, value in assessment.items()
        if key not in {"changed_paths", "verification_plan"}
    }
    summary = {
        "format": SUMMARY_FORMAT,
        "changed_files": sorted({item["path"] for item in changes}),
        "risk": assessment["effective_risk"],
        "risk_assessment": risk_assessment,
        "tests": [asdict(item) for item in results],
        "verification_plan": assessment["verification_plan"],
        "verification_preserved_capture": verification_preserved_capture,
        "remaining_risks": list(args.remaining_risk),
        "dangerous_deletions_confirmed": confirmed,
        "passed": (
            bool(results)
            and all(item.passed for item in results)
            and verification_preserved_capture
        ),
    }
    atomic_write(output / "diff.patch", patch)
    atomic_write(output / "test.log", log)
    atomic_write(
        output / "summary.json",
        (json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

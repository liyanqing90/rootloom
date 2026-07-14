#!/usr/bin/env python3
"""Verify a personal engineering change and write a bounded review bundle."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


PLUGIN_LIB = Path(__file__).resolve().parents[3] / "lib"
sys.path.insert(0, str(PLUGIN_LIB))
from rootloom_paths import is_protected_deletion_path, normalize_repo_path

from runner.baseline import load_baseline, sensitive_preservation
from runner.change_contract import (
    claimed_commands,
    load_change_contract,
    parse_cli_claim,
    scope_violations,
    verification_coverage,
)
from runner.contracts import DANGEROUS_DELETE_EXIT, RISK_LEVELS, SUMMARY_FORMAT
from runner.errors import DangerousDeletionError
from runner.intelligence import analyze_change
from runner.state import repository_snapshot, snapshot_identity, tracked_patch
from runner.verification import verify


DEFAULT_MAX_PATCH_BYTES = 16 * 1024 * 1024
MAX_VERIFY_COMMANDS = 20
MAX_COMMAND_CHARS = 8192
MAX_REMAINING_RISKS = 20
MAX_REMAINING_RISK_CHARS = 4096
BUNDLE_MARKER = ".rootloom-engineering-bundle.json"
BUNDLE_MARKER_FORMAT = "rootloom-engineering-bundle-owner-v1"
BUNDLE_FILES = {BUNDLE_MARKER, "diff.patch", "test.log", "summary.json"}


def dangerous_deletions(
    changes: list[dict[str, str]], *, extra_sensitive: set[str] | None = None
) -> list[str]:
    dangerous: set[str] = set()
    for item in changes:
        if "D" in item["status"] and is_protected_deletion_path(
            item["path"], extra_sensitive=extra_sensitive
        ):
            dangerous.add(item["path"])
        if (
            "R" in item["status"]
            and item["original_path"]
            and is_protected_deletion_path(
                item["original_path"], extra_sensitive=extra_sensitive
            )
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


def output_preflight(output: Path) -> None:
    if output.is_symlink():
        raise ValueError("output directory must not be a symlink")
    if not output.exists():
        return
    if not output.is_dir():
        raise ValueError("output path must be a directory")
    entries = {item.name for item in output.iterdir()}
    if not entries:
        return
    marker = output / BUNDLE_MARKER
    try:
        payload = json.loads(marker.read_text(encoding="ascii"))
    except (FileNotFoundError, UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError(
            "nonempty output directory requires a valid Rootloom ownership marker"
        ) from None
    if payload != {"format": BUNDLE_MARKER_FORMAT, "managed_by": "rootloom"}:
        raise ValueError("output directory has an invalid Rootloom ownership marker")
    unexpected = sorted(entries - BUNDLE_FILES)
    if unexpected:
        raise ValueError(
            "Rootloom-owned output directory contains unexpected files: "
            + ", ".join(unexpected)
        )


def write_bundle(output: Path, *, patch: bytes, log: bytes, summary: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    marker = (
        json.dumps(
            {"format": BUNDLE_MARKER_FORMAT, "managed_by": "rootloom"},
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")
    atomic_write(output / BUNDLE_MARKER, marker)
    atomic_write(output / "diff.patch", patch)
    atomic_write(output / "test.log", log)
    atomic_write(
        output / "summary.json",
        (
            json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
        ).encode("ascii"),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", default="")
    parser.add_argument("--risk", choices=RISK_LEVELS)
    parser.add_argument("--verify", action="append", default=[])
    parser.add_argument("--verify-claim", action="append", default=[])
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--change-contract", type=Path)
    parser.add_argument("--sensitive-path", action="append", default=[])
    parser.add_argument("--remaining-risk", action="append", default=[])
    parser.add_argument("--confirm-dangerous-delete", action="append", default=[])
    parser.add_argument("--allow-no-change", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="require governed Tier 1/2 evidence and fail on incomplete coverage",
    )
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
    try:
        output_preflight(output)
        cli_claims = [parse_cli_claim(value) for value in args.verify_claim]
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    commands = list(args.verify)
    for _claim, command in cli_claims:
        if command not in commands:
            commands.append(command)
    if len(commands) > MAX_VERIFY_COMMANDS:
        raise SystemExit(f"at most {MAX_VERIFY_COMMANDS} verification commands are supported")
    if any(len(command) > MAX_COMMAND_CHARS for command in commands):
        raise SystemExit(f"verification commands must be at most {MAX_COMMAND_CHARS} characters")
    if len(args.remaining_risk) > MAX_REMAINING_RISKS or any(
        len(value) > MAX_REMAINING_RISK_CHARS for value in args.remaining_risk
    ):
        raise SystemExit(
            f"at most {MAX_REMAINING_RISKS} remaining risks of "
            f"{MAX_REMAINING_RISK_CHARS} characters are supported"
        )

    baseline: dict[str, Any] | None = None
    baseline_extra: list[str] = []
    if args.baseline:
        try:
            baseline = load_baseline(args.baseline.expanduser().resolve(), repo)
            baseline_extra = list(baseline["sensitive_paths"])
        except (OSError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc
    extra_sensitive = sorted(
        {
            normalize_repo_path(path, label="sensitive path")
            for path in [*args.sensitive_path, *baseline_extra]
        }
    )
    try:
        snapshot_before, untracked_patch_before = repository_snapshot(
            repo,
            extra_sensitive=extra_sensitive,
            max_untracked_patch_bytes=args.max_patch_bytes,
        )
        sensitive_before = [
            item["path"] for item in snapshot_before["sensitive_paths"]
        ]
        remaining_patch = args.max_patch_bytes - len(untracked_patch_before)
        if remaining_patch <= 0:
            raise ValueError("untracked patch exhausted the aggregate patch budget")
        patch_before = tracked_patch(
            repo,
            max_bytes=remaining_patch,
            sensitive_paths=sensitive_before,
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    assessment = analyze_change(
        repo,
        task=args.task,
        anticipated_paths=[],
        changes=snapshot_before["changes"],
        tracked_patch=patch_before,
        declared_risk=args.risk,
    )
    tier = int(assessment["minimum_tier"])
    if args.strict and tier >= 1 and baseline is None:
        raise SystemExit("Tier 1/2 finalization requires --baseline from pre-change analysis")
    if args.strict and tier >= 1 and args.change_contract is None:
        raise SystemExit("Tier 1/2 finalization requires --change-contract")

    contract: dict[str, Any] | None = None
    if args.change_contract:
        try:
            contract = load_change_contract(args.change_contract.expanduser().resolve())
        except (OSError, ValueError) as exc:
            raise SystemExit(str(exc)) from exc
    scope = (
        scope_violations(contract, snapshot_before["changes"])
        if contract is not None
        else {"outside_allowed_paths": [], "forbidden_paths_changed": []}
    )
    contract_scope_valid = not any(scope.values())
    defect_repair = "defect-repair" in {
        item["id"] for item in assessment["signals"]
    }
    root_cause_alignment = (
        contract.get("root_cause_alignment") if contract is not None else None
    )
    root_cause_valid = not defect_repair or root_cause_alignment == "PASS"

    baseline_guard = (
        sensitive_preservation(baseline, snapshot_before)
        if baseline is not None
        else {"preserved": True, "missing": [], "changed": []}
    )
    confirmed = sorted(
        {
            normalize_repo_path(path, label="dangerous deletion confirmation")
            for path in args.confirm_dangerous_delete
        }
    )
    dangerous = set(
        dangerous_deletions(
            snapshot_before["changes"], extra_sensitive=set(extra_sensitive)
        )
    )
    dangerous.update(baseline_guard["missing"])
    missing = sorted(dangerous - set(confirmed))
    if missing:
        error = DangerousDeletionError(
            "dangerous deletions require exact confirmation: " + ", ".join(missing)
        )
        print(str(error))
        return DANGEROUS_DELETE_EXIT

    changed_files = sorted({item["path"] for item in snapshot_before["changes"]})
    has_change = bool(changed_files)
    gate_errors: list[str] = []
    if not contract_scope_valid:
        gate_errors.append("change contract path scope was violated")
    if contract is not None and not root_cause_valid:
        gate_errors.append("behavioral defect requires ROOT_CAUSE_ALIGNMENT: PASS")
    if baseline_guard["changed"]:
        gate_errors.append("sensitive metadata changed since the pre-change baseline")
    if not has_change and not args.allow_no_change:
        gate_errors.append("no repository change; use --allow-no-change for pure verification")
    if gate_errors:
        results = []
        log = ("Rootloom: " + "; ".join(gate_errors) + "\n").encode("utf-8")
    else:
        results, log = verify(
            commands,
            repo=repo,
            timeout=args.timeout,
            max_output_bytes=args.max_output_bytes,
        )

    try:
        snapshot_after, untracked_patch_after = repository_snapshot(
            repo,
            extra_sensitive=extra_sensitive,
            max_untracked_patch_bytes=args.max_patch_bytes,
        )
        sensitive_after = [item["path"] for item in snapshot_after["sensitive_paths"]]
        remaining_patch = args.max_patch_bytes - len(untracked_patch_after)
        if remaining_patch <= 0:
            raise ValueError("untracked patch exhausted the aggregate patch budget")
        patch_after = tracked_patch(
            repo,
            max_bytes=remaining_patch,
            sensitive_paths=sensitive_after,
        )
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    capture_preserved = (
        snapshot_after == snapshot_before
        and untracked_patch_after == untracked_patch_before
        and patch_after == patch_before
    )
    if not capture_preserved:
        log += (
            b"\nRootloom: verification changed the tracked patch or captured path/content set; "
            b"quality status is FAILED.\n"
        )
    verification_sensitive = sensitive_preservation(
        {"snapshot": snapshot_before}, snapshot_after
    )
    dangerous_after = set(
        dangerous_deletions(
            snapshot_after["changes"], extra_sensitive=set(extra_sensitive)
        )
    )
    dangerous_after.update(verification_sensitive["missing"])
    missing_after = sorted(dangerous_after - set(confirmed))
    if missing_after:
        error = DangerousDeletionError(
            "verification introduced dangerous deletions requiring exact confirmation: "
            + ", ".join(missing_after)
        )
        print(str(error))
        return DANGEROUS_DELETE_EXIT

    commands_passed = bool(results) and all(item.passed for item in results)
    passed_commands = {
        commands[index]
        for index, result in enumerate(results)
        if result.passed and index < len(commands)
    }
    claims = claimed_commands(contract, cli_claims)
    coverage, coverage_detail = verification_coverage(
        assessment["verification_plan"]["required_behaviors"],
        claims,
        passed_commands,
        tier=tier,
    )
    baseline_guard_satisfied = (
        not baseline_guard["changed"]
        and set(baseline_guard["missing"]).issubset(confirmed)
    )
    governed_evidence_complete = tier == 0 or (
        baseline is not None
        and contract is not None
        and root_cause_valid
        and baseline_guard_satisfied
    )
    if not has_change:
        quality_status = "NO_CHANGE"
    elif gate_errors or not commands_passed or not capture_preserved:
        quality_status = "FAILED"
    elif not governed_evidence_complete or coverage != "complete":
        quality_status = "UNVERIFIED"
    else:
        quality_status = "VERIFIED_CHANGE"
    operational_success = (
        not gate_errors
        and commands_passed
        and capture_preserved
        and baseline_guard_satisfied
    )
    if args.strict:
        successful = quality_status == "VERIFIED_CHANGE" or (
            quality_status == "NO_CHANGE"
            and args.allow_no_change
            and operational_success
            and coverage == "complete"
        )
    else:
        successful = operational_success and (has_change or args.allow_no_change)
    patch = patch_after + (b"\n" if patch_after and untracked_patch_after else b"") + untracked_patch_after
    if len(patch) > args.max_patch_bytes:
        raise SystemExit(
            f"complete patch exceeds configured {args.max_patch_bytes}-byte budget"
        )
    risk_assessment = {
        key: value
        for key, value in assessment.items()
        if key not in {"changed_paths", "verification_plan"}
    }
    summary = {
        "format": SUMMARY_FORMAT,
        "changed_files": changed_files,
        "risk": assessment["effective_risk"],
        "risk_assessment": risk_assessment,
        "tests": [asdict(item) for item in results],
        "verification_plan": assessment["verification_plan"],
        "verification_claims": coverage_detail,
        "verification_coverage": coverage,
        "mode": "strict" if args.strict else "advisory",
        "commands_passed": commands_passed,
        "capture_preserved": capture_preserved,
        "verification_preserved_capture": capture_preserved,
        "baseline_sensitive_preservation": baseline_guard,
        "baseline": {
            "required": bool(args.strict and tier >= 1),
            "provided": baseline is not None,
        },
        "change_contract": {
            "required": bool(args.strict and tier >= 1),
            "provided": contract is not None,
            "scope_valid": contract_scope_valid,
            "scope_violations": scope,
            "root_cause_alignment": root_cause_alignment,
            "root_cause_alignment_valid": root_cause_valid,
        },
        "repository_capture": {
            "identity": snapshot_identity(snapshot_after),
            "untracked": snapshot_after["untracked"],
            "sensitive_paths": snapshot_after["sensitive_paths"],
            "bounds": snapshot_after["bounds"],
        },
        "quality_status": quality_status,
        "remaining_risks": list(args.remaining_risk),
        "dangerous_deletions_confirmed": confirmed,
        "allow_no_change": bool(args.allow_no_change),
        "passed": quality_status == "VERIFIED_CHANGE",
    }
    write_bundle(output, patch=patch, log=log, summary=summary)
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())

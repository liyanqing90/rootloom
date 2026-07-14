#!/usr/bin/env python3
"""Verify a personal engineering change and write a bounded review bundle."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any


PLUGIN_LIB = Path(__file__).resolve().parents[3] / "lib"
sys.path.insert(0, str(PLUGIN_LIB))
from rootloom_paths import is_protected_deletion_path, normalize_repo_path

from runner.baseline import read_baseline_with_hash, sensitive_preservation, task_sha256
from runner.change_contract import (
    claimed_commands,
    load_change_contract,
    parse_cli_claim,
    scope_violations,
    verification_coverage,
)
from runner.contracts import (
    DANGEROUS_DELETE_EXIT,
    RISK_LEVELS,
    SUMMARY_FORMAT,
    SUMMARY_SCHEMA_REVISION,
)
from runner.errors import DangerousDeletionError
from runner.intelligence import analyze_change
from runner.state import repository_snapshot, snapshot_identity, tracked_patch
from runner.verification import verify


DEFAULT_MAX_PATCH_BYTES = 16 * 1024 * 1024
MAX_VERIFY_COMMANDS = 20
MAX_COMMAND_CHARS = 8192
MAX_REMAINING_RISKS = 20
MAX_REMAINING_RISK_CHARS = 4096
QUALITY_EXIT_CODES = {
    "VERIFIED_CHANGE": 0,
    "MECHANICALLY_VERIFIED": 4,
    "COMMANDS_PASSED": 4,
    "NO_CHANGE": 3,
    "UNVERIFIED": 4,
    "FAILED": 1,
}
BUNDLE_MARKER = ".rootloom-engineering-bundle.json"
BUNDLE_MARKER_FORMAT = "rootloom-engineering-bundle-owner-v1"
BUNDLE_FILES = {BUNDLE_MARKER, "diff.patch", "test.log", "summary.json"}
REVIEW_MANIFEST = "review.json"
MAX_REVIEW_MANIFEST_BYTES = 256 * 1024


def absolute_lexical_path(path: Path) -> Path:
    expanded = path.expanduser()
    if expanded.is_absolute():
        return expanded
    return Path.cwd() / expanded


def read_review_manifest(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise ValueError("review manifest must not be a symlink")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError("review manifest must be a regular file")
        raw = bytearray()
        while len(raw) <= MAX_REVIEW_MANIFEST_BYTES:
            chunk = os.read(
                descriptor,
                min(64 * 1024, MAX_REVIEW_MANIFEST_BYTES + 1 - len(raw)),
            )
            if not chunk:
                break
            raw.extend(chunk)
        after = os.fstat(descriptor)
        if (
            (opened.st_dev, opened.st_ino, opened.st_size)
            != (after.st_dev, after.st_ino, after.st_size)
        ):
            raise ValueError("review manifest changed during read")
        if len(raw) > MAX_REVIEW_MANIFEST_BYTES or after.st_size > MAX_REVIEW_MANIFEST_BYTES:
            raise ValueError("review manifest exceeds byte budget")
    finally:
        os.close(descriptor)
    payload = json.loads(bytes(raw).decode("ascii"))
    if not isinstance(payload, dict):
        raise ValueError("review manifest must be a JSON object")
    return payload


def load_review_manifest(
    baseline_path: Path,
    contract_path: Path | None,
    *,
    baseline: dict[str, Any],
    baseline_sha256: str | None,
    contract: dict[str, Any] | None,
) -> tuple[bool, dict[str, Any]]:
    detail: dict[str, Any] = {
        "provided": False,
        "path": None,
        "valid": False,
        "errors": [],
    }
    if contract_path is None or baseline_path.parent != contract_path.parent:
        detail["errors"].append("baseline and change contract are not in one review run directory")
        return False, detail
    manifest_path = baseline_path.parent / REVIEW_MANIFEST
    detail["path"] = str(manifest_path)
    try:
        payload = read_review_manifest(manifest_path)
    except FileNotFoundError:
        detail["errors"].append("review manifest is missing")
        return False, detail
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        detail["errors"].append(f"review manifest is invalid: {exc}")
        return False, detail
    detail["provided"] = True
    if not isinstance(payload, dict) or payload.get("format") != "rootloom-review-run-v1":
        detail["errors"].append("review manifest format is invalid")
        return False, detail
    expected = {
        "run_id": baseline.get("run_id"),
        "nonce": baseline.get("nonce"),
        "task_sha256": baseline.get("task_sha256"),
        "baseline": baseline_path.name,
        "baseline_sha256": baseline_sha256,
        "change_contract": contract_path.name,
        "change_contract_sha256": contract.get("contract_sha256") if contract else None,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            detail["errors"].append(f"review manifest {field} does not match")
    valid = not detail["errors"]
    detail["valid"] = valid
    return valid, detail


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
    parser.add_argument("--exit-policy", choices=("bundle", "quality"), default="bundle")
    parser.add_argument(
        "--require-verified",
        action="store_true",
        help="CI-friendly alias for --exit-policy quality",
    )
    parser.add_argument(
        "--semantic-coverage",
        choices=("unknown", "partial", "reviewed"),
        default="unknown",
    )
    parser.add_argument("--max-baseline-age-seconds", type=int)
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
    if args.require_verified:
        args.exit_policy = "quality"
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
    baseline_path: Path | None = None
    baseline_sha256: str | None = None
    baseline_extra: list[str] = []
    if args.baseline:
        baseline_path = absolute_lexical_path(args.baseline)
        try:
            baseline, baseline_sha256 = read_baseline_with_hash(baseline_path, repo)
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
    contract_path: Path | None = None
    contract_sha256: str | None = None
    if args.change_contract:
        contract_path = absolute_lexical_path(args.change_contract)
        try:
            contract = load_change_contract(contract_path)
            contract_sha256 = contract["actual_contract_sha256"]
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
    expected_task_sha256 = task_sha256(args.task)
    baseline_age_seconds: int | None = None
    baseline_freshness = "not-provided"
    baseline_operator_sealed = False
    contract_operator_sealed = False
    review_manifest_valid = False
    review_manifest: dict[str, Any] = {"provided": False, "valid": False, "errors": []}
    hash_chain_errors: list[str] = []
    if baseline is not None:
        created_at = baseline.get("created_at")
        if isinstance(created_at, str):
            try:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                baseline_age_seconds = max(
                    0,
                    int((datetime.now(UTC) - created.astimezone(UTC)).total_seconds()),
                )
                baseline_freshness = "fresh"
                if (
                    args.max_baseline_age_seconds is not None
                    and baseline_age_seconds > args.max_baseline_age_seconds
                ):
                    baseline_freshness = "too-old"
                    hash_chain_errors.append("baseline exceeds max age")
                elif baseline_age_seconds > 24 * 60 * 60:
                    baseline_freshness = "old"
            except ValueError:
                baseline_freshness = "unknown"
        if baseline.get("task_sha256") not in {None, expected_task_sha256}:
            hash_chain_errors.append("baseline task_sha256 does not match task")
        if contract is not None and (
            baseline_operator_sealed
            or any(
                contract.get(field) is not None
                for field in ("baseline_sha256", "task_sha256", "run_id", "nonce")
            )
        ):
            if contract.get("baseline_sha256") == baseline_sha256:
                contract_operator_sealed = True
            else:
                hash_chain_errors.append("change contract baseline_sha256 does not match baseline")
            for field in ("task_sha256", "run_id", "nonce"):
                baseline_value = expected_task_sha256 if field == "task_sha256" else baseline.get(field)
                contract_value = contract.get(field)
                if contract_value != baseline_value:
                    hash_chain_errors.append(f"change contract {field} does not match baseline")
            contract_operator_sealed = contract_operator_sealed and not hash_chain_errors
            review_manifest_valid, review_manifest = load_review_manifest(
                baseline_path,
                contract_path,
                baseline=baseline,
                baseline_sha256=baseline_sha256,
                contract=contract,
            )
            if (
                baseline.get("evidence_provenance") == "operator-sealed"
                and review_manifest_valid
            ):
                baseline_operator_sealed = True
                contract_operator_sealed = contract_operator_sealed and True
            else:
                contract_operator_sealed = False
    if contract is not None and contract.get("task_sha256") not in {None, expected_task_sha256}:
        hash_chain_errors.append("change contract task_sha256 does not match task")

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
    if args.strict and hash_chain_errors:
        gate_errors.extend(hash_chain_errors)
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
    claim_binding, coverage_detail = verification_coverage(
        assessment["verification_plan"]["required_behaviors"],
        claims,
        passed_commands,
        tier=tier,
    )
    process_converged = all(item.process_tree_converged for item in results)
    process_convergence = "complete" if process_converged else "uncertain"
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
    operator_sealed_evidence = (
        governed_evidence_complete
        and baseline_operator_sealed
        and contract_operator_sealed
        and not hash_chain_errors
    )
    if not has_change:
        quality_status = "NO_CHANGE"
    elif gate_errors or not commands_passed or not capture_preserved:
        quality_status = "FAILED"
    elif process_convergence != "complete":
        quality_status = "UNVERIFIED"
    elif not governed_evidence_complete or claim_binding == "unverified":
        quality_status = "UNVERIFIED"
    elif claim_binding != "complete":
        quality_status = "COMMANDS_PASSED"
    elif not operator_sealed_evidence:
        quality_status = "MECHANICALLY_VERIFIED"
    else:
        quality_status = "VERIFIED_CHANGE"
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
        "schema_revision": SUMMARY_SCHEMA_REVISION,
        "producer_version": "2.2.1",
        "changed_files": changed_files,
        "risk": assessment["effective_risk"],
        "risk_assessment": risk_assessment,
        "tests": [asdict(item) for item in results],
        "verification_plan": assessment["verification_plan"],
        "verification_claims": coverage_detail,
        "claim_binding": claim_binding,
        "verification_coverage": claim_binding,
        "semantic_coverage": args.semantic_coverage,
        "mode": "strict" if args.strict else "advisory",
        "exit_policy": args.exit_policy,
        "commands_passed": commands_passed,
        "capture_preserved": capture_preserved,
        "verification_preserved_capture": capture_preserved,
        "process_convergence": process_convergence,
        "detached_descendant_possible": True,
        "isolation": "process-group-only",
        "baseline_sensitive_preservation": baseline_guard,
        "baseline": {
            "required": bool(args.strict and tier >= 1),
            "provided": baseline is not None,
            "format": baseline.get("format") if baseline is not None else None,
            "sha256": baseline_sha256,
            "run_id": baseline.get("run_id") if baseline is not None else None,
            "nonce": baseline.get("nonce") if baseline is not None else None,
            "task_sha256": baseline.get("task_sha256") if baseline is not None else None,
            "age_seconds": baseline_age_seconds,
            "freshness": baseline_freshness,
        },
        "change_contract": {
            "required": bool(args.strict and tier >= 1),
            "provided": contract is not None,
            "sha256": contract_sha256,
            "run_id": contract.get("run_id") if contract is not None else None,
            "nonce": contract.get("nonce") if contract is not None else None,
            "task_sha256": contract.get("task_sha256") if contract is not None else None,
            "baseline_sha256": contract.get("baseline_sha256") if contract is not None else None,
            "contract_sha256": contract.get("contract_sha256") if contract is not None else None,
            "scope_valid": contract_scope_valid,
            "scope_violations": scope,
            "root_cause_alignment": root_cause_alignment,
            "root_cause_alignment_valid": root_cause_valid,
            "hash_chain_valid": not hash_chain_errors,
            "hash_chain_errors": hash_chain_errors,
        },
        "review_manifest": review_manifest,
        "evidence_provenance": {
            "baseline": "operator-sealed" if baseline_operator_sealed else "self-declared",
            "change_contract": (
                "operator-sealed" if contract_operator_sealed else "self-declared"
            ),
            "verification_claims": "self-declared",
        },
        "hash_chain": {
            "baseline_sha256": baseline_sha256,
            "change_contract_sha256": contract_sha256,
            "task_sha256": expected_task_sha256,
            "run_id": baseline.get("run_id") if baseline is not None else None,
            "nonce": baseline.get("nonce") if baseline is not None else None,
            "valid": not hash_chain_errors,
            "errors": hash_chain_errors,
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
    summary["process_exit_code"] = (
        0
        if args.exit_policy == "bundle" and quality_status != "FAILED"
        else QUALITY_EXIT_CODES[quality_status]
    )
    write_bundle(output, patch=patch, log=log, summary=summary)
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return int(summary["process_exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())

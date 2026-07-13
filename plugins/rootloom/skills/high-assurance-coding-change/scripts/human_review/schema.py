"""Complete structural validation for persisted Human Review v4 evidence."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any

from runner.errors import EvidenceInvalidError, PipelineError
from runner.state import commitment_sha256

from .constants import MAX_HUMAN_REVIEW_ARTIFACTS


BINDING_FIELDS = {
    "format",
    "repo",
    "run_directory",
    "git_head",
    "state_policy",
    "final_metadata_only_floor_paths",
    "repository_state",
    "protected_deletions",
    "result_core_sha256",
    "artifacts",
}
REPOSITORY_COMPONENTS = {
    "status",
    "paths",
    "ignored_paths",
    "untracked_paths",
    "sensitive_untracked_paths",
    "metadata_only_paths",
    "worktree",
    "index",
    "git_control",
}
STATE_POLICY_FIELDS = {
    "max_ignored_paths",
    "max_state_paths",
    "max_state_bytes",
    "sensitive_paths",
    "redact_untracked_dotfiles",
    "max_human_review_artifact_bytes",
    "max_human_review_total_bytes",
    "max_human_review_binding_seconds",
}
RESULT_FIELDS = {
    "format",
    "runner_version",
    "run_id",
    "metadata_artifact",
    "result",
    "run_dir",
    "repair_cycles",
    "changed_paths",
    "allowed_paths",
    "git_index_unchanged",
    "git_status",
    "git_diff_stat",
    "untracked",
    "ignored_metadata",
    "redacted_untracked_metadata",
    "protected_deletions",
    "delta_artifacts",
    "human_review_binding",
}
DELTA_ARTIFACT_FIELDS = {
    "status",
    "staged_patch",
    "unstaged_patch",
    "head_to_worktree_patch",
    "untracked_patch",
    "untracked_manifest",
    "ignored_metadata",
    "redacted_untracked_metadata",
}


def _invalid(message: str) -> None:
    raise EvidenceInvalidError(message)


def normalize_review_scope(repo: Path, run_dir: Path) -> tuple[Path, Path]:
    try:
        normalized_repo = repo.expanduser().resolve()
        supplied_run_dir = run_dir.expanduser()
        unsafe_run_dir = supplied_run_dir.is_symlink() or not supplied_run_dir.is_dir()
        normalized_run_dir = supplied_run_dir.resolve()
    except (OSError, RuntimeError) as exc:
        raise EvidenceInvalidError("review scope path is invalid") from exc
    if unsafe_run_dir:
        _invalid("review run directory is missing or symlinked")
    return normalized_repo, normalized_run_dir


def _require_exact_fields(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _invalid(f"{label} must be an object")
    assert isinstance(value, dict)
    if set(value) != fields:
        _invalid(f"{label} fields are invalid")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        _invalid(f"{label} must be a lowercase SHA-256")
    return value


def _require_nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _invalid(f"{label} must be a nonnegative integer")
    return value


def _canonical_repo_paths(runtime: Any, value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        _invalid(f"{label} must be a string list")
    assert isinstance(value, list)
    normalized: list[str] = []
    for raw in value:
        try:
            path = runtime.normalize_repo_path(raw, contract=True)
        except PipelineError as exc:
            raise EvidenceInvalidError(f"{label} contains an invalid path") from exc
        if path != raw:
            _invalid(f"{label} paths must be canonical")
        normalized.append(path)
    if normalized != sorted(set(normalized)):
        _invalid(f"{label} paths must be unique and sorted")
    return normalized


def _canonical_sensitive_paths(runtime: Any, value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        _invalid("human review sensitive_paths must be a string list")
    assert isinstance(value, list)
    try:
        rules = runtime.normalize_sensitive_paths(value)
    except PipelineError as exc:
        raise EvidenceInvalidError(
            "human review sensitive_paths contains an invalid path"
        ) from exc
    canonical = [path + "/**" if recursive else path for path, recursive in rules]
    if canonical != value or canonical != sorted(set(canonical)):
        _invalid("human review sensitive_paths must be canonical, unique, and sorted")
    return canonical


def validate_state_policy(runtime: Any, value: Any) -> dict[str, Any]:
    policy = _require_exact_fields(value, STATE_POLICY_FIELDS, "human review state policy")
    try:
        normalized, _ = runtime.normalize_human_review_state_policy(policy)
    except PipelineError as exc:
        raise EvidenceInvalidError("human review state policy is invalid") from exc
    _canonical_sensitive_paths(runtime, policy["sensitive_paths"])
    if normalized != policy:
        _invalid("human review state policy is not canonical")
    return policy


def validate_repository_state_commitment(
    value: Any,
    *,
    state_policy: dict[str, Any],
) -> dict[str, Any]:
    commitment = _require_exact_fields(
        value,
        {
            "format",
            "path_count",
            "worktree_entry_count",
            "component_sha256",
            "sha256",
        },
        "human review repository commitment",
    )
    if commitment["format"] != "rootloom-repository-state-commitment-v1":
        _invalid("human review repository commitment format is invalid")
    path_count = _require_nonnegative_int(
        commitment["path_count"], "repository path_count"
    )
    worktree_entry_count = _require_nonnegative_int(
        commitment["worktree_entry_count"],
        "repository worktree_entry_count",
    )
    if worktree_entry_count > path_count:
        _invalid("repository worktree_entry_count exceeds path_count")
    if path_count > state_policy["max_state_paths"]:
        _invalid("repository path_count exceeds the persisted state-path budget")
    component_hashes = _require_exact_fields(
        commitment["component_sha256"],
        REPOSITORY_COMPONENTS,
        "human review repository component hashes",
    )
    for name, digest in component_hashes.items():
        _require_sha256(digest, f"repository component {name}")
    expected_sha256 = _require_sha256(
        commitment["sha256"],
        "human review repository commitment hash",
    )
    unsigned = {key: item for key, item in commitment.items() if key != "sha256"}
    if commitment_sha256(unsigned) != expected_sha256:
        _invalid("human review repository commitment hash is inconsistent")
    return commitment


def validate_run_directory_identity(
    value: Any,
    *,
    expected_run_dir: Path,
) -> dict[str, Any]:
    identity = _require_exact_fields(
        value,
        {"path", "device", "inode", "mode"},
        "human review Run Directory commitment",
    )
    path = identity["path"]
    if (
        not isinstance(path, str)
        or not Path(path).is_absolute()
        or os.path.normpath(path) != path
        or path != str(expected_run_dir)
    ):
        _invalid("human review Run Directory commitment path is invalid")
    _require_nonnegative_int(identity["device"], "Run Directory device")
    _require_nonnegative_int(identity["inode"], "Run Directory inode")
    mode = _require_nonnegative_int(identity["mode"], "Run Directory mode")
    if not stat.S_ISDIR(mode):
        _invalid("human review Run Directory mode is not a directory")
    if stat.S_IMODE(mode) != 0o700:
        _invalid("human review Run Directory mode must be 0700")
    return identity


def _validate_directory_boundary(value: Any) -> dict[str, Any]:
    fingerprint = _require_exact_fields(
        value,
        {"kind", "device", "inode", "mode", "mtime_ns", "ctime_ns"},
        "protected deletion parent fingerprint",
    )
    if fingerprint["kind"] != "directory-boundary":
        _invalid("protected deletion parent fingerprint kind is invalid")
    for field in ("device", "inode", "mode", "mtime_ns", "ctime_ns"):
        _require_nonnegative_int(fingerprint[field], f"protected deletion parent {field}")
    if not stat.S_ISDIR(fingerprint["mode"]):
        _invalid("protected deletion parent mode is not a directory")
    return fingerprint


def validate_protected_deletion_commitment(
    value: Any,
    *,
    protected_deletions: list[str],
) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        _invalid("human review protected deletion commitment must be an object")
    assert isinstance(value, dict)
    if list(value) != protected_deletions:
        _invalid("human review binding drifted: protected deletions do not match Result")
    for path, raw_commitment in value.items():
        commitment = _require_exact_fields(
            raw_commitment,
            {"state", "parents"},
            "protected deletion commitment",
        )
        if commitment["state"] != "exact-missing":
            _invalid("protected deletion state is invalid")
        parents = commitment["parents"]
        if not isinstance(parents, list):
            _invalid("protected deletion parents must be a list")
        expected_paths = ["."]
        current_parts: list[str] = []
        for part in PurePosixPath(path).parts[:-1]:
            current_parts.append(part)
            expected_paths.append(PurePosixPath(*current_parts).as_posix())
        observed_paths: list[str] = []
        for raw_parent in parents:
            parent = _require_exact_fields(
                raw_parent,
                {"path", "fingerprint"},
                "protected deletion parent",
            )
            if not isinstance(parent["path"], str):
                _invalid("protected deletion parent path is invalid")
            observed_paths.append(parent["path"])
            _validate_directory_boundary(parent["fingerprint"])
        if observed_paths != expected_paths:
            _invalid("protected deletion parent boundary sequence is invalid")
    return value


def validate_artifact_map(
    value: Any,
    *,
    state_policy: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        _invalid("human review Artifact map must be an object")
    assert isinstance(value, dict)
    names = list(value)
    if names != sorted(names) or len(names) > MAX_HUMAN_REVIEW_ARTIFACTS:
        _invalid("human review Artifact names must be sorted and within budget")
    total_bytes = 0
    excluded = {"result.json", "human-review.ndjson", "human-review-summary.json"}
    for name, raw_fingerprint in value.items():
        if (
            not name
            or name in {".", ".."}
            or name in excluded
            or "/" in name
            or "\\" in name
            or "\x00" in name
            or len(name.encode("utf-8", errors="surrogatepass")) > 4096
        ):
            _invalid("human review Artifact name is invalid")
        fingerprint = _require_exact_fields(
            raw_fingerprint,
            {"size", "sha256"},
            "human review Artifact fingerprint",
        )
        size = _require_nonnegative_int(fingerprint["size"], "Artifact size")
        _require_sha256(fingerprint["sha256"], "Artifact hash")
        if size > state_policy["max_human_review_artifact_bytes"]:
            _invalid("human review Artifact size exceeds the persisted budget")
        total_bytes += size
        if total_bytes > state_policy["max_human_review_total_bytes"]:
            _invalid("human review total Artifact size exceeds the persisted budget")
    return value


def validate_human_review_binding_v4_schema(
    runtime: Any,
    binding: Any,
    *,
    repo: Path,
    run_dir: Path,
    protected_deletions: list[str],
) -> dict[str, Any]:
    if not isinstance(binding, dict):
        _invalid("human review binding is missing or invalid")
    assert isinstance(binding, dict)
    if binding.get("format") != "rootloom-human-review-binding-v4":
        _invalid("unsupported human review binding version; rerun with Human Review v4")
    missing = BINDING_FIELDS - set(binding)
    if "final_metadata_only_floor_paths" in missing:
        _invalid("human review metadata-only floor is missing or invalid")
    if "repository_state" in missing:
        _invalid("human review repository commitment is missing or invalid")
    if "run_directory" in missing:
        _invalid("human review Run Directory commitment is missing or invalid")
    value = _require_exact_fields(binding, BINDING_FIELDS, "Human Review v4 Binding")
    repo_path = value["repo"]
    if (
        not isinstance(repo_path, str)
        or not Path(repo_path).is_absolute()
        or os.path.normpath(repo_path) != repo_path
        or repo_path != str(repo)
    ):
        _invalid("human review Binding repository path is invalid")
    git_head = value["git_head"]
    if not isinstance(git_head, str) or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", git_head) is None:
        _invalid("human review Binding git_head is invalid")
    _require_sha256(value["result_core_sha256"], "human review result-core hash")
    policy = validate_state_policy(runtime, value["state_policy"])
    floor = _canonical_repo_paths(
        runtime,
        value["final_metadata_only_floor_paths"],
        "human review metadata-only floor",
    )
    try:
        normalized_floor = runtime.normalize_human_review_metadata_floor(
            floor,
            max_paths=policy["max_state_paths"],
            max_path_bytes=policy["max_state_bytes"],
        )
    except PipelineError as exc:
        raise EvidenceInvalidError(
            "human review metadata-only floor exceeds its persisted budget"
        ) from exc
    if normalized_floor != set(floor):
        _invalid("human review metadata-only floor is not canonical")
    if not set(protected_deletions).issubset(floor):
        _invalid("human review metadata-only floor omits a protected deletion")
    validate_repository_state_commitment(
        value["repository_state"],
        state_policy=policy,
    )
    validate_run_directory_identity(value["run_directory"], expected_run_dir=run_dir)
    validate_protected_deletion_commitment(
        value["protected_deletions"],
        protected_deletions=protected_deletions,
    )
    validate_artifact_map(value["artifacts"], state_policy=policy)
    return value


def _canonical_artifact_name(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or "\x00" in value
        or len(value.encode("utf-8", errors="surrogatepass")) > 4096
    ):
        _invalid(f"{label} is invalid")
    return value


def _canonical_metadata_records(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        _invalid(f"{label} must be an object list")
    paths: list[str] = []
    for item in value:
        if set(item) != {"path", "kind"} or item.get("kind") != "missing":
            _invalid(f"{label} entries must be exact missing-path records")
        path = item.get("path")
        if not isinstance(path, str):
            _invalid(f"{label} path is invalid")
        paths.append(path)
    if paths != sorted(set(paths)):
        _invalid(f"{label} paths must be unique and sorted")
    return value


def validate_review_result(
    runtime: Any,
    repo: Path,
    run_dir: Path,
    value: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    result = _require_exact_fields(value, RESULT_FIELDS, "Human Review Result Envelope")
    if result.get("format") != "rootloom-human-review-result-v1":
        _invalid("unsupported Human Review Result Envelope; rerun with Result v1")
    if value.get("result") != "HUMAN_REVIEW_REQUIRED":
        _invalid("run is not awaiting human review")
    runner_version = result.get("runner_version")
    if not isinstance(runner_version, str) or re.fullmatch(r"[0-9]+\.[0-9]+", runner_version) is None:
        _invalid("Human Review Result runner_version is invalid")
    if result.get("run_id") != run_dir.name:
        _invalid("Human Review Result run_id does not match the Run Directory")
    metadata_artifact = _canonical_artifact_name(
        result.get("metadata_artifact"),
        "Human Review metadata Artifact",
    )
    declared_run_dir = value.get("run_dir")
    try:
        normalized_declared_run_dir = (
            Path(declared_run_dir).expanduser().resolve()
            if isinstance(declared_run_dir, str)
            and Path(declared_run_dir).is_absolute()
            else None
        )
    except (OSError, RuntimeError):
        normalized_declared_run_dir = None
    if normalized_declared_run_dir != run_dir:
        _invalid("Result run_dir does not match the supplied review directory")
    protected = _canonical_repo_paths(
        runtime,
        value.get("protected_deletions"),
        "protected_deletions",
    )
    if not protected:
        _invalid("Human Review Result protected_deletions must be nonempty")
    if result.get("repair_cycles") != 0:
        _invalid("Human Review Result repair_cycles must be zero")
    changed_paths = _canonical_repo_paths(
        runtime,
        result.get("changed_paths"),
        "changed_paths",
    )
    if changed_paths != protected:
        _invalid("Human Review Result changed_paths must equal protected_deletions")
    if result.get("git_index_unchanged") is not True:
        _invalid("Human Review Result must prove an unchanged Git index")
    for field in ("git_status", "git_diff_stat"):
        if not isinstance(result.get(field), str):
            _invalid(f"Human Review Result {field} must be text")
    if result.get("untracked") != []:
        _invalid("Human Review deletion-only Result cannot contain untracked entries")
    allowed_paths = result.get("allowed_paths")
    try:
        allowed_rules = runtime.normalize_allowed_paths(allowed_paths)
    except PipelineError as exc:
        raise EvidenceInvalidError("Human Review Result allowed_paths is invalid") from exc
    if not isinstance(allowed_paths, list) or allowed_paths != sorted(set(allowed_paths)):
        _invalid("Human Review Result allowed_paths must be unique and sorted")
    if any(not runtime.path_is_allowed(path, allowed_rules) for path in protected):
        _invalid("Human Review Result allowed_paths omits a protected deletion")
    ignored = _canonical_metadata_records(
        result.get("ignored_metadata"),
        "Human Review ignored_metadata",
    )
    redacted = _canonical_metadata_records(
        result.get("redacted_untracked_metadata"),
        "Human Review redacted_untracked_metadata",
    )
    metadata_paths = [item["path"] for item in ignored + redacted]
    if sorted(metadata_paths) != protected or len(metadata_paths) != len(set(metadata_paths)):
        _invalid("Human Review metadata records must exactly cover protected deletions")
    artifacts = _require_exact_fields(
        result.get("delta_artifacts"),
        DELTA_ARTIFACT_FIELDS,
        "Human Review delta_artifacts",
    )
    artifact_names = [
        _canonical_artifact_name(name, "Human Review delta Artifact")
        for name in artifacts.values()
    ]
    if len(artifact_names) != len(set(artifact_names)):
        _invalid("Human Review delta Artifact names must be unique")
    expected = validate_human_review_binding_v4_schema(
        runtime,
        value.get("human_review_binding"),
        repo=repo,
        run_dir=run_dir,
        protected_deletions=protected,
    )
    bound_artifacts = expected["artifacts"]
    if metadata_artifact not in bound_artifacts or any(
        name not in bound_artifacts for name in artifact_names
    ):
        _invalid("Human Review Result references an unbound Artifact")
    if len(expected["protected_deletions"]) != len(protected):
        _invalid("Human Review protected-deletion count is inconsistent")
    if expected["result_core_sha256"] != runtime.human_review_result_core_sha256(value):
        _invalid("human review Binding result-core hash does not match Result")
    return expected, protected

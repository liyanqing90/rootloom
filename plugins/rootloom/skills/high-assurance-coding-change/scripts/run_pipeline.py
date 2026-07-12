#!/usr/bin/env python3
"""Run a model-routed high-assurance coding pipeline with explicit stage gates."""

from __future__ import annotations

import argparse
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import selectors
import shlex
import signal
import subprocess
import sys
import textwrap
import time
import tomllib
from typing import Any, Callable, Iterator

if os.name == "posix":
    import fcntl
else:  # pragma: no cover - import behavior is asserted through the platform gate
    fcntl = None  # type: ignore[assignment]


ROLE_FILES = {
    "evidence": "evidence_explorer.toml",
    "diagnosis": "root_cause_reviewer.toml",
    "implementation": "implementation_worker.toml",
    "review": "verification_reviewer.toml",
}

ROLE_SANDBOXES = {
    "evidence": "read-only",
    "diagnosis": "read-only",
    "implementation": "workspace-write",
    "review": "read-only",
}

COMMON_DISABLED_FEATURES = (
    "plugins",
    "apps",
    "remote_plugin",
    "memories",
    "tool_suggest",
)

VALID_REASONING_EFFORTS = {"low", "medium", "high", "xhigh", "max", "ultra"}
VALID_SANDBOX_MODES = {"read-only", "workspace-write"}
HARD_REVIEW_SEVERITIES = {"BLOCKER", "HIGH"}
MAX_DELTA_PROMPT_CHARS = 120_000
DEFAULT_MAX_IGNORED_PATHS = 50_000
BUILTIN_DIFF_CHECK_ID = "verify-0"
HUMAN_REVIEW_REQUIRED_EXIT = 10
COMMAND_OUTPUT_LIMIT_EXIT = 126
DEFAULT_MAX_COMMAND_OUTPUT_BYTES = 8 * 1024 * 1024
DEFAULT_MAX_VERIFICATION_OUTPUT_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_VERIFICATION_ARTIFACT_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_DELTA_BYTES = 32 * 1024 * 1024
DEFAULT_MAX_UNTRACKED_PATCH_BYTES = 8 * 1024 * 1024
MAX_DELTA_PATCH_EXCERPT_BYTES = 24_000
MAX_VERIFICATION_COMMANDS = 64
MAX_VERIFICATION_PROMPT_CHARS = 120_000
OUTPUT_READ_CHUNK_BYTES = 64 * 1024
RUNNER_VERSION = "2.13"
PROCESS_OUTPUT_DRAIN_TIMEOUT_SECONDS = 1.0
VERIFICATION_ENV_ALLOWLIST = (
    "CI",
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "LOGNAME",
    "PATH",
    "SHELL",
    "TERM",
    "TMP",
    "TMPDIR",
    "TEMP",
    "USER",
)
SENSITIVE_PATH_PARTS = {".aws", ".docker", ".gnupg", ".kube", ".ssh"}
SENSITIVE_FILE_SUFFIXES = {".jks", ".key", ".p12", ".pem", ".pfx"}
SENSITIVE_FILE_NAMES = {
    ".git-credentials",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "auth.json",
    "credentials",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "kubeconfig",
    "service-account.json",
    "service_account.json",
    "secrets.json",
}

EVIDENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "observed_facts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "statement": {"type": "string"},
                    "provenance_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "statement", "provenance_ids"],
            },
        },
        "evidence_provenance": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "claim": {"type": "string"},
                    "kind": {"type": "string", "enum": ["fact", "inference", "unknown"]},
                    "source_environment": {"type": "string"},
                    "observed_at": {"type": "string"},
                    "reference": {"type": "string"},
                    "freshness_redaction": {"type": "string"},
                },
                "required": [
                    "id",
                    "claim",
                    "kind",
                    "source_environment",
                    "observed_at",
                    "reference",
                    "freshness_redaction",
                ],
            },
        },
        "execution_path": {"type": "array", "items": {"type": "string"}},
        "reproduction": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["reproduced", "not_reproduced", "not_attempted"],
                },
                "evidence_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["status", "evidence_ids"],
        },
        "scope": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "direct": {"type": "array", "items": {"type": "string"}},
                "possible": {"type": "array", "items": {"type": "string"}},
                "excluded": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["direct", "possible", "excluded"],
        },
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "hypotheses": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "hypothesis": {"type": "string"},
                    "supporting_provenance_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "contradicting_provenance_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "hypothesis",
                    "supporting_provenance_ids",
                    "contradicting_provenance_ids",
                ],
            },
        },
    },
    "required": [
        "observed_facts",
        "evidence_provenance",
        "execution_path",
        "reproduction",
        "scope",
        "unknowns",
        "hypotheses",
    ],
}

DIAGNOSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decision": {"type": "string", "enum": ["GO", "NO_GO"]},
        "root_cause": {"type": "string"},
        "violated_invariant": {"type": "string"},
        "rejected_alternatives": {"type": "array", "items": {"type": "string"}},
        "change_contract": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "allowed_paths": {"type": "array", "items": {"type": "string"}},
                "allowed_behavior": {"type": "array", "items": {"type": "string"}},
                "forbidden_scope": {"type": "array", "items": {"type": "string"}},
                "preserved_contracts": {"type": "array", "items": {"type": "string"}},
                "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "allowed_paths",
                "allowed_behavior",
                "forbidden_scope",
                "preserved_contracts",
                "acceptance_criteria",
            ],
        },
        "required_tests": {"type": "array", "items": {"type": "string"}},
        "verification_map": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "original_failure_path": {"$ref": "#/$defs/verification_item"},
                "owning_boundary_invariant": {"$ref": "#/$defs/verification_item"},
                "adjacent_negative_or_alternate_path": {
                    "$ref": "#/$defs/verification_item"
                },
            },
            "required": [
                "original_failure_path",
                "owning_boundary_invariant",
                "adjacent_negative_or_alternate_path",
            ],
        },
        "risks": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "decision",
        "root_cause",
        "violated_invariant",
        "rejected_alternatives",
        "change_contract",
        "required_tests",
        "verification_map",
        "risks",
    ],
    "$defs": {
        "verification_item": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "requirement": {"type": "string"},
                "command_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["requirement", "command_ids"],
        }
    },
}

IMPLEMENTATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {"type": "string", "enum": ["completed", "blocked"]},
        "files_changed": {"type": "array", "items": {"type": "string"}},
        "behavioral_change": {"type": "string"},
        "tests_run": {"type": "array", "items": {"type": "string"}},
        "diff_risks": {"type": "array", "items": {"type": "string"}},
        "deviations": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "status",
        "files_changed",
        "behavioral_change",
        "tests_run",
        "diff_risks",
        "deviations",
    ],
}

REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "FAIL"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": ["BLOCKER", "HIGH", "MEDIUM", "LOW"],
                    },
                    "location": {"type": "string"},
                    "evidence": {"type": "string"},
                    "failure_mode": {"type": "string"},
                    "correction": {"type": "string"},
                },
                "required": [
                    "severity",
                    "location",
                    "evidence",
                    "failure_mode",
                    "correction",
                ],
            },
        },
        "contract_compliance": {"type": "array", "items": {"type": "string"}},
        "test_adequacy": {"type": "string"},
        "residual_risks": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "verdict",
        "findings",
        "contract_compliance",
        "test_adequacy",
        "residual_risks",
    ],
}


class PipelineError(RuntimeError):
    """A controlled pipeline failure with a stable exit code."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def require_nonempty_text(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise PipelineError(f"semantic gate failed: {field} must be non-empty", 8)


def require_nonempty_list(value: Any, field: str) -> None:
    if not isinstance(value, list) or not value:
        raise PipelineError(f"semantic gate failed: {field} must be non-empty", 8)


def normalize_repo_path(value: str, *, contract: bool = False) -> str:
    candidate = value.strip() if contract else value
    if not candidate or "\x00" in candidate or "\\" in candidate:
        raise PipelineError(f"unsafe repository path: {value!r}", 8)
    path = PurePosixPath(candidate)
    if path.is_absolute() or candidate.startswith("./"):
        raise PipelineError(f"repository path must be relative and normalized: {value!r}", 8)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise PipelineError(f"repository path contains an unsafe segment: {value!r}", 8)
    if path.parts[0] == ".git":
        raise PipelineError(f"repository metadata is outside the change contract: {value!r}", 8)
    return path.as_posix()


def normalize_path_rules(
    values: Any,
    *,
    field: str,
    require_entries: bool,
) -> list[tuple[str, bool]]:
    if not isinstance(values, list) or (require_entries and not values):
        requirement = "must be a non-empty list" if require_entries else "must be a list"
        raise PipelineError(f"semantic gate failed: {field} {requirement}", 8)
    rules: list[tuple[str, bool]] = []
    for raw in values:
        if not isinstance(raw, str):
            raise PipelineError(f"{field} entries must be strings", 8)
        value = raw.strip()
        recursive = value.endswith("/**") or value.endswith("/")
        base = value[:-3] if value.endswith("/**") else value.rstrip("/")
        if any(token in base for token in ("*", "?", "[", "]")):
            raise PipelineError(
                f"unsupported {field} glob {raw!r}; use an exact path or directory/**",
                8,
            )
        normalized = normalize_repo_path(base, contract=True)
        rules.append((normalized, recursive))
    return rules


def normalize_allowed_paths(values: Any) -> list[tuple[str, bool]]:
    return normalize_path_rules(
        values,
        field="change_contract.allowed_paths",
        require_entries=True,
    )


def normalize_sensitive_paths(values: Any) -> list[tuple[str, bool]]:
    return normalize_path_rules(
        values,
        field="--sensitive-path",
        require_entries=False,
    )


def normalize_protected_deletions(values: Any) -> set[str]:
    if not isinstance(values, list):
        raise PipelineError("--allow-protected-path-delete must be a list", 8)
    paths: set[str] = set()
    for raw in values:
        if not isinstance(raw, str):
            raise PipelineError(
                "--allow-protected-path-delete entries must be strings",
                8,
            )
        value = raw.strip()
        if value.endswith("/") or any(token in value for token in ("*", "?", "[", "]")):
            raise PipelineError(
                "--allow-protected-path-delete requires exact file paths; "
                f"directory or glob rule rejected: {raw!r}",
                8,
            )
        paths.add(normalize_repo_path(value, contract=True))
    return paths


def path_is_allowed(path: str, rules: list[tuple[str, bool]]) -> bool:
    normalized = normalize_repo_path(path)
    return any(
        normalized == base or (recursive and normalized.startswith(base + "/"))
        for base, recursive in rules
    )


def _path_within(path: Path, root: Path) -> bool:
    try:
        return path.is_relative_to(root)
    except ValueError:
        return False


def _check_existing_symlink_target(repo: Path, path: Path, label: str) -> None:
    if not path.is_symlink():
        return
    repo_root = repo.resolve()
    target = path.resolve(strict=False)
    if not _path_within(target, repo_root):
        raise PipelineError(
            f"{label} crosses a symlink outside the repository: "
            f"{path.relative_to(repo).as_posix()} -> {target}",
            9,
        )


def validate_repo_path_symlink_boundary(repo: Path, path: str, label: str) -> None:
    """Reject existing symlink components that resolve outside the repository."""

    normalized = normalize_repo_path(path, contract=True)
    current = repo
    for part in PurePosixPath(normalized).parts:
        current = current / part
        if current.exists() or current.is_symlink():
            _check_existing_symlink_target(repo, current, label)


def validate_allowed_path_boundaries(repo: Path, rules: list[tuple[str, bool]]) -> None:
    for base, recursive in rules:
        validate_repo_path_symlink_boundary(repo, base, "allowed path")
        root = repo / base
        if not recursive or not root.exists() or root.is_symlink():
            continue
        if not root.is_dir():
            continue
        for current_raw, directories, files in os.walk(root, followlinks=False):
            current = Path(current_raw)
            for name in list(directories):
                candidate = current / name
                if candidate.is_symlink():
                    _check_existing_symlink_target(repo, candidate, "allowed path")
                    directories.remove(name)
            for name in files:
                _check_existing_symlink_target(repo, current / name, "allowed path")


def validate_verification_command_boundaries(
    repo: Path,
    commands: list[dict[str, Any]],
) -> None:
    for command in commands:
        for token in command["argv"]:
            normalized = _repo_path_from_token(token)
            if normalized is None:
                continue
            validate_repo_path_symlink_boundary(
                repo,
                normalized,
                f"verification command {command['id']}",
            )


def _repo_path_from_token(token: str, *, require_slash: bool = True) -> str | None:
    if token.startswith("./"):
        token = token[2:]
    if token.startswith("-") or token.startswith("/") or "://" in token:
        return None
    if require_slash and "/" not in token:
        return None
    try:
        return normalize_repo_path(token, contract=True)
    except PipelineError:
        return None


def _protected_entrypoint_reason(state: dict[str, Any], path: str) -> str | None:
    normalized = normalize_repo_path(path, contract=True)
    for field, label in (
        ("ignored_paths", "ignored"),
        ("sensitive_untracked_paths", "sensitive untracked"),
    ):
        for protected in state[field]:
            if normalized == protected or normalized.startswith(protected + "/"):
                return label
    for protected in state.get("metadata_only_paths", set()):
        if normalized == protected or normalized.startswith(protected + "/"):
            return "baseline protected metadata-only"
    return None


def _reject_protected_entrypoint(state: dict[str, Any], path: str) -> None:
    reason = _protected_entrypoint_reason(state, path)
    if reason is not None:
        raise PipelineError(
            f"verification entrypoint is {reason} and cannot be read or hashed: {path}; "
            "move the harness to a visible, non-sensitive tracked path",
            9,
        )


def _entrypoint_fingerprint(
    repo: Path,
    path: str,
    state: dict[str, Any],
    *,
    source: str = "discovered",
    require_existing_file: bool = False,
) -> dict[str, Any]:
    """Fingerprint a harness only after every resolved path passes classification."""

    repo_root = repo.resolve()
    normalized = normalize_repo_path(path, contract=True)
    _reject_protected_entrypoint(state, normalized)
    remaining = list(PurePosixPath(normalized).parts)
    current = repo_root
    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    followed = 0
    while remaining:
        current = current / remaining.pop(0)
        current_path = current.relative_to(repo_root).as_posix()
        _reject_protected_entrypoint(state, current_path)
        if not current.is_symlink():
            continue
        followed += 1
        if followed > 40 or current_path in seen:
            raise PipelineError(f"symlink cycle in verification entrypoint: {path}", 9)
        seen.add(current_path)
        target_text = os.readlink(current)
        target = Path(target_text)
        if not target.is_absolute():
            target = current.parent / target
        lexical_target = Path(os.path.abspath(target))
        if not _path_within(lexical_target, repo_root):
            raise PipelineError(
                f"verification entrypoint crosses a symlink outside the repository: "
                f"{path} -> {lexical_target}",
                9,
            )
        target_repo_path = lexical_target.relative_to(repo_root).as_posix()
        _reject_protected_entrypoint(state, target_repo_path)
        chain.append(
            {
                "link": current_path,
                "target": target_text,
                "resolved": target_repo_path,
            }
        )
        remaining = list(PurePosixPath(target_repo_path).parts) + remaining
        current = repo_root

    resolved_path = current.relative_to(repo_root).as_posix()
    _reject_protected_entrypoint(state, resolved_path)
    resolved_fingerprint = file_fingerprint(current)
    if require_existing_file and resolved_fingerprint.get("kind") != "file":
        raise PipelineError(
            f"explicit verification harness must resolve to an existing regular file: {path}",
            9,
        )
    for link in chain:
        link["fingerprint"] = resolved_fingerprint
    return {
        "path": normalized,
        "source": source,
        "require_existing_file": require_existing_file,
        "entry": file_fingerprint(repo / normalized),
        "resolved_path": resolved_path,
        "resolved_entry": resolved_fingerprint,
        "chain": chain,
    }


def normalize_verification_bindings(
    values: list[str],
    commands: list[dict[str, Any]],
) -> dict[str, set[str]]:
    command_ids = {command["id"] for command in commands}
    user_command_ids = sorted(command_ids - {BUILTIN_DIFF_CHECK_ID})
    bindings: dict[str, set[str]] = {}
    for raw in values:
        command_id: str | None = None
        path = raw
        prefix, separator, suffix = raw.partition(":")
        if separator and re.fullmatch(r"verify-\d+", prefix):
            command_id = prefix
            path = suffix
        elif len(user_command_ids) == 1:
            command_id = user_command_ids[0]
        else:
            raise PipelineError(
                "--bind-verification-path must use verify-N:path when more than one "
                "user verification command is configured",
                9,
            )
        if command_id not in command_ids or command_id == BUILTIN_DIFF_CHECK_ID:
            raise PipelineError(
                f"--bind-verification-path references unknown user command: {command_id}",
                9,
            )
        normalized = normalize_repo_path(path, contract=True)
        bindings.setdefault(command_id, set()).add(normalized)
    return bindings


def discover_verification_entrypoints(
    repo: Path,
    commands: list[dict[str, Any]],
    state: dict[str, Any],
    bound_paths: dict[str, set[str]] | None = None,
) -> dict[str, dict[str, Any]]:
    paths: dict[str, set[str]] = {}
    required: set[tuple[str, str]] = set()
    sources: dict[tuple[str, str], str] = {}

    def add(
        command_id: str,
        path: str,
        *,
        require_existing_file: bool = False,
        source: str = "discovered",
    ) -> None:
        paths.setdefault(command_id, set()).add(path)
        key = (command_id, path)
        if require_existing_file:
            required.add(key)
        if source == "operator-bound" or key not in sources:
            sources[key] = source

    def add_common(command_id: str, candidates: tuple[str, ...]) -> None:
        for candidate in candidates:
            add(command_id, candidate)

    def unwrap(argv: list[str]) -> list[str]:
        if len(argv) >= 3 and Path(argv[0]).name in {"python", "python3"} and argv[1] == "-m":
            return argv[2:]
        if len(argv) >= 3 and Path(argv[0]).name in {"uv", "poetry"} and argv[1] == "run":
            return argv[2:]
        return argv

    if bound_paths:
        for command_id, command_paths in bound_paths.items():
            for path in command_paths:
                add(
                    command_id,
                    path,
                    require_existing_file=True,
                    source="operator-bound",
                )

    for command in commands:
        command_id = command["id"]
        argv = unwrap(command["argv"])
        if not argv:
            continue
        executable = Path(argv[0]).name
        direct = _repo_path_from_token(argv[0])
        if direct is not None:
            add(command_id, direct, require_existing_file=True, source="executable")
        elif executable in {"bash", "sh", "zsh", "python", "python3", "node", "ruby", "perl"}:
            if "-c" in argv[1:]:
                continue
            for token in argv[1:]:
                if token.startswith("-"):
                    continue
                normalized = _repo_path_from_token(token, require_slash=False)
                if normalized is not None:
                    add(
                        command_id,
                        normalized,
                        require_existing_file=True,
                        source="interpreter-script",
                    )
                break
        if executable == "make":
            add_common(command_id, ("GNUmakefile", "makefile", "Makefile"))
            for index, token in enumerate(argv[:-1]):
                if token == "-f":
                    normalized = _repo_path_from_token(argv[index + 1], require_slash=False)
                    if normalized is not None:
                        add(command_id, normalized)
        elif executable in {"npm", "pnpm", "yarn", "bun"}:
            add_common(command_id, ("package.json", "pnpm-workspace.yaml"))
            for index, token in enumerate(argv[:-1]):
                if token == "--prefix":
                    normalized = _repo_path_from_token(argv[index + 1], require_slash=False)
                    if normalized is not None:
                        add(command_id, f"{normalized}/package.json")
        elif executable == "pytest":
            add_common(
                command_id,
                (
                "pyproject.toml",
                "pytest.ini",
                "tox.ini",
                "setup.cfg",
                ),
            )
            for index, token in enumerate(argv[:-1]):
                if token == "-c":
                    normalized = _repo_path_from_token(argv[index + 1], require_slash=False)
                    if normalized is not None:
                        add(command_id, normalized)

    return {
        command_id: {
            path: _entrypoint_fingerprint(
                repo,
                path,
                state,
                source=sources.get((command_id, path), "discovered"),
                require_existing_file=(command_id, path) in required,
            )
            for path in sorted(command_paths)
        }
        for command_id, command_paths in sorted(paths.items())
    }


def validate_verification_entrypoints_unchanged(
    repo: Path,
    baseline: dict[str, dict[str, Any]],
    state: dict[str, Any],
    command_ids: set[str] | None = None,
) -> None:
    changed: list[str] = []
    for command_id, paths in baseline.items():
        if command_ids is not None and command_id not in command_ids:
            continue
        for path, expected in paths.items():
            actual = _entrypoint_fingerprint(
                repo,
                path,
                state,
                source=expected["source"],
                require_existing_file=expected["require_existing_file"],
            )
            if actual != expected:
                changed.append(f"{command_id}:{path}")
    if changed:
        raise PipelineError(
            "verification entrypoint changed after baseline capture; use a "
            "writer-immutable acceptance harness or split the task: "
            + ", ".join(changed),
            9,
        )


def validate_evidence(value: dict[str, Any]) -> None:
    provenance = value.get("evidence_provenance")
    require_nonempty_list(provenance, "evidence_provenance")
    provenance_ids: set[str] = set()
    for index, record in enumerate(provenance):
        if not isinstance(record, dict):
            raise PipelineError(
                f"semantic gate failed: evidence_provenance[{index}] must be an object",
                8,
            )
        for field in (
            "id",
            "claim",
            "kind",
            "source_environment",
            "observed_at",
            "reference",
            "freshness_redaction",
        ):
            require_nonempty_text(record.get(field), f"evidence_provenance[{index}].{field}")
        provenance_id = record["id"].strip()
        if provenance_id in provenance_ids:
            raise PipelineError(
                f"semantic gate failed: duplicate provenance id {provenance_id!r}",
                8,
            )
        provenance_ids.add(provenance_id)

    def validate_references(values: Any, field: str, *, required: bool) -> None:
        if required:
            require_nonempty_list(values, field)
        elif not isinstance(values, list):
            raise PipelineError(f"semantic gate failed: {field} must be a list", 8)
        for reference in values:
            require_nonempty_text(reference, field)
            if reference not in provenance_ids:
                raise PipelineError(
                    f"semantic gate failed: {field} references unknown provenance "
                    f"id {reference!r}",
                    8,
                )

    observed_facts = value.get("observed_facts")
    require_nonempty_list(observed_facts, "observed_facts")
    fact_ids: set[str] = set()
    for index, fact in enumerate(observed_facts):
        if not isinstance(fact, dict):
            raise PipelineError(
                f"semantic gate failed: observed_facts[{index}] must be an object",
                8,
            )
        require_nonempty_text(fact.get("id"), f"observed_facts[{index}].id")
        require_nonempty_text(
            fact.get("statement"),
            f"observed_facts[{index}].statement",
        )
        fact_id = fact["id"].strip()
        if fact_id in fact_ids:
            raise PipelineError(f"semantic gate failed: duplicate fact id {fact_id!r}", 8)
        fact_ids.add(fact_id)
        validate_references(
            fact.get("provenance_ids"),
            f"observed_facts[{index}].provenance_ids",
            required=True,
        )

    reproduction = value.get("reproduction", {})
    evidence_ids = reproduction.get("evidence_ids")
    validate_references(
        evidence_ids,
        "reproduction.evidence_ids",
        required=reproduction.get("status") == "reproduced",
    )

    hypotheses = value.get("hypotheses")
    if not isinstance(hypotheses, list):
        raise PipelineError("semantic gate failed: hypotheses must be a list", 8)
    for index, hypothesis in enumerate(hypotheses):
        if not isinstance(hypothesis, dict):
            raise PipelineError(
                f"semantic gate failed: hypotheses[{index}] must be an object",
                8,
            )
        validate_references(
            hypothesis.get("supporting_provenance_ids"),
            f"hypotheses[{index}].supporting_provenance_ids",
            required=False,
        )
        validate_references(
            hypothesis.get("contradicting_provenance_ids"),
            f"hypotheses[{index}].contradicting_provenance_ids",
            required=False,
        )


def validate_diagnosis(
    value: dict[str, Any],
    available_command_ids: set[str] | None = None,
) -> list[tuple[str, bool]]:
    decision = value.get("decision")
    if decision != "GO":
        return []
    require_nonempty_text(value.get("root_cause"), "root_cause")
    require_nonempty_text(value.get("violated_invariant"), "violated_invariant")
    contract = value.get("change_contract")
    if not isinstance(contract, dict):
        raise PipelineError("semantic gate failed: GO requires a change_contract", 8)
    rules = normalize_allowed_paths(contract.get("allowed_paths"))
    require_nonempty_list(contract.get("allowed_behavior"), "change_contract.allowed_behavior")
    require_nonempty_list(
        contract.get("acceptance_criteria"),
        "change_contract.acceptance_criteria",
    )
    require_nonempty_list(value.get("required_tests"), "required_tests")
    verification_map = value.get("verification_map")
    if not isinstance(verification_map, dict):
        raise PipelineError("semantic gate failed: GO requires a verification_map", 8)
    referenced_command_ids: set[str] = set()
    for field in (
        "original_failure_path",
        "owning_boundary_invariant",
        "adjacent_negative_or_alternate_path",
    ):
        item = verification_map.get(field)
        if not isinstance(item, dict):
            raise PipelineError(
                f"semantic gate failed: verification_map.{field} must be an object",
                8,
            )
        require_nonempty_text(
            item.get("requirement"),
            f"verification_map.{field}.requirement",
        )
        command_ids = item.get("command_ids")
        require_nonempty_list(
            command_ids,
            f"verification_map.{field}.command_ids",
        )
        if not all(isinstance(command_id, str) and command_id.strip() for command_id in command_ids):
            raise PipelineError(
                f"semantic gate failed: verification_map.{field}.command_ids "
                "must contain non-empty strings",
                8,
            )
        referenced_command_ids.update(command_ids)
        if available_command_ids is not None:
            unknown = sorted(set(command_ids) - available_command_ids)
            if unknown:
                raise PipelineError(
                    f"semantic gate failed: verification_map.{field} references "
                    "unknown command ids: " + ", ".join(unknown),
                    8,
                )
    if (
        available_command_ids is not None
        and not (referenced_command_ids - {BUILTIN_DIFF_CHECK_ID})
    ):
        raise PipelineError(
            "semantic gate failed: verification_map must reference at least one "
            "user-supplied verification command; verify-0 only checks diff formatting",
            8,
        )
    return rules


def validate_implementation(
    value: dict[str, Any],
    allowed_rules: list[tuple[str, bool]],
    actual_paths: set[str],
) -> None:
    if value.get("status") != "completed":
        if actual_paths:
            raise PipelineError(
                "blocked implementation changed repository paths: "
                + ", ".join(sorted(actual_paths)),
                6,
            )
        return
    require_nonempty_text(value.get("behavioral_change"), "behavioral_change")
    require_nonempty_list(value.get("files_changed"), "files_changed")
    deviations = value.get("deviations")
    if deviations:
        raise PipelineError(
            "semantic gate failed: completed implementation contains unapproved deviations",
            8,
        )
    reported_paths: list[str] = []
    for raw in value["files_changed"]:
        if not isinstance(raw, str):
            raise PipelineError("files_changed entries must be strings", 8)
        path = normalize_repo_path(raw, contract=True)
        reported_paths.append(path)
    outside = [path for path in reported_paths if not path_is_allowed(path, allowed_rules)]
    if outside:
        raise PipelineError(
            "semantic gate failed: implementation reported paths outside the contract: "
            + ", ".join(outside),
            8,
        )
    reported = set(reported_paths)
    if reported != actual_paths:
        missing = sorted(actual_paths - reported)
        extra = sorted(reported - actual_paths)
        details = []
        if missing:
            details.append("unreported actual paths=" + ", ".join(missing))
        if extra:
            details.append("reported but unchanged paths=" + ", ".join(extra))
        raise PipelineError(
            "semantic gate failed: files_changed does not equal the actual stage delta: "
            + "; ".join(details),
            8,
        )


def validate_review(value: dict[str, Any]) -> None:
    findings = value.get("findings")
    if not isinstance(findings, list):
        raise PipelineError("semantic gate failed: review findings must be a list", 8)
    hard = [
        finding
        for finding in findings
        if isinstance(finding, dict) and finding.get("severity") in HARD_REVIEW_SEVERITIES
    ]
    if value.get("verdict") == "PASS" and hard:
        raise PipelineError(
            "semantic gate failed: PASS review contains BLOCKER or HIGH findings",
            8,
        )
    if value.get("verdict") == "FAIL" and not findings:
        raise PipelineError("semantic gate failed: FAIL review must include findings", 8)
    require_nonempty_list(value.get("contract_compliance"), "contract_compliance")
    require_nonempty_text(value.get("test_adequacy"), "test_adequacy")


def run_bytes(argv: list[str], cwd: Path) -> bytes:
    result = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace")
        raise PipelineError(
            f"command failed ({result.returncode}): {shlex.join(argv)}\n{message}",
        )
    return result.stdout


def run_text_exact(argv: list[str], cwd: Path) -> str:
    return run_bytes(argv, cwd).decode("utf-8", errors="backslashreplace")


def git_status_raw(repo: Path) -> bytes:
    return run_bytes(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        repo,
    )


def ensure_supported_repository_topology(repo: Path) -> None:
    stage_entries = run_bytes(["git", "ls-files", "--stage", "-z"], repo)
    gitlinks: list[str] = []
    for entry in stage_entries.split(b"\x00"):
        if not entry:
            continue
        if entry.startswith(b"160000 "):
            _, _, raw_path = entry.partition(b"\t")
            gitlinks.append(os.fsdecode(raw_path))

    nested: list[str] = []
    root_git = repo / ".git"
    for current_raw, directories, files in os.walk(repo, followlinks=False):
        current = Path(current_raw)
        candidate = current / ".git"
        if candidate == root_git:
            if ".git" in directories:
                directories.remove(".git")
            continue
        if ".git" in directories:
            nested.append(str(candidate.relative_to(repo)))
            directories.remove(".git")
        if ".git" in files:
            nested.append(str(candidate.relative_to(repo)))

    if gitlinks or nested:
        details = []
        if gitlinks:
            details.append("gitlinks=" + ", ".join(sorted(gitlinks)))
        if nested:
            details.append("nested repositories=" + ", ".join(sorted(nested)))
        raise PipelineError(
            "submodules and nested Git repositories are not supported by the strict "
            "snapshot gate; use an isolated flattened worktree or a repository-specific "
            "external pipeline (" + "; ".join(details) + ")",
            9,
        )


def optional_git_bytes(argv: list[str], repo: Path) -> bytes:
    result = subprocess.run(
        argv,
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode in (0, 1):
        return result.stdout
    message = result.stderr.decode("utf-8", errors="replace")
    raise PipelineError(
        f"command failed ({result.returncode}): {shlex.join(argv)}\n{message}",
    )


def tree_fingerprint(root: Path) -> dict[str, Any]:
    def metadata_fingerprint(path: Path) -> dict[str, Any]:
        try:
            info = path.lstat()
        except FileNotFoundError:
            return {"kind": "missing"}
        if path.is_dir() and not path.is_symlink():
            return {"kind": "directory", "mode": info.st_mode}
        return file_fingerprint(path)

    if not root.exists() and not root.is_symlink():
        return {".": {"kind": "missing"}}
    if not root.is_dir() or root.is_symlink():
        return {".": file_fingerprint(root)}
    values: dict[str, Any] = {".": metadata_fingerprint(root)}
    for path in sorted(root.rglob("*")):
        values[path.relative_to(root).as_posix()] = metadata_fingerprint(path)
    return values


def git_control_state(repo: Path) -> dict[str, Any]:
    common_raw = run_checked(["git", "rev-parse", "--git-common-dir"], repo)
    common_dir = Path(common_raw)
    if not common_dir.is_absolute():
        common_dir = (repo / common_dir).resolve()
    git_dir_raw = run_checked(["git", "rev-parse", "--git-dir"], repo)
    git_dir = Path(git_dir_raw)
    if not git_dir.is_absolute():
        git_dir = (repo / git_dir).resolve()
    operation_files = (
        "ORIG_HEAD",
        "MERGE_HEAD",
        "CHERRY_PICK_HEAD",
        "REVERT_HEAD",
        "REBASE_HEAD",
        "BISECT_LOG",
        "AUTO_MERGE",
    )
    gitfile_path = repo / ".git"
    gitfile_state = (
        {"kind": "directory", "mode": gitfile_path.lstat().st_mode}
        if gitfile_path.is_dir() and not gitfile_path.is_symlink()
        else file_fingerprint(gitfile_path)
    )
    return {
        "head": run_bytes(["git", "rev-parse", "--verify", "HEAD"], repo),
        "symbolic_head": optional_git_bytes(["git", "symbolic-ref", "-q", "HEAD"], repo),
        "refs": run_bytes(
            [
                "git",
                "for-each-ref",
                "--sort=refname",
                "--format=%(refname)%00%(objectname)%00%(symref)",
            ],
            repo,
        ),
        "config": file_fingerprint(common_dir / "config"),
        "config_worktree": file_fingerprint(git_dir / "config.worktree"),
        "gitfile": gitfile_state,
        "hooks": tree_fingerprint(common_dir / "hooks"),
        "info": tree_fingerprint(common_dir / "info"),
        "logs": tree_fingerprint(git_dir / "logs"),
        "operation_files": {
            name: file_fingerprint(git_dir / name) for name in operation_files
        },
        "sequencer": tree_fingerprint(git_dir / "sequencer"),
        "rebase_apply": tree_fingerprint(git_dir / "rebase-apply"),
        "rebase_merge": tree_fingerprint(git_dir / "rebase-merge"),
        "alternates": file_fingerprint(common_dir / "objects" / "info" / "alternates"),
    }


def parse_status_paths(raw: bytes) -> set[str]:
    fields = raw.split(b"\x00")
    paths: set[str] = set()
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        if len(entry) < 4 or entry[2:3] != b" ":
            raise PipelineError(f"could not parse git status entry: {entry!r}")
        status = entry[:2].decode("ascii", errors="strict")
        paths.add(normalize_repo_path(os.fsdecode(entry[3:])))
        if "R" in status or "C" in status:
            if index >= len(fields) or not fields[index]:
                raise PipelineError("could not parse renamed/copied git status entry")
            paths.add(normalize_repo_path(os.fsdecode(fields[index])))
            index += 1
    return paths


def file_fingerprint(path: Path) -> dict[str, Any]:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"kind": "missing"}
    base: dict[str, Any] = {"mode": info.st_mode}
    if path.is_symlink():
        target = os.readlink(path)
        base.update(
            kind="symlink",
            target=target,
            sha256=hashlib.sha256(os.fsencode(target)).hexdigest(),
        )
        return base
    if path.is_file():
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        base.update(kind="file", size=info.st_size, sha256=digest.hexdigest())
        return base
    if path.is_dir():
        nested = subprocess.run(
            [
                "git",
                "-C",
                str(path),
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        head = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        payload = head.stdout + b"\x00" + nested.stdout
        base.update(kind="directory", sha256=hashlib.sha256(payload).hexdigest())
        return base
    base.update(kind="other", size=info.st_size)
    return base


def file_metadata_fingerprint(path: Path) -> dict[str, Any]:
    """Detect ordinary ignored-path mutation without reading file contents."""

    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"kind": "missing"}
    base: dict[str, Any] = {
        "mode": info.st_mode,
        "size": info.st_size,
        "mtime_ns": info.st_mtime_ns,
        "ctime_ns": info.st_ctime_ns,
    }
    if path.is_symlink():
        base.update(kind="symlink-metadata")
    elif path.is_file():
        base.update(kind="file-metadata")
    elif path.is_dir():
        base.update(kind="directory-metadata")
    else:
        base.update(kind="other-metadata")
    return base


def list_git_paths(
    repo: Path,
    argv: list[str],
    *,
    max_paths: int | None = None,
    budget_name: str = "path",
) -> set[str]:
    """Stream NUL-delimited Git paths and fail closed before an unbounded manifest."""

    process = subprocess.Popen(
        ["git", *argv],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    pending = b""
    paths: set[str] = set()
    try:
        while True:
            chunk = process.stdout.read(64 * 1024)
            if not chunk:
                break
            pending += chunk
            items = pending.split(b"\x00")
            pending = items.pop()
            for item in items:
                if not item:
                    continue
                paths.add(normalize_repo_path(os.fsdecode(item)))
                if max_paths is not None and len(paths) > max_paths:
                    process.kill()
                    process.communicate()
                    raise PipelineError(
                        f"{budget_name} path budget exceeded ({max_paths}); "
                        "raise the explicit budget only after inspecting repository caches",
                        9,
                    )
        if pending:
            paths.add(normalize_repo_path(os.fsdecode(pending)))
        stderr = process.stderr.read() if process.stderr is not None else b""
        return_code = process.wait()
        if return_code != 0:
            raise PipelineError(
                f"git path enumeration failed ({return_code}): "
                + stderr.decode("utf-8", errors="backslashreplace").strip(),
            )
        if max_paths is not None and len(paths) > max_paths:
            raise PipelineError(
                f"{budget_name} path budget exceeded ({max_paths}); "
                "raise the explicit budget only after inspecting repository caches",
                9,
            )
        return paths
    except BaseException:
        if process.poll() is None:
            process.kill()
            process.communicate()
        raise
    finally:
        process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()


def is_sensitive_repo_path(
    path: str,
    custom_rules: list[tuple[str, bool]] | None = None,
    *,
    redact_dotfiles: bool = False,
) -> bool:
    """Return whether an untracked path must remain metadata-only."""

    parts = tuple(part.lower() for part in PurePosixPath(path).parts)
    if custom_rules and path_is_allowed(path, custom_rules):
        return True
    if redact_dotfiles and any(part.startswith(".") for part in parts):
        return True
    if any(
        part in SENSITIVE_PATH_PARTS
        or part.startswith(".env")
        or re.search(
            r"(?:^|[._-])(credential|credentials|key|keys|password|passwd|secret|secrets|token)(?:[._-]|$)",
            part,
        )
        for part in parts
    ):
        return True
    name = parts[-1] if parts else ""
    if name in SENSITIVE_FILE_NAMES or PurePosixPath(name).suffix in SENSITIVE_FILE_SUFFIXES:
        return True
    return False


def capture_repo_state(
    repo: Path,
    *,
    max_ignored_paths: int = DEFAULT_MAX_IGNORED_PATHS,
    sensitive_rules: list[tuple[str, bool]] | None = None,
    redact_untracked_dotfiles: bool = False,
    metadata_only_floor: set[str] | None = None,
    check_topology: bool = True,
) -> dict[str, Any]:
    if check_topology:
        ensure_supported_repository_topology(repo)
    if max_ignored_paths <= 0:
        raise PipelineError("ignored path budget must be positive", 9)
    status_raw = git_status_raw(repo)
    tracked_paths = list_git_paths(
        repo,
        ["ls-files", "-z", "--cached"],
    )
    untracked_paths = list_git_paths(
        repo,
        ["ls-files", "-z", "--others", "--exclude-standard"],
    )
    sensitive_untracked_paths = {
        path
        for path in untracked_paths
        if is_sensitive_repo_path(
            path,
            sensitive_rules,
            redact_dotfiles=redact_untracked_dotfiles,
        )
    }
    visible_paths = tracked_paths | untracked_paths
    ignored_paths = list_git_paths(
        repo,
        ["ls-files", "-z", "--others", "--ignored", "--exclude-standard"],
        max_paths=max_ignored_paths,
        budget_name="ignored",
    ) - visible_paths
    metadata_only_paths = (
        ignored_paths
        | sensitive_untracked_paths
        | set(metadata_only_floor or set())
    )
    content_paths = (tracked_paths | untracked_paths) - metadata_only_paths
    present_metadata_only_paths = metadata_only_paths & (visible_paths | ignored_paths)
    worktree = {path: file_fingerprint(repo / path) for path in content_paths}
    worktree.update(
        {
            path: file_metadata_fingerprint(repo / path)
            for path in present_metadata_only_paths
        }
    )
    return {
        "status_raw": status_raw,
        "paths": visible_paths | ignored_paths,
        "ignored_paths": ignored_paths,
        "untracked_paths": untracked_paths,
        "sensitive_untracked_paths": sensitive_untracked_paths,
        "metadata_only_paths": metadata_only_paths,
        "worktree": worktree,
        "index": run_bytes(["git", "ls-files", "--stage", "-v", "-z"], repo),
        "git_control": git_control_state(repo),
    }


def changed_paths_between(before: dict[str, Any], after: dict[str, Any]) -> set[str]:
    paths = before["paths"] | after["paths"]
    missing = {"kind": "missing"}
    return {
        path
        for path in paths
        if before["worktree"].get(path, missing) != after["worktree"].get(path, missing)
    }


def assert_repo_unchanged(
    before: dict[str, Any],
    after: dict[str, Any],
    stage: str,
) -> None:
    paths = sorted(changed_paths_between(before, after))
    index_changed = before["index"] != after["index"]
    control_changed = before["git_control"] != after["git_control"]
    if paths or index_changed or control_changed:
        detail = []
        if paths:
            detail.append("paths=" + ", ".join(paths))
        if index_changed:
            detail.append("Git index changed")
        if control_changed:
            detail.append("Git control metadata changed")
        raise PipelineError(
            f"{stage} was required to be repository-read-only but changed state: "
            + "; ".join(detail),
            6,
        )


def metadata_manifest(
    state: dict[str, Any],
    paths: set[str],
) -> list[dict[str, Any]]:
    missing = {"kind": "missing"}
    return [
        {"path": path, **state["worktree"].get(path, missing)}
        for path in sorted(paths)
    ]


def protected_metadata_paths(state: dict[str, Any]) -> set[str]:
    """Return every path whose content is forbidden to the current run."""

    return (
        set(state.get("metadata_only_paths", set()))
        | set(state["ignored_paths"])
        | set(state["sensitive_untracked_paths"])
    )


def intrinsic_protected_paths(state: dict[str, Any]) -> set[str]:
    """Return paths protected by the current snapshot without its baseline floor."""

    return set(state["ignored_paths"]) | set(state["sensitive_untracked_paths"])


def state_untracked_manifests(
    state: dict[str, Any],
    only_paths: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected = set(state["untracked_paths"])
    if only_paths is not None:
        selected &= only_paths
    metadata_only = selected & protected_metadata_paths(state)
    ordinary = selected - metadata_only
    return metadata_manifest(state, ordinary), metadata_manifest(state, metadata_only)


def stream_command_artifact(
    argv: list[str],
    *,
    repo: Path,
    destination: Path,
    max_bytes: int,
    timeout_seconds: float,
    append: bool = False,
    accepted_exit_codes: set[int] | None = None,
) -> int:
    """Stream stdout to one private artifact and fail before crossing max_bytes."""

    if max_bytes < 0:
        raise PipelineError("artifact byte limit must not be negative", 9)
    if timeout_seconds <= 0:
        raise PipelineError("artifact command timeout must be positive", 9)
    accepted = accepted_exit_codes or {0}
    starting_size = destination.stat().st_size if append and destination.exists() else 0
    flags = os.O_WRONLY | os.O_CREAT | (os.O_APPEND if append else os.O_TRUNC)
    descriptor = os.open(destination, flags, 0o600)
    try:
        process = subprocess.Popen(
            argv,
            cwd=repo,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            start_new_session=True,
        )
    except BaseException:
        os.close(descriptor)
        raise
    assert process.stdout is not None and process.stderr is not None
    selector: selectors.BaseSelector | None = None
    descriptor_open = True
    stderr = OutputTailBuffer(64 * 1024)
    written = 0
    exceeded = False
    timed_out = False
    output_drain_timed_out = False
    command_deadline = time.monotonic() + timeout_seconds
    drain_deadline: float | None = None

    def restore_artifact() -> None:
        try:
            os.truncate(destination, starting_size)
        except OSError as exc:
            raise PipelineError(
                f"could not restore partial artifact after capture failure: {destination}",
                9,
            ) from exc

    try:
        selector = selectors.DefaultSelector()
        artifact_handle = os.fdopen(
            descriptor,
            "ab" if append else "wb",
            buffering=0,
        )
        descriptor_open = False
        with artifact_handle as artifact:
            for stream, label in ((process.stdout, "stdout"), (process.stderr, "stderr")):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, label)
            while selector.get_map() or process.poll() is None:
                now = time.monotonic()
                if process.poll() is None and now >= command_deadline:
                    timed_out = True
                    if process_group_exists(process.pid):
                        terminate_process_group(process)
                    else:
                        process.kill()
                        process.wait(timeout=2)
                    break
                if (
                    process.poll() is not None
                    and selector.get_map()
                    and drain_deadline is None
                ):
                    if process_group_exists(process.pid):
                        terminate_process_group(process)
                    drain_deadline = (
                        time.monotonic() + PROCESS_OUTPUT_DRAIN_TIMEOUT_SECONDS
                    )
                if drain_deadline is not None and now >= drain_deadline:
                    output_drain_timed_out = True
                    break
                if not selector.get_map():
                    time.sleep(min(0.05, max(0.0, command_deadline - now)))
                    continue
                active_deadline = (
                    min(command_deadline, drain_deadline)
                    if drain_deadline is not None
                    else command_deadline
                )
                wait = max(0.0, min(0.1, active_deadline - time.monotonic()))
                for key, mask in selector.select(wait):
                    if not mask & selectors.EVENT_READ:
                        continue
                    stream = key.fileobj
                    try:
                        chunk = os.read(stream.fileno(), OUTPUT_READ_CHUNK_BYTES)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        close_selector_stream(selector, stream)
                        continue
                    if key.data == "stderr":
                        stderr.append(chunk)
                        continue
                    remaining = max_bytes - written
                    if len(chunk) > remaining:
                        if remaining > 0:
                            artifact.write(chunk[:remaining])
                            written += remaining
                        exceeded = True
                        terminate_process_group(process)
                        break
                    artifact.write(chunk)
                    written += len(chunk)
                if exceeded:
                    break
    except BaseException as exc:
        cleanup_error: BaseException | None = None
        try:
            if process_group_exists(process.pid):
                terminate_process_group(process)
            elif process.poll() is None:
                process.kill()
                process.wait(timeout=2)
        except BaseException as caught_cleanup_error:
            cleanup_error = caught_cleanup_error
        restore_error: PipelineError | None = None
        try:
            restore_artifact()
        except PipelineError as caught_restore_error:
            restore_error = caught_restore_error
        if restore_error is not None:
            raise restore_error from exc
        if cleanup_error is not None:
            raise PipelineError(
                f"artifact command cleanup failed: {shlex.join(argv)}",
                9,
            ) from cleanup_error
        raise
    finally:
        if descriptor_open:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if selector is not None:
            close_selector_stream(selector, process.stdout)
            close_selector_stream(selector, process.stderr)
            selector.close()
        else:
            for stream in (process.stdout, process.stderr):
                try:
                    stream.close()
                except OSError:
                    pass

    if timed_out or output_drain_timed_out or exceeded:
        restore_artifact()
        if timed_out:
            detail = f"artifact command timed out after {timeout_seconds}s"
        elif output_drain_timed_out:
            detail = "artifact command output pipe remained open after parent exit"
        else:
            detail = "artifact byte budget was exceeded"
        raise PipelineError(
            f"{detail} while running {shlex.join(argv)}; Delta is incomplete and "
            "automated review was refused",
            9,
        )
    if process.returncode not in accepted:
        restore_artifact()
        raise PipelineError(
            f"could not capture artifact with {shlex.join(argv)} "
            f"(exit {process.returncode}): {stderr.text().strip()}",
        )
    return written


def remaining_deadline_seconds(deadline: float, context: str) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise PipelineError(f"{context} deadline expired before capture completed", 9)
    return remaining


def read_artifact_excerpt(
    path: Path,
    max_bytes: int = MAX_DELTA_PATCH_EXCERPT_BYTES,
) -> tuple[str, bool]:
    if max_bytes <= 0:
        raise PipelineError("artifact excerpt byte limit must be positive", 9)
    size = path.stat().st_size
    with path.open("rb") as artifact:
        if size <= max_bytes:
            raw = artifact.read(max_bytes)
            return raw.decode("utf-8", errors="replace"), False
        head_size = max_bytes // 2
        tail_size = max_bytes - head_size
        head = artifact.read(head_size)
        artifact.seek(-tail_size, os.SEEK_END)
        tail = artifact.read(tail_size)
    marker = (
        f"\n... PATCH PROMPT EXCERPT OMITTED {size - max_bytes} BYTES; "
        "COMPLETE PRIVATE ARTIFACT RETAINED ...\n"
    )
    return (
        head.decode("utf-8", errors="replace")
        + marker
        + tail.decode("utf-8", errors="replace"),
        True,
    )


def stream_untracked_patch(
    repo: Path,
    manifest: list[dict[str, Any]],
    destination: Path,
    max_bytes: int,
    deadline: float,
) -> int:
    destination.write_bytes(b"")
    total = 0
    for entry in manifest:
        if str(entry.get("kind", "")).endswith("-metadata"):
            raise PipelineError("refusing to patch a metadata-only untracked path", 9)
        path = entry["path"]
        try:
            written = stream_command_artifact(
                [
                    "git",
                    "diff",
                    "--no-index",
                    "--binary",
                    "--full-index",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--",
                    os.devnull,
                    path,
                ],
                repo=repo,
                destination=destination,
                max_bytes=max_bytes - total,
                timeout_seconds=remaining_deadline_seconds(
                    deadline,
                    "untracked Delta capture",
                ),
                append=True,
                accepted_exit_codes={0, 1},
            )
        except PipelineError as exc:
            raise PipelineError(
                f"could not fully capture untracked delta for {path}: {exc}",
                exc.exit_code,
            ) from exc
        total += written
    return total


def capture_delta(
    repo: Path,
    run_dir: Path,
    prefix: str,
    introduced_paths: set[str],
    current: dict[str, Any],
    ignored_changed_paths: set[str],
    redacted_untracked_paths: set[str],
    max_delta_bytes: int = DEFAULT_MAX_DELTA_BYTES,
    max_untracked_patch_bytes: int = DEFAULT_MAX_UNTRACKED_PATCH_BYTES,
    timeout_seconds: int = 3600,
) -> dict[str, Any]:
    if max_delta_bytes <= 0 or max_untracked_patch_bytes <= 0:
        raise PipelineError("Delta byte limits must be positive", 9)
    capture_deadline = time.monotonic() + timeout_seconds
    status_raw = current["status_raw"]
    status_text = status_raw.decode("utf-8", errors="backslashreplace").replace("\x00", "\n")
    visible_manifest, _ = state_untracked_manifests(
        current,
        introduced_paths,
    )
    ignored_manifest = metadata_manifest(current, ignored_changed_paths)
    redacted_manifest = metadata_manifest(current, redacted_untracked_paths)
    patch_specs = (
        (
            "staged_patch",
            run_dir / f"{prefix}-staged.patch",
            [
                "git", "diff", "--cached", "--binary", "--full-index",
                "--no-ext-diff", "--no-textconv",
            ],
        ),
        (
            "unstaged_patch",
            run_dir / f"{prefix}-unstaged.patch",
            [
                "git", "diff", "--binary", "--full-index", "--no-ext-diff",
                "--no-textconv",
            ],
        ),
        (
            "head_to_worktree_patch",
            run_dir / f"{prefix}-head-to-worktree.patch",
            [
                "git", "diff", "HEAD", "--binary", "--full-index",
                "--no-ext-diff", "--no-textconv",
            ],
        ),
    )
    delta_bytes = 0
    patch_text: dict[str, str] = {}
    patch_prompt_state: dict[str, dict[str, Any]] = {}
    for key, path, command in patch_specs:
        written = stream_command_artifact(
            command,
            repo=repo,
            destination=path,
            max_bytes=max_delta_bytes - delta_bytes,
            timeout_seconds=remaining_deadline_seconds(
                capture_deadline,
                "Delta capture",
            ),
        )
        delta_bytes += written
        excerpt, truncated = read_artifact_excerpt(path)
        patch_text[key] = excerpt
        patch_prompt_state[key] = {
            "artifact_bytes": written,
            "excerpt_utf8_bytes": len(excerpt.encode("utf-8")),
            "truncated": truncated,
        }
    untracked_path = run_dir / f"{prefix}-untracked.patch"
    untracked_limit = min(
        max_untracked_patch_bytes,
        max_delta_bytes - delta_bytes,
    )
    untracked_bytes = stream_untracked_patch(
        repo,
        visible_manifest,
        untracked_path,
        untracked_limit,
        capture_deadline,
    )
    delta_bytes += untracked_bytes
    untracked, untracked_truncated = read_artifact_excerpt(untracked_path)
    patch_prompt_state["untracked_patch"] = {
        "artifact_bytes": untracked_bytes,
        "excerpt_utf8_bytes": len(untracked.encode("utf-8")),
        "truncated": untracked_truncated,
    }
    (run_dir / f"{prefix}-status.txt").write_text(status_text, encoding="utf-8")
    write_json(run_dir / f"{prefix}-untracked.json", visible_manifest)
    write_json(run_dir / f"{prefix}-ignored-metadata.json", ignored_manifest)
    write_json(run_dir / f"{prefix}-redacted-untracked-metadata.json", redacted_manifest)
    summary = {
        "artifacts": {
            "status": f"{prefix}-status.txt",
            "staged_patch": f"{prefix}-staged.patch",
            "unstaged_patch": f"{prefix}-unstaged.patch",
            "head_to_worktree_patch": f"{prefix}-head-to-worktree.patch",
            "untracked_patch": f"{prefix}-untracked.patch",
            "untracked_manifest": f"{prefix}-untracked.json",
            "ignored_metadata": f"{prefix}-ignored-metadata.json",
            "redacted_untracked_metadata": f"{prefix}-redacted-untracked-metadata.json",
        },
        "status": status_text,
        "changed_paths": sorted(introduced_paths),
        "introduced_paths": sorted(introduced_paths),
        "untracked": visible_manifest,
        "visible_untracked": visible_manifest,
        "ignored_metadata": ignored_manifest,
        "redacted_untracked_metadata": redacted_manifest,
        "delta_bytes": delta_bytes,
        "untracked_patch_bytes": untracked_bytes,
        "delta_complete": True,
        "delta_schema_version": 1,
        "patch_prompt_excerpts": patch_prompt_state,
        "staged_patch": patch_text["staged_patch"],
        "unstaged_patch": patch_text["unstaged_patch"],
        "head_to_worktree_patch": patch_text["head_to_worktree_patch"],
        "untracked_patch": untracked,
    }
    return summary


def compact_delta(delta: dict[str, Any]) -> str:
    payload = json.dumps(delta, ensure_ascii=False, indent=2)
    if len(payload) <= MAX_DELTA_PROMPT_CHARS:
        return payload
    head = payload[: MAX_DELTA_PROMPT_CHARS // 2]
    tail = payload[-MAX_DELTA_PROMPT_CHARS // 2 :]
    return (
        head
        + "\n... DELTA TRUNCATED IN PROMPT; FULL REPOSITORY STATE REMAINS INSPECTABLE ...\n"
        + tail
    )


def validate_protected_changes(
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
    introduced_paths: set[str],
    allowed_deletions: set[str],
) -> set[str]:
    protected_paths = protected_metadata_paths(baseline) | protected_metadata_paths(current)
    changed_protected = introduced_paths & protected_paths
    missing = {"kind": "missing"}
    approved_deletions: set[str] = set()
    violations: list[str] = []
    for path in sorted(changed_protected):
        existed = baseline["worktree"].get(path, missing) != missing
        deleted = current["worktree"].get(path, missing) == missing
        if path in allowed_deletions and existed and deleted:
            approved_deletions.add(path)
        else:
            violations.append(path)
    if violations:
        raise PipelineError(
            "writer changed protected metadata-only paths; content cannot be "
            "independently reviewed: " + ", ".join(violations),
            9,
        )
    unused = sorted(allowed_deletions - approved_deletions)
    if unused:
        raise PipelineError(
            "protected deletion authorization was unused or did not resolve to an "
            "existing protected path deleted by the writer: " + ", ".join(unused),
            9,
        )
    if allowed_deletions and introduced_paths != approved_deletions:
        mixed = sorted(introduced_paths - approved_deletions)
        raise PipelineError(
            "protected deletion authorization requires a deletion-only run; "
            "ordinary repository changes must be performed in a separate run: "
            + ", ".join(mixed),
            9,
        )
    return approved_deletions


def validate_protected_deletion_preflight(
    *,
    repo: Path,
    baseline: dict[str, Any],
    allowed_rules: list[tuple[str, bool]],
    allowed_deletions: set[str],
) -> None:
    missing = {"kind": "missing"}
    protected_paths = protected_metadata_paths(baseline)
    invalid: list[str] = []
    for path in sorted(allowed_deletions):
        validate_repo_path_symlink_boundary(repo, path, "protected deletion")
        fingerprint = baseline["worktree"].get(path, missing)
        if fingerprint == missing:
            invalid.append(f"{path} (not present in baseline)")
            continue
        if path not in protected_paths:
            invalid.append(f"{path} (not a baseline protected path)")
            continue
        if fingerprint.get("kind") == "directory-metadata":
            invalid.append(f"{path} (directories are not valid exact deletion targets)")
            continue
        if not path_is_allowed(path, allowed_rules):
            invalid.append(f"{path} (not permitted by diagnosis allowed_paths)")
    if invalid:
        raise PipelineError(
            "protected deletion preflight failed before writer execution: "
            + ", ".join(invalid),
            9,
        )


def validate_protected_deletion_runtime_options(
    *,
    allowed_deletions: set[str],
    allow_dirty: bool,
    max_repair_cycles: int,
) -> None:
    if not allowed_deletions:
        return
    if allow_dirty:
        raise PipelineError(
            "protected deletion mode requires a clean worktree; --allow-dirty is not supported",
            9,
        )
    if max_repair_cycles != 0:
        raise PipelineError(
            "protected deletion mode is deletion-only and does not support repair cycles; "
            "set --max-repair-cycles 0",
            9,
        )


def completion_outcome(protected_deletions: list[str]) -> tuple[str, int]:
    if protected_deletions:
        return "HUMAN_REVIEW_REQUIRED", HUMAN_REVIEW_REQUIRED_EXIT
    return "PASS", 0


def enforce_repository_contract(
    *,
    repo: Path,
    run_dir: Path,
    prefix: str,
    baseline: dict[str, Any],
    allowed_rules: list[tuple[str, bool]],
    max_ignored_paths: int = DEFAULT_MAX_IGNORED_PATHS,
    sensitive_rules: list[tuple[str, bool]] | None = None,
    redact_untracked_dotfiles: bool = False,
    check_topology: bool = True,
    allowed_protected_deletions: set[str] | None = None,
    max_delta_bytes: int = DEFAULT_MAX_DELTA_BYTES,
    max_untracked_patch_bytes: int = DEFAULT_MAX_UNTRACKED_PATCH_BYTES,
    timeout_seconds: int = 3600,
) -> tuple[dict[str, Any], dict[str, Any]]:
    current = capture_repo_state(
        repo,
        max_ignored_paths=max_ignored_paths,
        sensitive_rules=sensitive_rules,
        redact_untracked_dotfiles=redact_untracked_dotfiles,
        metadata_only_floor=protected_metadata_paths(baseline),
        check_topology=check_topology,
    )
    introduced = changed_paths_between(baseline, current)
    if current["index"] != baseline["index"]:
        raise PipelineError(
            "Git index changed during the pipeline; delta capture was refused",
            6,
        )
    if current["git_control"] != baseline["git_control"]:
        raise PipelineError("Git control metadata changed during the pipeline", 6)
    missing = {"kind": "missing"}
    declassified = sorted(
        path
        for path in protected_metadata_paths(baseline)
        if current["worktree"].get(path, missing) != missing
        and path not in intrinsic_protected_paths(current)
    )
    if declassified:
        raise PipelineError(
            "writer declassified baseline protected metadata-only paths: "
            + ", ".join(declassified),
            9,
        )
    outside = sorted(path for path in introduced if not path_is_allowed(path, allowed_rules))
    if outside:
        raise PipelineError(
            "repository paths changed outside the approved contract: " + ", ".join(outside),
            6,
        )
    approved_deletions = validate_protected_changes(
        baseline=baseline,
        current=current,
        introduced_paths=introduced,
        allowed_deletions=allowed_protected_deletions or set(),
    )
    ignored_changed_paths = introduced & (
        baseline["ignored_paths"] | current["ignored_paths"]
    )
    redacted_untracked_paths = introduced & (
        (protected_metadata_paths(baseline) | protected_metadata_paths(current))
        - (baseline["ignored_paths"] | current["ignored_paths"])
    )
    delta = capture_delta(
        repo,
        run_dir,
        prefix,
        introduced,
        current,
        ignored_changed_paths,
        redacted_untracked_paths,
        max_delta_bytes=max_delta_bytes,
        max_untracked_patch_bytes=max_untracked_patch_bytes,
        timeout_seconds=timeout_seconds,
    )
    delta["protected_deletions"] = sorted(approved_deletions)
    return delta, current


def process_group_exists(process_group_id: int) -> bool:
    try:
        os.killpg(process_group_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_for_process_group_exit(process_group_id: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while process_group_exists(process_group_id):
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)
    return True


class ManagedResult:
    __slots__ = (
        "exit_code",
        "output",
        "timed_out",
        "leftover_process_group",
        "output_bytes_observed",
        "output_bytes_retained",
        "output_truncated",
        "output_limit_exceeded",
        "output_drain_timed_out",
        "detached_descendant_possible",
    )

    def __init__(
        self,
        *,
        exit_code: int,
        output: str,
        timed_out: bool,
        leftover_process_group: bool,
        output_bytes_observed: int,
        output_bytes_retained: int,
        output_truncated: bool,
        output_limit_exceeded: bool,
        output_drain_timed_out: bool,
        detached_descendant_possible: bool,
    ) -> None:
        self.exit_code = exit_code
        self.output = output
        self.timed_out = timed_out
        self.leftover_process_group = leftover_process_group
        self.output_bytes_observed = output_bytes_observed
        self.output_bytes_retained = output_bytes_retained
        self.output_truncated = output_truncated
        self.output_limit_exceeded = output_limit_exceeded
        self.output_drain_timed_out = output_drain_timed_out
        self.detached_descendant_possible = detached_descendant_possible

    def __iter__(self) -> Iterator[Any]:
        """Preserve the former four-value unpacking contract during migration."""

        yield self.exit_code
        yield self.output
        yield self.timed_out
        yield self.leftover_process_group


def managed_result_metadata(result: ManagedResult) -> dict[str, Any]:
    return {
        "exit_code": result.exit_code,
        "leftover_process_group": result.leftover_process_group,
        "timed_out": result.timed_out,
        "output_bytes_observed": result.output_bytes_observed,
        "output_bytes_retained": result.output_bytes_retained,
        "output_truncated": result.output_truncated,
        "output_limit_exceeded": result.output_limit_exceeded,
        "output_drain_timed_out": result.output_drain_timed_out,
        "detached_descendant_possible": result.detached_descendant_possible,
    }


class OutputTailBuffer:
    def __init__(self, limit: int) -> None:
        if limit <= 0:
            raise PipelineError("command output byte limit must be positive", 9)
        self.limit = limit
        self.observed = 0
        self.retained = 0
        self._chunks: deque[bytes] = deque()

    def append(self, chunk: bytes) -> None:
        if not chunk:
            return
        self.observed += len(chunk)
        self.retained += len(chunk)
        self._chunks.append(chunk)
        while self.retained > self.limit:
            excess = self.retained - self.limit
            first = self._chunks[0]
            if len(first) <= excess:
                self._chunks.popleft()
                self.retained -= len(first)
                continue
            self._chunks[0] = first[excess:]
            self.retained -= excess

    def text(self) -> str:
        raw = b"".join(self._chunks)
        text = raw.decode("utf-8", errors="replace")
        encoded = text.encode("utf-8")
        if len(encoded) <= self.limit:
            return text
        return encoded[-self.limit :].decode("utf-8", errors="ignore")


def close_selector_stream(
    selector: selectors.BaseSelector,
    stream: Any,
) -> None:
    if stream is None or stream.closed:
        return
    try:
        selector.unregister(stream)
    except (KeyError, ValueError):
        pass
    try:
        stream.close()
    except OSError:
        pass


def terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    process_group_id = process.pid
    process_group_signalable = True
    try:
        os.killpg(process_group_id, signal.SIGTERM)
    except ProcessLookupError:
        process_group_signalable = False
    except PermissionError as exc:
        if process.poll() is None:
            raise PipelineError(
                f"could not SIGTERM managed command process group {process_group_id}",
                9,
            ) from exc
        process_group_signalable = False

    # Reap the direct child promptly when possible. Process-group existence checks
    # can otherwise observe that exited child as a zombie and mistake it for a live
    # descendant. Do not wait on stdout here: descendants may still hold the pipe.
    try:
        process.wait(timeout=0.25)
    except subprocess.TimeoutExpired:
        pass

    if process_group_signalable and not wait_for_process_group_exit(process_group_id, 5):
        try:
            os.killpg(process_group_id, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            raise PipelineError(
                f"could not SIGKILL managed command process group {process_group_id}",
                9,
            ) from exc
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired as exc:
            raise PipelineError(
                f"managed command process {process.pid} survived SIGKILL",
                9,
            ) from exc
        if not wait_for_process_group_exit(process_group_id, 2):
            raise PipelineError(
                f"managed command process group {process_group_id} survived SIGKILL",
                9,
            )


def ensure_process_group_finished(process: subprocess.Popen[bytes]) -> bool:
    if not process_group_exists(process.pid):
        return False
    terminate_process_group(process)
    return True


def run_managed(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int,
    input_text: str | None = None,
    max_output_bytes: int = DEFAULT_MAX_COMMAND_OUTPUT_BYTES,
    environment: dict[str, str] | None = None,
) -> ManagedResult:
    if timeout <= 0:
        raise PipelineError("managed command timeout must be positive", 9)
    if max_output_bytes <= 0:
        raise PipelineError("command output byte limit must be positive", 9)
    command_environment = dict(os.environ if environment is None else environment)
    command_environment["PYTHONDONTWRITEBYTECODE"] = "1"
    input_bytes = input_text.encode("utf-8") if input_text is not None else None
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
        start_new_session=True,
        env=command_environment,
    )
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    os.set_blocking(process.stdout.fileno(), False)
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    stdout_open = True
    stdin_open = input_bytes is not None
    input_offset = 0
    if stdin_open:
        assert process.stdin is not None
        os.set_blocking(process.stdin.fileno(), False)
        selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")

    output = OutputTailBuffer(max_output_bytes)
    command_deadline = time.monotonic() + timeout
    drain_deadline: float | None = None
    timed_out = False
    output_limit_exceeded = False
    output_drain_timed_out = False
    cleanup_started = False
    leftover_process_group = False

    try:
        while True:
            now = time.monotonic()
            if not cleanup_started and output.observed > max_output_bytes:
                output_limit_exceeded = True
            if not cleanup_started and now >= command_deadline:
                timed_out = True
            parent_exited_with_open_output = (
                not cleanup_started
                and process.poll() is not None
                and stdout_open
            )
            if not cleanup_started and (
                timed_out or output_limit_exceeded or parent_exited_with_open_output
            ):
                if stdin_open:
                    close_selector_stream(selector, process.stdin)
                    stdin_open = False
                if process_group_exists(process.pid):
                    if parent_exited_with_open_output:
                        leftover_process_group = True
                    terminate_process_group(process)
                cleanup_started = True
                drain_deadline = time.monotonic() + PROCESS_OUTPUT_DRAIN_TIMEOUT_SECONDS

            if cleanup_started and drain_deadline is not None and now >= drain_deadline:
                if stdout_open:
                    output_drain_timed_out = True
                    close_selector_stream(selector, process.stdout)
                    stdout_open = False
                break

            if not cleanup_started and process.poll() is not None and not stdout_open:
                break
            if cleanup_started and not stdout_open:
                break

            active_deadline = drain_deadline if cleanup_started else command_deadline
            assert active_deadline is not None
            wait = max(0.0, min(0.1, active_deadline - time.monotonic()))
            for key, mask in selector.select(wait):
                if key.data == "stdout" and mask & selectors.EVENT_READ:
                    try:
                        chunk = os.read(process.stdout.fileno(), OUTPUT_READ_CHUNK_BYTES)
                    except BlockingIOError:
                        continue
                    if chunk:
                        output.append(chunk)
                    else:
                        close_selector_stream(selector, process.stdout)
                        stdout_open = False
                elif key.data == "stdin" and mask & selectors.EVENT_WRITE:
                    assert process.stdin is not None and input_bytes is not None
                    try:
                        written = os.write(
                            process.stdin.fileno(),
                            input_bytes[input_offset : input_offset + OUTPUT_READ_CHUNK_BYTES],
                        )
                    except BlockingIOError:
                        written = 0
                    except BrokenPipeError:
                        written = 0
                        close_selector_stream(selector, process.stdin)
                        stdin_open = False
                    input_offset += written
                    if input_offset >= len(input_bytes):
                        close_selector_stream(selector, process.stdin)
                        stdin_open = False

        if process.poll() is None:
            process.wait(timeout=2)
        if not cleanup_started:
            leftover_process_group = ensure_process_group_finished(process)
    except BaseException:
        if process_group_exists(process.pid):
            terminate_process_group(process)
        elif process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        raise
    finally:
        close_selector_stream(selector, process.stdin)
        close_selector_stream(selector, process.stdout)
        selector.close()

    exit_code = process.returncode if process.returncode is not None else 1
    if timed_out:
        exit_code = 124
    elif output_limit_exceeded:
        exit_code = COMMAND_OUTPUT_LIMIT_EXIT
    elif leftover_process_group and exit_code == 0:
        exit_code = 125

    output_text = output.text()
    if output_limit_exceeded:
        output_text += (
            f"\nmanaged command exceeded output limit of {max_output_bytes} bytes; "
            "only the bounded tail was retained and the process group was terminated\n"
        )
    if output_drain_timed_out:
        output_text += (
            "\nmanaged command output pipe remained open after process-group cleanup; "
            "local capture was closed at its deadline and a detached descendant may "
            "still be running\n"
        )
    if leftover_process_group:
        output_text += (
            "\nmanaged command left a live process group; leftover children were "
            "terminated\n"
        )
    return ManagedResult(
        exit_code=exit_code,
        output=output_text,
        timed_out=timed_out,
        leftover_process_group=leftover_process_group,
        output_bytes_observed=output.observed,
        output_bytes_retained=output.retained,
        output_truncated=output.observed > output.retained,
        output_limit_exceeded=output_limit_exceeded,
        output_drain_timed_out=output_drain_timed_out,
        detached_descendant_possible=output_drain_timed_out,
    )


def ensure_supported_runner_platform() -> None:
    if os.name != "posix" or fcntl is None:
        raise PipelineError(
            "the strict high-assurance runner supports Linux, macOS, and WSL; "
            "native Windows is not supported",
            9,
        )


@contextmanager
def repository_lock(repo: Path) -> Iterator[Path]:
    ensure_supported_runner_platform()
    assert fcntl is not None
    common_raw = run_checked(["git", "rev-parse", "--git-common-dir"], repo)
    common_dir = Path(common_raw)
    if not common_dir.is_absolute():
        common_dir = (repo / common_dir).resolve()
    lock_path = common_dir / "codex-high-assurance.lock"
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    handle = os.fdopen(descriptor, "r+", encoding="utf-8")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            handle.seek(0)
            owner = handle.read().strip() or "unknown owner"
            raise PipelineError(
                f"another high-assurance pipeline holds {lock_path}: {owner}",
                7,
            ) from exc
        handle.seek(0)
        handle.truncate()
        handle.write(f"pid={os.getpid()} acquired={datetime.now(timezone.utc).isoformat()}\n")
        handle.flush()
        os.fchmod(handle.fileno(), 0o600)
        yield lock_path
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run evidence -> diagnosis -> one writer -> verification -> review.",
    )
    parser.add_argument("--repo", required=True, type=Path, help="Git repository root")
    parser.add_argument("--task", required=True, type=Path, help="UTF-8 task Markdown file")
    parser.add_argument(
        "--verify",
        action="append",
        required=True,
        help="Verification command parsed without a shell; repeat for multiple commands",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow a dirty worktree after recording its baseline (clean is safer)",
    )
    parser.add_argument(
        "--max-repair-cycles",
        type=int,
        choices=(0, 1),
        default=1,
        help="Maximum targeted repair cycles after verification or review failure",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        default=None,
        help="Artifact root; defaults to $CODEX_HOME/runs/high-assurance",
    )
    parser.add_argument("--codex-bin", default="codex", help="Codex executable")
    parser.add_argument("--stage-timeout", type=int, default=3600)
    parser.add_argument(
        "--max-command-output-bytes",
        type=int,
        default=DEFAULT_MAX_COMMAND_OUTPUT_BYTES,
        help=(
            "Terminate a model or verification command after observed merged output "
            f"exceeds this per-command byte budget (default: {DEFAULT_MAX_COMMAND_OUTPUT_BYTES})"
        ),
    )
    parser.add_argument(
        "--max-verification-output-bytes",
        type=int,
        default=DEFAULT_MAX_VERIFICATION_OUTPUT_BYTES,
        help=(
            "Cap retained merged output across one deterministic-verification batch "
            f"(default: {DEFAULT_MAX_VERIFICATION_OUTPUT_BYTES})"
        ),
    )
    parser.add_argument(
        "--max-verification-artifact-bytes",
        type=int,
        default=DEFAULT_MAX_VERIFICATION_ARTIFACT_BYTES,
        help=(
            "Cap actual NDJSON bytes written by one deterministic-verification batch "
            f"(default: {DEFAULT_MAX_VERIFICATION_ARTIFACT_BYTES})"
        ),
    )
    parser.add_argument(
        "--max-delta-bytes",
        type=int,
        default=DEFAULT_MAX_DELTA_BYTES,
        help=(
            "Fail closed before Review when complete staged, unstaged, HEAD, and "
            f"untracked patches exceed this byte budget (default: {DEFAULT_MAX_DELTA_BYTES})"
        ),
    )
    parser.add_argument(
        "--max-untracked-patch-bytes",
        type=int,
        default=DEFAULT_MAX_UNTRACKED_PATCH_BYTES,
        help=(
            "Fail closed when complete ordinary-untracked binary patches exceed this "
            f"byte budget (default: {DEFAULT_MAX_UNTRACKED_PATCH_BYTES})"
        ),
    )
    parser.add_argument(
        "--verify-env",
        action="append",
        default=[],
        metavar="NAME",
        help=(
            "Pass one additional existing host environment variable to verification; "
            "repeatable; names are recorded but values are not"
        ),
    )
    parser.add_argument(
        "--max-ignored-paths",
        type=int,
        default=DEFAULT_MAX_IGNORED_PATHS,
        help=(
            "Fail closed when ignored-path enumeration exceeds this count "
            f"(default: {DEFAULT_MAX_IGNORED_PATHS})"
        ),
    )
    parser.add_argument(
        "--sensitive-path",
        action="append",
        default=[],
        help=(
            "Keep an exact visible-untracked repo path or directory/** metadata-only; "
            "repeat for multiple rules (tracked files remain content-fingerprinted)"
        ),
    )
    parser.add_argument(
        "--redact-untracked-dotfiles",
        action="store_true",
        help="Keep every visible-untracked path containing a dotfile segment metadata-only",
    )
    parser.add_argument(
        "--bind-verification-path",
        action="append",
        default=[],
        help=(
            "Bind VERIFY_ID:path as an existing repo-relative stability dependency; "
            "a bare path is accepted only with one user --verify command; repeatable"
        ),
    )
    parser.add_argument(
        "--allow-protected-path-delete",
        action="append",
        default=[],
        help=(
            "Explicitly authorize deletion of one exact baseline ignored/sensitive path; "
            "repeat for multiple paths; successful runs still require human acceptance"
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def run_checked(argv: list[str], cwd: Path) -> str:
    result = subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise PipelineError(
            f"command failed ({result.returncode}): {shlex.join(argv)}\n{result.stdout}",
        )
    return result.stdout.strip()


def load_role(codex_home: Path, stage: str) -> dict[str, Any]:
    path = codex_home / "agents" / ROLE_FILES[stage]
    if not path.is_file():
        raise PipelineError(f"missing role file: {path}")
    with path.open("rb") as handle:
        role = tomllib.load(handle)
    for key in (
        "model",
        "model_reasoning_effort",
        "sandbox_mode",
        "developer_instructions",
    ):
        if not role.get(key):
            raise PipelineError(f"{path}: missing {key}")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", role["model"]):
        raise PipelineError(f"{path}: invalid model slug")
    if role["model_reasoning_effort"] not in VALID_REASONING_EFFORTS:
        raise PipelineError(f"{path}: unsupported reasoning effort")
    if role["sandbox_mode"] not in VALID_SANDBOX_MODES:
        raise PipelineError(f"{path}: unsafe or unsupported sandbox mode")
    if role["sandbox_mode"] != ROLE_SANDBOXES[stage]:
        raise PipelineError(
            f"{path}: {stage} must use sandbox_mode={ROLE_SANDBOXES[stage]!r}",
        )
    return role


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def best_effort_command(argv: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable: {exc}"
    output = result.stdout.strip()
    return output if result.returncode == 0 else f"unavailable ({result.returncode}): {output}"


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"invalid structured stage output {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PipelineError(f"stage output must be a JSON object: {path}")
    return value


def run_stage(
    *,
    args: argparse.Namespace,
    repo: Path,
    run_dir: Path,
    stage_name: str,
    artifact_prefix: str,
    role: dict[str, Any],
    schema: dict[str, Any],
    prompt: str,
) -> dict[str, Any]:
    schema_path = run_dir / f"{artifact_prefix}-schema.json"
    output_path = run_dir / f"{artifact_prefix}.json"
    log_path = run_dir / f"{artifact_prefix}.log"
    command_result_path = run_dir / f"{artifact_prefix}-command.json"

    command = [
        args.codex_bin,
        "exec",
        "--strict-config",
        "--ignore-user-config",
        "--ephemeral",
        "-C",
        str(repo),
        "-m",
        role["model"],
        "-s",
        role["sandbox_mode"],
        "-c",
        f'model_reasoning_effort="{role["model_reasoning_effort"]}"',
        "-c",
        'approval_policy="never"',
        "-c",
        "sandbox_workspace_write.network_access=false",
        "-c",
        "developer_instructions="
        + json.dumps(role["developer_instructions"], ensure_ascii=False),
        "--output-schema",
        str(schema_path),
        "-o",
        str(output_path),
    ]
    for feature in COMMON_DISABLED_FEATURES:
        command.extend(("--disable", feature))
    command.append("-")

    print(
        f"[{stage_name}] {role['model']} / {role['model_reasoning_effort']} / "
        f"{role['sandbox_mode']}",
        flush=True,
    )
    if args.dry_run:
        print(f"  {shlex.join(command)}", flush=True)
        return {"dry_run": True}

    write_json(schema_path, schema)
    effective_prompt = "RUNNER STAGE INSTRUCTIONS:\n" + prompt
    start_error: OSError | None = None
    try:
        result = run_managed(
            command,
            cwd=repo,
            timeout=args.stage_timeout,
            input_text=effective_prompt,
            max_output_bytes=args.max_command_output_bytes,
        )
    except OSError as exc:
        start_error = exc
        result = ManagedResult(
            exit_code=127,
            output=f"could not start {stage_name}: {exc}",
            timed_out=False,
            leftover_process_group=False,
            output_bytes_observed=0,
            output_bytes_retained=0,
            output_truncated=False,
            output_limit_exceeded=False,
            output_drain_timed_out=False,
            detached_descendant_possible=False,
        )

    log_path.write_text(result.output, encoding="utf-8")
    write_json(
        command_result_path,
        {
            "stage": stage_name,
            "output_log": log_path.name,
            **managed_result_metadata(result),
        },
    )
    if start_error is not None:
        raise PipelineError(result.output) from start_error
    if result.output_limit_exceeded:
        raise PipelineError(
            f"{stage_name} exceeded the {args.max_command_output_bytes}-byte command "
            f"output limit; see {log_path}",
            9,
        )
    if result.timed_out:
        detached_note = (
            "; detached descendant possible because output drain hit its deadline"
            if result.detached_descendant_possible
            else ""
        )
        raise PipelineError(
            f"{stage_name} timed out after {args.stage_timeout}s; original process-group "
            f"cleanup completed{detached_note}; see {log_path}",
        )
    if result.exit_code != 0:
        raise PipelineError(
            f"{stage_name} failed with exit code {result.exit_code}; see {log_path}",
        )
    if not output_path.is_file():
        raise PipelineError(f"{stage_name} produced no output: {output_path}")
    return read_json(output_path)


def verification_commands(args: argparse.Namespace) -> list[dict[str, Any]]:
    commands: list[list[str]] = [["git", "diff", "HEAD", "--check"]]
    for raw in args.verify:
        argv = shlex.split(raw)
        if not argv:
            raise PipelineError("--verify must not be empty")
        commands.append(argv)
    if len(commands) > MAX_VERIFICATION_COMMANDS:
        raise PipelineError(
            "verification command count exceeds the supported batch limit of "
            f"{MAX_VERIFICATION_COMMANDS}",
            9,
        )
    return [
        {
            "id": BUILTIN_DIFF_CHECK_ID if index == 0 else f"verify-{index}",
            "argv": argv,
        }
        for index, argv in enumerate(commands)
    ]


def build_verification_environment(
    extra_names: list[str],
    source: dict[str, str] | None = None,
) -> dict[str, str]:
    source_environment = os.environ if source is None else source
    requested: set[str] = set()
    for name in extra_names:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise PipelineError(f"invalid --verify-env name: {name!r}", 9)
        if name not in source_environment:
            raise PipelineError(
                f"--verify-env requested an unset variable: {name}",
                9,
            )
        requested.add(name)
    names = set(VERIFICATION_ENV_ALLOWLIST) | requested
    environment = {
        name: source_environment[name]
        for name in sorted(names)
        if name in source_environment
    }
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def json_string_content_byte_length(value: str) -> int:
    """Return the exact UTF-8 byte length of a JSON string's escaped content."""

    total = 0
    for character in value:
        codepoint = ord(character)
        if character in {'"', "\\"} or character in "\b\f\n\r\t":
            total += 2
        elif codepoint < 0x20 or 0xD800 <= codepoint <= 0xDFFF:
            total += 6
        else:
            total += len(character.encode("utf-8"))
    return total


def json_string_tail_within_bytes(value: str, max_content_bytes: int) -> str:
    if max_content_bytes <= 0:
        return ""
    used = 0
    index = len(value)
    while index > 0:
        character = value[index - 1]
        cost = json_string_content_byte_length(character)
        if used + cost > max_content_bytes:
            break
        used += cost
        index -= 1
    return value[index:]


def encode_ndjson_value(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8", errors="backslashreplace")


def verification_record_line(
    record: dict[str, Any],
    *,
    max_bytes: int,
    artifact_bytes_written: int,
    force_truncated: bool = False,
    output_utf8_bytes_hint: int | None = None,
) -> tuple[dict[str, Any], bytes]:
    """Serialize one NDJSON record without expanding rejected output first."""

    if max_bytes <= 0:
        raise PipelineError("verification artifact byte budget is exhausted", 9)
    original = dict(record)
    original_output = str(original.get("output", ""))
    original_output_utf8_bytes = (
        output_utf8_bytes_hint
        if output_utf8_bytes_hint is not None
        else len(original_output.encode("utf-8", errors="backslashreplace"))
    )

    def prepare(output: str, truncated: bool) -> tuple[dict[str, Any], int]:
        candidate = dict(original)
        candidate["output"] = ""
        candidate["record_schema_version"] = 1
        candidate["output_utf8_bytes"] = original_output_utf8_bytes
        candidate["artifact_output_utf8_bytes"] = len(
            output.encode("utf-8", errors="backslashreplace")
        )
        candidate["artifact_output_truncated"] = truncated
        if truncated:
            candidate["command_exit_code"] = candidate.get("exit_code")
            candidate["exit_code"] = COMMAND_OUTPUT_LIMIT_EXIT
            candidate["verification_artifact_budget_exceeded"] = True
        else:
            candidate["verification_artifact_budget_exceeded"] = False
        candidate["record_json_bytes"] = 0
        candidate["artifact_bytes_written_total"] = artifact_bytes_written
        content_bytes = json_string_content_byte_length(output)
        predicted_size = 0
        for _ in range(8):
            base_size = len(encode_ndjson_value(candidate))
            predicted_size = base_size + content_bytes
            total = artifact_bytes_written + predicted_size
            if (
                candidate["record_json_bytes"] == predicted_size
                and candidate["artifact_bytes_written_total"] == total
            ):
                break
            candidate["record_json_bytes"] = predicted_size
            candidate["artifact_bytes_written_total"] = total
        return candidate, predicted_size

    def materialize(
        candidate: dict[str, Any],
        output: str,
        predicted_size: int,
    ) -> tuple[dict[str, Any], bytes]:
        candidate["output"] = output
        payload = encode_ndjson_value(candidate)
        if len(payload) != predicted_size:
            raise PipelineError("verification JSON byte prediction drifted", 9)
        return candidate, payload

    if not force_truncated:
        full_record, full_size = prepare(original_output, False)
        if full_size <= max_bytes:
            return materialize(full_record, original_output, full_size)

    empty_record, empty_size = prepare("", True)
    if empty_size > max_bytes:
        raise PipelineError(
            "verification artifact byte budget is too small for required structured metadata",
            9,
        )
    output = json_string_tail_within_bytes(
        original_output,
        max_bytes - empty_size,
    )
    truncated_record, truncated_size = prepare(output, True)
    while truncated_size > max_bytes and output:
        output = output[1:]
        truncated_record, truncated_size = prepare(output, True)
    if truncated_size > max_bytes:
        raise PipelineError(
            "verification artifact byte budget is too small for required structured metadata",
            9,
        )
    return materialize(truncated_record, output, truncated_size)


def empty_verification_record(
    command_id: str,
    argv: list[str],
    byte_hint: int = 0,
) -> dict[str, Any]:
    return {
        "id": command_id,
        "command": shlex.join(argv),
        "output": "",
        "exit_code": COMMAND_OUTPUT_LIMIT_EXIT,
        "leftover_process_group": False,
        "timed_out": False,
        "output_bytes_observed": byte_hint + OUTPUT_READ_CHUNK_BYTES,
        "output_bytes_retained": byte_hint,
        "output_truncated": False,
        "output_limit_exceeded": False,
        "output_drain_timed_out": False,
        "detached_descendant_possible": False,
        "verification_output_budget_exceeded": False,
    }


def run_verification(
    *,
    repo: Path,
    run_dir: Path,
    prefix: str,
    commands: list[dict[str, Any]],
    dry_run: bool,
    timeout_seconds: int,
    expected_state: dict[str, Any],
    state_supplier: Callable[[], dict[str, Any]],
    entrypoints: dict[str, dict[str, Any]],
    environment: dict[str, str],
    max_output_bytes: int,
    max_total_output_bytes: int,
    max_artifact_bytes: int = DEFAULT_MAX_VERIFICATION_ARTIFACT_BYTES,
) -> tuple[bool, list[dict[str, Any]]]:
    if max_total_output_bytes <= 0:
        raise PipelineError("verification output byte limit must be positive", 9)
    if max_artifact_bytes <= 0:
        raise PipelineError("verification artifact byte limit must be positive", 9)
    records: list[dict[str, Any]] = []
    retained_output_bytes = 0
    artifact_bytes_written = 0
    ndjson_path = run_dir / f"{prefix}.ndjson"
    summary_path = run_dir / f"{prefix}-summary.json"
    if not dry_run:
        ndjson_path.write_bytes(b"")

    def persist_record(record: dict[str, Any]) -> dict[str, Any]:
        nonlocal artifact_bytes_written
        remaining = max_artifact_bytes - artifact_bytes_written
        persisted, payload = verification_record_line(
            record,
            max_bytes=remaining,
            artifact_bytes_written=artifact_bytes_written,
        )
        with ndjson_path.open("ab") as artifact:
            artifact.write(payload)
        artifact_bytes_written += len(payload)
        if artifact_bytes_written != persisted["artifact_bytes_written_total"]:
            raise PipelineError("verification artifact byte accounting drifted", 9)
        records.append(persisted)
        return persisted

    for command in commands:
        command_id = command["id"]
        argv = command["argv"]
        print(f"[verify] {shlex.join(argv)}", flush=True)
        if dry_run:
            records.append(
                {
                    "id": command_id,
                    "command": shlex.join(argv),
                    "exit_code": None,
                    "output": "dry-run",
                }
            )
            continue
        remaining_output_bytes = max_total_output_bytes - retained_output_bytes
        preflight_output_bytes = (
            min(max_output_bytes, remaining_output_bytes)
            if remaining_output_bytes > 0
            else 0
        )
        verification_record_line(
            empty_verification_record(
                command_id,
                argv,
                preflight_output_bytes,
            ),
            max_bytes=max_artifact_bytes - artifact_bytes_written,
            artifact_bytes_written=artifact_bytes_written,
            force_truncated=True,
            output_utf8_bytes_hint=(
                preflight_output_bytes
                + len(shlex.join(argv).encode("utf-8", errors="backslashreplace"))
                + 4096
            ),
        )
        if remaining_output_bytes <= 0:
            persist_record(
                {
                    "id": command_id,
                    "command": shlex.join(argv),
                    "exit_code": COMMAND_OUTPUT_LIMIT_EXIT,
                    "output": (
                        "verification command was not run because the batch retained-"
                        f"output budget of {max_total_output_bytes} bytes was exhausted"
                    ),
                    "leftover_process_group": False,
                    "timed_out": False,
                    "output_bytes_observed": 0,
                    "output_bytes_retained": 0,
                    "output_truncated": False,
                    "output_limit_exceeded": False,
                    "output_drain_timed_out": False,
                    "detached_descendant_possible": False,
                    "verification_output_budget_exceeded": True,
                }
            )
            break
        effective_output_limit = min(max_output_bytes, remaining_output_bytes)
        before = state_supplier()
        assert_repo_unchanged(
            expected_state,
            before,
            f"before verification command {command_id}",
        )
        validate_verification_entrypoints_unchanged(
            repo,
            entrypoints,
            before,
            {command_id},
        )
        try:
            result = run_managed(
                argv,
                cwd=repo,
                timeout=timeout_seconds,
                max_output_bytes=effective_output_limit,
                environment=environment,
            )
            output = result.output
            if result.timed_out:
                output = (
                    f"verification timed out after {timeout_seconds}s; "
                    "original process-group cleanup completed; inspect structured "
                    "drain state for detached-descendant risk\n" + output
                )
        except OSError as exc:
            result = ManagedResult(
                exit_code=127,
                output=f"could not start verification command: {exc}",
                timed_out=False,
                leftover_process_group=False,
                output_bytes_observed=0,
                output_bytes_retained=0,
                output_truncated=False,
                output_limit_exceeded=False,
                output_drain_timed_out=False,
                detached_descendant_possible=False,
            )
            output = f"could not start verification command: {exc}"
        retained_output_bytes += result.output_bytes_retained
        verification_output_budget_exceeded = (
            effective_output_limit < max_output_bytes
            and result.output_limit_exceeded
        )
        persisted = persist_record(
            {
                "id": command_id,
                "command": shlex.join(argv),
                "output": output,
                **managed_result_metadata(result),
                "verification_output_budget_exceeded": (
                    verification_output_budget_exceeded
                ),
            }
        )
        after = state_supplier()
        assert_repo_unchanged(
            expected_state,
            after,
            f"verification command {command_id}",
        )
        if (
            verification_output_budget_exceeded
            or persisted["verification_artifact_budget_exceeded"]
        ):
            break
    verified = all(item["exit_code"] in (0, None) for item in records)
    if not dry_run:
        write_json(
            summary_path,
            {
                "format": "rootloom-verification-summary-v1",
                "record_format": "rootloom-verification-ndjson-v1",
                "ndjson": ndjson_path.name,
                "record_count": len(records),
                "verified": verified,
                "artifact_bytes_written": artifact_bytes_written,
                "max_artifact_bytes": max_artifact_bytes,
                "output_bytes_observed": sum(
                    int(record.get("output_bytes_observed", 0)) for record in records
                ),
                "output_bytes_retained": sum(
                    int(record.get("output_bytes_retained", 0)) for record in records
                ),
                "output_utf8_bytes": sum(
                    int(record.get("output_utf8_bytes", 0)) for record in records
                ),
                "artifact_output_truncated": any(
                    bool(record.get("artifact_output_truncated")) for record in records
                ),
            },
        )
        if ndjson_path.stat().st_size != artifact_bytes_written:
            raise PipelineError("verification NDJSON size does not match byte accounting", 9)
    return verified, records


def validate_verification_coverage(
    diagnosis: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    results = {record.get("id"): record.get("exit_code") for record in records}
    verification_map = diagnosis["verification_map"]
    for field, item in verification_map.items():
        for command_id in item["command_ids"]:
            if command_id not in results:
                raise PipelineError(
                    f"verification coverage failed: {field} has no record for {command_id}",
                    8,
                )
            if results[command_id] != 0:
                raise PipelineError(
                    f"verification coverage failed: {field} maps to unsuccessful "
                    f"command {command_id}",
                    8,
                )


def compact_verification(records: list[dict[str, Any]]) -> str:
    compact: list[dict[str, Any]] = []
    for record in records:
        output = record.get("output", "")
        compact.append(
            {
                "id": record.get("id"),
                "command": record.get("command"),
                "exit_code": record.get("exit_code"),
                "leftover_process_group": record.get("leftover_process_group", False),
                "timed_out": record.get("timed_out", False),
                "output_bytes_observed": record.get("output_bytes_observed", 0),
                "output_bytes_retained": record.get("output_bytes_retained", 0),
                "output_truncated": record.get("output_truncated", False),
                "output_limit_exceeded": record.get("output_limit_exceeded", False),
                "output_drain_timed_out": record.get("output_drain_timed_out", False),
                "detached_descendant_possible": record.get(
                    "detached_descendant_possible",
                    False,
                ),
                "verification_output_budget_exceeded": record.get(
                    "verification_output_budget_exceeded",
                    False,
                ),
                "output_utf8_bytes": record.get("output_utf8_bytes", 0),
                "artifact_output_utf8_bytes": record.get(
                    "artifact_output_utf8_bytes",
                    0,
                ),
                "record_json_bytes": record.get("record_json_bytes", 0),
                "artifact_bytes_written_total": record.get(
                    "artifact_bytes_written_total",
                    0,
                ),
                "artifact_output_truncated": record.get(
                    "artifact_output_truncated",
                    False,
                ),
                "verification_artifact_budget_exceeded": record.get(
                    "verification_artifact_budget_exceeded",
                    False,
                ),
                "output_tail": output[-12000:],
            }
        )
    payload = json.dumps(compact, ensure_ascii=False, indent=2)
    if len(payload) <= MAX_VERIFICATION_PROMPT_CHARS:
        return payload
    marker = (
        "\n... verification summary truncated to the model prompt budget; "
        f"bounded machine records remain in the private artifact ({len(payload)} chars) ...\n"
    )
    available = MAX_VERIFICATION_PROMPT_CHARS - len(marker)
    head_size = available // 2
    return payload[:head_size] + marker + payload[-(available - head_size) :]


def run_pipeline_locked(
    args: argparse.Namespace,
    repo: Path,
    task_path: Path,
) -> int:
    ensure_supported_repository_topology(repo)
    if args.max_command_output_bytes <= 0:
        raise PipelineError("--max-command-output-bytes must be positive", 9)
    if args.max_verification_output_bytes <= 0:
        raise PipelineError("--max-verification-output-bytes must be positive", 9)
    if args.max_verification_artifact_bytes <= 0:
        raise PipelineError("--max-verification-artifact-bytes must be positive", 9)
    if args.max_delta_bytes <= 0:
        raise PipelineError("--max-delta-bytes must be positive", 9)
    if args.max_untracked_patch_bytes <= 0:
        raise PipelineError("--max-untracked-patch-bytes must be positive", 9)
    verification_environment = build_verification_environment(args.verify_env)
    sensitive_rules = normalize_sensitive_paths(args.sensitive_path)
    allowed_protected_deletions = normalize_protected_deletions(
        args.allow_protected_path_delete
    )
    validate_protected_deletion_runtime_options(
        allowed_deletions=allowed_protected_deletions,
        allow_dirty=args.allow_dirty,
        max_repair_cycles=args.max_repair_cycles,
    )

    metadata_only_floor: set[str] | None = None

    def capture_state(*, check_topology: bool = False) -> dict[str, Any]:
        return capture_repo_state(
            repo,
            max_ignored_paths=args.max_ignored_paths,
            sensitive_rules=sensitive_rules,
            redact_untracked_dotfiles=args.redact_untracked_dotfiles,
            metadata_only_floor=metadata_only_floor,
            check_topology=check_topology,
        )

    baseline = capture_state()
    metadata_only_floor = protected_metadata_paths(baseline)
    baseline_status = baseline["status_raw"].decode(
        "utf-8",
        errors="backslashreplace",
    ).replace("\x00", "\n").rstrip()
    if baseline["status_raw"] and not args.allow_dirty:
        raise PipelineError(
            "worktree is dirty; use a clean worktree or pass --allow-dirty after reviewing the baseline",
        )

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    roles = {stage: load_role(codex_home, stage) for stage in ROLE_FILES}
    role_hashes = {
        stage: file_sha256(codex_home / "agents" / filename)
        for stage, filename in ROLE_FILES.items()
    }
    policy_payload = json.dumps(role_hashes, sort_keys=True).encode("utf-8")
    policy_hash = hashlib.sha256(policy_payload).hexdigest()
    requested_run_root = (
        args.run_root.expanduser()
        if args.run_root
        else codex_home / "runs" / "high-assurance"
    )
    if requested_run_root.is_symlink():
        raise PipelineError(f"artifact root must not be a symlink: {requested_run_root}")
    run_root = requested_run_root.resolve()
    if run_root == repo or run_root.is_relative_to(repo):
        raise PipelineError("artifact root must be outside the target repository")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short_sha = run_checked(["git", "rev-parse", "--short", "HEAD"], repo)
    run_dir = run_root / f"{timestamp}-{short_sha}-{os.urandom(4).hex()}"
    if not args.dry_run:
        run_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
        run_dir.chmod(0o700)

    task = task_path.read_text(encoding="utf-8")
    baseline_untracked, baseline_redacted_untracked = state_untracked_manifests(baseline)
    commands = verification_commands(args)
    bound_verification_paths = normalize_verification_bindings(
        args.bind_verification_path,
        commands,
    )
    validate_verification_command_boundaries(repo, commands)
    verification_entrypoints = discover_verification_entrypoints(
        repo,
        commands,
        baseline,
        bound_paths=bound_verification_paths,
    )
    metadata = {
        "runner_version": RUNNER_VERSION,
        "runner_sha256": file_sha256(Path(__file__)),
        "codex_version": best_effort_command([args.codex_bin, "--version"], repo),
        "policy_hash": policy_hash,
        "role_file_sha256": role_hashes,
        "repo": str(repo),
        "git_sha": run_checked(["git", "rev-parse", "HEAD"], repo),
        "baseline_status": baseline_status,
        "baseline_untracked": baseline_untracked,
        "baseline_redacted_untracked_metadata": baseline_redacted_untracked,
        "baseline_ignored_path_count": len(baseline["ignored_paths"]),
        "max_ignored_paths": args.max_ignored_paths,
        "max_command_output_bytes": args.max_command_output_bytes,
        "max_verification_output_bytes": args.max_verification_output_bytes,
        "max_verification_artifact_bytes": args.max_verification_artifact_bytes,
        "max_delta_bytes": args.max_delta_bytes,
        "max_untracked_patch_bytes": args.max_untracked_patch_bytes,
        "verification_artifact_format": "ndjson-v1",
        "delta_artifact_format": "complete-patch-with-bounded-prompt-excerpt-v1",
        "max_verification_commands": MAX_VERIFICATION_COMMANDS,
        "max_verification_prompt_chars": MAX_VERIFICATION_PROMPT_CHARS,
        "verification_environment_names": sorted(verification_environment),
        "explicit_verification_environment_names": sorted(set(args.verify_env)),
        "sensitive_paths": args.sensitive_path,
        "bound_verification_paths": {
            command_id: sorted(paths)
            for command_id, paths in sorted(bound_verification_paths.items())
        },
        "redact_untracked_dotfiles": args.redact_untracked_dotfiles,
        "allowed_protected_path_deletions": sorted(allowed_protected_deletions),
        "task_file": str(task_path),
        "roles": {
            stage: {
                "model": role["model"],
                "reasoning": role["model_reasoning_effort"],
                "sandbox": role["sandbox_mode"],
            }
            for stage, role in roles.items()
        },
        "verify": [
            {"id": command["id"], "command": shlex.join(command["argv"])}
            for command in commands
        ],
        "verification_entrypoints": verification_entrypoints,
    }
    if not args.dry_run:
        write_json(run_dir / "00-metadata.json", metadata)
        (run_dir / "00-task.md").write_text(task, encoding="utf-8")
        (run_dir / "00-baseline-status.txt").write_text(
            baseline_status + ("\n" if baseline_status else ""),
            encoding="utf-8",
        )
        baseline_capture_deadline = time.monotonic() + args.stage_timeout
        baseline_delta_bytes = stream_command_artifact(
            [
                "git", "diff", "--binary", "--full-index", "--no-ext-diff",
                "--no-textconv",
            ],
            repo=repo,
            destination=run_dir / "00-baseline.patch",
            max_bytes=args.max_delta_bytes,
            timeout_seconds=remaining_deadline_seconds(
                baseline_capture_deadline,
                "baseline Delta capture",
            ),
        )
        stream_command_artifact(
            [
                "git", "diff", "--cached", "--binary", "--full-index",
                "--no-ext-diff", "--no-textconv",
            ],
            repo=repo,
            destination=run_dir / "00-baseline-cached.patch",
            max_bytes=args.max_delta_bytes - baseline_delta_bytes,
            timeout_seconds=remaining_deadline_seconds(
                baseline_capture_deadline,
                "baseline Delta capture",
            ),
        )
        write_json(run_dir / "00-baseline-untracked.json", baseline_untracked)
        write_json(
            run_dir / "00-baseline-redacted-untracked-metadata.json",
            baseline_redacted_untracked,
        )
    else:
        print(json.dumps(metadata, ensure_ascii=False, indent=2), flush=True)

    evidence_prompt = textwrap.dedent(
        f"""
        Act only as the evidence stage for a high-assurance code change.
        Do not modify files. Do not call MCP, apps, browsers, or remote services.
        Do not open or read ignored files, known secret-like untracked paths, or
        caller-configured sensitive paths. Configured sensitive rules are
        {json.dumps(args.sensitive_path, ensure_ascii=False)}; untracked dotfile
        redaction is {args.redact_untracked_dotfiles}.
        Inspect repository instructions, relevant source, tests, and local git state.
        Distinguish facts, inference, and unknowns. Do not choose the final fix.
        Attribute material evidence with source/environment, observed time or window,
        stable reference when available, and freshness/redaction notes. The schema
        enforces shape and process discipline, not factual truth. Give every provenance
        record a stable id and make every observed fact, reproduction item, and
        hypothesis evidence list reference existing provenance ids.

        TASK:
        {task}
        """
    ).strip()
    evidence = run_stage(
        args=args,
        repo=repo,
        run_dir=run_dir,
        stage_name="evidence",
        artifact_prefix="01-evidence",
        role=roles["evidence"],
        schema=EVIDENCE_SCHEMA,
        prompt=evidence_prompt,
    )
    if args.dry_run:
        run_stage(
            args=args,
            repo=repo,
            run_dir=run_dir,
            stage_name="diagnosis",
            artifact_prefix="02-diagnosis",
            role=roles["diagnosis"],
            schema=DIAGNOSIS_SCHEMA,
            prompt="dry-run",
        )
        run_stage(
            args=args,
            repo=repo,
            run_dir=run_dir,
            stage_name="implementation",
            artifact_prefix="03-implementation",
            role=roles["implementation"],
            schema=IMPLEMENTATION_SCHEMA,
            prompt="dry-run",
        )
        for command in commands:
            print(f"[verify] {command['id']}: {shlex.join(command['argv'])}", flush=True)
        run_stage(
            args=args,
            repo=repo,
            run_dir=run_dir,
            stage_name="review",
            artifact_prefix="05-review",
            role=roles["review"],
            schema=REVIEW_SCHEMA,
            prompt="dry-run",
        )
        return 0

    validate_evidence(evidence)
    assert_repo_unchanged(baseline, capture_state(), "evidence stage")

    verification_catalog = [
        {"id": command["id"], "command": shlex.join(command["argv"])}
        for command in commands
    ]

    diagnosis_prompt = textwrap.dedent(
        f"""
        Act as the independent root-cause gate. Do not modify files and do not call
        external tools. Do not open or read ignored files, known secret-like untracked
        paths, or caller-configured sensitive paths. Recheck material evidence against
        the repository. Return GO
        only when the root cause and a focused, testable change contract are supported.
        Map verification to the original failure path, the owning-boundary invariant,
        and an adjacent negative or alternate path. Each verification-map item must
        name one or more ids from the machine command catalog below. This proves that
        the declared requirement is linked to an executed command; it does not by
        itself prove that the command is semantically sufficient.
        allowed_paths must contain exact repo-relative paths or directory/** prefixes;
        include both endpoints of a move or rename. Do not use ambiguous glob syntax.

        TASK:
        {task}

        EVIDENCE:
        {json.dumps(evidence, ensure_ascii=False, indent=2)}

        MACHINE VERIFICATION COMMAND CATALOG:
        {json.dumps(verification_catalog, ensure_ascii=False, indent=2)}
        """
    ).strip()
    diagnosis = run_stage(
        args=args,
        repo=repo,
        run_dir=run_dir,
        stage_name="diagnosis",
        artifact_prefix="02-diagnosis",
        role=roles["diagnosis"],
        schema=DIAGNOSIS_SCHEMA,
        prompt=diagnosis_prompt,
    )
    assert_repo_unchanged(baseline, capture_state(), "diagnosis stage")
    allowed_rules = validate_diagnosis(
        diagnosis,
        {command["id"] for command in commands},
    )
    if diagnosis.get("decision") != "GO":
        raise PipelineError(f"diagnosis returned NO_GO; see {run_dir / '02-diagnosis.json'}", 2)
    validate_allowed_path_boundaries(repo, allowed_rules)
    validate_protected_deletion_preflight(
        repo=repo,
        baseline=baseline,
        allowed_rules=allowed_rules,
        allowed_deletions=allowed_protected_deletions,
    )

    previous_failure = ""
    for attempt in range(args.max_repair_cycles + 1):
        label = "implementation" if attempt == 0 else f"repair-{attempt}"
        prefix_number = 3 + attempt * 3
        stage_baseline = capture_state()
        implementation_prompt = textwrap.dedent(
            f"""
            Act as the sole write stage. Implement only the approved change contract.
            Preserve unrelated work. Do not perform external writes, releases, deploys,
            credential changes, destructive operations, or scope expansion. Add focused
            regression coverage and run relevant local checks. Stop as blocked if the
            proper fix exceeds the contract. Do not stage, unstage, or otherwise change
            the Git index. Do not open, read, create, or modify ignored files, known
            secret-like untracked paths, caller-configured sensitive paths, caches, build
            output, or other generated files; disable such caches when running local
            checks. The only protected-path operation authorized by the operator is
            deletion of these exact paths: {json.dumps(sorted(allowed_protected_deletions), ensure_ascii=False)}.
            Do not create or modify them. Even an authorized deletion requires human
            acceptance and cannot receive automated PASS. Report exactly the files
            changed during this stage.

            TASK:
            {task}

            APPROVED DIAGNOSIS AND CHANGE CONTRACT:
            {json.dumps(diagnosis, ensure_ascii=False, indent=2)}

            TARGETED FAILURE TO REPAIR (empty on first implementation):
            {previous_failure}
            """
        ).strip()
        implementation = run_stage(
            args=args,
            repo=repo,
            run_dir=run_dir,
            stage_name=label,
            artifact_prefix=f"{prefix_number:02d}-{label}",
            role=roles["implementation"],
            schema=IMPLEMENTATION_SCHEMA,
            prompt=implementation_prompt,
        )
        post_implementation_state = capture_state(check_topology=True)
        validate_allowed_path_boundaries(repo, allowed_rules)
        validate_verification_command_boundaries(repo, commands)
        validate_verification_entrypoints_unchanged(
            repo,
            verification_entrypoints,
            post_implementation_state,
        )
        if post_implementation_state["index"] != stage_baseline["index"]:
            raise PipelineError(f"{label} changed the Git index", 6)
        if post_implementation_state["git_control"] != stage_baseline["git_control"]:
            raise PipelineError(f"{label} changed Git control metadata", 6)
        stage_changed_paths = changed_paths_between(stage_baseline, post_implementation_state)
        validate_implementation(implementation, allowed_rules, stage_changed_paths)
        if implementation.get("status") != "completed":
            raise PipelineError(f"{label} returned blocked", 3)

        delta, post_implementation_state = enforce_repository_contract(
            repo=repo,
            run_dir=run_dir,
            prefix=f"{prefix_number:02d}-post-{label}-delta",
            baseline=baseline,
            allowed_rules=allowed_rules,
            max_ignored_paths=args.max_ignored_paths,
            sensitive_rules=sensitive_rules,
            redact_untracked_dotfiles=args.redact_untracked_dotfiles,
            check_topology=False,
            allowed_protected_deletions=allowed_protected_deletions,
            max_delta_bytes=args.max_delta_bytes,
            max_untracked_patch_bytes=args.max_untracked_patch_bytes,
            timeout_seconds=args.stage_timeout,
        )

        validate_allowed_path_boundaries(repo, allowed_rules)
        validate_verification_command_boundaries(repo, commands)
        validate_verification_entrypoints_unchanged(
            repo,
            verification_entrypoints,
            post_implementation_state,
        )
        verified, verification = run_verification(
            repo=repo,
            run_dir=run_dir,
            prefix=f"{prefix_number + 1:02d}-verification",
            commands=commands,
            dry_run=False,
            timeout_seconds=args.stage_timeout,
            expected_state=post_implementation_state,
            state_supplier=lambda: capture_state(check_topology=True),
            entrypoints=verification_entrypoints,
            environment=verification_environment,
            max_output_bytes=args.max_command_output_bytes,
            max_total_output_bytes=args.max_verification_output_bytes,
            max_artifact_bytes=args.max_verification_artifact_bytes,
        )
        post_verification_state = capture_state(check_topology=True)
        assert_repo_unchanged(
            post_implementation_state,
            post_verification_state,
            "deterministic verification",
        )
        delta, post_verification_state = enforce_repository_contract(
            repo=repo,
            run_dir=run_dir,
            prefix=f"{prefix_number + 1:02d}-post-verification-delta",
            baseline=baseline,
            allowed_rules=allowed_rules,
            max_ignored_paths=args.max_ignored_paths,
            sensitive_rules=sensitive_rules,
            redact_untracked_dotfiles=args.redact_untracked_dotfiles,
            check_topology=False,
            allowed_protected_deletions=allowed_protected_deletions,
            max_delta_bytes=args.max_delta_bytes,
            max_untracked_patch_bytes=args.max_untracked_patch_bytes,
            timeout_seconds=args.stage_timeout,
        )
        if not delta["introduced_paths"]:
            raise PipelineError(
                "semantic gate failed: completed pipeline has no net repository change",
                8,
            )
        if not verified:
            previous_failure = "DETERMINISTIC VERIFICATION FAILED:\n" + compact_verification(
                verification
            )
            if attempt < args.max_repair_cycles:
                continue
            raise PipelineError(
                f"verification failed after {attempt} repair cycle(s); see {run_dir}",
                4,
            )
        validate_verification_coverage(diagnosis, verification)

        review_prompt = textwrap.dedent(
            f"""
            Act as an independent final reviewer. Do not modify files and do not call
            external tools. Inspect the actual current diff and repository state. Check
            the original task, approved contract, implementation, and raw deterministic
            verification. Any BLOCKER or HIGH finding requires FAIL.

            TASK:
            {task}

            APPROVED DIAGNOSIS:
            {json.dumps(diagnosis, ensure_ascii=False, indent=2)}

            IMPLEMENTATION REPORT:
            {json.dumps(implementation, ensure_ascii=False, indent=2)}

            VERIFICATION:
            {compact_verification(verification)}

            The classified delta below deliberately excludes ignored-file and
            sensitive-untracked content. Do not open or read those paths; review only
            their path, kind, and metadata changes. The content-bearing patch contains
            only ordinary visible repository paths.

            MACHINE-CAPTURED CLASSIFIED GIT DELTA:
            {compact_delta(delta)}
            """
        ).strip()
        review = run_stage(
            args=args,
            repo=repo,
            run_dir=run_dir,
            stage_name="review",
            artifact_prefix=f"{prefix_number + 2:02d}-review",
            role=roles["review"],
            schema=REVIEW_SCHEMA,
            prompt=review_prompt,
        )
        post_review_state = capture_state(check_topology=True)
        assert_repo_unchanged(post_verification_state, post_review_state, "review stage")
        delta, _ = enforce_repository_contract(
            repo=repo,
            run_dir=run_dir,
            prefix=f"{prefix_number + 2:02d}-post-review-delta",
            baseline=baseline,
            allowed_rules=allowed_rules,
            max_ignored_paths=args.max_ignored_paths,
            sensitive_rules=sensitive_rules,
            redact_untracked_dotfiles=args.redact_untracked_dotfiles,
            check_topology=False,
            allowed_protected_deletions=allowed_protected_deletions,
            max_delta_bytes=args.max_delta_bytes,
            max_untracked_patch_bytes=args.max_untracked_patch_bytes,
            timeout_seconds=args.stage_timeout,
        )
        validate_review(review)
        if review.get("verdict") == "PASS":
            result_status, result_exit_code = completion_outcome(
                delta["protected_deletions"]
            )
            summary = {
                "result": result_status,
                "run_dir": str(run_dir),
                "repair_cycles": attempt,
                "changed_paths": delta["introduced_paths"],
                "allowed_paths": diagnosis["change_contract"]["allowed_paths"],
                "git_index_unchanged": True,
                "git_status": delta["status"],
                "git_diff_stat": run_checked(["git", "diff", "HEAD", "--stat"], repo),
                "untracked": delta["untracked"],
                "ignored_metadata": delta["ignored_metadata"],
                "redacted_untracked_metadata": delta["redacted_untracked_metadata"],
                "protected_deletions": delta["protected_deletions"],
                "delta_artifacts": delta["artifacts"],
            }
            write_json(run_dir / "result.json", summary)
            print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
            return result_exit_code

        previous_failure = "INDEPENDENT REVIEW FAILED:\n" + json.dumps(
            review,
            ensure_ascii=False,
            indent=2,
        )
        if attempt >= args.max_repair_cycles:
            raise PipelineError(
                f"review failed after {attempt} repair cycle(s); see {run_dir}",
                5,
            )

    raise PipelineError("unreachable pipeline state")


def main() -> int:
    os.umask(0o077)
    ensure_supported_runner_platform()
    args = parse_args()
    if args.stage_timeout <= 0:
        raise PipelineError("--stage-timeout must be positive")
    if args.max_ignored_paths <= 0:
        raise PipelineError("--max-ignored-paths must be positive", 9)
    repo = args.repo.expanduser().resolve()
    task_path = args.task.expanduser().resolve()
    if not repo.is_dir():
        raise PipelineError(f"repository does not exist: {repo}")
    if not task_path.is_file():
        raise PipelineError(f"task file does not exist: {task_path}")
    git_root = Path(run_checked(["git", "rev-parse", "--show-toplevel"], repo)).resolve()
    if git_root != repo:
        raise PipelineError(f"--repo must be the repository root: {git_root}")
    with repository_lock(repo):
        return run_pipeline_locked(args, repo, task_path)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("ERROR: interrupted; active process group was terminated", file=sys.stderr)
        raise SystemExit(130)
    except PipelineError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(exc.exit_code)

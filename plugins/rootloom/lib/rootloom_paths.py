"""Shared repository-path and sensitive-path policy for Rootloom."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import re


SENSITIVE_EXACT_NAMES = {
    ".env",
    ".git-credentials",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials.json",
    "id_ed25519",
    "id_rsa",
    "kubeconfig",
    "service-account.json",
    "secrets.yaml",
    "secrets.yml",
}
SENSITIVE_SUFFIXES = {".jks", ".key", ".p12", ".pem", ".pfx"}
SENSITIVE_WORDS = {
    "credential",
    "credentials",
    "secret",
    "secrets",
    "service-account",
    "token",
    "tokens",
}
PROTECTED_STATE_WORDS = {"database", "databases", "db", "migration", "migrations"}
PROTECTED_STATE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
WORD_SPLIT = re.compile(r"[._-]+")


def normalize_repo_path(raw: str, *, label: str = "path") -> str:
    value = raw.strip().replace("\\", "/")
    parsed = PurePosixPath(value)
    if (
        not value
        or parsed.is_absolute()
        or any(part in {"", ".", ".."} for part in parsed.parts)
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError(
            f"{label} must be a normalized repository-relative path: {raw!r}"
        )
    return parsed.as_posix()


def validate_git_repo_path(raw: str, *, label: str = "Git path") -> str:
    """Validate a Git-reported path without changing its byte-level meaning."""

    if raw != raw.strip() or "\\" in raw:
        raise ValueError(
            f"{label} cannot be represented safely without changing the path: {raw!r}"
        )
    normalized = normalize_repo_path(raw, label=label)
    if normalized != raw:
        raise ValueError(f"{label} is not a canonical repository path: {raw!r}")
    return normalized


def path_words(path: str) -> set[str]:
    words: set[str] = set()
    for part in PurePosixPath(path).parts:
        lowered = part.lower()
        words.add(lowered)
        words.update(word for word in WORD_SPLIT.split(lowered) if word)
    return words


def is_sensitive_path(path: str, *, extra_sensitive: set[str] | None = None) -> bool:
    normalized = normalize_repo_path(path)
    lowered = normalized.lower()
    parts = PurePosixPath(lowered).parts
    if extra_sensitive:
        for raw_root in extra_sensitive:
            root = normalize_repo_path(raw_root, label="sensitive path").lower()
            if lowered == root or lowered.startswith(root + "/"):
                return True
    if any(
        part in SENSITIVE_EXACT_NAMES
        or part.startswith(".env.")
        or PurePosixPath(part).suffix in SENSITIVE_SUFFIXES
        for part in parts
    ):
        return True
    return bool(path_words(lowered) & SENSITIVE_WORDS)


def is_protected_deletion_path(
    path: str, *, extra_sensitive: set[str] | None = None
) -> bool:
    normalized = normalize_repo_path(path)
    return (
        is_sensitive_path(normalized, extra_sensitive=extra_sensitive)
        or PurePosixPath(normalized).suffix.lower() in PROTECTED_STATE_SUFFIXES
        or bool(path_words(normalized) & PROTECTED_STATE_WORDS)
    )


def sensitive_git_pathspecs() -> list[str]:
    """Return bounded Git globs that discover the shared secret-like policy."""

    patterns = {
        "**/.env",
        "**/.env.*",
        "**/.git-credentials",
        "**/.netrc",
        "**/.npmrc",
        "**/.pypirc",
        "**/credentials.json",
        "**/id_ed25519",
        "**/id_rsa",
        "**/kubeconfig",
        "**/service-account.json",
        "**/secrets.yaml",
        "**/secrets.yml",
        "**/*credential*",
        "**/*credential*/**",
        "**/*secret*",
        "**/*secret*/**",
        "**/*token*",
        "**/*token*/**",
        "**/*.jks",
        "**/*.key",
        "**/*.p12",
        "**/*.pem",
        "**/*.pfx",
    }
    for name in SENSITIVE_EXACT_NAMES:
        patterns.add(f"**/{name}/**")
    for suffix in SENSITIVE_SUFFIXES:
        patterns.add(f"**/*{suffix}/**")
    patterns.add("**/.env.*/**")
    return [f":(glob,icase){pattern}" for pattern in sorted(patterns)]


def validate_nonsensitive_managed_targets(paths: list[str]) -> None:
    sensitive = sorted(path for path in paths if is_sensitive_path(path))
    if sensitive:
        raise ValueError(
            "setup target catalog must not manage sensitive paths: "
            + ", ".join(sensitive)
        )

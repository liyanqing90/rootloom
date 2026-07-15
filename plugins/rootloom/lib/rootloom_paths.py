"""Shared repository-path, secret-material, and security-domain policy."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import re


SENSITIVE_MATERIAL_EXACT_NAMES = {
    ".env",
    ".envrc",
    ".git-credentials",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "kubeconfig",
    "service-account.json",
    "secrets.yaml",
    "secrets.yml",
}
SENSITIVE_MATERIAL_SUFFIXES = {
    ".cer",
    ".crt",
    ".der",
    ".jks",
    ".key",
    ".keystore",
    ".p12",
    ".p7b",
    ".p7c",
    ".pem",
    ".pfx",
    ".ppk",
}
SENSITIVE_MATERIAL_CONFIG_SUFFIXES = {
    ".cfg",
    ".conf",
    ".ini",
    ".json",
    ".properties",
    ".toml",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
SENSITIVE_MATERIAL_WORDS = {
    "certificate",
    "credential",
    "credentials",
    "keystore",
    "secret",
    "secrets",
    "token",
    "tokens",
}
SECURITY_DOMAIN_DESCRIPTOR_WORDS = {
    "controller",
    "example",
    "fixture",
    "handler",
    "interface",
    "manager",
    "model",
    "parser",
    "policy",
    "provider",
    "sample",
    "schema",
    "service",
    "spec",
    "test",
    "tests",
    "type",
    "types",
    "validator",
}
SENSITIVE_MATERIAL_CONTEXTS = (
    frozenset({"client", "secret"}),
    frozenset({"api", "secret"}),
    frozenset({"app", "secret"}),
    frozenset({"api", "token"}),
    frozenset({"access", "token"}),
    frozenset({"refresh", "token"}),
    frozenset({"auth", "token"}),
    frozenset({"bearer", "token"}),
    frozenset({"session", "token"}),
    frozenset({"id", "token"}),
    frozenset({"client", "credentials"}),
    frozenset({"database", "credentials"}),
    frozenset({"db", "credentials"}),
    frozenset({"aws", "credentials"}),
    frozenset({"cloud", "credentials"}),
    frozenset({"gcp", "credentials"}),
    frozenset({"google", "credentials"}),
    frozenset({"azure", "credentials"}),
    frozenset({"service", "account"}),
    frozenset({"private", "key"}),
    frozenset({"api", "key"}),
    frozenset({"access", "key"}),
    frozenset({"tls", "key"}),
    frozenset({"signing", "key"}),
    frozenset({"client", "certificate"}),
    frozenset({"server", "certificate"}),
    frozenset({"tls", "certificate"}),
    frozenset({"client", "keystore"}),
    frozenset({"server", "keystore"}),
    frozenset({"app", "keystore"}),
)
SENSITIVE_MATERIAL_ENVIRONMENTS = {
    "dev",
    "development",
    "local",
    "prod",
    "production",
    "stage",
    "staging",
    "test",
    "testing",
}
SENSITIVE_MATERIAL_DIRECTORIES = {
    ".credentials",
    ".private-keys",
    ".private_keys",
    ".secrets",
    "certificates",
    "certs",
    "keystores",
    "private-keys",
    "private_keys",
    "private-secrets",
    "private_secrets",
}
ROOT_SENSITIVE_MATERIAL_DIRECTORIES = {"credentials", "secrets"}
SOURCE_CODE_SUFFIXES = {
    ".asm",
    ".bash",
    ".c",
    ".cc",
    ".clj",
    ".cljs",
    ".cpp",
    ".cs",
    ".dart",
    ".ex",
    ".exs",
    ".fish",
    ".fs",
    ".fsx",
    ".go",
    ".groovy",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".m",
    ".mm",
    ".pl",
    ".pm",
    ".php",
    ".ps1",
    ".py",
    ".r",
    ".rb",
    ".rs",
    ".scala",
    ".sh",
    ".sql",
    ".svelte",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
    ".zsh",
}
SECURITY_DOMAIN_WORDS = {
    "auth",
    "authentication",
    "authorization",
    "certificate",
    "certificates",
    "credential",
    "credentials",
    "crypto",
    "jwt",
    "keystore",
    "keystores",
    "oauth",
    "oidc",
    "permission",
    "permissions",
    "secret",
    "secrets",
    "security",
    "token",
    "tokens",
}
PROTECTED_STATE_WORDS = {"database", "databases", "db", "migration", "migrations"}
PROTECTED_STATE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
WORD_SPLIT = re.compile(r"[._-]+")
CAMEL_ACRONYM_BOUNDARY = re.compile(r"([A-Z]+)([A-Z][a-z])")
CAMEL_LOWER_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")


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
        words.add(part.lower())
        for segment in WORD_SPLIT.split(part):
            if not segment:
                continue
            separated = CAMEL_ACRONYM_BOUNDARY.sub(r"\1 \2", segment)
            separated = CAMEL_LOWER_BOUNDARY.sub(r"\1 \2", separated)
            words.update(word.lower() for word in separated.split() if word)
    return words


def is_sensitive_material_path(
    path: str, *, extra_sensitive: set[str] | None = None
) -> bool:
    """Return whether path alone identifies content that must remain unread."""

    normalized = normalize_repo_path(path)
    lowered = normalized.casefold()
    parts = PurePosixPath(lowered).parts
    explicit_material_root = parts[0] in (
        SENSITIVE_MATERIAL_DIRECTORIES | ROOT_SENSITIVE_MATERIAL_DIRECTORIES
    )
    source_like = (
        PurePosixPath(lowered).suffix in SOURCE_CODE_SUFFIXES
        and not explicit_material_root
    )
    if extra_sensitive:
        for raw_root in extra_sensitive:
            root = normalize_repo_path(raw_root, label="sensitive path").casefold()
            if lowered == root or lowered.startswith(root + "/"):
                return True
    if any(
        part in SENSITIVE_MATERIAL_EXACT_NAMES
        or part.startswith(".env")
        or PurePosixPath(part).suffix in SENSITIVE_MATERIAL_SUFFIXES
        for part in parts
    ):
        return True
    for part in parts[:-1]:
        if part in SENSITIVE_MATERIAL_DIRECTORIES and (
            part.startswith(".") or not source_like
        ):
            return True
        if (
            part in ROOT_SENSITIVE_MATERIAL_DIRECTORIES
            and not source_like
        ):
            return True
    name = PurePosixPath(normalized).name
    name_words = path_words(name)
    suffix = PurePosixPath(name).suffix.casefold()
    config_like = suffix in SENSITIVE_MATERIAL_CONFIG_SUFFIXES or not suffix
    stem = PurePosixPath(name).stem.casefold()
    if config_like and stem in SENSITIVE_MATERIAL_WORDS:
        return True
    domain_descriptor = bool(name_words & SECURITY_DOMAIN_DESCRIPTOR_WORDS)
    if config_like and any(
        context.issubset(name_words)
        and not ((name_words - context) & SECURITY_DOMAIN_DESCRIPTOR_WORDS)
        for context in SENSITIVE_MATERIAL_CONTEXTS
    ):
        return True
    if (
        config_like
        and not domain_descriptor
        and name_words & {"credentials", "secrets"}
        and name_words & SENSITIVE_MATERIAL_ENVIRONMENTS
    ):
        return True
    return False


def is_security_domain_path(path: str) -> bool:
    """Return whether a path names security behavior that raises review risk."""

    normalized = normalize_repo_path(path)
    words = path_words(normalized)
    return (
        is_sensitive_material_path(normalized)
        or bool(words & SECURITY_DOMAIN_WORDS)
        or {"api", "key"}.issubset(words)
        or {"access", "key"}.issubset(words)
        or {"private", "key"}.issubset(words)
        or {"service", "account"}.issubset(words)
        or {"tls", "key"}.issubset(words)
        or {"signing", "key"}.issubset(words)
    )


def is_protected_deletion_path(
    path: str, *, extra_sensitive: set[str] | None = None
) -> bool:
    normalized = normalize_repo_path(path)
    return (
        is_sensitive_material_path(normalized, extra_sensitive=extra_sensitive)
        or PurePosixPath(normalized).suffix.lower() in PROTECTED_STATE_SUFFIXES
        or bool(path_words(normalized) & PROTECTED_STATE_WORDS)
    )


def sensitive_material_git_pathspecs() -> list[str]:
    """Return bounded Git globs that find secret-material candidates."""

    patterns = {
        "**/.env",
        "**/.env*",
        "**/.git-credentials",
        "**/.netrc",
        "**/.npmrc",
        "**/.pypirc",
        "**/credentials.json",
        "**/id_dsa",
        "**/id_ecdsa",
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
        "**/*certificate*",
        "**/*keystore*",
        "**/*api*key*",
        "**/*access*key*",
        "**/*private*key*",
        "**/*service*account*",
        "**/*tls*key*",
        "**/*signing*key*",
    }
    for name in SENSITIVE_MATERIAL_EXACT_NAMES:
        patterns.add(f"**/{name}/**")
    for directory in (
        SENSITIVE_MATERIAL_DIRECTORIES | ROOT_SENSITIVE_MATERIAL_DIRECTORIES
    ):
        patterns.add(f"**/{directory}/**")
    for suffix in SENSITIVE_MATERIAL_SUFFIXES:
        patterns.add(f"**/*{suffix}")
        patterns.add(f"**/*{suffix}/**")
    patterns.add("**/.env*/**")
    return [f":(glob,icase){pattern}" for pattern in sorted(patterns)]


def validate_nonsensitive_managed_targets(paths: list[str]) -> None:
    sensitive = sorted(path for path in paths if is_sensitive_material_path(path))
    if sensitive:
        raise ValueError(
            "setup target catalog must not manage sensitive paths: "
            + ", ".join(sensitive)
        )

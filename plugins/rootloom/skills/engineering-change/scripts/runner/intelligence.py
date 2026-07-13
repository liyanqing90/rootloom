"""Explainable task risk and verification recommendations for Personal Core."""

from __future__ import annotations

from datetime import date
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any


ASSESSMENT_FORMAT = "rootloom-change-assessment-v1"
MEMORY_FORMAT = "rootloom-project-memory-v1"
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}
TIER_FOR_RISK = {"low": 0, "medium": 1, "high": 2}
MAX_PATCH_BYTES = 1024 * 1024
MAX_MEMORY_BYTES = 1024 * 1024
MAX_MEMORY_MATCHES = 5
MAX_TASK_CHARS = 32 * 1024
MAX_CHANGED_PATHS = 1000
MAX_SIGNAL_PATHS = 20
WORD = re.compile(r"[\w.-]+", re.UNICODE)
DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt", ".png", ".svg", ".webp"}
MEMORY_FILES = {
    "failures": "failures.json",
    "risks": "known-risks.json",
    "decisions": "decisions.json",
}
MEMORY_IDENTITY_FIELDS = {
    "failures": ("summary", "root_cause", "fix", "paths", "evidence", "expires"),
    "risks": ("summary", "mitigation", "paths", "evidence", "expires"),
    "decisions": ("summary", "record", "paths", "evidence", "expires"),
}


def normalized_path(raw: str) -> str:
    value = raw.strip().replace("\\", "/")
    parsed = PurePosixPath(value)
    if not value or parsed.is_absolute() or any(part in {"", ".", ".."} for part in parsed.parts):
        raise ValueError(f"analysis paths must be normalized repository-relative paths: {raw!r}")
    return parsed.as_posix()


def tokens(value: str) -> set[str]:
    return {token.lower() for token in WORD.findall(value) if len(token) > 1}


def path_parts(path: str) -> tuple[str, ...]:
    return tuple(part.lower() for part in PurePosixPath(path).parts)


def is_documentation_or_test(path: str) -> bool:
    parsed = PurePosixPath(path)
    parts = path_parts(path)
    name = parsed.name.lower()
    if any(part in {"doc", "docs", "example", "examples", "test", "tests", "fixtures"} for part in parts):
        return True
    if name.startswith(("readme", "changelog", "contributing", "license", "code_of_conduct")):
        return True
    return parsed.suffix.lower() in DOC_SUFFIXES


def is_product_path(path: str) -> bool:
    if is_documentation_or_test(path):
        return False
    return True


def path_has(path: str, values: set[str]) -> bool:
    parts = set(path_parts(path))
    stem = PurePosixPath(path).stem.lower()
    return bool(parts & values) or stem in values


def add_signal(
    signals: dict[str, dict[str, Any]],
    signal_id: str,
    *,
    risk: str,
    reason: str,
    paths: list[str] | None = None,
) -> None:
    candidate = {
        "id": signal_id,
        "risk": risk,
        "minimum_tier": TIER_FOR_RISK[risk],
        "reason": reason,
        "paths": sorted(set(paths or []))[:MAX_SIGNAL_PATHS],
        "paths_truncated": len(set(paths or [])) > MAX_SIGNAL_PATHS,
    }
    existing = signals.get(signal_id)
    if existing is None or RISK_ORDER[risk] > RISK_ORDER[existing["risk"]]:
        signals[signal_id] = candidate
    elif paths:
        combined = sorted(set(existing["paths"]) | set(paths))
        existing["paths"] = combined[:MAX_SIGNAL_PATHS]
        existing["paths_truncated"] = existing["paths_truncated"] or len(combined) > MAX_SIGNAL_PATHS


def change_paths(
    changes: list[dict[str, str]], anticipated_paths: list[str]
) -> tuple[list[str], dict[str, str]]:
    operations: dict[str, str] = {}
    for item in changes:
        path = normalized_path(item["path"])
        status = item["status"]
        operations[path] = status
        if item.get("original_path"):
            operations[normalized_path(item["original_path"])] = status
    for raw in anticipated_paths:
        operations.setdefault(normalized_path(raw), "planned")
    return sorted(operations), operations


def semantic_match(text: str, english: set[str], localized: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return bool(tokens(lowered) & english) or any(value in text for value in localized)


def fallback_memory_id(kind: str, entry: dict[str, Any]) -> str:
    identity = {
        field: entry.get(field, [] if field in {"paths", "evidence"} else "")
        for field in MEMORY_IDENTITY_FIELDS[kind]
    }
    digest = hashlib.sha256(
        json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"{kind[:-1]}-{digest}"


def related_path_score(candidate: str, requested: str) -> int:
    try:
        candidate = normalized_path(candidate)
    except ValueError:
        return 0
    if candidate == requested:
        return 100
    left = PurePosixPath(candidate)
    right = PurePosixPath(requested)
    if left in right.parents or right in left.parents:
        return 60
    if left.name == right.name:
        return 30
    return 0


def load_memory_matches(
    repo: Path, *, paths: list[str], task: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    root = repo / ".project-memory"
    query = tokens(task)
    active: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    warnings: list[str] = []
    today = date.today()
    if root.is_symlink():
        return [], [], ["ignored symlinked .project-memory directory"]
    for kind, filename in MEMORY_FILES.items():
        path = root / filename
        if path.is_symlink():
            warnings.append(f"ignored symlinked memory file: {filename}")
            continue
        if not path.exists():
            continue
        if path.stat().st_size > MAX_MEMORY_BYTES:
            warnings.append(f"ignored oversized memory file: {filename}")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            warnings.append(f"ignored unreadable memory file: {filename}")
            continue
        if (
            not isinstance(payload, dict)
            or payload.get("format") != MEMORY_FORMAT
            or payload.get("kind") != kind
            or not isinstance(payload.get("entries"), list)
        ):
            warnings.append(f"ignored unsupported memory file: {filename}")
            continue
        for entry in payload["entries"][:1000]:
            if not isinstance(entry, dict) or not isinstance(entry.get("summary"), str):
                continue
            entry_paths = entry.get("paths", [])
            if not isinstance(entry_paths, list) or any(not isinstance(item, str) for item in entry_paths):
                continue
            score = 0
            for candidate in entry_paths:
                for requested in paths:
                    score = max(score, related_path_score(candidate, requested))
            searchable = " ".join(
                str(entry.get(field, ""))
                for field in ("summary", "root_cause", "fix", "mitigation", "record", "evidence")
            )
            score += 5 * len(query & tokens(searchable))
            if score <= 0:
                continue
            item = {
                "id": entry.get("id") or fallback_memory_id(kind, entry),
                "kind": kind,
                "summary": entry["summary"],
                "paths": entry_paths,
                "score": score,
            }
            status = entry.get("status", "active")
            reason: str | None = None
            if status != "active":
                reason = str(status)
            expires = entry.get("expires")
            if not reason and isinstance(expires, str):
                try:
                    if date.fromisoformat(expires) < today:
                        reason = f"expired:{expires}"
                except ValueError:
                    reason = "invalid-expiry"
            if reason:
                item["reason"] = reason
                stale.append(item)
            else:
                active.append(item)
    active.sort(key=lambda item: (-item["score"], item["kind"], item["id"]))
    stale.sort(key=lambda item: (-item["score"], item["kind"], item["id"]))
    return active[:MAX_MEMORY_MATCHES], stale[:MAX_MEMORY_MATCHES], warnings


def repository_commands(repo: Path, risk: str) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    makefile = repo / "Makefile"
    targets: set[str] = set()
    if makefile.is_file() and not makefile.is_symlink() and makefile.stat().st_size <= 256 * 1024:
        text = makefile.read_text(encoding="utf-8", errors="replace")
        targets = set(re.findall(r"^([A-Za-z0-9_.-]+):", text, re.MULTILINE))
    if risk == "low" and "validate" in targets:
        suggestions.append(
            {"command": "make validate", "reason": "repository contract and documentation checks"}
        )
    elif "check" in targets:
        suggestions.append(
            {"command": "make check", "reason": "repository-wide validation and tests"}
        )
    elif "test" in targets:
        suggestions.append({"command": "make test", "reason": "repository test target"})
    elif (repo / "tests").is_dir():
        suggestions.append(
            {
                "command": "python3 -m unittest discover -s tests -p 'test_*.py'",
                "reason": "detected Python unittest tree",
            }
        )
    return suggestions


def verification_plan(
    repo: Path,
    *,
    product_scope: bool,
    has_paths: bool,
    signals: list[dict[str, Any]],
    risk: str,
) -> dict[str, Any]:
    signal_ids = {signal["id"] for signal in signals}
    behaviors: list[dict[str, str]] = []

    def require(item_id: str, behavior: str, reason: str) -> None:
        if any(item["id"] == item_id for item in behaviors):
            return
        behaviors.append({"id": item_id, "behavior": behavior, "reason": reason})

    if product_scope:
        require(
            "primary-behavior",
            "Exercise the user-visible or caller-visible behavior changed by this patch.",
            "A passing helper test does not prove the primary behavior.",
        )
        require(
            "owning-invariant",
            "Prove the invariant at the module or contract that owns the changed behavior.",
            "This distinguishes an owning fix from symptom suppression.",
        )
        require(
            "adjacent-path",
            "Exercise one negative, failure, rollback, or alternate path next to the change.",
            "Adjacent coverage challenges the strongest nearby counterexample.",
        )
    elif has_paths:
        require(
            "documentation-contract",
            "Validate local links, examples, synchronized translations, and rendered assets affected by the change.",
            "Documentation-only changes fail through broken public instructions or assets.",
        )
    else:
        require(
            "scope-needed",
            "Locate the owning paths and consumers before selecting implementation verification.",
            "Task text alone cannot identify the executable verification boundary.",
        )
    if signal_ids & {"authentication", "security"}:
        require(
            "auth-boundaries",
            "Verify success, invalid/expired credential, and unauthorized/insufficient-permission paths.",
            "Authentication and authorization regress at boundary conditions.",
        )
    if signal_ids & {"persistence", "migration"}:
        require(
            "data-compatibility",
            "Verify existing data, forward change, partial failure, and rollback or compensating repair.",
            "Persisted-state changes must account for old/new coexistence.",
        )
    if "money" in signal_ids:
        require(
            "financial-boundaries",
            "Verify rounding, idempotency, duplicate delivery, and failure/retry behavior.",
            "Money paths amplify small consistency errors.",
        )
    if signal_ids & {"concurrency", "state-machine"}:
        require(
            "ordering-and-races",
            "Verify competing orderings, repeated transitions, cancellation, and cleanup.",
            "Happy-path tests rarely expose race or state-transition defects.",
        )
    if "infrastructure" in signal_ids:
        require(
            "deployment-contract",
            "Validate configuration syntax, least privilege, rollout, failure detection, and rollback.",
            "Infrastructure changes affect execution outside the local process.",
        )
    if "public-contract" in signal_ids:
        require(
            "consumer-compatibility",
            "Verify current consumers plus one old/new or omitted/invalid input compatibility path.",
            "Public contracts fail at consumer boundaries, not only at the producer.",
        )
    if "destructive-change" in signal_ids:
        require(
            "destructive-effect",
            "Verify the exact deletion/rename set, dependent references, and a recovery or revert path.",
            "Destructive changes can pass tests while losing required state or assets.",
        )
    if "project-memory" in signal_ids:
        require(
            "historical-counterexample",
            "Reproduce or explicitly rule out the matched historical failure/risk against current code.",
            "Memory is a lead and must be revalidated before it changes the fix.",
        )
    return {
        "status": "suggested-not-executed",
        "required_behaviors": behaviors,
        "suggested_commands": repository_commands(repo, risk),
    }


def code_signal_text(line: str) -> str:
    without_strings = re.sub(r'"(?:\\.|[^"\\])*"', " ", line)
    without_strings = re.sub(r"'(?:\\.|[^'\\])*'", " ", without_strings)
    if without_strings.lstrip().startswith(("#", "//", "/*", "*")):
        return ""
    return re.split(r"\s(?:#|//)", without_strings, maxsplit=1)[0]


def changed_patch_text(value: bytes, product_paths: list[str]) -> tuple[str, bool]:
    selected: list[str] = []
    selected_bytes = 0
    truncated = False
    product_markers = tuple(f" b/{path}" for path in product_paths)
    include_section = False
    binary_section = False
    for raw in io.BytesIO(value):
        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        if line.startswith("diff --git "):
            include_section = any(marker in line for marker in product_markers)
            binary_section = False
            continue
        if not include_section:
            continue
        if line in {"GIT binary patch"} or line.startswith("Binary files "):
            binary_section = True
            continue
        if binary_section or not line.startswith(("+", "-")) or line.startswith(("+++", "---")):
            continue
        candidate = code_signal_text(line[1:]).strip()
        if not candidate:
            continue
        encoded_size = len(candidate.encode("utf-8", errors="replace")) + 1
        if selected_bytes + encoded_size > MAX_PATCH_BYTES:
            truncated = True
            continue
        selected.append(candidate)
        selected_bytes += encoded_size
    return "\n".join(selected), truncated


def analyze_change(
    repo: Path,
    *,
    task: str,
    anticipated_paths: list[str],
    changes: list[dict[str, str]],
    tracked_patch: bytes,
    declared_risk: str | None,
) -> dict[str, Any]:
    repo = repo.expanduser().resolve()
    if len(task) > MAX_TASK_CHARS:
        raise ValueError(f"task text exceeds {MAX_TASK_CHARS} characters")
    if declared_risk is not None and declared_risk not in RISK_ORDER:
        raise ValueError(f"unsupported declared risk: {declared_risk}")
    paths, operations = change_paths(changes, anticipated_paths)
    if len(paths) > MAX_CHANGED_PATHS:
        raise ValueError(f"change analysis exceeds {MAX_CHANGED_PATHS} paths")
    product_paths = [path for path in paths if is_product_path(path)]
    docs_or_tests_only = bool(paths) and all(is_documentation_or_test(path) for path in paths)
    signal_paths = product_paths or ([] if docs_or_tests_only else paths)
    signals: dict[str, dict[str, Any]] = {}

    if product_paths:
        add_signal(
            signals,
            "behavioral-code",
            risk="medium",
            reason="Product code or executable configuration changed.",
            paths=product_paths,
        )
    elif docs_or_tests_only:
        add_signal(
            signals,
            "docs-or-tests-only",
            risk="low",
            reason="Only documentation, examples, assets, fixtures, or tests are in scope.",
            paths=paths,
        )

    auth_paths = [
        path
        for path in signal_paths
        if path_has(path, {"auth", "authentication", "authorization", "oauth", "permission", "permissions", "token", "tokens"})
    ]
    if auth_paths:
        add_signal(
            signals,
            "authentication",
            risk="high",
            reason="Authentication, authorization, permission, or token behavior is in scope.",
            paths=auth_paths,
        )
    security_paths = [path for path in signal_paths if path_has(path, {"security", "crypto", "credential", "credentials", "secret", "secrets"})]
    if security_paths:
        add_signal(
            signals,
            "security",
            risk="high",
            reason="Security or credential handling is in scope.",
            paths=security_paths,
        )
    persistence_paths = [
        path
        for path in signal_paths
        if path_has(path, {"database", "databases", "db", "model", "models", "persistence", "repository", "repositories", "schema", "schemas"})
        or PurePosixPath(path).suffix.lower() == ".sql"
    ]
    if persistence_paths:
        add_signal(
            signals,
            "persistence",
            risk="high",
            reason="Persisted data or schema ownership is in scope.",
            paths=persistence_paths,
        )
    migration_paths = [path for path in signal_paths if path_has(path, {"migration", "migrations", "migrate"})]
    if migration_paths:
        add_signal(
            signals,
            "migration",
            risk="high",
            reason="A data or schema migration path is in scope.",
            paths=migration_paths,
        )
    infrastructure_paths = [
        path
        for path in signal_paths
        if path.startswith(".github/workflows/")
        or path_has(path, {"docker", "terraform", "deploy", "deployment", "infra", "infrastructure", "k8s", "kubernetes"})
        or PurePosixPath(path).name.lower() == "dockerfile"
    ]
    if infrastructure_paths:
        add_signal(
            signals,
            "infrastructure",
            risk="high",
            reason="CI, deployment, container, or infrastructure behavior is in scope.",
            paths=infrastructure_paths,
        )
    money_paths = [path for path in signal_paths if path_has(path, {"billing", "invoice", "money", "payment", "payments", "price", "pricing"})]
    if money_paths:
        add_signal(
            signals,
            "money",
            risk="high",
            reason="Money, billing, pricing, or payment behavior is in scope.",
            paths=money_paths,
        )
    public_paths = [
        path
        for path in signal_paths
        if path_has(path, {"api", "cli", "contract", "contracts"})
        or PurePosixPath(path).name.lower() in {"package.json", "pyproject.toml", "plugin.json", "cargo.toml", "go.mod"}
    ]
    if public_paths:
        add_signal(
            signals,
            "public-contract",
            risk="high",
            reason="A public API, CLI, package, plugin, or persisted contract is in scope.",
            paths=public_paths,
        )

    deleted = [path for path, status in operations.items() if "D" in status or "R" in status]
    if deleted:
        add_signal(
            signals,
            "destructive-change",
            risk="high" if any(path_has(path, {"database", "db", "migration", "secret", ".env"}) for path in deleted) else "medium",
            reason="Deletion or rename changes the available path set and requires dependent-reference review.",
            paths=deleted,
        )
    top_levels = {PurePosixPath(path).parts[0] for path in product_paths}
    if len(product_paths) >= 12 or (len(product_paths) >= 6 and len(top_levels) >= 3):
        add_signal(
            signals,
            "broad-blast-radius",
            risk="high",
            reason="The change spans many product files or top-level ownership areas.",
            paths=product_paths,
        )

    patch_text, patch_text_truncated = changed_patch_text(tracked_patch, product_paths)
    semantic_text = f"{task}\n{patch_text}" if product_paths or not paths else ""
    if not paths and semantic_match(
        semantic_text,
        {"add", "build", "change", "fix", "implement", "refactor", "remove"},
        ("修改", "修复", "新增", "实现", "重构", "删除"),
    ):
        add_signal(
            signals,
            "behavioral-task",
            risk="medium",
            reason="The task describes a behavioral implementation or defect before paths are known.",
        )
    if semantic_match(semantic_text, {"concurrency", "concurrent", "race", "deadlock", "mutex", "lock"}, ("并发", "竞态", "死锁")):
        add_signal(
            signals,
            "concurrency",
            risk="high",
            reason="Task or tracked patch contains concurrency, race, or lock semantics.",
            paths=signal_paths,
        )
    if semantic_match(semantic_text, {"state-machine", "state_machine", "transition", "lifecycle"}, ("状态机", "状态转换", "生命周期")):
        add_signal(
            signals,
            "state-machine",
            risk="high",
            reason="State-machine or lifecycle transitions are in scope.",
            paths=signal_paths,
        )
    if semantic_match(
        semantic_text,
        {
            "access-token",
            "auth",
            "authentication",
            "authorization",
            "jwt",
            "login",
            "oauth",
            "permission",
            "refresh-token",
        },
        ("登录", "认证", "授权", "权限", "令牌"),
    ):
        add_signal(
            signals,
            "authentication",
            risk="high",
            reason="Task or tracked patch contains authentication or authorization semantics.",
            paths=signal_paths,
        )
    if semantic_match(semantic_text, {"migration", "database", "schema", "persisted"}, ("迁移", "数据库", "持久化", "数据结构")):
        add_signal(
            signals,
            "persistence",
            risk="high",
            reason="Task or tracked patch contains persisted-data or migration semantics.",
            paths=signal_paths,
        )
    if semantic_match(
        semantic_text,
        {"argparse", "command-line", "public-api", "public_contract", "add_argument"},
        ("公共接口", "命令行", "契约格式"),
    ):
        add_signal(
            signals,
            "public-contract",
            risk="high",
            reason="Task or tracked patch contains public API, CLI, or contract semantics.",
            paths=signal_paths,
        )
    if semantic_match(semantic_text, {"payment", "billing", "invoice", "money", "price"}, ("支付", "账单", "金额", "价格")):
        add_signal(
            signals,
            "money",
            risk="high",
            reason="Task or tracked patch contains money or billing semantics.",
            paths=signal_paths,
        )

    memory_matches, stale_memory, memory_warnings = load_memory_matches(
        repo, paths=paths, task=task
    )
    if memory_matches and not docs_or_tests_only:
        add_signal(
            signals,
            "project-memory",
            risk="medium",
            reason="Active project failure, risk, or decision memory matches this task/change.",
            paths=sorted({path for item in memory_matches for path in item["paths"]}),
        )

    ordered_signals = sorted(
        signals.values(), key=lambda item: (-RISK_ORDER[item["risk"]], item["id"])
    )
    detected_risk = max(
        (item["risk"] for item in ordered_signals),
        key=lambda value: RISK_ORDER[value],
        default="low",
    )
    effective_risk = detected_risk
    if declared_risk and RISK_ORDER[declared_risk] > RISK_ORDER[effective_risk]:
        effective_risk = declared_risk
    risk_was_raised = bool(
        declared_risk and RISK_ORDER[detected_risk] > RISK_ORDER[declared_risk]
    )
    confidence = "high" if ordered_signals and paths else "medium" if ordered_signals else "low"
    return {
        "format": ASSESSMENT_FORMAT,
        "advisory": True,
        "changed_paths": paths,
        "detected_risk": detected_risk,
        "declared_risk": declared_risk,
        "effective_risk": effective_risk,
        "minimum_tier": TIER_FOR_RISK[detected_risk],
        "risk_was_raised": risk_was_raised,
        "confidence": confidence,
        "input_bounds": {
            "tracked_patch_truncated": patch_text_truncated,
            "maximum_paths": MAX_CHANGED_PATHS,
        },
        "signals": ordered_signals,
        "memory": {
            "matches": memory_matches,
            "stale": stale_memory,
            "warnings": memory_warnings,
        },
        "verification_plan": verification_plan(
            repo,
            product_scope=bool(product_paths or (not paths and ordered_signals)),
            has_paths=bool(paths),
            signals=ordered_signals,
            risk=effective_risk,
        ),
        "limitations": [
            "Static signals cannot prove semantic risk or test sufficiency.",
            "Memory is advisory and must be checked against current repository evidence.",
            "Suggested verification is not executed by the analyzer.",
        ],
    }

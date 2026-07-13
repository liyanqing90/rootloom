#!/usr/bin/env python3
"""Manage Rootloom's small, repository-owned engineering memory."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any


MEMORY_DIR = ".project-memory"
FILES = {
    "failures": "failures.json",
    "risks": "known-risks.json",
    "decisions": "decisions.json",
}
FORMAT = "rootloom-project-memory-v1"
CONTEXT_FORMAT = "rootloom-project-context-v1"
STATUSES = ("active", "resolved", "superseded")
MAX_COLLECTION_BYTES = 1024 * 1024
MAX_ARCHITECTURE_BYTES = 64 * 1024
MAX_ENTRIES = 1000
DEFAULT_CONTEXT_LIMIT = 20
TOKEN = re.compile(r"[\w.-]+", re.UNICODE)
IDENTITY_FIELDS = {
    "failures": ("summary", "root_cause", "fix", "paths", "evidence", "expires"),
    "risks": ("summary", "mitigation", "paths", "evidence", "expires"),
    "decisions": ("summary", "record", "paths", "evidence", "expires"),
}
REQUIRED_FIELDS = {
    "failures": ("summary", "root_cause", "fix"),
    "risks": ("summary", "mitigation"),
    "decisions": ("summary", "record"),
}


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


def memory_root(repo: Path) -> Path:
    resolved = repo.expanduser().resolve()
    if not (resolved / ".git").exists():
        raise ValueError(f"not a Git repository: {resolved}")
    root = resolved / MEMORY_DIR
    if root.is_symlink():
        raise ValueError(f"project-memory directory must not be a symlink: {root}")
    return root


def bounded_text(path: Path, limit: int) -> tuple[str, bool]:
    if path.is_symlink():
        raise ValueError(f"project-memory files must not be symlinks: {path}")
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        return "", False
    if size > limit:
        with path.open("rb") as handle:
            raw = handle.read(limit)
        return raw.decode("utf-8", errors="replace"), True
    return path.read_text(encoding="utf-8"), False


def default_collection(kind: str) -> dict[str, Any]:
    return {"format": FORMAT, "kind": kind, "entries": []}


def parse_iso_date(value: Any, *, field: str, path: Path | None = None) -> date:
    if not isinstance(value, str):
        raise ValueError(f"project-memory {field} must be an ISO date{f': {path}' if path else ''}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"project-memory {field} must be an ISO date{f': {path}' if path else ''}"
        ) from exc


def normalize_path(raw: str) -> str:
    value = raw.strip().replace("\\", "/")
    parsed = PurePosixPath(value)
    if not value or parsed.is_absolute() or any(part in {"", ".", ".."} for part in parsed.parts):
        raise ValueError(f"memory paths must be normalized repository-relative paths: {raw!r}")
    return parsed.as_posix()


def clean_text(value: str, *, field: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field} must not be empty")
    return normalized


def normalized_strings(values: list[str], *, field: str) -> list[str]:
    return sorted({clean_text(value, field=field) for value in values})


def validate_entry(kind: str, entry: Any, *, path: Path) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError(f"project-memory entries must be objects: {path}")
    for field in REQUIRED_FIELDS[kind]:
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            raise ValueError(f"project-memory {kind}.{field} must be a nonempty string: {path}")
    if "date" in entry:
        parse_iso_date(entry["date"], field="date", path=path)
    if "expires" in entry:
        parse_iso_date(entry["expires"], field="expires", path=path)
    if entry.get("status", "active") not in STATUSES:
        raise ValueError(f"project-memory status must be one of {', '.join(STATUSES)}: {path}")
    for field in ("paths", "evidence"):
        values = entry.get(field, [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"project-memory {field} must be a string list: {path}")
        if field == "paths" and "id" in entry:
            for value in values:
                normalize_path(value)
    if "id" in entry and (not isinstance(entry["id"], str) or not entry["id"].strip()):
        raise ValueError(f"project-memory id must be a nonempty string: {path}")
    return entry


def load_collection(root: Path, kind: str) -> dict[str, Any]:
    path = root / FILES[kind]
    if path.is_symlink():
        raise ValueError(f"project-memory files must not be symlinks: {path}")
    if not path.exists():
        return default_collection(kind)
    raw, truncated = bounded_text(path, MAX_COLLECTION_BYTES)
    if truncated:
        raise ValueError(f"project-memory file exceeds {MAX_COLLECTION_BYTES} bytes: {path}")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or payload.get("format") != FORMAT or payload.get("kind") != kind:
        raise ValueError(f"unsupported project-memory file: {path}")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"project-memory entries must be a list: {path}")
    if len(entries) > MAX_ENTRIES:
        raise ValueError(f"project-memory entries exceed {MAX_ENTRIES}: {path}")
    for entry in entries:
        validate_entry(kind, entry, path=path)
    return payload


def save_collection(root: Path, kind: str, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    if len(encoded) > MAX_COLLECTION_BYTES:
        raise ValueError(f"project-memory file would exceed {MAX_COLLECTION_BYTES} bytes")
    atomic_write(root / FILES[kind], encoded)


def initialize(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    architecture = root / "architecture.md"
    if architecture.is_symlink():
        raise ValueError(f"project-memory files must not be symlinks: {architecture}")
    if not architecture.exists():
        atomic_write(
            architecture,
            (
                "# Project architecture\n\n"
                "Record stable module ownership, dependency direction, and invariants here. "
                "Link each rule to current source, tests, or an accepted decision record.\n"
            ).encode("utf-8"),
        )
    readme = root / "README.md"
    if readme.is_symlink():
        raise ValueError(f"project-memory files must not be symlinks: {readme}")
    if not readme.exists():
        atomic_write(
            readme,
            (
                "# Engineering memory\n\n"
                "Reviewable architecture, risk, decision, and failure knowledge for future "
                "engineering tasks. Memory is advisory; current repository evidence wins. "
                "Updates are always explicit.\n"
            ).encode("utf-8"),
        )
    for kind in FILES:
        path = root / FILES[kind]
        if path.is_symlink():
            raise ValueError(f"project-memory files must not be symlinks: {path}")
        if not path.exists():
            save_collection(root, kind, default_collection(kind))


def entry_identity(kind: str, entry: dict[str, Any]) -> str:
    identity = {field: entry.get(field, [] if field in {"paths", "evidence"} else "") for field in IDENTITY_FIELDS[kind]}
    digest = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()[:16]
    return f"{kind[:-1]}-{digest}"


def append_entry(root: Path, kind: str, entry: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    initialize(root)
    payload = load_collection(root, kind)
    entry["id"] = entry_identity(kind, entry)
    for existing in payload["entries"]:
        if existing.get("id", entry_identity(kind, existing)) == entry["id"]:
            return existing, True
    if len(payload["entries"]) >= MAX_ENTRIES:
        raise ValueError(f"project-memory entries exceed {MAX_ENTRIES}")
    payload["entries"].append(entry)
    save_collection(root, kind, payload)
    return entry, False


def words(value: str) -> set[str]:
    return {token.lower() for token in TOKEN.findall(value) if len(token) > 1}


def path_score(candidate: str, requested: str) -> int:
    if candidate == requested:
        return 100
    candidate_path = PurePosixPath(candidate)
    requested_path = PurePosixPath(requested)
    if candidate_path in requested_path.parents or requested_path in candidate_path.parents:
        return 60
    if candidate_path.name == requested_path.name:
        return 30
    return 0


def relevance(kind: str, entry: dict[str, Any], paths: list[str], query_terms: set[str]) -> int:
    if not paths and not query_terms:
        return 1
    score = 0
    for candidate in entry.get("paths", []):
        for requested in paths:
            score = max(score, path_score(candidate, requested))
    searchable = " ".join(
        str(entry.get(field, ""))
        for field in (*REQUIRED_FIELDS[kind], "paths", "evidence")
    )
    score += 5 * len(query_terms & words(searchable))
    return score


def stale_reason(entry: dict[str, Any], today: date) -> str | None:
    status = entry.get("status", "active")
    if status != "active":
        return status
    expires = entry.get("expires")
    if expires and parse_iso_date(expires, field="expires") < today:
        return f"expired:{expires}"
    return None


def context_payload(
    root: Path,
    *,
    paths: list[str],
    query: str,
    limit: int,
    include_stale: bool,
    today: date | None = None,
) -> dict[str, Any]:
    if limit <= 0 or limit > 100:
        raise ValueError("context limit must be between 1 and 100")
    today = today or date.today()
    normalized_paths = sorted({normalize_path(path) for path in paths})
    query_terms = words(query)
    architecture, architecture_truncated = bounded_text(
        root / "architecture.md", MAX_ARCHITECTURE_BYTES
    )
    result: dict[str, Any] = {
        "format": CONTEXT_FORMAT,
        "architecture": architecture,
        "selection": {
            "paths": normalized_paths,
            "query": query,
            "limit_per_kind": limit,
            "include_stale": include_stale,
            "truncated": {},
        },
        "stale": {kind: [] for kind in FILES},
        "warnings": (["architecture.md truncated"] if architecture_truncated else []),
    }
    for kind in FILES:
        ranked: list[tuple[int, str, str, dict[str, Any]]] = []
        stale: list[tuple[int, str, dict[str, Any]]] = []
        for raw in load_collection(root, kind)["entries"]:
            score = relevance(kind, raw, normalized_paths, query_terms)
            if score <= 0:
                continue
            entry = dict(raw)
            entry.setdefault("id", entry_identity(kind, entry))
            entry.setdefault("status", "active")
            reason = stale_reason(entry, today)
            if reason:
                stale.append((score, entry["id"], {"id": entry["id"], "summary": entry["summary"], "reason": reason}))
                if not include_stale:
                    continue
            ranked.append((score, entry.get("date", ""), entry["id"], entry))
        ranked.sort(key=lambda item: item[2])
        ranked.sort(key=lambda item: item[1], reverse=True)
        ranked.sort(key=lambda item: item[0], reverse=True)
        stale.sort(key=lambda item: (-item[0], item[1]))
        result[kind] = [entry for _score, _date, _id, entry in ranked[:limit]]
        result["stale"][kind] = [entry for _score, _id, entry in stale[:limit]]
        result["selection"]["truncated"][kind] = len(ranked) > limit
    return result


def set_status(
    root: Path,
    *,
    kind: str,
    entry_id: str,
    status: str,
    superseded_by: str | None,
) -> dict[str, Any]:
    if status == "superseded" and not superseded_by:
        raise ValueError("superseded status requires --superseded-by")
    if status != "superseded" and superseded_by:
        raise ValueError("--superseded-by is valid only with superseded status")
    payload = load_collection(root, kind)
    for entry in payload["entries"]:
        existing_id = entry.get("id", entry_identity(kind, entry))
        if existing_id != entry_id:
            continue
        entry["id"] = existing_id
        entry["status"] = status
        entry["updated"] = date.today().isoformat()
        if superseded_by:
            entry["superseded_by"] = superseded_by
        else:
            entry.pop("superseded_by", None)
        save_collection(root, kind, payload)
        return entry
    raise ValueError(f"project-memory entry not found: {kind}/{entry_id}")


def add_record_options(parser: argparse.ArgumentParser, *, paths: bool = True) -> None:
    if paths:
        parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--expires")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")

    context = commands.add_parser("context")
    context.add_argument("--path", action="append", default=[])
    context.add_argument("--query", default="")
    context.add_argument("--limit", type=int, default=DEFAULT_CONTEXT_LIMIT)
    context.add_argument("--include-stale", action="store_true")

    failure = commands.add_parser("record-failure")
    failure.add_argument("--summary", required=True)
    failure.add_argument("--root-cause", required=True)
    failure.add_argument("--fix", required=True)
    add_record_options(failure)

    risk = commands.add_parser("record-risk")
    risk.add_argument("--summary", required=True)
    risk.add_argument("--mitigation", required=True)
    add_record_options(risk)

    decision = commands.add_parser("record-decision")
    decision.add_argument("--summary", required=True)
    decision.add_argument("--record", required=True)
    add_record_options(decision)

    status = commands.add_parser("set-status")
    status.add_argument("--kind", choices=tuple(FILES), required=True)
    status.add_argument("--id", required=True)
    status.add_argument("--status", choices=STATUSES, required=True)
    status.add_argument("--superseded-by")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = memory_root(args.repo)
    if args.command == "init":
        initialize(root)
        print(root)
        return 0
    if args.command == "context":
        payload = context_payload(
            root,
            paths=args.path,
            query=args.query,
            limit=args.limit,
            include_stale=args.include_stale,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "set-status":
        entry = set_status(
            root,
            kind=args.kind,
            entry_id=args.id,
            status=args.status,
            superseded_by=args.superseded_by,
        )
        print(json.dumps(entry, ensure_ascii=False, sort_keys=True))
        return 0

    expires = args.expires
    if expires:
        parsed_expiry = parse_iso_date(expires, field="expires")
        if parsed_expiry < date.today():
            raise ValueError("new project-memory entries cannot already be expired")
    common = {
        "date": date.today().isoformat(),
        "status": "active",
        "evidence": normalized_strings(args.evidence, field="evidence"),
        "paths": sorted({normalize_path(path) for path in args.path}),
    }
    if expires:
        common["expires"] = expires
    if args.command == "record-failure":
        kind = "failures"
        entry = {
            **common,
            "summary": clean_text(args.summary, field="summary"),
            "root_cause": clean_text(args.root_cause, field="root-cause"),
            "fix": clean_text(args.fix, field="fix"),
        }
    elif args.command == "record-risk":
        kind = "risks"
        entry = {
            **common,
            "summary": clean_text(args.summary, field="summary"),
            "mitigation": clean_text(args.mitigation, field="mitigation"),
        }
    else:
        kind = "decisions"
        entry = {
            **common,
            "summary": clean_text(args.summary, field="summary"),
            "record": clean_text(args.record, field="record"),
        }
    stored, deduplicated = append_entry(root, kind, entry)
    result = dict(stored)
    result["deduplicated"] = deduplicated
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

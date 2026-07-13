#!/usr/bin/env python3
"""Manage Rootloom's small, repository-owned project memory."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import tempfile
import os
from typing import Any


MEMORY_DIR = ".project-memory"
FILES = {
    "failures": "failures.json",
    "risks": "known-risks.json",
    "decisions": "decisions.json",
}
FORMAT = "rootloom-project-memory-v1"


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
    return resolved / MEMORY_DIR


def default_collection(kind: str) -> dict[str, Any]:
    return {"format": FORMAT, "kind": kind, "entries": []}


def load_collection(root: Path, kind: str) -> dict[str, Any]:
    path = root / FILES[kind]
    if not path.exists():
        return default_collection(kind)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("format") != FORMAT or payload.get("kind") != kind:
        raise ValueError(f"unsupported project-memory file: {path}")
    if not isinstance(payload.get("entries"), list):
        raise ValueError(f"project-memory entries must be a list: {path}")
    return payload


def save_collection(root: Path, kind: str, payload: dict[str, Any]) -> None:
    atomic_write(
        root / FILES[kind],
        (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        ),
    )


def initialize(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    architecture = root / "architecture.md"
    if not architecture.exists():
        atomic_write(
            architecture,
            b"# Project architecture\n\nRecord stable module ownership, dependency direction, and invariants here.\n",
        )
    readme = root / "README.md"
    if not readme.exists():
        atomic_write(
            readme,
            b"# Project memory\n\nReviewable architecture, risk, decision, and failure knowledge for future engineering tasks.\n",
        )
    for kind in FILES:
        path = root / FILES[kind]
        if not path.exists():
            save_collection(root, kind, default_collection(kind))


def append_entry(root: Path, kind: str, entry: dict[str, Any]) -> dict[str, Any]:
    initialize(root)
    payload = load_collection(root, kind)
    payload["entries"].append(entry)
    save_collection(root, kind, payload)
    return entry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    commands.add_parser("context")

    failure = commands.add_parser("record-failure")
    failure.add_argument("--summary", required=True)
    failure.add_argument("--root-cause", required=True)
    failure.add_argument("--fix", required=True)
    failure.add_argument("--path", action="append", default=[])

    risk = commands.add_parser("record-risk")
    risk.add_argument("--summary", required=True)
    risk.add_argument("--mitigation", required=True)
    risk.add_argument("--path", action="append", default=[])

    decision = commands.add_parser("record-decision")
    decision.add_argument("--summary", required=True)
    decision.add_argument("--record", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = memory_root(args.repo)
    if args.command == "init":
        initialize(root)
        print(root)
        return 0
    if args.command == "context":
        payload = {
            "architecture": (
                (root / "architecture.md").read_text(encoding="utf-8")
                if (root / "architecture.md").is_file()
                else ""
            ),
            **{kind: load_collection(root, kind)["entries"] for kind in FILES},
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    common = {"date": date.today().isoformat()}
    if args.command == "record-failure":
        entry = append_entry(
            root,
            "failures",
            {
                **common,
                "summary": args.summary,
                "root_cause": args.root_cause,
                "fix": args.fix,
                "paths": sorted(set(args.path)),
            },
        )
    elif args.command == "record-risk":
        entry = append_entry(
            root,
            "risks",
            {
                **common,
                "summary": args.summary,
                "mitigation": args.mitigation,
                "paths": sorted(set(args.path)),
            },
        )
    else:
        entry = append_entry(
            root,
            "decisions",
            {**common, "summary": args.summary, "record": args.record},
        )
    print(json.dumps(entry, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

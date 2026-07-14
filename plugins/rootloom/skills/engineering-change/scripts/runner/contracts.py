"""Public data contracts for personal engineering summaries."""

from __future__ import annotations

from dataclasses import dataclass


SUMMARY_FORMAT = "rootloom-engineering-summary-v1"
SUMMARY_SCHEMA_REVISION = 3
RISK_LEVELS = ("low", "medium", "high")
DANGEROUS_DELETE_EXIT = 10
QUALITY_STATUSES = (
    "VERIFIED_CHANGE",
    "SEMANTICALLY_REVIEWED",
    "MECHANICALLY_VERIFIED",
    "COMMANDS_PASSED",
    "NO_CHANGE",
    "FAILED",
    "UNVERIFIED",
)


@dataclass(frozen=True)
class VerificationResult:
    command: list[str]
    exit_code: int
    duration_seconds: float
    passed: bool
    timed_out: bool = False
    output_bytes_observed: int = 0
    output_bytes_retained: int = 0
    output_limit_exceeded: bool = False
    process_tree_converged: bool = True

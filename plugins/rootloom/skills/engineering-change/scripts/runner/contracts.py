"""Public data contracts for personal engineering summaries."""

from __future__ import annotations

from dataclasses import dataclass


SUMMARY_FORMAT = "rootloom-engineering-summary-v1"
RISK_LEVELS = ("low", "medium", "high")
DANGEROUS_DELETE_EXIT = 10


@dataclass(frozen=True)
class VerificationResult:
    command: list[str]
    exit_code: int
    duration_seconds: float
    passed: bool

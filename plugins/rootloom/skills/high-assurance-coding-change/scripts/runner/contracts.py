"""Dependency-free Human Review and verifier resource contracts."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import VerificationError


MAX_HUMAN_REVIEW_ARTIFACTS = 256
MAX_HUMAN_REVIEW_DECISION_BYTES = 1024 * 1024
MAX_HUMAN_REVIEW_IDENTITY_BYTES = 4096
MAX_HUMAN_REVIEW_DIAGNOSTIC_BYTES = 4096

DEFAULT_VERIFY_MAX_IGNORED_PATHS = 50_000
DEFAULT_VERIFY_MAX_STATE_PATHS = 200_000
DEFAULT_VERIFY_MAX_STATE_BYTES = 16 * 1024 * 1024
DEFAULT_VERIFY_MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
DEFAULT_VERIFY_MAX_TOTAL_BYTES = 512 * 1024 * 1024
DEFAULT_VERIFY_TIMEOUT_SECONDS = 120

VERIFY_INVALID_EXIT = 9
VERIFY_STALE_EXIT = 12
VERIFY_UNVERIFIED_EXIT = 13


@dataclass(frozen=True)
class VerificationLimits:
    max_ignored_paths: int = DEFAULT_VERIFY_MAX_IGNORED_PATHS
    max_state_paths: int = DEFAULT_VERIFY_MAX_STATE_PATHS
    max_state_bytes: int = DEFAULT_VERIFY_MAX_STATE_BYTES
    max_artifact_bytes: int = DEFAULT_VERIFY_MAX_ARTIFACT_BYTES
    max_total_bytes: int = DEFAULT_VERIFY_MAX_TOTAL_BYTES
    timeout_seconds: int = DEFAULT_VERIFY_TIMEOUT_SECONDS

    def validate(self) -> "VerificationLimits":
        for field, value in self.__dict__.items():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise VerificationError(
                    f"verifier limit {field} must be a positive integer"
                )
        return self

    def constrain_policy(self, recorded: dict[str, object]) -> dict[str, object]:
        ceilings = {
            "max_ignored_paths": self.max_ignored_paths,
            "max_state_paths": self.max_state_paths,
            "max_state_bytes": self.max_state_bytes,
            "max_human_review_artifact_bytes": self.max_artifact_bytes,
            "max_human_review_total_bytes": self.max_total_bytes,
            "max_human_review_binding_seconds": self.timeout_seconds,
        }
        effective = dict(recorded)
        for field, ceiling in ceilings.items():
            value = recorded[field]
            if not isinstance(value, int) or isinstance(value, bool):
                raise VerificationError(f"recorded verifier policy {field} is unusable")
            if value > ceiling:
                raise VerificationError(
                    f"recorded verifier policy {field} exceeds the local ceiling"
                )
            effective[field] = min(value, ceiling)
        return effective

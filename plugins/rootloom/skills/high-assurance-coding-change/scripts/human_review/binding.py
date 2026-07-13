"""Current-state recomputation for a structurally valid Human Review Binding."""

from __future__ import annotations

import os
from pathlib import Path
import stat
from typing import Any

from runner.errors import BindingDriftError, EvidenceInvalidError, VerificationError
from runner.git_capture import read_only_git_environment


def _preflight_current_artifacts(
    runtime: Any,
    run_dir: Path,
    expected: dict[str, Any],
) -> None:
    excluded = {"result.json", "human-review.ndjson", "human-review-summary.json"}
    descriptor = -1
    try:
        descriptor, _ = runtime._safe_run_directory_descriptor(run_dir)
        current_names = sorted(name for name in os.listdir(descriptor) if name not in excluded)
        expected_names = sorted(expected["artifacts"])
        if current_names != expected_names:
            raise BindingDriftError(
                "human review Artifact name set is stale"
            )
        for name in expected_names:
            info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise EvidenceInvalidError(
                    "human review Artifact is not a regular single-link file"
                )
    except (BindingDriftError, EvidenceInvalidError):
        raise
    except FileNotFoundError as exc:
        raise BindingDriftError("human review Artifact is stale or missing") from exc
    except OSError as exc:
        raise VerificationError(
            "human review Artifact inventory could not be read"
        ) from exc
    finally:
        if descriptor >= 0:
            runtime.close_descriptor_quietly(descriptor)


def _preflight_protected_deletions(repo: Path, paths: list[str]) -> None:
    for path in paths:
        try:
            (repo / path).lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise VerificationError(
                "protected deletion state could not be read"
            ) from exc
        raise BindingDriftError("protected deletion state is stale; target exists")


def recompute_human_review_binding(
    runtime: Any,
    repo: Path,
    run_dir: Path,
    result: dict[str, Any],
    expected: dict[str, Any],
    protected_deletions: list[str],
) -> dict[str, Any]:
    """Recapture current state only after the caller validates persisted schema."""

    _preflight_current_artifacts(runtime, run_dir, expected)
    _preflight_protected_deletions(repo, protected_deletions)
    with read_only_git_environment():
        return runtime.compute_human_review_binding(
            repo,
            run_dir,
            runtime.human_review_result_core_sha256(result),
            protected_deletions,
            state_policy=expected["state_policy"],
            metadata_only_floor=expected["final_metadata_only_floor_paths"],
        )

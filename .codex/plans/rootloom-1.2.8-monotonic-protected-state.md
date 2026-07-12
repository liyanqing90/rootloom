# Rootloom 1.2.8 protected-state and process cleanup hardening

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security
- Risk: Tier 2 (Governed)

## Goal and observable success

Keep every path classified as ignored or sensitive at the run baseline metadata-only for the entire high-assurance pipeline, even if a writer changes ignore configuration. Ensure managed command process groups that ignore SIGTERM are escalated to SIGKILL and cannot outlive verification. Focused regression tests and the repository validation suite must pass.

## Non-goals

- Redesigning the complete repository snapshot model.
- Adding native Windows support to the strict runner.
- Publishing or releasing without separate explicit authorization.

## Baseline evidence

- `capture_repo_state()` currently derives content-read eligibility from the current ignore and sensitivity classification, so removing an ignore rule can make a baseline-protected path content-readable before the protected-change gate executes.
- `terminate_process_group()` waits on the already-exited direct child after SIGTERM; a surviving descendant that ignores SIGTERM can therefore avoid SIGKILL escalation.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Protected classification can shrink between snapshots | fact | local repository source | 2026-07-12 | `run_pipeline.py:capture_repo_state` | Current HEAD; no protected content read |
| Process cleanup waits on the direct child rather than the process group | fact | local repository source | 2026-07-12 | `run_pipeline.py:terminate_process_group` | Current HEAD |

## Governed defect diagnosis

- Observed failure: a baseline ignored path can be declassified and hashed in a later snapshot; a descendant that ignores SIGTERM can remain alive after its parent exits.
- Competing hypotheses: protected validation alone prevents leakage; direct-child `communicate()` proves group exit. Both are rejected because the content read occurs before validation and the direct child may already be reaped while descendants remain.
- Ownership path: repository-state capture owns content-read classification; managed-process cleanup owns descendant termination.
- Violated invariant: baseline-protected content must never become readable during a run; no managed command descendant may survive command completion.
- Root cause: both controls recalculate or observe only current/direct state instead of preserving the run-level security boundary.
- Root-cause alignment: PASS

## Constraints and invariants

- Never read or patch baseline-protected file content.
- Preserve exact protected-deletion behavior and metadata-only artifacts.
- Preserve original nonzero command exit codes while failing successful commands closed when leftovers are found.
- Keep the strict runner POSIX-only as currently documented.

## Impact map

- Producers: high-assurance runner repository snapshots and managed verification commands.
- Consumers: contract gates, delta artifacts, reviewer prompts, verification records.
- Persisted data: runner artifacts only.
- Public contracts: runner version and plugin patch version.
- Generated artifacts: none.
- External systems: none for local implementation.

## Design and decisions

- Ownership: add a baseline-derived metadata-only floor to repository-state capture and propagate it through the run closure and standalone contract enforcement.
- Interfaces: snapshots expose `metadata_only_paths`; untracked manifests use that set to decide whether content patching is permitted.
- Dependency direction: contract enforcement derives its floor from the supplied baseline; callers cannot weaken it.
- Compatibility window: additive state key and optional keyword argument; existing callers remain valid.
- Alternatives rejected: checking only after snapshot capture, because the prohibited read would already have occurred.

## Implementation sequence

1. Add protected-path helpers and monotonic metadata-only snapshot semantics.
2. Make process-group termination poll the group and escalate from SIGTERM to SIGKILL.
3. Add declassification and SIGTERM-ignoring-child regressions.
4. Bump Runner/plugin patch versions, changelog, and repository contract checks.
5. Run focused tests and full repository validation.

## Rollout, failure, and rollback

- Dry-run/preview: inspect the local diff and focused test results.
- Mixed-version behavior: plugin 1.2.8 ships Runner 2.10 as one repository change.
- Failure detection: unit-test failure, validation failure, or leaked marker file.
- Rollback or compensation: revert the scoped commit before any publication.
- Irreversible point: none; publication requires explicit approval.

## Verification

- Original failure path: regression that removes `.gitignore` or `.git/info/exclude` classification while rejecting any content fingerprint of the protected file.
- Owning-boundary invariant: repository-state tests assert metadata-only fingerprints and pre-delta rejection.
- Adjacent negative/alternate path: ordinary visible untracked files retain content patches.
- Focused tests: `python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py`
- Contract/migration tests: `python3 scripts/validate_repo.py`
- Type/lint/build/package: `make check`
- UI/browser evidence: not applicable.
- Security/dependency checks: regression test with a SIGTERM-ignoring descendant and delayed marker.
- Post-action verification: clean scoped diff and version consistency search.

## Risks

- Risk: process-group existence polling may behave differently around short-lived zombies.
  - Mitigation: bounded TERM and KILL waits with fail-closed behavior and real subprocess tests.
  - Residual risk: platform-specific timing remains possible within the documented POSIX support boundary.

## Decision log

- 2026-07-12 — Preserve baseline protected classification as a monotonic floor because current Git ignore state is not a security authority after writer execution.
- 2026-07-12 — Poll the process group itself, not the direct child process, before deciding cleanup succeeded.
- 2026-07-12 — Reject declassification even without file metadata changes and apply the monotonic boundary to verification-entrypoint resolution as well as repository snapshots.
- 2026-07-12 — Verification completed: `make check` passed 41 repository tests and 47 Runner tests; `make compatibility-smoke` passed on `codex-cli 0.144.0-alpha.4` with no managed leftovers and exact pre-existing configuration restoration.
- 2026-07-12 — Pre-release review reproduced a direct timed-out process that ignored SIGTERM being killed but misreported as surviving because the post-SIGKILL group check ran before reaping that process. The release gate was reopened for a targeted repair and regression.
- 2026-07-12 — The targeted repair now reaps the direct process after SIGKILL before confirming the remaining process group. Final verification passed: 41 repository tests, 48 Runner tests, repository validation, diff checks, and the Codex CLI compatibility smoke with no managed leftovers and exact config restoration.
- 2026-07-12 — User explicitly authorized “修复后 发布新版本”. Publication target is `liyanqing90/rootloom` `main`, annotated tag `v1.2.8`, and a non-draft GitHub Release; no force-push or pull request is required by the repository's established release sequence.
- 2026-07-12 — Published code commit `d5ce40cb005721981bac2f2d22b8cbe9389b37e8`. Its tree `b37c00e5b7ca7bebcf294904b64a877e1f968c3e` exactly matches the locally verified release tree. GitHub CI passed at `https://github.com/liyanqing90/rootloom/actions/runs/29188066531`.
- 2026-07-12 — Created annotated tag object `bfa6219291168f763ad445ccf3355bc15e0f7a7a` for `v1.2.8` and published `https://github.com/liyanqing90/rootloom/releases/tag/v1.2.8` as a non-draft, non-prerelease Release.

## Durable decision records

- None; this hardens an existing security contract rather than introducing a new durable architecture decision.

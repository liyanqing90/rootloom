# Bind human acceptance and setup recovery to exact local state

- Status: accepted
- Date: 2026-07-12
- Owners: Rootloom maintainers
- Scope: protected-deletion Human Review and setup transaction recovery

## Context

Exit 10 previously had no durable accept/reject transition, and setup compensation covered caught exceptions but not an orphaned process. Automatic success or blind recovery would violate the same invariant: a state transition must bind the exact evidence and filesystem state it authorizes.

## Decision

- Human Review v3 uses versioned binding and decision records over the canonical final Result core; a bounded canonical commitment to visible content fingerprints, metadata-only fingerprints, status/path sets, Git index, and Git control state; each authorized deletion's exact-missing state and lexical parent boundaries; reviewed private Artifact hashes captured through stable directory-relative no-follow descriptors; asserted reviewer plus local account/uid; and decision time. Accept/reject re-reads Result and computes the pre-write commitment under the repository lock, fsyncs the no-follow terminal record, recomputes the complete commitment, and compensates the record if that post-write check drifts. Existing v2 results fail closed rather than being silently upgraded from evidence they never captured.
- Setup recovery v2 journals remain Manifest-bound, while Manifest recovery schema v2 records producer version and target type. Recovery owns literal historical target catalogs, including the implicit schema emitted through 1.2.12, rather than consulting only the targets known by the currently installed plugin. Apply/rollback refuse unresolved transactions, and ordinary rollback verifies the committed Manifest binding. `recover` restores the pre-state only after the entire unique, historically managed-target-only plan—including every backup, Hash, before/after Mode, and setup-state payload—has been validated while current state still matches recorded before/after hashes and modes; ambiguous edits fail closed.
- Local identity and private append-only files are attribution, not cryptographic organizational identity or WORM storage. Atomic rename does not prove storage durability under corruption or power loss.

## Alternatives rejected

- Treat exit 10 as success — rejected because no human decision exists.
- Accept based only on Git SHA — rejected because worktree and private evidence can drift without a commit.
- Accept based on HEAD plus ordinary Git status — rejected because recreated ignored deletion targets do not appear in that status.
- Trust a startup-only isolation-launcher hash — rejected because later stage/verification spawns reopen the path and require their own immediate identity check.
- Automatically overwrite every orphaned target — rejected because legitimate post-crash user edits could be destroyed.
- Derive recovery allowlists only from current `all_targets()` — rejected because a future target rename/removal could orphan an older interrupted transaction.

## Consequences and limits

- Human Review Result creation and acceptance now pay the bounded full-state capture cost and can fail closed on the configured path/byte ceilings.
- The repository lock serializes cooperative Rootloom writers only. A post-write check narrows but cannot eliminate arbitrary external-process TOCTOU; higher assurance still requires an immutable snapshot/worktree and external signing or WORM storage.
- Isolation launcher identity is checked through stable no-follow descriptors at configuration and immediately before spawn, but Rootloom does not attest launcher semantics or eliminate the final path-to-`exec` race.
- Every future managed target rename/removal must preserve the historical recovery schema entry until an explicit migration/deprecation decision supersedes it.

## Evidence provenance

- Verified repository fact, 2026-07-13: `compute_human_review_binding()` in the 1.2.12 tree bound HEAD/status but did not receive protected deletion paths; supplied audit reproduction showed an ignored `.env` could be recreated without status drift. No protected content was read.
- Verified repository fact, 2026-07-13: `review_decision.py` computed its binding and wrote a decision without `repository_lock(repo)` or a post-write capture.
- Verified repository fact, 2026-07-13: `build_recovery_plan()` derived its allowlist directly from current `all_targets(plugin_root())`.
- Executable regression evidence is owned by `plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py` and `tests/test_setup_rootloom.py`.

## Verification

- Runner tests cover ignored deletion-target recreation refusal, canonical state commitments, repository-lock contention, post-write drift compensation, Result/Artifact drift refusal, no-follow terminal files, full-capacity Artifact binding, durable acceptance, launcher identity drift, selector-initialization cleanup, and duplicate terminal refusal.
- Setup tests cover interrupted apply and rollback recovery, Manifest binding in recovery and ordinary rollback, historical target recovery after current-catalog removal, unknown-target and corrupt-backup refusal before mutation, content/mode drift, apply blocking, superseded terminal journals, idempotent completion, and ambiguous-edit refusal.
- `make check` and compatibility smoke remain release gates.

## 2026-07-13 amendment

The v1 candidate covered interrupted apply but did not journal rollback, did not bind the final Result core, and validated restoration sources too late. Version 2 closes those ownership gaps rather than documenting them as residual limitations. Version 1 was never published as an installable Rootloom release.

## 2026-07-13 v3 amendment

The published v2 wording overstated “exact local state”: HEAD plus ordinary status omitted recreated ignored deletion targets, acceptance was not repository-lock serialized, and Recovery depended on the current target catalog. Version 3 binds the bounded canonical repository state and exact deletion assertions, adds locked pre/post decision checks, and versions historical Recovery target schemas. This amendment supersedes the Human Review v2 acceptance contract while retaining v2 as a fail-closed legacy format.

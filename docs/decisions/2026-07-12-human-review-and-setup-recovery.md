# Bind human acceptance and setup recovery to exact local state

- Status: accepted
- Date: 2026-07-12
- Owners: Rootloom maintainers
- Scope: protected-deletion Human Review and setup transaction recovery

## Context

Exit 10 previously had no durable accept/reject transition, and setup compensation covered caught exceptions but not an orphaned process. Automatic success or blind recovery would violate the same invariant: a state transition must bind the exact evidence and filesystem state it authorizes.

## Decision

- Human Review v2 uses versioned binding and decision records over the canonical final Result core, repository HEAD, Git status, reviewed private Artifact hashes captured through stable directory-relative no-follow descriptors, asserted reviewer plus local account/uid, and decision time. Acceptance refuses Result/evidence drift and duplicate terminal decisions; the terminal record is fsynced through a no-follow descriptor and its summary is reconstructable.
- Setup recovery v2 writes a Manifest-bound phase journal and prior-state backup before the first apply or rollback mutation. Apply/rollback refuse unresolved transactions, and ordinary v2 rollback verifies the committed Manifest binding. `recover` restores the pre-state only after the entire unique, managed-target-only plan—including every backup, Hash, before/after Mode, and setup-state payload—has been validated while current state still matches recorded before/after hashes and modes; ambiguous edits fail closed.
- Local identity and private append-only files are attribution, not cryptographic organizational identity or WORM storage. Atomic rename does not prove storage durability under corruption or power loss.

## Alternatives rejected

- Treat exit 10 as success — rejected because no human decision exists.
- Accept based only on Git SHA — rejected because worktree and private evidence can drift without a commit.
- Automatically overwrite every orphaned target — rejected because legitimate post-crash user edits could be destroyed.

## Verification

- Runner tests cover Result/Artifact drift refusal, no-follow terminal files, full-capacity Artifact binding, durable acceptance, and duplicate terminal refusal.
- Setup tests cover interrupted apply and rollback recovery, Manifest binding in recovery and ordinary rollback, unknown-target and corrupt-backup refusal before mutation, content/mode drift, apply blocking, superseded terminal journals, idempotent completion, and ambiguous-edit refusal.
- `make check` and compatibility smoke remain release gates.

## 2026-07-13 amendment

The v1 candidate covered interrupted apply but did not journal rollback, did not bind the final Result core, and validated restoration sources too late. Version 2 closes those ownership gaps rather than documenting them as residual limitations. Version 1 was never published as an installable Rootloom release.

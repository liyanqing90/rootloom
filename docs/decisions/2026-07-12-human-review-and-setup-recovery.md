# Bind human acceptance and setup recovery to exact local state

- Status: accepted
- Date: 2026-07-12
- Owners: Rootloom maintainers
- Scope: protected-deletion Human Review and setup transaction recovery

## Context

Exit 10 previously had no durable accept/reject transition, and setup compensation covered caught exceptions but not an orphaned process. Automatic success or blind recovery would violate the same invariant: a state transition must bind the exact evidence and filesystem state it authorizes.

## Decision

- Human Review v4 uses versioned binding and decision records over the canonical final Result core and canonical run-directory identity; the complete final metadata-only floor; a bounded canonical commitment to visible content fingerprints, metadata-only fingerprints, status/path sets, Git index, and Git control state; each authorized deletion's exact-missing state and lexical parent boundaries; reviewed private Artifact hashes with count, per-file, aggregate-byte, and time budgets; asserted reviewer plus local account/uid; and decision time. Accept/reject reads Result through a bounded directory-relative no-follow descriptor, rejects v2/v3 or a malformed v4 policy/floor before repository capture, and computes the pre-write commitment under the repository lock. It then fsyncs the no-follow terminal record, safely re-reads the complete canonical Result, recomputes the complete commitment, re-reads Result again, and compensates the record if any check drifts. Existing v2/v3 results fail closed rather than being silently upgraded from evidence they never captured.
- Setup, project Guidance, and Strict Runner repository locks use the shared `plugins/rootloom/lib/rootloom_lock.py` boundary. POSIX opens the target relative to a stable no-follow parent descriptor; Windows uses reparse-point-aware parent and target handles. Both require a direct regular single-link target with stable identity, acquire non-blockingly, and only then truncate/write owner data.
- Setup recovery v2 journals remain Manifest-bound, while Manifest recovery schema v2 records producer version and target type. Recovery owns literal historical target catalogs, including the implicit schema emitted through 1.2.12, rather than consulting only the targets known by the currently installed plugin. Apply/rollback refuse unresolved transactions, and ordinary rollback verifies the committed Manifest binding. `recover` restores the pre-state only after the entire unique, historically managed-target-only plan—including every backup, Hash, before/after Mode, and setup-state payload—has been validated while current state still matches recorded before/after hashes and modes; ambiguous edits fail closed.
- Local identity and private append-only files are attribution, not cryptographic organizational identity or WORM storage. Atomic rename does not prove storage durability under corruption or power loss.

## Alternatives rejected

- Treat exit 10 as success — rejected because no human decision exists.
- Accept based only on Git SHA — rejected because worktree and private evidence can drift without a commit.
- Accept based on HEAD plus ordinary Git status — rejected because recreated ignored deletion targets do not appear in that status.
- Trust a startup-only isolation-launcher hash — rejected because later stage/verification spawns reopen the path and require their own immediate identity check.
- Accept a copied private Run directory — rejected because duplicate directories could otherwise produce independent terminal decisions for one evidence set; Result and binding must name the supplied directory and its stable identity.
- Reclassify metadata-only files from the current ignore rules before checking drift — rejected because the check itself would read content that the original Result treated as protected.
- Hash every private Artifact without source-level budgets — rejected because a local reviewer command must not turn an oversized evidence directory into unbounded I/O.
- Automatically overwrite every orphaned target — rejected because legitimate post-crash user edits could be destroyed.
- Derive recovery allowlists only from current `all_targets()` — rejected because a future target rename/removal could orphan an older interrupted transaction.

## Consequences and limits

- Human Review Result creation and acceptance now pay the bounded full-state capture cost and can fail closed on configured state, Artifact, Result-size, or time ceilings.
- v4 Result is intentionally incompatible with v2/v3 because prior bindings do not carry the final metadata-only floor or canonical run-directory identity.
- The repository lock serializes cooperative Rootloom writers only. A post-write check narrows but cannot eliminate arbitrary external-process TOCTOU; higher assurance still requires an immutable snapshot/worktree and external signing or WORM storage.
- Isolation launcher identity is checked through stable no-follow descriptors at configuration and immediately before spawn, but Rootloom does not attest launcher semantics or eliminate the final path-to-`exec` race.
- Every future managed target rename/removal must preserve the historical recovery schema entry until an explicit migration/deprecation decision supersedes it.

## Evidence provenance

- Verified repository fact, 2026-07-13: `compute_human_review_binding()` in the 1.2.12 tree bound HEAD/status but did not receive protected deletion paths; supplied audit reproduction showed an ignored `.env` could be recreated without status drift. No protected content was read.
- Verified repository fact, 2026-07-13: `review_decision.py` computed its binding and wrote a decision without `repository_lock(repo)` or a post-write capture.
- Verified repository fact, 2026-07-13: `build_recovery_plan()` derived its allowlist directly from current `all_targets(plugin_root())`.
- Executable regression evidence is owned by `plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py` and `tests/test_setup_rootloom.py`.
- Verified repository fact, 2026-07-13: the 1.2.13 repository, Setup, and Guidance lock paths checked a pathname and then used ordinary `os.open`; the Runner repository lock followed and truncated a final symlink directly. Synthetic local victims were preserved by the v1.2.14 shared opener regressions.

## Verification

- Runner tests cover ignored deletion-target recreation refusal, canonical state commitments, full metadata-floor reuse after ignore declassification, repository-lock contention, copied-run refusal, post-write repository and Result drift compensation, no-follow bounded Result/Artifact reads, Artifact per-file/aggregate/deadline limits, full-capacity binding, durable acceptance, launcher identity drift, selector-initialization cleanup, and duplicate terminal refusal.
- Shared-lock and Setup tests cover final symlink, hardlink, symlinked-parent, identity, and contention refusal, plus interrupted apply and rollback recovery, Manifest binding in recovery and ordinary rollback, historical target recovery after current-catalog removal, unknown-target and corrupt-backup refusal before mutation, content/mode drift, apply blocking, superseded terminal journals, idempotent completion, and ambiguous-edit refusal.
- `make check` and compatibility smoke remain release gates.

## 2026-07-13 amendment

The v1 candidate covered interrupted apply but did not journal rollback, did not bind the final Result core, and validated restoration sources too late. Version 2 closes those ownership gaps rather than documenting them as residual limitations. Version 1 was never published as an installable Rootloom release.

## 2026-07-13 v3 amendment

The published v2 wording overstated “exact local state”: HEAD plus ordinary status omitted recreated ignored deletion targets, acceptance was not repository-lock serialized, and Recovery depended on the current target catalog. Version 3 binds the bounded canonical repository state and exact deletion assertions, adds locked pre/post decision checks, and versions historical Recovery target schemas. This amendment supersedes the Human Review v2 acceptance contract while retaining v2 as a fail-closed legacy format.

## 2026-07-13 v4 amendment

The v3 contract still allowed the review recapture to derive content eligibility from current ignore rules before comparing commitments, trusted only the initially loaded Result during the write window, and did not bind one terminal decision to the original Run directory. Version 4 carries the complete final metadata-only floor into recapture, binds path plus directory identity, safely re-reads the full canonical Result twice after append, and adds Artifact/Result resource boundaries. The same release moves all three lock users behind a no-follow/reparse-aware shared opener. Isolation launcher path-to-`exec`, arbitrary external writers after the last check, storage durability, and cryptographic identity remain explicitly external boundaries.

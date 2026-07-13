# Rootloom 1.2.15 Human Review I/O ownership hardening

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-13
- Task type: security, persisted audit-contract repair, and release
- Risk: Tier 2 (Governed)

## Goal and observable success

Close every actionable 1.2.14 independent-review finding without weakening Human Review v4 or changing its persisted format. The terminal decision must be created, appended, validated, and compensated through one pinned single-link descriptor; initial Binding must preserve and exactly match the final validated repository checkpoint; Artifact hashing must stop at the byte source when a file grows past its per-file or remaining aggregate allowance.

Success requires victim-preservation regressions for an initial hardlink, create-to-append path replacement, and compensation-time replacement; a no-read plus commitment-drift regression between the final contract and initial Binding; a growing-read budget regression; full local checks; exact-sha cross-platform CI; and publication as `v1.2.15` / Strict Runner `2.20` under the user's standing direct-release authorization.

## Non-goals

- Container/cgroup isolation, stable-FD launcher execution, external signatures, WORM storage, enterprise identity, or parent-directory crash durability.
- Preventing an arbitrary same-UID process from mutating repository state after the final checked operation.
- Refactoring unrelated Human Review, process, or Artifact subsystems.
- Force-push, tag movement, destructive release rollback, or unrelated cleanup.

## Baseline evidence

- `v1.2.14` points to `7cc3bb9f5de69b13c77f1c06e499a8328e095204`; `main` began clean at publication-record commit `8e141cd88b7bf64ef0208cfdbb44350baa0b11cb`.
- `ensure_empty_private_file()`, `append_complete_artifact()`, and `truncate_private_artifact()` independently reopen `human-review.ndjson`; none binds all terminal operations to one descriptor, and the terminal path omits the shared lock/Result `st_nlink == 1` contract.
- The final `enforce_repository_contract()` returns a validated state but the caller discards it before initial `compute_human_review_binding()`; that call supplies neither the existing metadata-only floor nor an expected repository commitment.
- `private_artifact_fingerprint()` checks initial size but reads until EOF without an observed-byte counter, so a concurrently growing file can be read past its declared bound before later stability/deadline rejection.
- The published 1.2.14 suite passed; these are source/data-flow gaps with missing negative regressions, not known automatic-PASS fail-open behavior.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Terminal decision can write/truncate a prepared same-UID hardlink victim | fact | local v1.2.14 source and supplied audit | 2026-07-13 | `run_pipeline.py` terminal helpers; `review_decision.py:decide` | current; tests use synthetic sentinels |
| Initial Binding can recapture after classification/state drift rather than reject the final checkpoint | fact | local v1.2.14 source and supplied audit | 2026-07-13 | final pipeline contract call and `compute_human_review_binding` invocation | current; protected content remains synthetic |
| Growing Artifact reads can exceed the byte source limit before rejection | fact | local v1.2.14 source and supplied audit | 2026-07-13 | `private_artifact_fingerprint` loop | current; no external payload |

## Governed defect diagnosis

- Observed failure: terminal record operations can target different path-resolved inodes; initial Binding can adopt a post-contract repository snapshot; Artifact budgets constrain initial/final state but not bytes actually consumed while a file grows.
- Competing hypotheses: repeated path checks are sufficient—rejected because each reopen can resolve a replacement. Repository-lock ownership is sufficient—rejected because the threat is a non-cooperative same-UID writer. Final metadata comparison is sufficient for budgets—rejected because resource consumption occurs before the comparison.
- Ownership path: the Human Review terminal descriptor transaction owns decision-file identity; the final repository-contract result owns initial Binding input; the descriptor hash loop owns actual byte consumption.
- Violated invariant: a terminal decision may mutate only the exact private inode safely created/opened for that decision, initial review evidence must equal the already validated checkpoint without newly reading protected content, and declared budgets must cap source reads rather than merely reject afterward.
- Root cause: path-based helper composition and post-hoc state/size checks left identity, checkpoint, and byte ownership outside their executing boundaries.
- Root-cause alignment: PASS

## Constraints and invariants

- Human Review Binding and decision remain v4; existing valid v4 Results stay compatible and v2/v3 remain fail closed.
- Terminal record opening is directory-relative and no-follow, requires regular file, `st_nlink == 1`, and descriptor/path device+inode identity before and after mutation.
- Append and compensation use the same pinned descriptor; compensation must never reopen an attacker-replaced pathname.
- Initial Binding receives the complete final validated metadata-only floor and rejects any repository commitment mismatch instead of adopting it.
- Artifact per-file and aggregate allowances are decremented from bytes actually read and fail immediately on the first excess byte.
- No new dependency; implementation remains standard-library-only and supported on the existing Linux/macOS/WSL Runner platforms.

## Impact map

- Producers: final Runner contract state, Human Review v4 Binding, `human-review.ndjson`.
- Consumers: `review_decision.py`, protected-deletion operators, contract validator, focused and cross-platform CI.
- Persisted data: existing v4 `result.json`, decision NDJSON, summary JSON; no schema migration.
- Public contracts: Rootloom 1.2.15, Strict Runner 2.20, strengthened v4 safety semantics.
- Generated artifacts: private Run Directory files only.
- External systems: GitHub `main`, exact-sha Actions, annotated tag, and formal Release after local gates.

## Design and decisions

- Ownership: a pinned private-Artifact context owns safe directory-relative create/open and descriptor lifetime; descriptor append/compensation helpers own complete writes, fsync, identity checks, and rollback.
- Interfaces: initial Binding adds an optional expected repository commitment used by the pipeline and revalidation; it is an execution precondition, not a new persisted field.
- Dependency direction: `review_decision.py` consumes Runner I/O primitives; pipeline orchestration passes its final validated state into Binding; no reverse dependency or new module is needed.
- Compatibility window: valid v4 Results and ordinary empty single-link decision files continue to work. Multi-linked or replaced terminal files and checkpoint drift now fail closed.
- Alternatives rejected: adding `st_nlink` independently to three path helpers preserves TOCTOU; advancing to v5 is unnecessary because v4 already persists the needed floor/commitment; a mutable global aggregate-budget abstraction adds no enforcement beyond passing the exact remaining allowance into a source-bounded serial reader.

## Implementation sequence

1. Completed — added fail-before regressions for hardlink/path replacement, pinned compensation, final-checkpoint floor/commitment, source-bounded growth, and malformed-v4 pre-capture refusal.
2. Completed — replaced terminal path reopen composition with one pinned descriptor transaction and routed all decision mutations through it.
3. Completed — carried the final validated state into initial Binding, enforced its repository commitment, and bounded the hash loop by observed bytes and remaining aggregate allowance.
4. Completed — updated contract validation, version metadata, bilingual public docs, Changelog, and existing durable decision records.
5. Completed — local focused/full/compatibility/challenge checks passed; exact-sha CI passed; annotated tag and formal Release were published and post-publication state was verified.

## Rollout, failure, and rollback

- Dry-run/preview: temporary repositories and Run Directories with external sentinel victims, deliberate directory-entry replacement, classification drift, and synthetic growing reads.
- Mixed-version behavior: v4 format is unchanged. Older 1.2.14 decision commands remain less hardened; operators should use the bundled 1.2.15 command with a 1.2.15 Run installation.
- Failure detection: explicit multi-link, identity-drift, final-checkpoint-drift, and byte-budget errors with nonzero exit; no summary on refusal.
- Rollback or compensation: before publication, revert scoped commits. During decision validation, truncate only the pinned original inode. After publication, fix forward with a new patch release rather than moving the tag.
- Irreversible point: pushing the annotated tag and publishing the GitHub Release; explicitly authorized by the user's standing instruction.

## Verification

- Original failure path: prepared `human-review.ndjson` hardlink victim must be refused with content/mode unchanged.
- Owning-boundary invariant: create-to-append and compensation-time path replacement must never write or truncate the replacement victim; final Binding must retain the validated floor and reject commitment drift without protected content reads.
- Adjacent negative/alternate path: unchanged valid v4 decision still accepts; existing aggregate static-file budget still rejects; v2/v3 and duplicate decisions remain closed.
- Focused tests: Human Review tests in `test_run_pipeline.py`.
- Contract/migration tests: repository validator plus unchanged v4 compatibility tests.
- Type/lint/build/package: Python compilation, `make validate`, `make check`, `make compatibility-smoke`, `git diff --check`.
- UI/browser evidence: not applicable.
- Security/dependency checks: victim mode/content assertions, no new dependency, fresh analogous path review.
- Post-action verification: exact commit CI matrix, annotated/peeled tag equality, Release metadata, clean remote `main`.

## Risks

- Risk: a same-UID writer can still mutate state after the final verification.
  - Mitigation: descriptor pinning and repeated commitments close only the operations Rootloom can own; docs retain the external-writer boundary.
  - Residual risk: immutable snapshots/external isolation remain required for adversarial workloads.
- Risk: compensation sees its pathname replaced.
  - Mitigation: compensation always truncates the pinned original descriptor and reports identity drift; it never opens the replacement.
  - Residual risk: an attacker-created outside hardlink to Rootloom's newly created inode can observe later mutation; preventing same-UID alias creation requires OS isolation.
- Risk: stricter commitment equality rejects benign concurrent repository changes.
  - Mitigation: fail closed with a rerun; no state is adopted silently.
  - Residual risk: non-cooperative local automation can cause denial of service.

## Decision log

- 2026-07-13 — GO: all three findings share one I/O/checkpoint ownership root cause and have bounded fail-before regressions.
- 2026-07-13 — Keep Human Review v4 because the persisted record already contains the complete floor and repository commitment; strengthen production and consumption semantics instead of inventing a schema change.
- 2026-07-13 — Fresh challenge checked verification NDJSON's pinned append/rollback analog and the malformed-v4 consumer. Keep that separate existing Artifact path out of the terminal transaction, but reject a missing v4 repository commitment before any recapture and always clear the pinned original terminal inode before reporting compensation drift.
- 2026-07-13 — Exact-sha CI run `29226745172` passed seven jobs but macOS entered the existing valid process-group cleanup-uncertainty branch during the untracked-patch budget test. The inner capture refused automated Review and rolled back the Artifact, but `stream_untracked_patch()` dropped that invariant phrase while adding path context. Preserve the fail-closed behavior, propagate the diagnostic at the outer ownership boundary, add a deterministic batch-rollback assertion, and rerun the complete matrix.
- 2026-07-13 — Use the user's standing direct-publication authorization only after local and exact-sha CI gates succeed.

## Durable decision records

- Amend `docs/decisions/2026-07-12-human-review-and-setup-recovery.md` for pinned terminal ownership and final-checkpoint equality.
- Amend `docs/decisions/2026-07-12-strict-runner-resource-artifacts.md` for actual-read byte enforcement.

## Verification evidence

- Fail-before: 99-test focused suite reported two security failures and three missing-boundary errors for the five supplied findings.
- Focused corrected paths: seven terminal/floor/budget tests passed; the fresh malformed-v4 commitment regression also passed before state capture.
- `make validate` — passed.
- `make check` — passed: 58 repository tests and 100 focused Strict Runner tests.
- `make compatibility-smoke` — passed with pre-existing configuration restored and no managed leftovers.
- Python compilation and `git diff --check` — passed.
- Exact-sha CI run `29226745172` — seven jobs passed; macOS failed only because the outer untracked-Delta diagnostic omitted the preserved fail-closed invariant. No tag or Release was created.
- Exact-sha CI run `29227221911` — all eight jobs passed against `2fdffb6f9b6814ca945182c35abbcec4c6d9c2a6`, including Linux Python 3.11–3.14, macOS Strict Runner, macOS/Windows Portable Contracts, and pinned Codex CLI compatibility.
- Annotated tag `v1.2.15` — tag object `2cc4206586fadc81cd41ec09fc3d750bd3cfe24a`, peeled commit `2fdffb6f9b6814ca945182c35abbcec4c6d9c2a6`.
- Formal non-draft, non-prerelease GitHub Release — published 2026-07-13 at `https://github.com/liyanqing90/rootloom/releases/tag/v1.2.15`.

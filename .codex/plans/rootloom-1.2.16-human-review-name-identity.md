# Rootloom 1.2.16 Human Review name identity and terminal commit

## Status

- State: in progress
- Owner: Codex
- Last updated: 2026-07-13
- Task type: security and release
- Risk: Tier 2 (Governed)

## Goal and observable success

Release Rootloom 1.2.16 / Strict Runner 2.21 so Human Review v4 accepts a decision only when canonical Result and Artifact names remain bound to the descriptors that were read, the reviewed Artifact name set remains stable, and both Terminal and Summary survive one final Result/repository/run-directory/name-identity validation. Every induced failure before that commit point must compensate both pinned decision outputs to empty files so an unambiguous retry can succeed.

## Non-goals

- Do not claim protection from arbitrary same-UID mutation after the final validation, cryptographic reviewer identity, WORM durability, sandboxing, DLP lineage, or detached-process containment.
- Do not change the persisted Human Review v4 binding or decision schemas.
- Do not split Human Review I/O into a new module in this repair; the defect is owned by the existing descriptor helpers and decision transaction, and a module move would add migration surface without changing the invariant.
- Do not add a summary-rebuild command. New failures compensate both outputs; older mixed-version partial terminals continue to fail closed for manual inspection.

## Baseline evidence

- `read_human_review_result()` verifies descriptor fields before/after reading but does not prove after the read that canonical `result.json` still names that inode.
- `private_artifact_fingerprint()` has the same descriptor-only post-read check for reviewed Artifacts.
- `compute_human_review_binding()` enumerates the Artifact directory only once, so a concurrent name-set change can escape the commitment.
- `review_decision.decide()` completes Terminal validation before path-based Summary creation. A Summary failure leaves a non-empty terminal while reporting failure, and no final validation follows Rootloom's Summary write.
- A successful return still passed through descriptor-closing `finally` blocks that could raise after both outputs had crossed the intended commit point, recreating the same reported-failure ambiguity.
- Worktree was clean at `4729680` before the task.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Canonical-name substitution is not detected | fact | supplied independent audit plus repository source | 2026-07-13 | attached Rootloom 1.2.15 review; `run_pipeline.py` Result/Artifact readers | fresh; no secrets |
| Summary is outside the terminal transaction | fact | repository source | 2026-07-13 | `review_decision.py` | fresh |
| The existing terminal helper already enforces descriptor-to-name identity | fact | repository source | 2026-07-13 | `validate_pinned_private_artifact()` | fresh |
| Arbitrary mutation after the last check remains external | limitation | supplied audit and accepted decision record | 2026-07-13 | `docs/decisions/2026-07-12-human-review-and-setup-recovery.md` | current |

## Governed defect diagnosis

- Observed failure: a competing writer can rename/replace Result or a reviewed Artifact during its descriptor read, or mutate decision outputs/run identity during Summary persistence, while the consumer can still return a misleading success or leave an ambiguous terminal.
- Competing hypotheses: descriptor metadata instability; canonical directory-entry substitution; missing output transaction boundary. Stable descriptor fields contradict the first hypothesis for rename/replace, while the missing post-read `stat(..., dir_fd=...)` and Summary ordering support the latter two.
- Ownership path: `run_pipeline.py` owns safe directory-relative reads and pinned private artifacts; `review_decision.py` owns the accept/reject commit transaction.
- Violated invariant: bytes may be accepted only while their canonical name still identifies the read inode, and a reported decision is committed only when its Terminal and Summary are both pinned, durable, and covered by the last validation.
- Root cause: the v4 correction pinned only Terminal. Result and ordinary Artifact readers validated descriptor stability without revalidating directory-entry identity, Artifact enumeration had no closing snapshot, and Summary was written after the transaction's last check.
- Root-cause alignment: PASS.

## Constraints and invariants

- Preserve Human Review binding and decision format v4.
- Preserve ordinary valid decisions and fail-closed behavior for v2/v3.
- All decision outputs must remain regular, private, single-link files opened relative to a stable no-follow Run Directory descriptor.
- Compensation must mutate only pinned original inodes and must never truncate a substituted path or external hardlink victim.
- No Rootloom mutation may occur after the final successful validation.
- Public/safety behavior changes require synchronized English and Chinese documentation plus validator contracts.

## Impact map

- Producers: `run_pipeline.py` Human Review Result/binding creation.
- Consumers: `review_decision.py` and operators resolving exit 10.
- Persisted data: `result.json`, `human-review.ndjson`, `human-review-summary.json`; schemas remain v4.
- Public contracts: decision CLI commit/failure semantics and Rootloom/Runner versions.
- Generated artifacts: release tag and GitHub Release.
- External systems: GitHub branch, CI, tag, and Release after local gates pass.

## Design and decisions

- Ownership: extend the existing safe descriptor helpers rather than introduce a parallel I/O layer.
- Interfaces: validate directory entry to descriptor identity before and after Result/Artifact reads; compare sorted eligible Artifact names before and after hashing; expose final Run Directory descriptor identity validation; pin empty Terminal and Summary together.
- Dependency direction: `review_decision.py` composes `run_pipeline.py` safety primitives; helpers do not import CLI orchestration.
- Compatibility window: v4 Results remain accepted. New code may leave zero-length Terminal/Summary files after a compensated failure and reuses them on retry. Older partial non-empty Terminal states remain fail closed.
- Alternatives rejected: path-based atomic Summary replacement, because it is outside the pinned transaction; committing Terminal without Summary, because CLI failure becomes ambiguous; automatic repair of older partial terminals, because authorship and failure provenance cannot be reconstructed safely; module extraction, because it does not close the demonstrated race.

## Implementation sequence

1. Add true rename/replace and Summary-failure regressions and record fail-before evidence.
2. Add reusable descriptor/name and Run Directory identity validation, closing Result/Artifact/name-set reads.
3. Make Terminal plus Summary one pinned compensating transaction with a final no-write-after-check validation.
4. Update validator, bilingual public/architecture docs, changelog, version, and durable decision record.
5. Run focused and repository gates, challenge the repair, then publish only after exact-SHA CI succeeds.

## Rollout, failure, and rollback

- Dry-run/preview: focused unit tests with synthetic temporary repositories and victims; then `make validate`, `make test`, `make check`, and compatibility smoke.
- Mixed-version behavior: schemas remain v4. New zero-length compensated outputs are retryable; prior non-empty Terminal/no-Summary states are intentionally not inferred or rewritten.
- Failure detection: stable exit 9 errors naming Result/Artifact/name-set/run/output identity drift; tests assert preserved victims and empty pinned outputs.
- Rollback or compensation: pre-commit failures truncate pinned Summary and Terminal originals to zero. Release rollback is a normal follow-up commit/release; published tags are not moved.
- Irreversible point: annotated tag and public GitHub Release, already authorized by the user but gated on exact-SHA CI.

## Verification

- Original failure path: focused rename/replace and forced Summary-write tests must fail against 1.2.15.
- Owning-boundary invariant: the same tests must pass after descriptor/name and transaction changes.
- Adjacent negative/alternate path: valid decision and duplicate decision behavior; hardlink and substituted-victim preservation; Artifact name-set mutation.
- Focused tests: `python3 -m unittest plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py`.
- Contract/migration tests: `make validate`; Human Review v4 compatibility tests.
- Type/lint/build/package: `python3 -m compileall`; `make test`; `make check`.
- UI/browser evidence: not applicable.
- Security/dependency checks: no dependency change; repository validator and exact-SHA CI matrix.
- Post-action verification: remote main SHA, annotated tag target, public release metadata, eight CI jobs, and clean worktree.

Observed local evidence:

- Fail-before: five focused Result/Artifact/name-set/Summary/Terminal tests all failed against the 1.2.15 implementation; a later cleanup fault-injection also failed after the intended commit point.
- Pass-after: the supplied-finding paths plus descriptor/name metadata-window drift, Summary hardlink/replacement, Run Directory replacement, retry, and post-commit close injection pass.
- `make validate` passed.
- Final `make check` passed 58 repository tests and 110 focused Runner tests.
- Final `make compatibility-smoke` passed against pinned `codex-cli 0.144.0-alpha.4`, restored pre-existing config, and left no managed artifacts after rollback.
- `python3 -m compileall` and `git diff --check` passed.

## Risks

- Risk: compensation itself encounters a substituted name.
  - Mitigation: truncate only pinned descriptors and report identity drift while preserving substituted victims.
  - Residual risk: an arbitrary same-UID writer can still mutate after the final check.
- Risk: two independently opened output helpers bind different Run Directory inodes.
  - Mitigation: the final run-path identity validation rejects replacement, and both outputs receive their own stable directory descriptor.
  - Residual risk: no OS-level immutable snapshot is provided.
- Risk: Summary serialization or write failure leaves ambiguous state.
  - Mitigation: serialize before mutation, pin both empty outputs, compensate both before returning failure.
  - Residual risk: catastrophic storage failure may also prevent compensation/fsync.

## Decision log

- 2026-07-13 — GO: the supplied findings reproduce one descriptor/name ownership gap and one missing commit boundary; both have bounded repository-local fixes.
- 2026-07-13 — Keep Human Review v4 because no persisted field or interpretation changes; this is a compatible safety correction.
- 2026-07-13 — Define commit as Terminal + Summary + final validations, with no later Rootloom write.
- 2026-07-13 — Strongest-counterexample challenge found that a post-commit descriptor-close exception could still report failure; cleanup errors are now non-authoritative after the validated durable pair, with explicit fault injection.

## Durable decision records

- Amend `docs/decisions/2026-07-12-human-review-and-setup-recovery.md` with canonical-name continuity and two-output commit semantics.

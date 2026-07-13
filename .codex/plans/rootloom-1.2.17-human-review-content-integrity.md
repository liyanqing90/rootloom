# Rootloom 1.2.17 Human Review content integrity and pair verification

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-13
- Task type: security, public CLI, and release
- Risk: Tier 2 (Governed)

## Goal and observable success

Release Rootloom 1.2.17 / Strict Runner 2.22 so a Human Review v4 decision commits only when pinned Terminal and Summary descriptors still contain exactly the bytes Rootloom wrote, and operators can independently verify a committed Decision Pair without modifying repository or Run state. Equal-length same-inode mutation must fail, compensate both outputs, and permit a clean retry. Documentation must name the shared lock a hardened cooperative lock and freeze the local Human Review security scope at attributable small-team approval with content hashes.

## Non-goals

- Do not claim hostile same-UID exclusion, immutable leases, cryptographic organizational identity, WORM durability, or OS/container isolation.
- Do not change Human Review persisted format v4; content hashing validates existing bytes and fields.
- Do not implement the broader 1.3 roadmap (container/cgroup integration, incremental snapshots, external signer/store, retention policy, or authenticated model-routing smoke) in this security patch.

## Baseline evidence

- `validate_pinned_private_artifact()` checks name, inode, link count, mode, metadata, and size but not content.
- Final decision validation therefore accepts an equal-length overwrite on the same inode if it occurs after append and before the final check.
- `review_decision.py` supports only accept/reject and has no independent read-only Decision Pair verifier.
- Shared lock documentation describes cooperative scope in some locations but does not consistently use the explicit “hardened cooperative lock” capability name.
- Worktree began clean at `301c1ec` after the v1.2.16 publication evidence commit.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Equal-size content is not a final invariant | fact | repository source | 2026-07-13 | `run_pipeline.py::validate_pinned_private_artifact` | fresh; no sensitive data |
| Decision Pair lacks an independent verifier | fact | repository CLI source | 2026-07-13 | `review_decision.py` | fresh |
| Required attack paths and scope boundary | fact/requirement | user-supplied 1.2.16 review | 2026-07-13 | current task prompt | fresh |

## Governed defect diagnosis

- Observed failure: same-inode, same-length Terminal or Summary bytes can differ from the payload Rootloom intended while all existing final checks pass.
- Competing hypotheses: identity/size drift versus content-only drift. Existing rename/hardlink/metadata tests reject the first; the missing descriptor SHA comparison leaves the second ungoverned.
- Ownership path: pinned private Artifact validation in `run_pipeline.py` owns final byte acceptance; `review_decision.py` owns pair commit and public verification.
- Violated invariant: a committed Decision Pair must equal the exact canonical Terminal and Summary payloads Rootloom generated, not merely occupy the expected inode and size.
- Root cause: final validation has no expected digest and performs no bounded descriptor reread.
- Root-cause alignment: PASS.

## Constraints and invariants

- Hash only through the already pinned descriptor; never reopen an output pathname for content verification or compensation.
- Require observed byte count, expected size, and SHA-256 together, with identity/metadata validation before and after hashing.
- Any pre-commit content mismatch compensates both pinned original inodes to zero and returns nonzero.
- `verify` is strictly read-only: it must not acquire the mutating cooperative lock or write files.
- Existing accept/reject CLI syntax and Human Review v4 artifacts remain compatible.
- Verification statuses are `VALID` (exit 0), `INVALID` (exit 9), and `STALE` (exit 12).

## Impact map

- Producers: `review_decision.py::decide`.
- Consumers: operators and automation resolving exit 10; new `review_decision.py verify` consumer.
- Persisted data: existing `result.json`, `human-review.ndjson`, and `human-review-summary.json`; no schema migration.
- Public contracts: additive `verify` subcommand and status/exit-code contract; legacy decision flags remain unchanged.
- External systems: GitHub main, CI, annotated tag, and Release after gates pass.

## Design and decisions

- Extend pinned validation with `expected_sha256` and an exact-size `pread` digest helper. Pre/post identity and metadata checks bracket the content read.
- Refactor Result validation into a shared module-level function used by decide and verify.
- Verify one canonical terminal NDJSON record, reconstruct the canonical Summary, compare exact bytes and terminal hash, then recompute the current Human Review Binding and repeat Result/Pair/Run identity reads around that computation.
- Classify structurally unsafe, malformed, or inconsistent pairs as `INVALID`; classify a structurally valid pair whose current repository/Artifact/protected-deletion commitment no longer matches as `STALE`.
- Keep the verifier lock-free and repeat checks because acquiring the existing lock would mutate its owner record.
- Reject adding more local hostile-writer controls after content hashes; stronger assurance belongs to immutable external boundaries.

## Implementation sequence

1. Add fail-before equal-length Terminal/Summary/both mutation regressions and read-only verifier regressions.
2. Add exact descriptor hashing and wire final expected digests into the pair transaction.
3. Add compatible `verify` CLI parsing, pair validation, and `VALID`/`INVALID`/`STALE` exits.
4. Update version, validator, bilingual public/architecture/troubleshooting/maturity docs, changelog, and durable decision record.
5. Run focused/full gates and a fresh counterexample challenge; publish only after exact-SHA CI passes.

## Rollout, failure, and rollback

- Dry-run: synthetic temporary repositories and same-inode `pwrite` attacks; verifier tests snapshot file bytes and lock metadata before/after.
- Mixed-version behavior: all valid v4 pairs remain readable. The new verifier is additive. v2/v3 and pre-existing malformed/partial pairs remain invalid/fail closed.
- Failure detection: digest/byte-accounting errors during commit; `INVALID` or `STALE` verifier output.
- Compensation: truncate only pinned original Terminal and Summary descriptors to zero before reporting commit failure.
- Irreversible point: annotated tag and public GitHub Release, authorized by the user but gated on exact-SHA CI.

## Verification

- Original failure path: equal-length same-inode overwrite tests fail against v1.2.16.
- Owning-boundary invariant: Terminal, Summary, and combined overwrites fail and compensate; retry succeeds.
- Adjacent path: valid read-only verification, tampered pair `INVALID`, repository drift `STALE`, legacy accept/reject compatibility.
- Focused tests: `python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py`.
- Contract tests: `make validate`, `make check`, `make compatibility-smoke`.
- Type/build: `python3 -m compileall`, `git diff --check`.
- Post-action: exact remote SHA, 8/8 CI, annotated tag target, formal Release, final documentation CI, clean worktree.

## Risks

- Concurrent overwrite during hashing may produce mixed bytes.
  - Mitigation: exact expected digest plus identity/metadata checks before and after the bounded `pread` loop.
  - Residual risk: hostile mutation after the final check remains external.
- Read-only verification has no lock-stable snapshot.
  - Mitigation: repeat Result, Pair, and Run identity checks around repository recomputation; return non-valid on drift.
  - Residual risk: only an immutable snapshot can eliminate the final observation race.
- Additive CLI parsing could break legacy syntax.
  - Mitigation: treat only an initial literal `verify` as the new mode and preserve all existing flag-only decision invocations.

## Decision log

- 2026-07-13 — GO: content-only drift is reproduced at the owning boundary and is not covered by v1.2.16 identity/size checks.
- 2026-07-13 — Fail-before evidence: the three Terminal/Summary/both equal-length same-inode mutation tests all failed against the original size/identity-only commit gate because no `PipelineError` was raised.
- 2026-07-13 — Keep Human Review v4: no field or meaning changes; validation consumes the exact existing bytes.
- 2026-07-13 — Freeze local adversarial scope after descriptor content hashes; route stronger guarantees to immutable/external systems.
- 2026-07-13 — Focused PASS: 118 Strict Runner tests, including exact-payload compensation/retry and read-only VALID/INVALID/STALE verifier cases.
- 2026-07-13 — Repository PASS: `make validate`, `make check` (58 repository tests + 118 Strict Runner tests), compatibility smoke against `codex-cli 0.144.0-alpha.4`, isolated `compileall`, and `git diff --check`.
- 2026-07-13 — Publication PASS: exact commit `4b749632ca042a73546defd1e3ff0ddf2bdfe82c` passed all eight jobs in CI run `29234377961`, then received annotated tag `v1.2.17` and the formal GitHub Release.

## Durable decision records

- Amend `docs/decisions/2026-07-12-human-review-and-setup-recovery.md` with content-integrity, read-only pair verification, hardened cooperative lock naming, and scope-freeze decisions.

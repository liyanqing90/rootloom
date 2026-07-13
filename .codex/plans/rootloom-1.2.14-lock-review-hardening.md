# Rootloom 1.2.14 lock and Human Review hardening

## Status

- State: in progress
- Owner: Codex
- Last updated: 2026-07-13
- Task type: security and persisted audit-contract repair
- Risk: Tier 2 (Governed)

## Goal and observable success

Close the 1.2.13 audit findings without weakening existing fail-closed behavior. Runner, Setup, and Guidance locks must use one hardened no-follow opener that cannot truncate or chmod a symlink/hardlink victim. Human Review v4 must preserve the complete metadata-only floor before content reads, bind one canonical Run Directory identity, safely re-read the complete Result after terminal-record append, and enforce per-Artifact, aggregate, and wall-clock binding budgets.

Success requires fail-before/pass-after regressions for all three symlink lock paths, Human Review classification drift without protected-content hashing, Result write-window drift compensation, copied Run Directory refusal, Artifact byte/time limits, full local checks, compatibility smoke, exact-sha cross-platform CI, and publication as `v1.2.14` under the user's standing direct-release authorization.

## Non-goals

- Kernel-attested launcher execution, stable-FD `exec`, container/cgroup integration, external signing, WORM storage, parent-directory durability, or large-repository benchmarks.
- Treating local same-user concurrency as fully preventable after the final checked operation.
- Force-push, tag movement, destructive release rollback, or unrelated feature work.

## Baseline evidence

- Release `v1.2.13` points to `05627be11d17ff9aea2cd6997c73549eb5874f52`; `main` started clean at publication-record commit `5dd82aa22f62e9739e7780cedd397d5bd154e028`.
- `repository_lock()` opens `.git/codex-high-assurance.lock` with `O_CREAT | O_RDWR`, then truncates and writes after `flock`, without `O_NOFOLLOW`, regular-file, or link-count validation.
- `setup_lock()` and `guidance_lock()` perform a path-level symlink check followed by ordinary `os.open()`, leaving a check/use race.
- Human Review v3 recomputation uses only protected deletions as `metadata_only_floor`, reads Result once, omits canonical Run Directory identity from Binding, and hashes up to 256 unbounded Artifacts without total/time limits.
- Existing 1.2.13 local and GitHub release gates passed; findings are source-data-flow defects rather than pre-existing test failures.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Lock symlink can target an external writable victim | fact | local release source | 2026-07-13 | three lock functions named above; supplied 1.2.13 audit | current; no victim content exposed |
| Human Review can read a declassified protected file before rejecting | fact | local release source | 2026-07-13 | `compute_human_review_binding`, supplied audit path | current; test must use sentinel without logging content |
| Result and Run identity are not re-bound after decision append | fact | local release source | 2026-07-13 | `review_decision.py:decide` | current |
| Artifact hash work lacks byte/time limits | fact | local release source | 2026-07-13 | `private_artifact_fingerprint`, `compute_human_review_binding` | current |

## Governed defect diagnosis

- Observed failure: lock acquisition can mutate a non-lock target through a prepared symlink; Human Review can perform a forbidden protected-content read or persist a decision whose on-disk Result/Run identity no longer matches the reviewed object.
- Competing hypotheses: path-level `is_symlink()` checks are enough; rejected because replacement can occur before `open`. Repository-state commitment is enough for confidentiality; rejected because the content read happens before drift comparison. Repository lock is enough for Result consistency; rejected because arbitrary same-user Run Directory writers do not honor it.
- Ownership path: one plugin-level lock-file primitive; Human Review Binding owns complete review inputs and budgets; decision orchestration owns safe pre/post Result reads and terminal compensation.
- Violated invariant: no lock operation may follow or mutate an alias, and no review decision may read, identify, or persist a different object than the exact bounded Run/Result/protected state it binds.
- Root cause: security-critical identity and budget checks were distributed around ordinary path opens and caller-supplied partial review state instead of being enforced by the owning I/O boundaries.
- Root-cause alignment: PASS

## Constraints and invariants

- Shared lock opener remains standard-library-only and portable across Linux/macOS/WSL and native Windows portable Setup/Guidance tests.
- POSIX uses `O_NOFOLLOW`/`O_CLOEXEC`, regular-file and single-link checks, descriptor/path identity verification, mode hardening, nonblocking `flock`, and owner writes only after lock acquisition.
- Windows uses a no-follow reparse-point handle, regular-file/single-link attributes, non-inheritable descriptors, nonblocking `LockFileEx`, and no pre-lock file mutation; ACL equivalence to POSIX mode remains unclaimed.
- Human Review never hashes or reads a path present in the bound final metadata-only floor, even after ignore/sensitivity classification drift.
- Human Review v3 results fail closed; v4 is additive for newly produced Runs.
- Existing `--require-isolation` compatibility alias and Recovery schema readers remain unchanged.

## Impact map

- Producers: Runner lock owner record, Setup/Guidance lock files, Human Review v4 Binding and decision records.
- Consumers: pipeline startup, accept/reject, setup apply/rollback/recover/status, guidance seeding, CI and local tests.
- Persisted data: lock files, `result.json`, `human-review.ndjson`, `human-review-summary.json`; new v4 binding fields and policy budgets.
- Public contracts: plugin 1.2.14, Strict Runner 2.19, Human Review v4, three new Human Review budget CLI options.
- Generated artifacts: private Run Directory artifacts only.
- External systems: GitHub repository/release after local and exact-sha CI gates.

## Design and decisions

- Ownership: `plugins/rootloom/lib/rootloom_lock.py` owns safe lock opening/acquisition; Runner/Setup/Guidance only translate busy/error semantics. Human Review Binding owns floor/run/budget commitment; `review_decision.py` owns pre/post safe Result comparison.
- Interfaces: `hardened_lock(path, owner_bytes=None)` yields a locked descriptor/path after identity validation. Human Review Binding v4 includes canonical Run path and directory identity, complete metadata-only floor, and normalized review policy.
- Dependency direction: skill scripts import the plugin-level standard-library lock module; the module imports no skill code. Decision CLI imports Runner review primitives, never the reverse.
- Compatibility window: old lock files that are ordinary single-link files continue working. Symlink, hardlink, directory, reparse, or identity-drift locks fail closed. v3 review results require rerun/external handling.
- Alternatives rejected: three local lock patches would preserve duplicated unsafe ownership; two-phase classification alone would not bind the original full floor; hashing `result.json` as an ordinary Artifact creates recursion and is replaced by explicit safe Result reads.

## Implementation sequence

1. Completed — added the shared hardened lock primitive and victim-preservation regressions; routed Runner, Setup, and Guidance through it.
2. Completed — added Human Review v4 floor/run identity and byte/time budgets; Artifact hashing is complete-or-fail under those limits.
3. Completed — safely re-read and canonically compare Result after decision append and after state validation; compensate on mismatch/error; reject copied Run Directories.
4. Completed — updated contract validation, version metadata, bilingual public docs, Changelog, and the existing decision records.
5. In progress — local focused/full/compatibility verification is green; commit, push, exact-sha CI, annotated `v1.2.14`, and formal Release remain.

## Rollout, failure, and rollback

- Dry-run/preview: temporary repositories/Codex homes/Run Directories with external sentinel victims and bounded fake Artifacts.
- Mixed-version behavior: v4 decisions accept only v4 Bindings; v3 remains fail closed. Ordinary existing lock files are adopted without content mutation until the lock is acquired.
- Failure detection: explicit safe-lock, floor, Result, Run identity, Artifact byte, or binding-time errors with stable nonzero exits.
- Rollback or compensation: local revert before publication; terminal decision is truncated on all post-append validation failures. After release, fix forward with a patch release rather than moving the tag.
- Irreversible point: pushing the annotated tag and publishing the GitHub Release, already authorized by the user.

## Verification

- Original failure path: symlink each of the three lock paths to a sentinel victim and prove acquisition fails while content and mode remain unchanged.
- Owning-boundary invariant: shared opener tests regular/single-link/non-inheritable/no-follow behavior; Human Review test patches fingerprinting to prove a declassified floor path is never content-read.
- Adjacent negative/alternate path: ordinary lock contention still reports busy; valid unchanged v4 Run accepts; v3 and copied Runs fail closed; byte/time limits reject before terminal decisions.
- Focused tests: Runner, Setup, Guidance, and shared lock module tests.
- Contract/migration tests: v3/v4 Result compatibility, Run identity, Result post-write drift, complete metadata floor, budget policy.
- Type/lint/build/package: `make check`, `make compatibility-smoke`, `git diff --check`.
- UI/browser evidence: not applicable.
- Security/dependency checks: repository validator; no new dependency.
- Post-action verification: exact-sha CI matrix, annotated/peeled tag comparison, Release metadata, clean remote `main`.

## Risks

- Risk: Windows no-follow locking differs from POSIX semantics.
  - Mitigation: native `CreateFileW(FILE_FLAG_OPEN_REPARSE_POINT)` plus handle attributes and `LockFileEx`, exercised by Windows CI.
  - Residual risk: Windows ACLs are not POSIX modes and remain documented separately.
- Risk: hard wall-clock interruption leaves a child Git producer.
  - Mitigation: use existing complete-or-fail subprocess cleanup paths and focused timeout tests.
  - Residual risk: hostile filesystem/kernel behavior still requires an external sandbox/quota.
- Risk: Result can change after the final safe re-read.
  - Mitigation: re-read after append and after binding computation, bind Run inode/path, document same-user residual TOCTOU.
  - Residual risk: only immutable snapshots/WORM/external signing close the final local race.

## Decision log

- 2026-07-13 — Treat the three lock implementations as one security boundary and reject duplicated fixes.
- 2026-07-13 — Advance Human Review to v4 because v3 did not capture sufficient evidence to reconstruct its original confidentiality/Run identity contract.
- 2026-07-13 — Add explicit review byte/time controls rather than relying on producer-specific historical assumptions.
- 2026-07-13 — Fresh challenge found that merely recomputing a v2/v3 or malformed-v4 binding could still read under an absent floor before version drift was reported; reject unsupported formats and a missing policy/floor before any repository capture.
- 2026-07-13 — Exact-sha CI run `29220639902` passed seven jobs, including native Windows locks, but macOS observed the existing valid fail-closed cleanup-uncertainty branch during the untracked-budget test. Preserve that stronger failure and make its diagnostic explicitly retain the invariant that Delta is incomplete and automated Review was refused; rerun the complete matrix on the repair commit.
- 2026-07-13 — Use the user's standing direct-publication authorization after exact-sha CI succeeds.

## Durable decision records

- Amended `docs/decisions/2026-07-12-human-review-and-setup-recovery.md` with Human Review v4 and shared hardened-lock ownership.
- Amended `docs/decisions/2026-07-12-strict-runner-resource-artifacts.md` with Human Review Artifact and Result resource ownership.

## Verification evidence

- `make validate` — passed.
- `make check` — passed: repository validation, 58 repository tests, and 94 focused Strict Runner tests.
- `make compatibility-smoke` — passed with pre-existing configuration restored and no managed leftovers.
- Focused Human Review v4 tests — 11 passed, including pre-capture v2/v3/malformed-v4 refusal, copied Run, Result reread compensation, complete metadata floor, and resource limits.
- Shared lock/Setup/Guidance focused suite — 49 passed; direct shared-lock suite covers symlink, hardlink, symlinked parent, non-inheritable descriptor, and contention.
- `git diff --check` and Python compilation — passed.

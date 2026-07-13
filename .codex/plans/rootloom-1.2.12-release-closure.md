# Rootloom 1.2.12 recovery and Human Review closure

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-13
- Task type: security, persisted recovery contract, release
- Risk: Tier 2 (Governed)

## Goal and observable success

Close every actionable finding from the 2026-07-13 uncommitted-change review, publish the exact verified tree as Rootloom 1.2.12, and independently verify remote `main`, CI, annotated tag, and the non-draft/non-prerelease GitHub Release.

Success requires:

- interrupted apply and rollback both leave a recoverable, versioned transaction;
- recovery accepts only known managed targets and validates every restoration source before mutation;
- Human Review binds the canonical final result as well as repository/artifact state;
- decision artifacts are created without symlink-following check/use gaps;
- fail-before/pass-after regressions, full repository checks, compatibility smoke, release hygiene, remote CI, tag, and Release verification pass.

## Baseline evidence

- `_rollback_locked()` mutates targets and setup state without writing a nonterminal recovery journal; the previous apply journal remains terminal.
- `_recover_locked()` accepts any normalized Codex-home-relative target and begins mutation before validating every backup and `state.before` payload.
- `compute_human_review_binding()` explicitly excludes `result.json` without binding its canonical core content.
- `review_decision.py` checks decision paths for symlinks separately from `touch()`/ordinary JSON writes.
- `PYTHONWARNINGS=error::ResourceWarning make check` passes 43 repository tests and 82 focused Runner tests, demonstrating that these paths are coverage gaps rather than existing red tests.

## Governed defect diagnosis

- Observed failure: interruption or local artifact drift can leave setup unrecoverable, restore untrusted data, mutate an unowned Codex-home path, or approve a modified final result.
- Competing hypotheses: documentation-only limitation; tests-only gap; or ownership-boundary defect. Rejected documentation/tests-only explanations because the executable recovery and approval paths make the unsafe decisions directly.
- Ownership path: setup transaction journal/manifest/restoration plan; Strict Runner result binding; Human Review terminal record creation.
- Violated invariant: every destructive or accepting transition must bind and validate the exact state and payload it mutates or authorizes before the transition.
- Root cause: apply-only journaling, incomplete manifest/restoration preflight, recursive-result avoidance without a core hash, and path prechecks separated from file creation.
- Root-cause alignment: PASS.

## Constraints and invariants

- Preserve unrelated user changes and the existing transaction chain.
- Recovery must be deterministic, network-free, lock-serialized, path-confined, hash-aware, and fully preflighted before mutation.
- Do not claim atomic protection against arbitrary post-decision filesystem changes; bind the exact point-in-time decision evidence honestly.
- Update English/Chinese public behavior together and keep `scripts/validate_repo.py` as the contract gate.
- Release target is `liyanqing90/rootloom`, branch `main`, annotated tag `v1.2.12`, and a Latest non-draft/non-prerelease GitHub Release. No force-push or unrelated publication.

## Impact map

- Producers: `setup_rootloom.py`, `run_pipeline.py`, `review_decision.py`.
- Consumers: setup apply/rollback/recover CLI, Human Review operator flow, repository validator, tests, public docs.
- Persisted data: setup manifests/journals/backups/state; private Runner `result.json`, decision NDJSON and summary.
- Public contracts: setup recovery CLI, Runner private artifact formats, plugin version and release tag.
- External systems: GitHub `origin`, Actions, annotated tag, GitHub Release.

## Design and decisions

- Journal rollback as its own recoverable operation, recording the exact pre-rollback snapshots and intended post-state before the first mutation.
- Parse recovery manifests into a complete validated restoration plan: known target allowlist, unique normalized paths, backup regular-file confinement, content hash and mode checks, and state-backup checks before writes.
- Bind a canonical hash of `result.json` excluding only `human_review_binding`; verify that hash before accepting or rejecting.
- Create terminal decision files using no-follow/exclusive descriptor operations and atomic summary replacement.
- Keep one setup recovery format only if it can encode both directions without ambiguity; otherwise version the format deliberately.
- Rejected: documentation caveats, catchable-exception-only rollback compensation, and additional approval layers without executable enforcement.

## Implementation sequence

1. Add failing regressions for rollback interruption, arbitrary recovery target, corrupt/missing backup preflight, result tampering, and decision-path symlink replacement.
2. Implement a validated recovery plan and rollback journaling with idempotent compensation.
3. Bind the final result core and make terminal decision persistence no-follow and complete-write safe.
4. Update validator, decision record, changelog, and bilingual public contracts; bump plugin version to 1.2.12.
5. Run focused and full checks, fresh adjacent-path challenge, compatibility smoke, and release hygiene.
6. Commit and push the verified code tree; observe CI; create and push annotated `v1.2.12`; publish and verify the GitHub Release; record publication evidence in a follow-up commit.

## Rollout, failure, and rollback

- Dry-run/preview: local tests and compatibility smoke before any remote action.
- Mixed-version behavior: terminal journals from the unpublished candidate remain inert; nonterminal journals without the v2 Manifest binding fail closed instead of being guessed or mutated.
- Failure detection: semantic regression failures, validator errors, remote CI status, tag/Release target mismatch.
- Rollback or compensation: no remote action before local verification; before tagging, revert with ordinary Git history; after publication, do not move the tag—publish a corrective patch release.
- Irreversible point: publishing `v1.2.12`; explicitly authorized by the user's “修复后发布”.

## Verification

- Original failure path: new interruption/tamper regressions.
- Owning-boundary invariant: complete recovery-plan validation and final-result binding tests.
- Adjacent negative/alternate path: clean apply recovery, clean rollback, ambiguous user edit, duplicate terminal decision, reject decision, symlink and unknown-target refusal.
- Focused tests: setup suite and focused Runner suite with `ResourceWarning` as error.
- Contract/package: `make check`, `make compatibility-smoke`, Python compile, workflow YAML parse, `git diff --check`, release hygiene.
- Post-action verification: remote commit/tree, Actions run, `v1.2.12^{}` target, GitHub Release state and URL.

## Risks

- Risk: recovery-format changes can strand an unresolved journal produced by the unpublished v1 candidate.
  - Mitigation: fail closed and require explicit operator handling; do not weaken the v2 Manifest binding by guessing an older nonterminal contract.
- Risk: terminal decision write succeeds but summary write fails.
  - Mitigation: treat NDJSON as the terminal source of truth and make summary reconstructable/atomic.
- Risk: release commit differs from tested tree.
  - Mitigation: capture and compare commit/tree before tag and Release creation.

## Decision log

- 2026-07-13 — User explicitly authorized fixing the review findings and publishing the result.
- 2026-07-13 — GO: findings are executable ownership-boundary defects; documentation-only mitigation rejected.
- 2026-07-13 — Recovery v2 deliberately rejects unpublished v1 nonterminal journals because they do not bind the Manifest that enumerates mutation targets.
- 2026-07-13 — Adjacent-path challenge found and closed three additional ownership gaps: Artifact hashing now uses stable directory-relative no-follow descriptors; recovery binds before/after modes; ordinary v2 rollback verifies its committed Manifest binding and refuses mode drift.
- 2026-07-13 — Local release verification passed: repository contract validation, 50 repository tests, 82 Runner tests with `ResourceWarning` promoted to error, Codex CLI `0.144.0-alpha.4` compatibility smoke, Python compilation, workflow YAML parse, and diff check.
- 2026-07-13 — First remote run `29213020462` correctly blocked publication: Windows portable tests exposed unconditional POSIX-only `os.fchmod` calls in the pre-existing setup and guidance lock paths. Tagging remained paused; both locks now retain descriptor chmod on POSIX and enter their existing `msvcrt` branch on Windows.
- 2026-07-13 — Post-fix local gates passed again: 50 repository tests, 82 Runner tests, compatibility smoke, repository validator, and diff check. Exact POSIX-mode assertions are explicitly scoped away from Windows rather than pretending ACL semantics equal `fchmod`.
- 2026-07-13 — Second remote run `29214414883` passed the lock boundary and exposed two deeper portability assumptions: hard-coded POSIX post-write modes and LF-only config rendering. Mode drift is now a POSIX-only contract and config management preserves the active LF/CRLF style; the existing runtime-config regression now exercises CRLF on every platform.
- 2026-07-13 — Post-portability-fix local gates passed: 51 repository tests, 82 Runner tests, compatibility smoke, repository validator, and diff check; a platform-contract-disabled recovery regression exercises the Windows content-state path locally.
- 2026-07-13 — Final candidate `eb2052edfd791d07fe25bb7d765bda43aebb23e1` (tree `59e43d904e28bba62cd0a9954527eb29e3685011`) passed CI run `29214569463` across Linux 3.11–3.14, macOS portable/Strict Runner, Windows portable, and pinned Codex CLI compatibility.
- 2026-07-13 — Published annotated tag object `ed97ddff4aab28bef819210398a843d2a216e799` as `v1.2.12`; its peeled target and remote `main` both matched the final candidate.
- 2026-07-13 — Published GitHub Release `https://github.com/liyanqing90/rootloom/releases/tag/v1.2.12` at `2026-07-13T00:11:37Z`; Latest API confirmed non-draft, non-prerelease state and the exact target commit.

## Outcome

- Rootloom 1.2.12 is published from the exact locally and remotely verified code tree.
- The two failed Windows candidate runs remain visible evidence of the portability defects found before tagging; no failed candidate was tagged or released.
- Release verification is reproducible from commit, tree, CI run, annotated-tag object/peel, and GitHub Release metadata recorded above.

## Durable decision records

- Update `docs/decisions/2026-07-12-human-review-and-setup-recovery.md` because the accepted persisted recovery and approval contracts change materially.

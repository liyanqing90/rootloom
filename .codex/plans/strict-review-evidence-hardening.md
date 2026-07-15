# Make Strict Review evidence-honest and bounded

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-15
- Task type: public review-contract, privacy, and process-governance hardening
- Risk: Tier 2 (Governed)

## Goal and observable success

Deeply harden Personal Core Strict Review beyond the supplied 2.3.0 assessment without restoring Enterprise Assurance machinery. The review bundle must describe what its evidence actually establishes, redact sensitive changes without returning a complete result, bound every Git subprocess through the existing process-tree controller, avoid whole-repository sensitive-path enumeration, and make draft sealing recoverable after a partial publication.

Success is observable when:

- summary revision 4 replaces the overstrong `VERIFIED_CHANGE` value with `REVIEW_EVIDENCE_COMPLETE`, exposes the operator assertion separately, and reserves `passed: true`/strict exit zero for that evidence-completion state;
- any otherwise-complete capture that redacts changed content stops at `REVIEW_REQUIRED_WITH_REDACTIONS`, returns a nonzero quality exit, and keeps secret bytes out of the patch;
- `analyze_change.py`, `begin_review.py`, and `finalize_change.py` expose finite-positive `--max-git-seconds` and positive `--max-sensitive-paths` budgets, and every internal Git command uses the same bounded process-tree execution owner as verification;
- sensitive discovery uses the shared case-insensitive Git pathspec policy plus explicit user roots instead of listing every tracked and ignored path, while a configurable result budget fails closed;
- new drafts use an exact dedicated placeholder, legitimate Todo-domain strings seal, legacy unedited skeletons remain refused, and `seal_contract.py --recover` can validate and finish an exact orphan contract without overwriting mismatched evidence;
- exact unchanged pre-existing untracked fingerprints remain outside dirty-baseline task scope, while changed aggregate tracked patches and changed untracked fingerprints still fail closed through conservative attribution;
- focused regressions, `make check`, `make compatibility-smoke`, strict finalization, and a fresh counterexample/analogous-consumer challenge pass.

## Non-goals

- Proving root-cause correctness, semantic test sufficiency, production safety, or code correctness.
- Restoring reviewer identities, approvals, signatures, immutable audit storage, multi-agent enforcement, or an untrusted-command sandbox.
- Silently excluding vendor/cache trees from sensitive discovery; targeted pathspecs remove wholesale enumeration, but matched sensitive-looking paths still fail closed at the configured budget.
- Publishing, tagging, pushing, deploying, or creating a 2.4 release in this task.
- Changing the existing baseline, change-contract, review-manifest, or seal format names.

## Baseline evidence

- `main` and `origin/main` resolve to `6447849`; the only intake-time worktree change is the user's untracked `assets/rootloom-xiaohei-loom.png`, which is preserved as a dirty-baseline entry and excluded from task attribution.
- The advisory analyzer reports medium/Tier 1 from static path signals, but semantic impact is Tier 2 because summary values, strict exit behavior, CLI options, privacy gates, and recovery behavior are public/safety contracts.
- `make validate` passed before implementation.
- `python3 -m unittest tests.test_engineering_change -v` passed 95 tests with one environment skip before implementation.
- `finalize_change.py` currently yields `VERIFIED_CHANGE` and `passed: true` from operator-sealed command mappings plus `semantic_coverage: reviewed`, even when a command is only a tautology whose target string appears in argv.
- A confirmed sensitive rename is intentionally metadata-only but the current regression expects `VERIFIED_CHANGE` and exit zero.
- `runner/state.py` runs Git through blocking `subprocess.run`/`Popen` calls without timeouts and enumerates all tracked and ignored paths before classification, although `rootloom_paths.py` already owns bounded case-insensitive sensitive Git pathspecs.
- `seal_contract.py` rejects any recursive `TODO` substring and can leave an exact `change-contract.json` without its seal after an uncatchable process interruption.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Published baseline and dirty-tree constraint | fact | local Git repository on macOS volume | 2026-07-15 | `git status --short --branch`; `git log -8 --oneline` | current; untracked image content not read |
| Existing tests pass | fact | local Python 3 test runtime | 2026-07-15 | `make validate`; `python3 -m unittest tests.test_engineering_change -v` | current; synthetic test secrets only |
| Status and quarantine overclaim | fact | local source/tests plus supplied assessment | 2026-07-15 | `finalize_change.py`; `tests/test_engineering_change.py`; attached 523-line assessment | current; no raw secrets |
| Git timeout/discovery ownership gap | fact | local source | 2026-07-15 | `runner/state.py`; `runner/process.py`; `lib/rootloom_paths.py` | current; no sensitive content |
| Tier 2 classification | inference | public contract/consumer impact analysis | 2026-07-15 | this plan; governed review run `8799d276-abbf-47ce-bbe2-c508a8ed7066` | current |

## Governed defect diagnosis

- Observed failure: one aggregate `quality_status` conflates bounded mechanical evidence with an operator semantic assertion; redacted captures can still pass; Git capture has byte/path ceilings but no time ceiling or shared cleanup; sensitive discovery spends its budget before classification; draft usability and partial seal recovery are brittle.
- Competing hypotheses: (1) documentation warnings alone are sufficient; (2) stronger semantic test-framework adapters are required; (3) the owning contracts should change their status, capture, and recovery decisions. Documentation cannot change strict exit zero or a hanging Git child, while framework adapters still cannot prove semantics. The owning-boundary changes in (3) directly alter those decisions without a new orchestration system.
- Ownership path: statuses/exits in `finalize_change.py` and `runner/contracts.py`; Git/sensitive capture in `runner/state.py` using `runner/process.py` and `rootloom_paths.py`; draft/seal lifecycle in `begin_review.py`, `seal_contract.py`, and `runner/review_run.py`.
- Violated invariant: machine output must not claim more than captured evidence, privacy redaction must remain review-blocking, and every bounded external process/path enumeration must terminate or fail closed within its declared resource ceiling.
- Root cause: previously independent hardening increments added semantic assertions, quarantine, byte/path bounds, and process cleanup, but their aggregate decisions were not recomposed: the status still names quality, Git bypasses the process owner, discovery ignores its pathspec owner, and the two-file seal lifecycle has no validated continuation path.
- Root-cause alignment: PASS. The follow-up repairs recorded in `publish-2.4.0.md` now partition task evidence before analysis and bundle construction, close Git stdin for noninteractive capture, and separate discovery-candidate bounds from classified-sensitive result bounds.

## Constraints and invariants

- Runtime remains deterministic, local, network-free, Python 3.11+ standard-library-only, and single-agent.
- Sensitive contents and symlink targets remain unread/unserialized; path discovery must be case-insensitive and descendant-aware without silent vendor/cache blind spots.
- Time/path ceilings fail closed and never authorize a larger budget from repository-controlled evidence.
- Existing advisory behavior, artifact filenames, format names, review intake identity, and baseline/contract/seal readers remain usable.
- Public behavior and safety changes update English and Chinese README, architecture, and maturity documentation together.
- The retained Enterprise Assurance branch and installation/default-task paths remain untouched.

## Impact map

- Producers: `runner/{state,process,contracts,review_run}.py`, `begin_review.py`, `seal_contract.py`, `analyze_change.py`, `finalize_change.py`.
- Consumers: strict/advisory CLI users, CI checking quality exits/statuses, summary JSON readers, existing review-run directories, tests, repository validator, and Codex Skill instructions.
- Persisted data: `summary.json` revision 4; existing baseline/contract/manifest/seal formats stay unchanged.
- Public contracts: quality-status values and exit mapping; additive Git/path budget flags; additive seal recovery flag; draft placeholder text.
- Generated artifacts: existing `diff.patch`, `test.log`, and `summary.json`; no new mandatory artifact.
- External systems: none; no network or publication action is authorized.

## Design and decisions

- Ownership: Git invokes the existing `runner.process.run_command` controller; state capture supplies Git-specific error translation and budgets instead of copying termination logic.
- Interfaces: each CLI defaults to a 30-second per-Git-command ceiling and a 10,000-result sensitive-path ceiling; finite-positive time and positive path overrides are operator CLI inputs only and are recorded in summaries.
- Discovery: Git receives the shared built-in case-insensitive sensitive pathspecs plus literal user-declared roots, then Python reclassifies returned paths. This avoids enumerating ordinary vendor/cache contents while retaining protection for matched sensitive-looking paths.
- Status: revision 4 uses `REVIEW_EVIDENCE_COMPLETE` for a sealed mechanical chain plus operator semantic assertion. `semantic_review` remains explicitly `operator-asserted`/`not-reviewed`; it is not machine proof. Redacted otherwise-complete evidence becomes `REVIEW_REQUIRED_WITH_REDACTIONS` and `passed: false`.
- Compatibility window: format/key names and old readers remain structurally compatible, but exact-value consumers must migrate from `VERIFIED_CHANGE` to `REVIEW_EVIDENCE_COMPLETE` when `schema_revision >= 4`. No legacy alias is emitted because it would preserve the misleading authoritative result.
- Seal recovery: `--recover` is idempotent only when an existing contract and any seal bytes validate against the current baseline, manifest, draft-derived canonical contract, and expected seal. Mismatch, seal-without-contract, or no interrupted publication fails closed.
- Dirty-baseline partition: aggregate tracked-patch drift remains conservatively attributed because baseline v2 lacks per-path tracked patch bytes; untracked entries use their existing per-path fingerprints/metadata so byte-identical user state is not mislabeled as a task change.
- Alternatives rejected: documentation-only rename; heavy test-framework adapters; a second Git process controller; blanket vendor/cache exclusions; automatic cleanup/overwrite of ambiguous orphan evidence; retaining `VERIFIED_CHANGE` as an authoritative compatibility alias.

## Implementation sequence

1. Add focused fail-before regressions for status honesty, redaction caps, targeted discovery/path ceilings, Git timeout routing, exact placeholders, and seal recovery.
2. Route Git through the existing process owner and plumb finite-positive time/positive path budgets through analyzer, intake, baseline reads, finalizer preflight, and both stable captures.
3. Replace whole-repository discovery with shared pathspecs plus literal declared roots and fail-closed result budgets.
4. Advance summary revision/status semantics and redaction precedence; add explicit semantic-review and capture-limit fields.
5. Replace the draft sentinel and add exact, no-overwrite recovery for the two-file seal publication.
6. Synchronize Skill, changelog, validator, AGENTS pointer, English/Chinese README, architecture, maturity, and the durable decision record.
7. Run focused/full/compatibility/strict checks, inspect the diff, and challenge an analogous consumer plus the strongest counterexamples.

## Rollout, failure, and rollback

- Dry-run/preview: analyzer and intake tests exercise budgets in temporary repositories; seal recovery validates existing evidence without changing mismatched files.
- Mixed-version behavior: old review directories with edited drafts continue sealing; legacy untouched placeholders remain refused. Summary consumers branch on `schema_revision`: revision 3 recognizes `VERIFIED_CHANGE`; revision 4 recognizes `REVIEW_EVIDENCE_COMPLETE` and the new redaction state.
- Failure detection: nonzero CLI exit, no summary or `FAILED`/`REVIEW_REQUIRED_WITH_REDACTIONS`, bounded error text, unchanged secret-free patch, exact seal/hash validation, and repository-wide contract failures.
- Rollback or compensation: ordinary Git revert restores 2.3 behavior; existing evidence files are never migrated or rewritten. A recovery failure leaves its pre-existing files unchanged.
- Irreversible point: none. Publication and deployment are excluded.

## Verification

- Original failure path: `python3 -B -m unittest tests.test_engineering_change -v` with new regressions for tautological review naming, confirmed sensitive rename, hanging Git routing, oversized sensitive results, Todo-domain sealing, and orphan recovery.
- Owning-boundary invariant: the same focused suite exercises state/process, finalizer, intake/seal, summary, and privacy owners together.
- Adjacent negative/alternate path: mismatched orphan evidence, seal without contract, zero/negative budgets, uppercase ignored secret, declared directory boundary, output overflow/leaked descendant, and non-redacted ordinary changes.
- Focused tests: `python3 -B -m unittest tests.test_engineering_change -v`.
- Contract/migration tests: `make check`; revision-3 behavior is documented as the compatibility predecessor rather than rewritten.
- Type/lint/build/package: `make validate`; `git diff --check`.
- UI/browser evidence: not applicable.
- Security/dependency checks: source inspection for no direct Git subprocess path; synthetic secrets never enter patch/summary; no dependency changes.
- Post-action verification: `make compatibility-smoke`; strict finalization against the pre-change governed intake; inspect `summary.json`, patch, refs/index, and unchanged user image.

### Executed evidence

- Focused finalizer suite: 105 tests passed; one existing environment-only non-UTF-8 filename test was skipped because the current macOS volume rejects that filename.
- Repository contract: `make check` passed `scripts/validate_repo.py` and all 155 tests, with the same one environment skip.
- Compatibility consumer: `make compatibility-smoke` returned `passed: true`, no failed commands, no managed rollback leftovers, and no plugin-install side effects.
- Static/format checks: `make validate`, `git diff --check`, and source search confirmed the repository contract, whitespace integrity, and that the only engineering-change Git argv owner is `runner/state.py` routing through `run_command`.
- Strongest counterexamples: non-finite Git budgets are rejected before process launch; sensitive quarantine cannot pass; legitimate Todo-domain text seals while exact current/legacy placeholders do not; recovery refuses absent/mismatched evidence; unchanged dirty-baseline untracked bytes stay pre-existing while tracked overlap remains conservative; changed untracked bytes remain attributed; quoted paths and patch-like payload text cannot bypass exact untracked-patch filtering.
- Governed finalization: the intake sealed before implementation produced summary revision 4 with `REVIEW_EVIDENCE_COMPLETE`, `passed: true`, `change_partition: exact`, complete claim binding, valid hash chain/scope, preserved capture/evidence/base, and process exit 0. Its task patch contains no user-image patch header or content.
- User-state preservation: `assets/rootloom-xiaohei-loom.png` remains only in `preexisting_changes`; its current SHA-256 is the intake value `55ea78b17ac40b85cf347b478799dbda629ba8f4d52e7cea5044734c6ec1c0a6`.

## Risks

- Risk: exact status consumers break on the revision-4 rename.
  - Mitigation: explicit schema revision, synchronized migration documentation, unchanged field/artifact names, and compatibility smoke.
  - Residual risk: undocumented consumers that ignore schema revision must update.
- Risk: pathspec narrowing misses a classifier case.
  - Mitigation: shared policy ownership, Python reclassification, uppercase/nested/ignored/declared-root regressions, and fail-closed budgets.
  - Residual risk: Git pathspec semantics vary only within Git's supported cross-platform contract; unusual Git versions remain a compatibility risk.
- Risk: a per-command Git deadline still permits several commands to consume the budget serially.
  - Mitigation: every child is individually bounded and cleaned as a process tree; stable capture remains bounded by a small fixed command count.
  - Residual risk: slow non-Git filesystem metadata/fingerprint reads retain byte rather than wall-clock ceilings.
- Risk: recovery could bless attacker-modified evidence.
  - Mitigation: exact contract bytes and all existing baseline/manifest/seal hashes must match; no overwrite or inferred cleanup occurs.
  - Residual risk: Personal Core is not hostile-local-user tamper protection.

## Decision log

- 2026-07-15 — Raise semantic Tier 1 analyzer output to Tier 2 because status values, strict exits, privacy gates, and CLI limits are public/safety contracts.
- 2026-07-15 — Choose evidence-completion naming and a separate operator assertion rather than claiming machine proof of change quality.
- 2026-07-15 — Make sensitive redaction non-passing even when deletion was explicitly authorized; authorization and review sufficiency are separate decisions.
- 2026-07-15 — Reuse process-tree control for Git and prefer targeted pathspec discovery over blanket vendor/cache exclusion.
- 2026-07-15 — Support exact recovery, never orphan overwrite or automatic deletion.
- 2026-07-15 — Reject non-finite time budgets and recovery invocations with no interrupted contract; retain every exact generated legacy placeholder while allowing ordinary Todo-domain text.
- 2026-07-15 — After strict finalization exposed user-image scope contamination, partition dirty baselines with per-path untracked fingerprints while retaining conservative tracked-patch overlap.

## Durable decision records

- [Keep Strict Review Evidence-Honest and Resource-Bounded](../../docs/decisions/2026-07-15-evidence-honest-strict-review.md)

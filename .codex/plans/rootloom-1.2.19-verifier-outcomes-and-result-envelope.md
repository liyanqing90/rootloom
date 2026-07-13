# Rootloom 1.2.19 verifier outcomes and Result Envelope

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-13
- Task type: security, persisted schema, public CLI, architecture, and release
- Risk: Tier 2 (Governed)

## Goal and observable success

Release Rootloom 1.2.19 / Strict Runner 2.24 so Human Review verification distinguishes invalid evidence, genuine current-state drift, and environmental inability to verify; accepts only complete producer-owned Human Review Result Envelopes; applies independent consumer resource ceilings; and proves repository recapture uses read-only Git behavior. Remove Human Review's import dependency on `run_pipeline.py` while preserving the top-level CLI and decision workflow.

## Non-goals

- Do not add hostile same-UID approval guarantees, external signing, immutable storage, container isolation, or a new Human Review decision format.
- Do not silently migrate or rewrite older Result files. Results without the new Envelope marker fail closed and must be rerun.
- Do not extract the whole Strict Runner into new modules; extract the neutral errors/contracts and use an explicit runtime interface for remaining orchestration primitives.

## Baseline evidence

- `human_review/verify.py` converts every `PipelineError` raised by current-state recomputation to `StaleDecisionPair`, including Git, timeout, budget, permission, and I/O failures.
- `validate_review_result()` validates selected Result fields but not the complete producer envelope or deletion-only invariants.
- `state_policy` is both recorded evidence and the effective verifier resource policy; recorded values have no independent consumer ceiling.
- repository recapture uses inherited Git behavior and the read-only test observes only Result/Decision/lock files.
- Human Review modules import `run_pipeline.py`; `run_pipeline.py` imports Human Review constants.
- Worktree began clean on `main` at `2d1b8d7608c44bfae18b2489fa8617ca455d0591` after v1.2.18 publication evidence.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| all recapture failures become STALE | fact | local repository source | 2026-07-13 | `human_review/verify.py` | fresh; no sensitive data |
| Result validation is not a complete envelope | fact | local repository source | 2026-07-13 | `human_review/schema.py`, producer summary in `run_pipeline.py` | fresh |
| recorded policy controls verifier work | fact | local repository source | 2026-07-13 | `human_review/binding.py`, `compute_human_review_binding()` | fresh |
| required outcomes and Result invariants | requirement | supplied Rootloom 1.2.18 independent review | 2026-07-13 | current task attachment | fresh |

## Governed defect diagnosis

- Observed failure: environmental execution failures are mislabeled stale; synthetic incomplete Results can enter the decision path; modified recorded budgets can amplify verifier work; read-only Git behavior is not explicitly enforced.
- Competing hypotheses: repository drift versus inability to observe repository state. Current code collapses both through one generic catch, proving classification ownership—not state capture comparison—is the cause.
- Ownership path: schema validation owns `INVALID`; current expected-versus-observed comparison owns `STALE`; bounded recapture execution owns `UNVERIFIED`; producer owns the complete Result Envelope; verifier owns its local cost ceiling.
- Violated invariant: a public status must state only what the verifier proved, and untrusted persisted evidence must never choose verifier resource consumption.
- Root cause: one generic exception and one persisted policy cross three trust boundaries without typed outcomes or a consumer-side cap.
- Root-cause alignment: PASS.

## Constraints and invariants

- Public verify protocol becomes `VALID`/0, `INVALID`/9, `STALE`/12, `UNVERIFIED`/13; stdout remains exactly one word and stderr remains bounded/content-free.
- A structurally valid recapture that completes and differs is stale. Git launch, permission/I/O, timeout, topology-scan failure, and consumer ceiling refusal are unverified.
- Human Review Result Envelope v1 has an exact producer-owned field set, nonempty protected deletions, zero repair cycles, exact change-set agreement, unchanged index, canonical lists, bound delta/metadata artifacts, and Runner/run identity.
- Consumer limits never exceed compiled defaults or explicit positive CLI limits and never expand to a recorded value.
- Verification Git commands use `GIT_OPTIONAL_LOCKS=0`, `core.fsmonitor=false`, and `core.untrackedCache=false` without modifying repository config.
- Decision identities are canonical, control-free UTF-8; UID is null or nonnegative; timestamps use canonical UTC production form.
- Run directory commitments require directory mode 0700; repository counts obey policy and cross-field bounds.

## Impact map

- Producers: Result construction and Human Review Binding in `run_pipeline.py`; Decision Pair producer in `human_review/decision.py`.
- Consumers: `review_decision.py verify`, automation interpreting status/exit, existing Result/Decision pairs.
- Persisted data: `result.json` gains `format`, `runner_version`, `run_id`, and `metadata_artifact`; Binding v4 and Decision v4 fields remain unchanged.
- Public contracts: additive `UNVERIFIED` status/exit 13 and verifier resource flags.
- Architecture: neutral runner errors/contracts plus explicit Human Review runtime dependency; no Human Review import of `run_pipeline.py`.
- External systems: GitHub main, CI, annotated v1.2.19 tag, and formal Release after exact-SHA gates.

## Design and decisions

- Typed `EvidenceInvalidError`, `BindingDriftError`, and `VerificationError` own public classification.
- Result Envelope validation completes before pair read or repository recapture.
- Recorded policy is validated as evidence, then compared with consumer ceilings; exceeding a ceiling returns `UNVERIFIED` without recapture.
- Runtime operations are passed explicitly from the CLI/Runner adapter; Human Review imports only neutral `runner` modules.
- Existing v4 Result files without the v1 Envelope are invalid rather than guessed or upgraded.

## Implementation sequence

1. Add fail-before tests for the four outcome classes, complete Result Envelope, consumer ceilings, Git read-only environment/state, canonical Decision fields, and cross-field schema constraints.
2. Add neutral errors/contracts and remove the Human Review/run_pipeline import cycle through an explicit runtime interface.
3. Add Result Envelope production/validation and typed verifier classification.
4. Add consumer-limit flags/effective policy and verifier-only Git environment.
5. Update versions, validator, bilingual public/architecture/troubleshooting/maturity docs, changelog, and durable Human Review decision.
6. Run focused/full gates and a fresh counterexample challenge; publish only after exact-SHA CI succeeds.

## Rollout, failure, and rollback

- Dry-run: synthetic temporary repositories and Results assert status, exit, no recapture on invalid/over-limit evidence, and no repository mutation.
- Mixed-version behavior: v1.2.19 producers and consumers share Envelope v1; older Results fail `INVALID` and require a new Runner execution.
- Failure detection: stdout/exit/stderr subprocess tests, typed exception tests, Git-control byte/metadata snapshots, and environment capture.
- Rollback: revert before tagging; after publication use a forward patch. No existing artifact is mutated by verification.
- Irreversible point: annotated tag and GitHub Release, authorized by the user's standing direct-publication instruction and gated on exact-SHA CI.

## Verification

- Original failure path: focused verifier tests mocking Git launch, permission/I/O, deadline, consumer ceiling, and real repository drift.
- Owning-boundary invariant: schema validation and local-limit preflight occur before a mocked recapture; completed mismatch alone raises drift.
- Adjacent negative/alternate path: malformed pair remains invalid; valid pair remains valid; decide remains transactional; reject outcome remains 11.
- Focused tests: `python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py`.
- Contract tests: `make validate`, `make check`, `make compatibility-smoke`.
- Type/build: isolated `compileall`, import graph check, and `git diff --check`.
- Post-action: exact release SHA, eight-job CI, annotated tag target, formal Release, documentation CI, remote refs, and clean worktree.

## Risks

- Older v4 Results become unverifiable by the new complete-envelope contract.
  - Mitigation: explicit format error and bilingual release notes; rerun is the only trusted migration.
  - Residual risk: historical local pairs remain readable only with their producing version.
- Runtime injection may broaden signatures or create compatibility regressions.
  - Mitigation: keep `review_decision.py` compatibility wrappers and cover direct script/import paths.
  - Residual risk: consumers importing private Human Review internals are unsupported.
- Read-only Git controls may disable performance caches during verification.
  - Mitigation: verifier-only command policy; correctness and no-write evidence take precedence.
  - Residual risk: filesystem/OS behavior outside Git cannot be made immutable by environment variables.

## Decision log

- 2026-07-13 — GO: typed outcome ownership and consumer-side budgets directly correct the observed trust-boundary defects.
- 2026-07-13 — Adopt additive `UNVERIFIED`/13 rather than mapping execution failures to INVALID or STALE; neither conclusion is proved on observation failure.
- 2026-07-13 — Adopt Result Envelope v1 and fail closed for earlier incomplete Results; no reliable inference can reconstruct missing producer evidence.
- 2026-07-13 — Use explicit runtime injection as the bounded dependency-direction repair instead of extracting the entire repository-state engine in one release.
- 2026-07-13 — Fail-after evidence: `make check` passed 58 repository tests and 137 Strict Runner tests; compatibility smoke passed against `codex-cli 0.144.2` with configuration restoration and no managed leftovers.
- 2026-07-13 — Counterexample challenge found that producer `allowed_paths` retained model ordering while Envelope validation requires canonical ordering. The producer now persists a sorted unique list; this closes the producer/consumer mismatch before release.
- 2026-07-13 — Read-only challenge PASS: verifier Git subprocess policy was observed in the real recomputation path, and byte/size/mode/mtime/ctime snapshots of the complete repository plus Run Directory—including index, Git-control and lock paths—were identical before and after verification.
- 2026-07-13 — RELEASED: all eight jobs in CI run `29248176398` passed against exact commit `68f08cf64527d1a726ca469f2612a219da7893b2`; annotated tag `v1.2.19` targets that commit and the formal GitHub Release was published at 2026-07-13T12:02:42Z.

## Durable decision records

- Amend `docs/decisions/2026-07-12-human-review-and-setup-recovery.md` with typed outcomes, Result Envelope v1, verifier-owned budgets, and runtime dependency direction.

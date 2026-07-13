# Rootloom 1.2.18 Human Review schema, budgets, and module ownership

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-13
- Task type: security, public CLI, architecture, and release
- Risk: Tier 2 (Governed)

## Goal and observable success

Release Rootloom 1.2.18 / Strict Runner 2.23 so Decision Pair verification always maps structurally invalid evidence to `INVALID`/9, maps only structurally valid current-state drift to `STALE`/12, validates the complete Human Review v4 Binding before any repository or Artifact recapture, and prevents the decision producer from writing a pair that exceeds the consumer byte budget. Preserve the three-word stdout protocol while emitting a bounded diagnostic reason on stderr. Split Human Review schema, binding orchestration, pinned pair reads, decision production, and verification classification into a dedicated package without changing persisted v4 fields.

## Non-goals

- Do not introduce Human Review v5, migrate or rewrite existing evidence, add cryptographic identity, or extend the hostile same-UID threat model.
- Do not move the Runner's general repository-state capture engine or low-level private-file primitives in this release; the new package owns their Human Review composition and keeps `run_pipeline.py` as the compatibility export boundary.
- Do not add dependencies.

## Baseline evidence

- `review_decision.py::main` prints `INVALID` but returns `PipelineError.exit_code`, so path normalization errors can expose exit 8 instead of the public exit 9.
- `validate_review_result()` checks only selected container types before `compute_human_review_binding()`; malformed persisted Binding fields can therefore be reclassified as `STALE` when recapture raises.
- Terminal/Summary reads share `MAX_HUMAN_REVIEW_DECISION_BYTES`, but producer payloads have no pre-creation size gate and reviewer/local account identities have no UTF-8 byte bound.
- Human Review composition remains concentrated in `review_decision.py`; status classification, schema validation, pair parsing, producer transaction, and CLI presentation are not separate owners.
- Worktree began clean on `main` at `16758846bf96f82ad2ad66333f73c9b8867017b4` after v1.2.17 publication evidence.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| INVALID can return an internal exit code | fact | repository source | 2026-07-13 | `review_decision.py::main` | fresh; no sensitive data |
| Binding validation is shallow | fact | repository source | 2026-07-13 | `review_decision.py::validate_review_result` | fresh |
| Producer has no Decision Pair byte preflight | fact | repository source | 2026-07-13 | `review_decision.py::decide` | fresh |
| Required invalid/stale cases and module split | requirement | user-supplied v1.2.17 review | 2026-07-13 | current task prompt | fresh |

## Governed defect diagnosis

- Observed failure: one public status can have multiple exit codes, malformed evidence can be mislabeled as stale, and a successful producer can theoretically create a pair its own reader rejects.
- Competing hypotheses: current-state drift versus persisted-schema invalidity. Current code validates only shallow shapes, then catches all recapture `PipelineError` values as stale, so the ownership order—not repository drift—is the classification defect.
- Ownership path: persisted evidence schema must be decided before `compute_human_review_binding`; Decision Pair bytes must be bounded before `pinned_empty_private_artifact`; CLI classification must collapse all invalid exceptions to public exit 9.
- Violated invariant: `INVALID`/9 means evidence is structurally unsafe or inconsistent; `STALE`/12 means fully valid evidence no longer matches current state; every committed pair must be immediately readable by the same version.
- Root cause: schema validation, current-state evaluation, producer budgeting, and CLI mapping are composed in one module without explicit ownership boundaries.
- Root-cause alignment: PASS.

## Constraints and invariants

- Binding v4 exact fields and meanings remain unchanged; schema validation is read-only and occurs before repository/Artifact recapture.
- Validate all hashes, budgets, identities, canonical path lists, Artifact entries, repository commitment, and protected-deletion commitment, including Binding/Result agreement.
- Public verify results are fixed: `VALID`/0, `INVALID`/9, `STALE`/12. Internal stage exit codes never escape this protocol.
- Stdout contains only the status word. Stderr may contain one bounded diagnostic message but never Artifact bytes.
- Reviewer and local account UTF-8 values are nonempty and at most 4096 bytes. Terminal and Summary each share the exact 1 MiB producer/consumer limit.
- Payload budgets are checked before either decision file is created.
- Legacy accept/reject CLI syntax remains compatible; valid canonical v4 Results and pairs remain valid.

## Impact map

- Producers: Human Review Result creation in `run_pipeline.py`; Decision Pair creation in the new `human_review/decision.py`.
- Consumers: `review_decision.py`, automation interpreting stdout/exit status, and tests importing former public helpers.
- Persisted data: existing `result.json`, `human-review.ndjson`, and `human-review-summary.json`; no migration or rewrite.
- Public contracts: verify exit codes and stderr diagnostics; existing accept/reject flags unchanged.
- Architecture: new `scripts/human_review/` package with schema, binding, pinned I/O composition, decision, and verify owners.
- External systems: GitHub main, CI, annotated v1.2.18 tag, and formal Release after exact-SHA gates.

## Design and decisions

- `schema.py` owns complete v4 structural validation and Result/Binding agreement.
- `binding.py` owns current-state recomputation after schema validation.
- `pinned_io.py` owns bounded Decision Pair reads through Runner's stable private-descriptor primitives.
- `decision.py` owns identities, payload budgets, canonical pair parsing, and the compensating two-file transaction.
- `verify.py` owns stale versus invalid classification and returns verified details; the top-level script is a thin CLI adapter.
- `run_pipeline.py` imports shared Human Review constants and continues to expose compatibility names used by existing callers.
- Reject treating every recapture error as schema invalid: after full validation, repository/Artifact/protected-state recapture errors are precisely the stale boundary.

## Implementation sequence

1. Add fail-before classification and producer-budget tests, including the five required malformed Binding cases.
2. Add shared constants and complete v4 schema validation before recapture.
3. Split Human Review composition into the dedicated package and retain compatibility exports where tests or public script loading require them.
4. Enforce identity/payload budgets before file creation and fix public exit mapping plus bounded stderr reasons.
5. Update versions, validator contracts, bilingual public/architecture/troubleshooting/maturity docs, changelog, and the existing durable Human Review decision.
6. Run focused/full gates and a fresh counterexample challenge; publish only after exact-SHA CI succeeds.

## Rollout, failure, and rollback

- Dry-run: temporary repositories and synthetic malformed v4 documents; pair paths are asserted absent/empty on producer rejection.
- Mixed-version behavior: no persisted fields change. New verification rejects malformed/noncanonical evidence earlier; canonical v4 evidence remains compatible.
- Failure detection: exact stdout/exit/stderr tests, a no-recapture assertion for invalid schema, and immediate verify of every successful pair.
- Rollback: revert the code commit before tagging; after publication, publish a forward patch because existing artifacts are not rewritten.
- Irreversible point: annotated tag and public GitHub Release, already authorized by the user but gated on exact-SHA CI.

## Verification

- Original failure path: subprocess verify cases that currently print `INVALID` and return 8; malformed Binding recapture mislabeled `STALE`; producer payload boundary tests.
- Owning-boundary invariant: complete schema validator runs before a mocked recapture; exact Decision Pair budget preflight runs before pinned file creation.
- Adjacent negative/alternate path: real repository drift remains `STALE`/12; valid pair remains `VALID`/0 with stderr empty; diagnostic failures keep stdout stable.
- Focused tests: `python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py`.
- Contract tests: `make validate`, `make check`, `make compatibility-smoke`.
- Type/build: isolated `compileall`, import smoke, and `git diff --check`.
- Post-action: exact release SHA, eight-job CI, annotated tag target, formal Release, documentation CI, remote refs, and clean worktree.

## Risks

- Deep validation may reject previously tolerated malformed v4 documents.
  - Mitigation: enforce only producer-owned canonical forms and retain all persisted fields; document this as fail-closed validation, not migration.
  - Residual risk: manually edited or noncanonical v4 evidence must be rerun.
- Module extraction can create import cycles in direct-script and unittest loading modes.
  - Mitigation: keep shared constants dependency-free, add package import smoke coverage, and keep Runner as a one-way dependency of higher Human Review modules.
  - Residual risk: downstream code importing private functions from `review_decision.py` is unsupported; compatibility re-exports cover repository tests.
- Diagnostic stderr could expose evidence details.
  - Mitigation: emit exception messages only, cap UTF-8 output, and never include file contents or serialized Artifact data.
  - Residual risk: canonical path names may still be operationally sensitive and should be handled as private command output.

## Decision log

- 2026-07-13 — GO: classification and producer-budget defects are localized to missing precondition ownership, not current-state capture correctness.
- 2026-07-13 — Fail-before evidence: malformed metadata floor/sensitive path printed `INVALID` but exited 8; malformed protected deletion printed `STALE`/12; malformed Run identity lacked a reason; the producer accepted an over-budget mocked Summary; shared budget/identity helpers were absent.
- 2026-07-13 — Preserve Human Review v4: complete validation consumes existing fields and does not change their interpretation.
- 2026-07-13 — Split composition but retain Runner primitives: this reduces classification drift without a high-risk rewrite of the already-tested general state and descriptor engines.
- 2026-07-13 — Final local PASS: `make check` completed 58 repository tests and 127 Strict Runner tests; `make compatibility-smoke` passed against `codex-cli 0.144.0-alpha.4`; isolated `compileall` and `git diff --check` passed.
- 2026-07-13 — Counterexample challenge PASS: malformed Binding classes are rejected before recapture, invalid pair files remain `INVALID`, canonical current-state repository drift remains `STALE`, exact 1 MiB payloads remain readable, and one-byte-over-budget producer paths fail before either pair file is created.
- 2026-07-13 — Publication complete: release commit `16b9966a3512d46014da32196f331a73246ea4e3` passed all eight jobs in CI run `29237033241`; annotated tag `v1.2.18` targets that commit and the formal GitHub Release is public.

## Durable decision records

- Amend `docs/decisions/2026-07-12-human-review-and-setup-recovery.md` with schema-first classification, shared pair budgets, diagnostic protocol, and module ownership.

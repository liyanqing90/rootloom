# Keep Strict Review Evidence-Honest and Resource-Bounded

- Status: accepted
- Date: 2026-07-15
- Owners: Rootloom maintainers
- Scope: Personal Core Strict Review summary, sensitive capture, Git execution, and contract-seal lifecycle
- Supersedes: the summary-status, Git-capture, sensitive-discovery, and seal-recovery clauses of [Keep Personal Intelligence Advisory, Local, and Evidence-Subordinate](2026-07-14-personal-intelligence-contract.md)
- Superseded by: none

## Context

Personal Core 2.3 has a strong mechanical evidence chain, but its aggregate result still uses `VERIFIED_CHANGE` after combining machine-observed evidence with an operator assertion that semantic review occurred. That name can be read as proof of correctness even though a tautological command can mechanically satisfy a self-authored target mapping. A metadata-only sensitive quarantine can also return that complete result after intentionally withholding changed content.

The same review path bounds Git output and path counts but not Git time, sends Git through a separate process implementation from verification, and discovers sensitive paths by enumerating every tracked and ignored path before applying an already-shared classifier. Contract drafts use a recursive `TODO` substring check and the two-file contract/seal publication lacks a validated continuation after an uncatchable interruption. Dirty-baseline fallback also scopes every current path after any snapshot change, even when a pre-existing untracked fingerprint proves that the user-owned file is byte-identical to intake.

The product must correct those owning decisions without adding semantic-proof adapters, a second runner, blanket privacy blind spots, or Enterprise Assurance workflow state.

## Evidence

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| A tautological command plus operator assertion reaches the highest 2.3 status | fact | local 2.3 source/tests | 2026-07-15 | `finalize_change.py`; `tests/test_engineering_change.py::test_writes_compact_summary_and_verification_bundle` | current; synthetic data only |
| A confirmed sensitive rename redacts all changed content but returns the highest 2.3 status and exit zero | fact | local 2.3 regression | 2026-07-15 | `tests/test_engineering_change.py::test_confirmed_sensitive_rename_quarantines_all_changed_content` | current; synthetic secret never serialized |
| Git subprocesses have byte ceilings but no timeout/process-tree convergence | fact | local 2.3 source | 2026-07-15 | `runner/state.py`; `runner/process.py` | current; no sensitive content |
| Sensitive discovery enumerates all tracked and ignored paths although shared pathspecs exist | fact | local 2.3 source | 2026-07-15 | `runner/state.py`; `plugins/rootloom/lib/rootloom_paths.py::sensitive_git_pathspecs` | current; no sensitive content |
| Recursive TODO matching rejects legitimate business text and two exclusive writes can be interrupted between files | fact | local 2.3 source | 2026-07-15 | `begin_review.py`; `seal_contract.py`; `runner/review_run.py` | current; no sensitive content |
| Existing repository contract and focused suite pass before the change | fact | local Python/macOS environment | 2026-07-15 | `make validate`; 95-test `tests.test_engineering_change` run | current; one environment skip |

## Decision

`finalize_change.py` and `runner/contracts.py` own an evidence-completion status contract in summary revision 4:

- `REVIEW_EVIDENCE_COMPLETE` replaces `VERIFIED_CHANGE` as the only status that sets `passed: true` and returns strict quality exit zero;
- the status means the sealed scope/hash/command/capture chain is complete and an operator asserted semantic review; it does not mean Rootloom proved the change correct;
- top-level `semantic_review` records `operator-asserted`, `partial-operator-asserted`, or `not-reviewed` independently from machine evidence;
- a semantic assertion without an operator-sealed evidence chain is named `SEMANTIC_REVIEW_ASSERTED`, not a verified or completed review;
- an otherwise-complete review with changed content withheld by sensitive quarantine returns `REVIEW_REQUIRED_WITH_REDACTIONS`, `passed: false`, and a nonzero quality exit;
- existing artifact/field/format names remain, but exact-value consumers must branch on `schema_revision` and migrate at revision 4. No authoritative legacy alias is emitted.

`runner/process.py` remains the only process-tree controller. `runner/state.py` routes every Git child through it, closes inherited stdin, and translates Git-specific timeout/output/failure diagnostics. Public entry points accept a finite-positive operator-controlled `--max-git-seconds` budget and a positive `--max-sensitive-paths` budget; repository evidence cannot raise them.

Sensitive discovery sends Git the shared case-insensitive built-in pathspecs plus literal user-declared roots and rechecks returned paths with the shared Python classifier. It does not enumerate every ordinary tracked/ignored path and does not silently exclude vendor/cache trees. Deliberately overmatching Git candidates have a separate bounded internal ceiling; `--max-sensitive-paths` counts only the classified sensitive-result union, so false-positive names cannot spend the public result budget.

`runner/review_run.py` owns an exact draft placeholder. `begin_review.py` emits it, while `seal_contract.py` rejects that exact marker and every exact legacy generated marker rather than arbitrary Todo-domain text. `seal_contract.py --recover` requires an existing final contract and may complete or validate publication only when existing bytes exactly match the contract derived from the current baseline, manifest, and draft; absent, ambiguous, or mismatched evidence is never created, overwritten, deleted, or inferred by recovery.

Dirty-baseline attribution uses the strongest evidence already stored by baseline v2. A changed aggregate tracked patch still conservatively scopes every current pre-existing tracked endpoint because per-path tracked bytes are unavailable. Pre-existing untracked entries are compared through their per-path fingerprint or metadata records; an exact unchanged match remains pre-existing and outside task scope, risk analysis, and the emitted `diff.patch`, while a changed match is scoped. The partition is computed before analysis and reused by scope and patch consumers. Removed pre-existing paths remain a gate failure.

## Alternatives considered

- Keep `VERIFIED_CHANGE` and add stronger documentation — rejected because the authoritative machine value and zero exit still overstate what the evidence establishes.
- Add framework-specific semantic test adapters — rejected because adapters increase dependencies and still cannot prove root cause, consumer completeness, or semantic sufficiency.
- Emit both old and new authoritative success aliases indefinitely — rejected because it preserves the misleading contract and leaves consumers unsure which status governs `passed` and exits.
- Give redacted reviews `MECHANICALLY_VERIFIED` — rejected because a dedicated actionable state makes the missing content and required human review visible.
- Implement Git timeout/cleanup again in `state.py` — rejected because divergent process-tree behavior would recreate the ownership defect.
- Exclude common vendor/cache directories by default — rejected because a silent privacy blind spot is worse than a fail-closed budget; targeted pathspecs already avoid enumerating ordinary cache contents.
- Automatically delete or overwrite an orphan contract — rejected because partial evidence may be user- or attacker-modified; exact recovery is reversible and inspectable.

## Consequences

- Positive: summary/exit behavior now names evidence completeness rather than code correctness, and redaction cannot produce a passing review.
- Positive: Git and verification share timeout, output, descendant cleanup, and cross-platform process ownership; closed Git stdin also makes unborn-repository capture deterministic under interactive callers.
- Positive: large repositories no longer spend the sensitive discovery budget on every ordinary tracked/ignored path.
- Positive: legitimate Todo-domain contracts seal, and exact interrupted publications can resume without evidence overwrite.
- Positive: unchanged user-owned untracked files no longer contaminate governed task scope, risk claims, or patch content, without weakening tracked-overlap failure closure.
- Negative: consumers that hard-code `VERIFIED_CHANGE` must migrate for summary revision 4.
- Negative: operator semantic review remains an assertion; Rootloom still cannot prove test sufficiency or correctness.
- Negative: very large sets of targeted candidates can still exhaust the internal candidate ceiling, and very large classified sets can exhaust the configured result budget; both fail closed.
- Operational: defaults remain low-friction; callers raise budgets explicitly when repository evidence justifies it, inspect `REVIEW_REQUIRED_WITH_REDACTIONS` manually, and use `--recover` only on the original review directory.

## Verification

- `tests/test_engineering_change.py` must cover new status/exit semantics, redaction caps, Git controller timeout mapping and inherited-stdin closure, finite-positive budget validation, separate pathspec candidate/result ceilings, task-partitioned analysis/patch output, exact placeholder compatibility, and absent/matching/mismatched recovery.
- `make check` must enforce synchronized source, tests, README, architecture, maturity, decision, and Skill contracts.
- `make compatibility-smoke` must show plugin installation/default setup behavior is unchanged.
- Strict finalization of the implementing change must return revision-4 `REVIEW_EVIDENCE_COMPLETE`, preserve the pre-change baseline/ref/index, and leave the intake-time user image unchanged.

## Revisit when

- a future platform exposes trustworthy semantic coverage or signed CI provenance that changes what Rootloom can mechanically establish;
- measured repositories regularly exceed either the targeted-candidate or classified-result ceilings despite ordinary caches no longer being enumerated;
- Git process control can move to a stronger platform-native sandbox or a single total capture deadline without harming Personal Core portability;
- exact-value consumers require a new top-level summary format rather than schema-revision evolution.

## Follow-up

Summary revision 5, baseline v3, identity-neutral provenance, the secret-material/security-domain classifier split, and the aggregate stable-capture deadline are governed by [Separate secret material from security code and bound stable capture](2026-07-15-sensitive-material-and-capture-bounds.md). This record remains the historical owner of revision-4 status honesty and redaction-cap semantics.

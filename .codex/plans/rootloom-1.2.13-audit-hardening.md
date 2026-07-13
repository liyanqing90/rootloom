# Rootloom 1.2.13 audit hardening

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-13
- Task type: security and acceptance-integrity defect repair
- Risk: Tier 2 (Governed)

## Goal and observable success

Close the actionable 1.2.12 audit gaps in the Strict Runner without changing the protected-deletion authorization contract: Human Review must bind and recheck the exact deleted paths plus canonical bounded repository state under the repository lock; every isolation-launcher spawn must prove the configured executable identity; managed-process setup failures must transfer immediately to cleanup ownership; directory fingerprints must not invoke unbounded Git subprocesses.

Success requires focused fail-before/pass-after regression coverage, the bundled Strict Runner suite, repository validation, and a fresh adjacent-path challenge.

## Non-goals

- Kernel/container attestation, hostile-command containment, external signatures, or WORM storage.
- Release, tag, publication, deployment, or external mutation.

## Baseline evidence

- `compute_human_review_binding()` binds HEAD, ordinary Git status, Result core, and private Artifacts but receives no protected-deletion paths and does not commit the full final repository state.
- `review_decision.py` computes and persists a decision without `repository_lock(repo)` and without a post-write state check.
- `normalize_isolation_launcher()` hashes the executable only once; stage and verification spawn sites consume the saved argv without revalidation and allow an executable inside the target repository.
- `run_managed()` creates/configures its selector after `Popen()` but before entering cleanup `try/finally`.
- `file_fingerprint()` runs unbounded `git status` and `git rev-parse` for directories.
- Working tree was clean at `main` commit `0d18d69` before edits.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Human Review can miss recreated ignored protected paths | fact | local repository source | 2026-07-13 | `run_pipeline.py:compute_human_review_binding`, supplied 1.2.12 audit | current tree; no sensitive content read |
| Accept has a cooperative-writer TOCTOU | fact | local repository source | 2026-07-13 | `review_decision.py:decide` | current tree |
| Launcher identity is startup-only | fact | local repository source | 2026-07-13 | `normalize_isolation_launcher`, `run_stage`, verification spawn | current tree |
| Selector setup can escape ownership cleanup | fact | local repository source | 2026-07-13 | `run_managed` | current tree |
| Directory fingerprint bypasses capture budgets | fact | local repository source | 2026-07-13 | `file_fingerprint` | current tree |

## Governed defect diagnosis

- Observed failure: acceptance and execution metadata can describe a state or launcher identity that is no longer true at the terminal action/spawn boundary.
- Competing hypotheses: Git status/Artifact drift checks were sufficient; rejected because ignored recreated paths are absent from ordinary status. Repository locking alone was sufficient; rejected because non-cooperative writers remain possible and require a post-write recheck. A startup launcher hash was sufficient; rejected because later spawn sites reopen the path.
- Ownership path: Strict Runner state capture and Human Review protocol in `run_pipeline.py`/`review_decision.py`; process ownership in `run_managed()`; launcher execution at each spawn boundary.
- Violated invariant: a terminal acceptance or managed spawn must bind the exact local state/identity it authorizes at the point the action is persisted or executed.
- Root cause: the v2 binding and launcher contracts captured indirect/startup evidence rather than reusing the Runner's canonical bounded state and exact-path checks at terminal boundaries; cleanup ownership began too late; directory handling embedded an unrelated unbounded Git probe.
- Root-cause alignment: PASS

## Constraints and invariants

- Preserve deletion-only exit 10 and existing Result compatibility where safe; version the strengthened binding/decision formats.
- Never content-hash protected ignored/sensitive paths; bind only exact missing state and safe ancestor metadata for authorized deletion targets.
- Reuse existing repository-state budgets and safety classification; fail closed on budget, symlink, topology, or identity drift.
- Repository lock serializes cooperative Rootloom writers only; retain explicit documentation that it cannot stop arbitrary external mutation.
- No new dependency; standard library only.

## Impact map

- Producers: Strict Runner final Result, isolation launcher normalization, managed command/stage/verification spawn paths.
- Consumers: `review_decision.py`, Human Review automation, Runner tests, architecture/maturity/troubleshooting documentation.
- Persisted data: Result `human_review_binding`, `human-review.ndjson`, `human-review-summary.json` (versioned additive replacement for newly produced runs).
- Public contracts: Strict Runner CLI behavior for `--isolation-launcher`/`--require-isolation`; Human Review accept/reject format.
- Generated artifacts: none.
- External systems: none.

## Design and decisions

- Ownership: canonical state commitment belongs in `scripts/runner/state.py`; stable executable identity belongs in `scripts/runner/process.py`; decision sequencing belongs in `review_decision.py`; all spawn sites use one launcher helper.
- Interfaces: binding accepts the exact protected-deletion list, records canonical bounded repository state and exact-missing/ancestor-chain assertions, and rejects drift. Acceptance holds the repository lock, re-reads Result, writes the terminal record, then recomputes the same binding before success.
- Dependency direction: review helper imports Runner primitives; Runner does not import decision CLI.
- Compatibility window: newly produced results use a new binding/decision version. Older v2 results fail closed rather than being silently upgraded because their missing final-state evidence cannot be reconstructed.
- Alternatives rejected: hashing protected file contents violates the metadata-only contract; lock-only acceptance cannot constrain arbitrary local writers; stable-FD launcher execution would require a platform-specific execution redesign and is not needed when immediate pre-spawn no-follow identity validation fails closed.

## Implementation sequence

1. Add regression tests for ignored-path recreation, locked pre/post decision checks, in-repo launcher rejection and per-spawn drift, selector initialization cleanup, directory fingerprint behavior, and historical Recovery target compatibility. Completed.
2. Implement canonical Human Review state commitment and exact deletion assertions; update decision sequencing under lock with post-write recheck and compensation on drift. Completed as binding/decision v3.
3. Strengthen launcher provenance and validate immediately before every stage/verification spawn. Completed with configured and actual pre-spawn identities.
4. Move managed-process initialization under unified cleanup ownership and make directory fingerprints metadata-only/fail closed for entrypoints. Completed.
5. Version Setup Recovery target schemas independently of current `all_targets()`, record producer/schema/type, and preserve the implicit 1.2.12 reader. Completed.
6. Split canonical Runner state/process identity and Setup transaction/recovery ownership into internal modules, update bilingual public contracts and the accepted decision record, then run focused and repository-wide verification. Completed.

## Rollout, failure, and rollback

- Dry-run/preview: focused unit tests create temporary Git repositories and launchers only.
- Mixed-version behavior: v3 decisions accept only v3 bindings; existing v2 runs require rerun/manual external handling and are never auto-accepted.
- Failure detection: exit 9 with an explicit binding, exact-deletion, launcher identity, or cleanup error.
- Rollback or compensation: local code revert; decision writing truncates/removes its just-created terminal files when the post-write repository state recheck fails.
- Irreversible point: none; no release or external mutation is authorized.

## Verification

- Original failure path: focused test recreates ignored `.env` after binding and proves accept refusal.
- Owning-boundary invariant: focused tests compare canonical commitments and launcher identity immediately before spawn.
- Adjacent negative/alternate path: unchanged deleted path accepts; outside-repo unchanged launcher executes; selector setup failure reaps child; ordinary directory metadata fingerprint is bounded.
- Focused tests: `python3 -m unittest plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py tests/test_setup_rootloom.py` — 116 tests passed during implementation; final `make check` passed 52 repository tests plus 87 Runner tests.
- Contract/migration tests: Human Review v2 rejection/v3 acceptance tests in bundled suite.
- Type/lint/build/package: `make check` passed; `make compatibility-smoke` passed against `codex-cli 0.144.0-alpha.4` with no managed leftovers and exact config restoration.
- UI/browser evidence: not applicable.
- Security/dependency checks: repository contract validation; no dependency changes.
- Post-action verification: `git diff --check` passed. Fresh challenge inspected model-stage and verification launcher consumers, ordinary rollback and orphan-recovery schema consumers, and the exception (not only unequal-result) post-write drift path. It found and fixed missing compensation on a raised post-write exact-missing failure, stale setup recovery documentation, and verification preflight sizing for the added launcher identity field.

## Risks

- Risk: full repository commitment may be expensive on large trees.
  - Mitigation: reuse bounded state enumeration/digest cache and existing maximum path/byte budgets.
  - Residual risk: capture still enumerates paths and can fail closed on configured limits.
- Risk: post-write drift leaves a terminal record.
  - Mitigation: compensate decision and summary artifacts before returning failure.
  - Residual risk: arbitrary process/storage failure can still interrupt compensation; private audit files are not WORM or crash-atomic as a group.
- Risk: path-based launcher revalidation has a narrow open/exec race.
  - Mitigation: no-follow identity validation immediately before `Popen`; document absence of kernel attestation.
  - Residual risk: hostile local writers require external immutable/container execution infrastructure.

## Decision log

- 2026-07-13 — Treat all current actionable audit findings as one 1.2.13 integrity patch, including Recovery schema evolution and bounded ownership-module extraction; keep external 1.3 infrastructure guarantees out of local claims.
- 2026-07-13 — Strengthen the durable Human Review decision with a versioned binding rather than silently changing v2 semantics.
- 2026-07-13 — Preserve legacy Recovery schema 1 literally and require producer/schema/type fields for new schema-2 Manifests.

## Durable decision records

- Updated `docs/decisions/2026-07-12-human-review-and-setup-recovery.md` with the accepted v3 state-binding and historical Recovery-schema contracts.

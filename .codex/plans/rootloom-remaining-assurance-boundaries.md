# Rootloom remaining assurance-boundary closure

## Status

- State: complete (local candidate; remote platform jobs unobserved)
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security / architecture / recovery / CI
- Risk: Tier 2 (Governed)

## Goal and observable success

Close the assurance boundaries explicitly left open by the local Runner 2.14 candidate: source-bound repository/status/control/model-output budgets, reusable snapshot hashing, enforceable external isolation launch, durable Human Review acceptance/rejection, setup orphan-transaction recovery, and platform-scoped CI. Every new completeness or acceptance claim must have a fail-before/pass-after test, a versioned persisted contract where applicable, bilingual documentation, repository validation, and full local verification. No push, tag, Release, or production mutation is authorized.

## Non-goals

- Implementing a container, cgroup, VM, or Windows kernel sandbox inside Python. Rootloom will define and enforce a fingerprinted isolation-launcher interface; the launcher owns host containment and must be supplied by the operator/platform.
- Claiming Windows support for the POSIX Strict Runner. Windows CI covers portable setup/seeding/contracts; Strict Runner remains an explicit unsupported-platform failure.
- Replacing Git, introducing a database/service, adding a runtime dependency, or silently weakening completeness checks for performance.

## Baseline evidence

- `git_status_raw()`, index/control refs, and selected Git control trees use full-buffer or unbounded in-memory representations.
- tracked and ordinary-untracked path enumeration calls `list_git_paths()` without `max_paths`; complete manifests and Delta status are materialized afterward.
- `run_stage()` lets Codex write `-o` JSON and `read_json()` reads the complete file without a byte ceiling.
- repeated `capture_repo_state()` hashes every content-bearing file even when stable metadata proves a prior digest reusable.
- `run_managed()` has no isolation-launcher contract; POSIX process groups cannot contain `setsid()` descendants.
- protected deletion ends at exit 10 with no accept/reject command, reviewer identity, Git/Artifact binding, or acceptance-time drift check.
- setup writes a prepared manifest before mutation and compensates caught exceptions, but has no committed transaction phase/journal or orphan recovery command after `SIGKILL`/power loss.
- public CI runs only Ubuntu; setup/seeding contain Windows branches and Runner claims macOS support without CI jobs for those scopes.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Unbounded state/model producers | fact | local Rootloom source on macOS | 2026-07-12 | `run_pipeline.py:run_bytes`, `capture_repo_state`, `run_stage`, `read_json` | Current working tree |
| Missing durable Human Review transition | fact | local Rootloom source | 2026-07-12 | `run_pipeline.py:review_outcome`, final result write | Current working tree |
| Setup lacks orphan recovery | fact | local Rootloom source/tests | 2026-07-12 | `setup_rootloom.py:_apply_plan_locked`, transaction manifest/state flow | Current working tree |
| CI is Linux-only | fact | repository workflow | 2026-07-12 | `.github/workflows/ci.yml` | Current working tree |
| Priority and proposed surfaces | externally reviewed lead, locally verified | user-supplied 1.2.11 review and current request | 2026-07-12 | attachment `f77c6caa-94b5-4f2d-b73a-b309d817a611` | No sensitive payload copied |

## Governed defect diagnosis

- Observed failure: individual patch/log producers are bounded, while adjacent state, model-output, approval, recovery, and platform contracts can still allocate without a source limit, accept without an immutable binding, or remain ambiguous after process death.
- Competing hypotheses: external filesystem quotas, the current JSON Schema, repeated full snapshots, exit 10, caught-exception compensation, and Linux CI are sufficient. Rejected because they do not bound allocation before materialization, reduce repeated hashing, create a durable approval transition, recover an interrupted transaction, or attest claimed platform branches.
- Ownership path: Strict Runner state/model/managed-command boundaries; a repository-owned Human Review command; setup transaction journal; `.github/workflows/ci.yml` plus validator.
- Violated invariant: every automatic completeness/acceptance claim must be bounded and attributable at its producer; every interrupted mutation must be detectable and recoverable before another transaction; supported-platform claims require scoped executable evidence.
- Root cause: controls were added incrementally around the largest observed artifacts without a single budget context, approval protocol, recovery state machine, or platform-scope matrix.
- Root-cause alignment: PASS

## Constraints and invariants

- Preserve exact repository mutation detection; snapshot caching may reuse a digest only when identity and mutation-relevant metadata match.
- All new budgets are positive additive CLI options with conservative defaults and fail before downstream completeness claims.
- Isolation is opt-in for backward compatibility and mandatory when `--require-isolation` is set; the executable and its arguments are fingerprinted and every managed model/verification command is wrapped without a shell.
- Human acceptance binds the final result, current HEAD/state fingerprint, reviewed Delta/verification Artifact hashes, reviewer identity, decision, and timestamp; acceptance refuses drift and is append-only/private.
- Setup recovery is lock-serialized, phase-aware, idempotent, path-confined, hash/mode-aware, and refuses ambiguous post-crash user edits.
- Portable CI jobs never imply native-Windows Strict Runner support.

## Impact map

- Producers: Git/status/control/path state, model stage output, snapshot fingerprints, managed commands, final review result, setup transaction writes.
- Consumers: stage gates/prompts, verification, operators, future audit tooling, setup status/apply/rollback/recover, CI.
- Persisted data: Runner metadata/result/approval NDJSON; setup manifest/journal/state; private Artifacts.
- Public contracts: Runner CLI and exit codes, setup CLI, Artifact schemas, CI platform scope, bilingual docs.
- Generated artifacts: runtime run directories and Codex-home transaction backups/journals.
- External systems: local isolation launcher; GitHub Actions only after a separately authorized push.

## Design and decisions

- Budget context: one immutable `StateLimits` object is threaded through snapshots; bounded subprocess capture fails at the producer and reports the named budget.
- Snapshot cache: reuse SHA-256 only for same normalized path, file kind, device/inode, size, mtime-ns, ctime-ns, and mode within the current run; content is rehashed on any mismatch.
- Model output: remove/ignore an old output before launch, enforce a post-command byte ceiling before JSON read, and reject oversized/missing/symlinked output. The Codex process output budget remains separate.
- Isolation: a repeatable argv launcher prefix followed by `--` wraps managed commands; executable fingerprint and argv are recorded. Required isolation without a launcher fails before any stage.
- Human Review: add a separate local `review-decision` command operating on a completed run directory; it verifies immutable bindings and appends one signed-by-identity decision record. Reject is terminal; accept is valid only without drift.
- Setup recovery: prepared/applying/applied/committed/compensating phases are atomically journaled. New setup operations refuse an unresolved transaction; `recover` restores the pre-transaction snapshot or finishes state commit only when evidence is unambiguous.
- CI: keep the full Python/version matrix on Ubuntu, add portable repository tests on macOS/Windows, add Strict Runner tests on macOS, and validate explicit Windows rejection separately.

## Implementation sequence

1. Add fail-before tests for every state/model-output budget and snapshot digest reuse/invalidation.
2. Implement bounded state capture, `StateLimits`, digest cache, CLI/metadata propagation, and model JSON ceiling.
3. Add isolation launcher wrapping/fingerprinting/required-mode tests and contracts.
4. Add versioned Human Review decision records, accept/reject command, drift/hash/identity tests, and documentation.
5. Add setup transaction phase journal, orphan detection/recovery, fault-injection tests, and CLI/docs.
6. Expand platform-scoped workflow and validator contracts.
7. Run warning-as-error focused tests, repository checks, compatibility smoke, compile/diff checks, and final review.

## Rollout, failure, and rollback

- Dry-run/preview: CLI help, synthetic small-budget failures, synthetic orphan journals, workflow validation, and complete local tests.
- Mixed-version behavior: new fields/options are additive; new approval and setup-journal formats are explicitly versioned. Existing installed transactions remain rollback-compatible and are treated as committed legacy transactions.
- Failure detection: stable `PipelineError`/CLI nonzero before completeness; unresolved setup transaction blocks apply/rollback until recovery; Human Review drift blocks acceptance.
- Rollback or compensation: local source changes are reversible before publication; runtime setup recovery restores recorded pre-state only when hashes prove no ambiguous user edit.
- Irreversible point: none in the current task.

## Verification

- Original failure paths: synthetic oversized status/path/control/model JSON; unchanged repeated snapshot; drifted digest; missing isolation; approval after drift; interrupted setup phases.
- Owning-boundary invariant: named producers fail before claiming complete output; cache invalidates correctly; approval and recovery bind exact state.
- Adjacent negative/alternate path: defaults preserve ordinary repositories; changed same-size files are rehashed; optional isolation remains compatible; legacy transaction rollback remains green; reject decisions work without acceptance.
- Focused tests: Runner and setup test modules with `ResourceWarning` promoted to error.
- Contract tests: `make check`, repository validator, workflow/source contracts.
- Type/lint/build/package: Python compilation, compatibility smoke, diff check.
- Post-action verification: scoped dirty tree only; no external publication.

## Risks

- Risk: new defaults reject unusually large legitimate repositories or model results.
  - Mitigation: explicit positive overrides with metadata recording and clear producer names.
  - Residual risk: raising limits increases memory/disk/time exposure.
- Risk: metadata-based digest cache misses a content change that preserves all key metadata.
  - Mitigation: include inode/device/size/mode/mtime/ctime and scope cache to one locked run; platforms/filesystems with unreliable metadata can disable reuse.
  - Residual risk: hostile same-inode metadata restoration still requires OS isolation.
- Risk: isolation launcher is misconfigured or dishonest.
  - Mitigation: fingerprint argv/executable, require an explicit launcher, and never describe it as attested containment.
  - Residual risk: Rootloom cannot prove kernel containment from inside the child.
- Risk: recovery overwrites legitimate post-crash edits.
  - Mitigation: hash/mode preconditions and fail-closed ambiguous-state refusal.
  - Residual risk: operator-guided manual recovery may still be necessary after storage corruption.

## Decision log

- 2026-07-12 — User explicitly expanded scope to all previously disclosed remaining boundaries; external publication remains unauthorized.
- 2026-07-12 — Keep containment external but make its launcher interface executable, fingerprinted, and enforceable; do not claim process groups are a sandbox.
- 2026-07-12 — Use additive budgets and versioned records instead of truncating repository/model evidence after allocation.
- 2026-07-12 — Implemented Runner state-producer bounds, then simplified the Runner 2.16 public contract to 200,000 paths and 16 MiB per state/stage-JSON producer through `--max-state-paths` and `--max-state-bytes`, with positive-value validation and metadata recording.
- 2026-07-12 — Reused SHA-256 only within one repository-locked run and only across exact device/inode/size/mode/mtime/ctime identity; any mismatch rehashes content.
- 2026-07-12 — Added a no-shell absolute isolation-launcher prefix, rejects symlinks, fingerprints executable/argv, and makes missing isolation a pre-stage error when required. The launcher remains an operator/platform trust boundary.
- 2026-07-12 — The initial Human Review binding v1/decision v1 and setup recovery v1 candidates were superseded before publication: they did not bind the final Result core or Manifest, and rollback had no recovery journal.
- 2026-07-13 — Accepted Human Review binding/decision v2 and setup recovery v2 candidates after adding Result-core binding, no-follow durable terminal writes, Manifest-bound full preflight, and interrupted rollback recovery.
- 2026-07-12 — Expanded the candidate workflow to Linux full checks, macOS Strict Runner plus portable checks, and Windows portable checks. These new platform jobs are source-validated but cannot become observed CI evidence without an authorized push.
- 2026-07-12 — The superseded v1 candidate passed repository validation, 43 repository tests, 81 Runner tests with `ResourceWarning` promoted to error, Python compilation, workflow YAML parse, diff check, and Codex CLI `0.144.0-alpha.4` compatibility smoke; those results are historical evidence, not release evidence for v2.

## Outcome

- Repository state completeness is bounded before downstream claims: tracked/untracked path counts, status bytes, index/refs/control command output, control-tree entries/path bytes, Delta/log records, and model JSON parsing all have explicit limits.
- Repeated full content hashing is replaced by a locked-run identity cache without weakening metadata-change detection; exact identity mismatch rehashes.
- Host isolation is now an enforceable integration contract rather than a process-group claim: required mode refuses to start without a fingerprinted launcher, and every model/verification command is wrapped without a shell.
- Protected-deletion Human Review has drift-bound accept/reject records over HEAD, status, Artifact hashes, asserted reviewer and local identity, with duplicate terminal refusal.
- Setup has atomic phase journals, prior-state backups, orphan detection, lock-serialized idempotent recovery, and ambiguous-edit refusal.
- Platform scope is encoded in CI: Linux full matrix, macOS Strict Runner/portable contracts, and Windows portable contracts while native Windows Runner remains rejected.
- Remaining external guarantees are accurately outside Rootloom: kernel behavior of the supplied isolation launcher, cryptographic organizational identity/WORM storage, storage durability below atomic rename, and observed remote macOS/Windows CI until publication is authorized.

## Durable decision records

- Updated `docs/decisions/2026-07-12-strict-runner-resource-artifacts.md` for state/model budgets and isolation.
- Accepted `docs/decisions/2026-07-12-human-review-and-setup-recovery.md` for approval and orphan recovery.

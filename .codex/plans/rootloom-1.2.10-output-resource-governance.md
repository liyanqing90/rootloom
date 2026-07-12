# Rootloom 1.2.10 command-output and verification-environment governance

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security
- Risk: Tier 2 (Governed)

## Goal and observable success

Bound per-command stdout memory and artifact growth, terminate commands that exceed the configured byte budget, expose output and drain outcomes structurally, and stop verification commands from inheriting the complete host environment by default. The existing timeout, process-group, and detached-pipe behavior must remain bounded and tested.

## Non-goals

- Host-level isolation of escaped processes or secret-file access.
- Content DLP, incremental repository snapshots, Human Review state machines, or other 1.3 work.
- Publishing or releasing without separate explicit authorization.

## Baseline evidence

- `run_managed()` uses `communicate()` and stores complete merged stdout/stderr in one Python string.
- Verification commands inherit `os.environ.copy()`, so unrelated credential variables can reach untrusted repository scripts and later be persisted if printed.
- Output cutoff state is currently conveyed only through text and four positional return values.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Command output is accumulated without a byte limit | fact | Rootloom 1.2.9 source | 2026-07-12 | `run_pipeline.py:run_managed` | Published source |
| Verification inherits the complete host environment | fact | Rootloom 1.2.9 source | 2026-07-12 | `run_pipeline.py:run_managed` and `run_verification` | Variable names only; no values inspected |
| Resource-exhaustion and persistence risks | externally reviewed inference | supplied 1.2.9 review | 2026-07-12 | attachment `9456be52-4458-4034-b44d-74de3e30414d` | Review text only |

## Governed defect diagnosis

- Observed failure: a log storm can exhaust Runner memory or artifacts before timeout cleanup; printed inherited secrets can become persistent artifacts.
- Competing hypotheses: stage timeout bounds output, and private artifact permissions are sufficient. Rejected because output allocation occurs continuously before timeout and private persistence still expands secret exposure lifetime.
- Ownership path: managed command I/O capture and verification environment construction.
- Violated invariant: every managed command must have bounded resource capture, and verification receives only explicitly required environment authority.
- Root cause: full-buffer `communicate()` and implicit full-environment inheritance.
- Root-cause alignment: PASS

### Pre-publication review gate

- Observed failure path: an exception after the direct parent exits can skip cleanup even while its original process group still contains children.
- Observed resource gap: per-command capture is bounded, but cumulative verification records, repeated JSON writes, and Reviewer prompt construction are not batch-bounded.
- Observed audit gap: model-stage `ManagedResult` fields are discarded after the text log is written.
- Ownership path: `run_managed()` exception cleanup, `run_verification()` batch accounting, `compact_verification()` prompt construction, and `run_stage()` artifact persistence.
- Violated invariant: interruption cleanup is process-group scoped; every persisted command outcome is machine-readable; verification resources are bounded both per command and per batch.
- Root cause: cleanup is conditioned on direct-child liveness, while resource and artifact governance stop at the single-command boundary.
- Root-cause alignment: PASS

## Constraints and invariants

- Preserve bounded timeout and SIGTERM/SIGKILL cleanup.
- Keep model-stage authentication compatibility; apply the minimal environment default specifically to deterministic verification.
- Retain only a fixed output tail and fixed-size diagnostics.
- Record environment names, never values.
- Keep existing CLI behavior compatible except for intentional verification environment minimization; provide explicit `--verify-env NAME` expansion.

## Impact map

- Producers: model stages and deterministic verification commands.
- Consumers: stage logs, verification JSON, Reviewer prompts, repair prompts, CLI diagnostics.
- Persisted data: private Runner artifacts.
- Public contracts: Runner CLI, result records, plugin and Runner versions.
- External systems: host environment inherited by verification commands.

## Design and decisions

- Ownership: replace full-buffer `communicate()` in `run_managed()` with POSIX selector-based bounded streaming.
- Interfaces: return a `ManagedResult` with structured byte counts, truncation, output-limit, drain-timeout, and detached-descendant fields.
- Output policy: default 8 MiB per command, retain a tail ring, terminate the original process group when observed bytes exceed the budget, and return a stable nonzero output-limit exit.
- Environment policy: verification receives a small portability allowlist plus repeatable caller-authorized `--verify-env NAME`; model stages retain their current environment for Codex authentication compatibility.
- Compatibility: existing positional unpacking remains temporarily supported by `ManagedResult.__iter__`, while internal callers use named fields.
- Alternatives rejected: post-hoc string truncation because it does not prevent memory exhaustion; regex output redaction because it cannot replace least-authority environment construction.

## Implementation sequence

1. Add bounded tail capture, structured result, and selector-based command I/O.
2. Add output-limit termination and detached drain integration.
3. Add verification environment allowlist and explicit opt-in CLI.
4. Persist structured output metadata and improve timeout messages.
5. Add log-storm, environment, detached-drain, and adjacent regression tests.
6. Bump patch versions, update bilingual contracts, and run full validation.
7. Before publication, clean the original process group on every exceptional exit even when the direct parent has already exited.
8. Add a verification-batch output budget, verification command-count ceiling, and compact Reviewer prompt limit.
9. Persist model-stage managed-command sidecars and cover all three review findings with regressions.

## Rollout, failure, and rollback

- Dry-run/preview: inspect CLI metadata and scoped diff.
- Mixed-version behavior: new CLI flags are additive; verification scripts depending on undeclared environment variables must opt in.
- Failure detection: stable output-limit exit, structured fields, environment-name assertions, bounded elapsed time, and no completion marker after termination.
- Rollback: revert the local candidate before publication.
- Irreversible point: none; publication requires explicit approval.

## Verification

- Original failure path: high-rate output exceeds a small test budget and is terminated before completion.
- Owning-boundary invariant: retained output and artifacts remain within the configured budget plus fixed diagnostics.
- Adjacent negative/alternate path: ordinary output, timeout, detached stdout, and SIGTERM/SIGKILL tests remain green.
- Environment path: an unrelated fake secret is absent while an explicitly authorized variable is present.
- Focused tests: `python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py`
- Repository checks: `make check`
- Compatibility: `make compatibility-smoke`
- Post-action: `git diff --check` and scoped status review.

## Risks

- Risk: verification commands that relied on undeclared environment variables may fail.
  - Mitigation: explicit `--verify-env NAME`, documented variable-name audit, and stable default allowlist.
  - Residual risk: HOME and PATH still expose host-local tools/files; hostile commands require OS isolation.
- Risk: selector behavior differs across POSIX platforms.
  - Mitigation: pipe-only use, existing Linux CI, local macOS tests, and bounded cleanup fallbacks.

## Decision log

- 2026-07-12 — Use streaming prevention rather than post-hoc truncation because the security objective is to bound allocation before timeout.
- 2026-07-12 — Minimize verification environment independently from model stages to avoid breaking Codex authentication.
- 2026-07-12 — Carry structured output-limit, drain, and detached-descendant fields into compact repair/Reviewer prompts so downstream stages never need to parse diagnostic prose.
- 2026-07-12 — Keep the 8 MiB per-command ceiling and add an independent 32 MiB verification-batch ceiling; the former stops a log storm, while the latter bounds cumulative artifacts and memory.
- 2026-07-12 — Limit a verification batch to 64 commands and bound its model-facing summary to 120,000 characters so zero-output command lists cannot bypass byte accounting.
- 2026-07-12 — Persist one structured sidecar per model stage rather than expanding the text log contract.
- 2026-07-12 — Verification passed after the pre-publication review fixes: 41 repository tests, 57 Runner tests, repository validation, Python compilation, `git diff --check`, and the Codex CLI compatibility smoke on `codex-cli 0.144.0-alpha.4` with no managed leftovers and exact config restoration.
- 2026-07-12 — User explicitly authorized “修复后发布”. Publication target is `liyanqing90/rootloom` `main`, annotated tag `v1.2.10`, and a non-draft GitHub Release; no force-push or pull request is required by the repository's established release sequence.

## Outcome

- Replaced unbounded `communicate()` capture with selector-based bounded tail streaming and stable output-limit termination.
- Added least-authority deterministic-verification environments with explicit name-based opt-in and value-free metadata.
- Added a 32 MiB verification-batch budget, 64-command ceiling, 120,000-character model-summary ceiling, and structured model-stage command sidecars.
- Preserved timeout, process-group cleanup, detached-pipe drain deadlines, stdin prompt delivery, and four-value result unpacking compatibility; exceptional cleanup now targets the original group after direct-parent exit.
- Verified 41 repository tests and 57 strict Runner tests with `make check`.
- Verified the real local plugin lifecycle against `codex-cli 0.144.0-alpha.4` with `make compatibility-smoke`; rollback left no managed artifacts and restored the pre-existing config.
- Verified Python compilation and `git diff --check`.

## Durable decision records

- None; this extends the existing Runner security boundary without changing project architecture ownership.

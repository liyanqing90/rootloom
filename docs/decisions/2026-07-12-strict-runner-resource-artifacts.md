# Bound Strict Runner resources at their owning artifact boundary

- Status: accepted
- Date: 2026-07-12
- Owners: Rootloom maintainers
- Scope: `high-assurance-coding-change` Strict Runner command, Delta, and verification artifacts
- Supersedes: none
- Superseded by: none

## Context

The Strict Runner executes model stages, deterministic verification, and its own Git Delta capture while holding a repository lock. A stage timeout alone does not bound output allocation, escaped descriptor lifetime, repeated serialization, or patch artifacts. Prompt truncation is also too late to govern a complete patch that has already been captured and loaded. The resource contract must therefore live at each producing boundary and must fail before automated Review when evidence is incomplete.

## Evidence

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| A quiet detached stdout holder could retain the stage until the command deadline after its direct parent exited | fact | Rootloom 1.2.10 source and local macOS regression | 2026-07-12 | `plugins/rootloom/skills/high-assurance-coding-change/scripts/run_pipeline.py`, `test_parent_exit_starts_detached_stdout_drain_without_waiting_for_timeout` | Current candidate; no sensitive payload |
| Delta capture previously buffered complete tracked and untracked patches before prompt compaction | fact | Rootloom 1.2.10 source | 2026-07-12 | `.codex/plans/rootloom-runner-resource-closure.md` | Sanitized repository-owned plan |
| Aggregate verification JSON rewrites amplified I/O and raw retained bytes did not equal serialized artifact bytes | fact | Rootloom 1.2.10 source and control-character regression | 2026-07-12 | `test_verification_batch_output_budget_stops_remaining_commands`, `test_verification_ndjson_budget_uses_actual_serialized_bytes` | Current candidate tests |
| An 8 MiB control-character output can be rejected into a 1,500-byte record without materializing its expanded JSON first | fact | local macOS CPython 3.13 measurement | 2026-07-12 | `test_log_sized_control_output_is_not_expanded_before_rejection`; ExecPlan evidence log | Input was synthetic NUL bytes |

## Decision

Resource governance is owned by the producer that can stop allocation or persistence:

- `run_managed()` streams merged output into a bounded tail, terminates the original process group on timeout or byte exhaustion, and starts the one-second local drain immediately when the direct parent exits with stdout still open.
- One deterministic-verification batch has independent retained-output, actual serialized-NDJSON, command-count, and model-prompt budgets. JSON escape bytes are counted before a rejected record is materialized, and the minimum fail-closed record is checked before the command executes.
- Verification records use the explicit private format `rootloom-verification-ndjson-v1` plus `rootloom-verification-summary-v1`; one record is appended per command.
- Staged, unstaged, `HEAD`-to-worktree, and ordinary-untracked patches stream to complete private artifacts under aggregate and untracked byte budgets. All Git commands in one capture share one deadline and parent-exit drain, external diff and textconv execution is disabled, and partial writes are compensated.
- Model-facing Delta state uses `complete-patch-with-bounded-prompt-excerpt-v1`: complete source patches stay on disk, while each patch view contributes at most 24,000 raw bytes plus a marker to in-memory prompt state.
- Any incomplete command record or Delta capture fails before automated Review. Prompt excerpts may be bounded because the read-only Reviewer can inspect the approved repository state; incomplete source capture may not receive PASS.
- A true quota over the complete run directory remains an external filesystem/container responsibility. Rootloom must not describe polling or post-write size checks as a hard host quota.

## Alternatives considered

- Truncate strings only after `communicate()` or JSON serialization — rejected because allocation has already occurred.
- Keep complete patches in the Delta dictionary — rejected because prompt compaction would still follow full decode and JSON amplification.
- Silently omit oversized binary patches — rejected because Review would receive incomplete source evidence and could incorrectly PASS.
- Rewrite one aggregate verification JSON file after every command — rejected because cumulative persistence is O(n²).
- Claim a Runner-wide hard artifact quota through periodic directory-size polling — rejected because an external writer can overshoot between polls; use a quota-backed artifact root when that guarantee is required.

## Consequences

- Positive: the reviewed command, Delta, and verification paths have explicit source-level bounds, bounded cleanup, structured audit fields, and fail-closed incomplete-evidence behavior.
- Negative: unusually large but legitimate changes or logs can fail under defaults and require an explicit operator-reviewed budget increase; private artifact readers must understand the versioned NDJSON/summary format.
- Operational: keep the artifact root private and quota-backed for hostile workloads. Increasing a budget increases memory, disk, and review cost. Artifact format changes require a new version and compatibility analysis.

## Verification

- `make check` must pass repository validation, the repository test suite, and the focused Strict Runner regressions.
- `make compatibility-smoke` must restore pre-existing configuration exactly and leave no managed artifacts after rollback.
- Regressions must cover parent-exit drain, Runner-owned capture timeout/drain, shared Delta deadline, textconv suppression, partial-write compensation, complete-or-fail patch budgets, bounded patch excerpts, exact JSON byte prediction, pre-command record preflight, and full-command-budget control-character output.

## Revisit when

- Rootloom adopts incremental snapshots, a quota-backed artifact service, or container/cgroup execution as a supported built-in boundary.
- A documented external consumer requires a compatibility window for a private artifact format.
- Default budgets reject representative real repositories or fail to bound measured memory/disk use.
- The Runner adds another content-bearing artifact producer that is not covered by this decision.

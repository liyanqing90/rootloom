# Rootloom Strict Runner detached-execution fail-closed closure

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security
- Risk: Tier 2 (Governed)

## Goal and observable success

Produce a local Rootloom 1.2.12 candidate that cannot automatically accept a command after the Runner has observed an output-drain timeout or possible detached descendant. Preserve the direct command exit code separately from the Runner's effective machine result, make streamed patch writes complete-or-fail even under short writes, and make multi-file untracked capture transactional at the batch boundary. Success requires fail-before/pass-after regressions for the original detached-child path and adjacent success/timeout/output-limit paths, plus the full repository and compatibility gates.

## Non-goals

- Publishing, tagging, pushing, or creating a GitHub Release; the user's current request authorizes local correction and deep review, not a new external publication.
- Claiming containment or termination of processes that escape into a new session; hostile commands still require container/cgroup/worker isolation.
- Closing the separately disclosed full-snapshot cost, global run-directory quota, Human Review state machine, setup crash recovery, cross-platform CI, path/status/control-manifest limits, or model structured-output byte limit in this correction.

## Baseline evidence

- `run_managed()` records `output_drain_timed_out=True` and `detached_descendant_possible=True`, but leaves a successful direct parent's `exit_code` at 0 when the original process group no longer exists.
- `run_verification()` decides success only from each persisted `exit_code`, so the known uncertain execution state can pass before an escaped child mutates the repository or host.
- Existing regressions at `test_run_pipeline.py:test_detached_child_holding_stdout_cannot_defeat_timeout` and `test_parent_exit_starts_detached_stdout_drain_without_waiting_for_timeout` explicitly expect exit code 0.
- `stream_command_artifact()` increments `written` by requested chunk length without checking the value returned by `artifact.write()`.
- `stream_untracked_patch()` compensates a failed per-file append only to that append's starting length, leaving prior files from the failed batch in the destination.
- Intake worktree was clean on `main` at publication-record commit `e95b47bf7f751013ac77b4237101fd6608b5fee6`.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Drain timeout can retain effective exit 0 | fact | Rootloom 1.2.11 source, local macOS repository | 2026-07-12 | `run_pipeline.py:run_managed` | Current HEAD source |
| Verification success ignores detached-risk fields | fact | Rootloom 1.2.11 source, local macOS repository | 2026-07-12 | `run_pipeline.py:run_verification` | Current HEAD source |
| Short writes can overstate Artifact completeness | fact | Rootloom 1.2.11 source review | 2026-07-12 | `run_pipeline.py:stream_command_artifact` | Current HEAD source |
| Batch rollback stops at the failed append | fact | Rootloom 1.2.11 source review | 2026-07-12 | `run_pipeline.py:stream_untracked_patch` | Current HEAD source |
| Priority and failure scenario | externally reviewed inference, locally verified | user-supplied 1.2.11 review | 2026-07-12 | attachment `f77c6caa-94b5-4f2d-b73a-b309d817a611` | Review text; no sensitive payload copied |

## Governed defect diagnosis

- Observed failure: a direct parent can return 0 after spawning a `setsid()` child that keeps stdout open; after the one-second drain expires, the Runner returns effective 0 and deterministic verification may auto-pass before delayed mutation.
- Competing hypotheses: the structured risk flag or post-command snapshot is sufficient. Rejected because no hard gate consumes the flag and an escaped child can mutate only after the immediate post-command snapshot.
- Ownership path: `run_managed()` owns command lifecycle outcome; `managed_result_metadata()` and verification NDJSON own audit semantics; `run_stage()` and `run_verification()` consume the effective outcome.
- Violated invariant: a known-uncertain command lifecycle must never produce an automatic success result, and complete Artifact claims must equal bytes durably presented by the producer boundary.
- Root cause: lifecycle uncertainty is modeled as advisory metadata rather than part of the effective machine result; artifact writes trust requested rather than returned byte counts; untracked capture lacks a transaction boundary above per-file appends.
- Root-cause alignment: PASS

## Constraints and invariants

- Preserve raw direct-process status for audit as `command_exit_code`.
- Use effective nonzero exit 125 for leftover process groups or output-drain timeout; timeout 124 and output-limit 126 retain precedence.
- Persist `runner_exit_code` separately when verification Artifact truncation changes final record `exit_code` to 126.
- Every stage using `run_managed()` must fail closed through the same owning-boundary effective result; no reviewer-only exception.
- Streamed Artifact success requires complete writes and exact destination size growth.
- A failed multi-file untracked capture must restore the whole destination to its batch-start state.
- Version private Artifact schemas and update English/Chinese contracts together.

## Impact map

- Producers: `run_managed()`, `stream_command_artifact()`, `stream_untracked_patch()`, verification record serialization.
- Consumers: Evidence, Diagnosis, Implementation, Review, deterministic verification, compact verification prompts, operators reading command sidecars and NDJSON.
- Persisted data: private `*-command.json`, verification NDJSON and summary, untracked patch Artifacts.
- Public contracts: Runner version and documented private Artifact field semantics; no CLI removal.
- Generated artifacts: runtime private Artifacts only.
- External systems: none for implementation; publication is outside current authority.

## Design and decisions

- Ownership: `run_managed()` converts observed lifecycle uncertainty into an effective failure exactly once; all callers consume it.
- Interfaces: `ManagedResult.command_exit_code` stores the direct process status, `ManagedResult.exit_code` stores the effective Runner status, and verification records add `runner_exit_code` before any Artifact-budget override of final `exit_code`.
- Artifact writes: a single `write_all()` loop rejects `None`, zero, negative, and over-reported writes; completion checks actual destination growth against accounted bytes.
- Batch atomicity: untracked capture records its destination baseline and truncates back to it for any child-path or deadline failure.
- Compatibility window: new audit fields are additive, but corrected semantics are security-significant; version Runner and private verification format rather than silently reinterpreting version 1 records.
- Alternatives rejected: reviewer-only checks, because deterministic gates must not delegate known uncertainty to a model; retaining exit 0 plus a boolean, because existing consumers demonstrably ignore the boolean.

## Implementation sequence

1. Add failing regressions for effective exit 125, raw exit 0, delayed mutation unable to auto-pass, short-write completion, and whole-batch rollback.
2. Correct lifecycle result ownership and propagate raw/effective/final codes through sidecars, verification persistence, compaction, and semantic gates.
3. Add complete-write and batch-transaction helpers with exact post-write accounting.
4. Version Runner/private formats; update tests, validator, changelog, bilingual public documentation, architecture/maturity disclosures, and the existing Artifact decision record.
5. Run focused tests, repository checks, warning-as-error verification, compilation, compatibility smoke, and a final source/contract review.

## Rollout, failure, and rollback

- Dry-run/preview: local diff, focused regressions, CLI/help/metadata inspection, and compatibility smoke.
- Mixed-version behavior: old Artifacts retain v1 semantics; 1.2.12 emits versioned v2 verification records with additive raw/effective exit fields.
- Failure detection: exit 125 plus `output_drain_timed_out=true` / `detached_descendant_possible=true`; Artifact write mismatch or failed batch raises `PipelineError` and restores destination.
- Rollback or compensation: before publication, revert only this scoped local candidate; after any separately authorized future publication, use a corrective release rather than rewriting history.
- Irreversible point: none in the current task.

## Verification

- Original failure path: detached child holds inherited stdout and mutates later; direct parent exits 0, Runner returns 125, verification remains false before delayed mutation.
- Owning-boundary invariant: raw command exit is 0 while effective Runner exit is 125; every model/deterministic consumer rejects the effective result.
- Adjacent negative/alternate path: ordinary success remains 0; timeout remains 124; output-limit remains 126; killed in-group children remain 125 without detached-risk conflation.
- Focused tests: `PYTHONWARNINGS=error::ResourceWarning python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py`
- Contract tests: `PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_repo.py`; `make check`
- Type/lint/build/package: `python3 -m py_compile plugins/rootloom/skills/high-assurance-coding-change/scripts/run_pipeline.py`; `make compatibility-smoke`; `git diff --check`
- Security/dependency checks: repository validator and source review; no dependency changes.
- Post-action verification: cleanly scoped diff and status; no external action.

## Risks

- Risk: a benign daemonizing command that previously passed now fails with 125.
  - Mitigation: strict/high-assurance stages require foreground, terminating commands; document isolation and command-shaping expectations.
  - Residual risk: an escaped process that closes inherited stdout before parent exit may remain undetectable without host isolation.
- Risk: readers assume `command_exit_code` was the final verification decision.
  - Mitigation: version the format and document raw (`command_exit_code`), Runner-effective (`runner_exit_code`), and final record (`exit_code`) semantics.
  - Residual risk: undocumented external readers of private Artifacts may require adaptation.
- Risk: rollback truncation itself fails.
  - Mitigation: surface a fail-closed `PipelineError` naming the uncompensated Artifact.
  - Residual risk: filesystem failure requires operator cleanup of the private run directory.

## Decision log

- 2026-07-12 — Classified the detached-descendant acceptance path as High, verified, and root-cause aligned at `run_managed()` rather than at individual model/verification callers.
- 2026-07-12 — Treat the user-supplied review as a lead, not truth: detached fail-open, short write, and batch rollback were independently verified; broader path/status/model-output limits remain real but are separate unclosed contracts.
- 2026-07-12 — Current authority covers local correction and validation only; a 1.2.12 push, tag, or Release requires explicit publication authorization.
- 2026-07-12 — Fail-before regressions reproduced all four material paths: detached verification returned `verified=True`; a simulated 100-byte short write persisted only 3 bytes; zero-progress writes were accepted; and second-file untracked failure retained both earlier and partial bytes.
- 2026-07-12 — Version the verification contract as v2 because the former `command_exit_code` field represented an Artifact-truncation preservation value rather than a stable raw direct-process status. The accepted three-level meaning is raw `command_exit_code`, lifecycle-governed `runner_exit_code`, and final persisted `exit_code`.
- 2026-07-12 — Second-pass self-review found that append-only NDJSON still lacked partial-disk-append compensation. The shared complete-write boundary now rolls it back and has a fault-injection regression.
- 2026-07-12 — Repository validation rejected an early local plugin-manifest bump because 1.2.12 has no authorized release section. The introduced failure was corrected: the installable manifest remains 1.2.11, Runner 2.14 stays under Unreleased, and publication remains a separate approval gate.
- 2026-07-12 — Final local verification passed: 41 repository tests, 77 focused Runner tests, `ResourceWarning`-as-error focused execution, repository validation, Python compilation, diff whitespace checks, and the `codex-cli 0.144.0-alpha.4` compatibility smoke with exact rollback and no managed leftovers.

## Outcome

- A known uncertain lifecycle can no longer return automatic success: direct parent status 0 is retained for audit while drain cutoff and leftover-process-group states produce effective exit 125 for Evidence, Diagnosis, Implementation, Review, and deterministic verification.
- The delayed-mutation regression proves verification is already false before an escaped child changes the repository after the immediate snapshot window.
- Streamed patches and verification NDJSON now complete valid short writes, reject zero/invalid progress, verify actual file growth, and compensate partial persistence; failed multi-file ordinary-untracked capture restores the complete batch to empty.
- Verification Artifacts use version 2 raw/effective/final exit semantics, and English/Chinese public, architecture, maturity, Skill, decision, changelog, and validator contracts agree.
- The candidate deliberately does not claim host containment, a Runner-wide quota, bounded status/path/control/model-JSON allocation, incremental snapshots, a durable Human Review approval state machine, setup crash recovery, or macOS/Windows certification.

## Durable decision records

- Updated accepted record: `docs/decisions/2026-07-12-strict-runner-resource-artifacts.md` now owns the corrected raw/effective/final exit-code and complete-write contracts.

# Rootloom Strict Runner resource-boundary closure

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security
- Risk: Tier 2 (Governed)

## Goal and observable success

Close the prioritized resource gaps identified in the supplied 1.2.10 review and publish the verified tree as Rootloom 1.2.11: a direct parent exit must start process-group cleanup and a one-second drain immediately; verification persistence must be append-only and governed by actual serialized bytes; Git Delta and untracked-patch capture must be streamed and hard-bounded so incomplete review cannot auto-pass. Publication succeeds only when the exact code commit is on `liyanqing90/rootloom` `main`, CI passes, annotated tag `v1.2.11` targets that commit, and a non-draft/non-prerelease GitHub Release is verified.

## Non-goals

- Host/container isolation for escaped sessions, secret-file access, or hostile verification commands.
- Incremental repository snapshots, Human Review state machines, setup crash recovery, release, or publication.
- A filesystem-enforced quota over every file in the complete run directory; model structured outputs and fixed-count stage artifacts remain governed by their existing stage/schema boundaries rather than a new host quota.
- Deployment, package publication, infrastructure mutation, or any external action beyond the explicitly authorized GitHub `main` push, annotated `v1.2.11` tag, and formal Release.

## Baseline evidence

- `run_managed()` waits for stdout EOF until the full command deadline after the direct process exits; a quiet detached descriptor holder can therefore retain the Runner lock for the stage timeout.
- `capture_delta()` loads staged, unstaged, combined, and untracked binary patches completely into Python strings before writing artifacts.
- `run_verification()` rewrites the complete JSON record list after every command and budgets retained command bytes rather than serialized artifact bytes.
- The worktree was clean at intake on `main` at `c041db5`.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Parent-exit drain can wait for the stage timeout | fact | Rootloom 1.2.10 source, local repository | 2026-07-12 | `run_pipeline.py:run_managed` | Current HEAD source |
| Delta capture is fully buffered | fact | Rootloom 1.2.10 source, local repository | 2026-07-12 | `run_pipeline.py:capture_delta`, `untracked_patch` | Current HEAD source |
| Verification JSON persistence is O(n^2) | fact | Rootloom 1.2.10 source, local repository | 2026-07-12 | `run_pipeline.py:run_verification` | Current HEAD source |
| Priority and impact assessment | externally reviewed inference | User-supplied 1.2.10 review | 2026-07-12 | attachment `b0c65c60-50c8-4d1c-94ac-63c83cddb81e` | Review text; no secrets copied |
| Full-command-budget control output is rejected without expanded JSON allocation | fact | local macOS, CPython 3.13 | 2026-07-12 | `/usr/bin/time -l` against `verification_record_line()` | Synthetic 8 MiB NUL input; 1,495-byte artifact, 0.42 s wall time, 50,692,096-byte max RSS |

## Governed defect diagnosis

- Observed failure: quiet escaped stdout holders can consume the stage timeout; large Git deltas can exhaust memory or artifacts; repeated verification serialization amplifies disk I/O and JSON escaping invalidates the raw-byte artifact claim.
- Competing hypotheses: the existing timeout, prompt compaction, and 32 MiB retained-output budget are sufficient. Rejected because cleanup starts only at the command deadline, prompt compaction happens after full Delta allocation, and JSON bytes can exceed retained raw bytes.
- Ownership path: `run_managed()` lifecycle loop, `capture_delta()` / `untracked_patch()`, and `run_verification()` artifact persistence.
- Violated invariant: parent completion must trigger bounded cleanup; every content-bearing Delta must be fully reviewable within configured budgets; persisted verification growth must be append-only and measured in bytes actually written.
- Root cause: cleanup is deadline-triggered rather than parent-state-triggered; Delta capture uses full-buffer subprocess APIs; verification persistence rewrites aggregate JSON and budgets a pre-serialization representation.
- Root-cause alignment: PASS

### Self-review findings before second-pass implementation

- High, verified from `stream_command_artifact()`: Runner-owned Git artifact capture has neither a command deadline nor a parent-exit drain. A quiet escaped stdout/stderr holder can therefore reproduce the lock-retention failure outside `run_managed()`.
- Medium, verified from `capture_delta()`: complete patches are streamed to disk but then fully loaded and decoded into Python strings before `compact_delta()` truncates the model prompt. This is bounded by the raw patch limit but still permits avoidable decode/JSON amplification and does not satisfy the intended fixed-excerpt memory design.
- Medium, verified from `verification_record_line()`: the function serializes the complete output repeatedly during fixed-point calculation and binary search. Control-character output can therefore allocate the expanded JSON representation multiple times before the actual serialized-byte gate takes effect.
- Medium, strongly inferred from `run_verification()`: a minimum structured record that cannot fit the remaining artifact budget is discovered only after its command runs, leaving an executed verification command without a durable machine record.
- Low, verified from `stream_command_artifact()`: exceptional write failures clean the process group but do not consistently restore the artifact to its pre-command length.
- Low, observed by warning-as-error verification: selector setup failure left stdout/stderr file objects open after the child process was terminated; cleanup ownership did not cover pre-registration failure.

## Constraints and invariants

- Preserve direct-parent exit codes, timeout 124, output-limit 126, and existing process-group cleanup semantics.
- Preserve private artifact permissions and repository-read-only verification gates.
- New CLI controls are additive and positive-integer validated; old invocations continue with safe defaults.
- If a complete Delta cannot fit the configured review budget, fail closed before model Review rather than presenting a truncated Delta as reviewable.
- Update English and Chinese public contracts together and extend `scripts/validate_repo.py`.

## Impact map

- Producers: model-stage commands, Git, deterministic verification commands.
- Consumers: Runner repair/review prompts, operators inspecting private run artifacts, repository tests and validation.
- Persisted data: private run-directory logs, patches, NDJSON records, summaries, metadata.
- Public contracts: Runner CLI flags and artifact filenames/fields.
- Generated artifacts: none committed; runtime private artifacts only.
- External systems: none.

## Design and decisions

- Ownership: stage-specific Delta and verification budgets own the two reviewed unbounded/amplified persistence paths; a true run-directory quota remains an external filesystem/container concern.
- Interfaces: add positive byte-budget CLI flags for Delta, untracked patches, verification serialization, and total artifacts; record configured values in metadata.
- Delta: stream Git output to bounded artifacts, retain only bounded review data, and reject any incomplete patch capture before Review.
- Verification: append one compact JSON object per command to NDJSON, then write a small summary; record UTF-8 output bytes, serialized record bytes, and cumulative artifact bytes.
- Compatibility window: CLI changes are additive; the former aggregate verification JSON artifact is replaced by NDJSON plus summary and documented as such.
- Alternatives rejected: post-hoc truncation because it does not bound allocation; retaining per-command full JSON rewrites because it preserves O(n^2) I/O; silently omitting large binaries because incomplete content cannot receive automated PASS.

## Implementation sequence

1. Add parent-exit-triggered cleanup and a 3600-second-timeout regression that returns within seconds.
2. Add streamed, fail-closed Git Delta/untracked capture with per-capture accounting.
3. Replace verification aggregate rewrites with byte-accounted NDJSON and a small summary.
4. Harden the second-pass implementation: bound Runner-owned capture lifecycle, disable textconv, retain only fixed Delta excerpts in memory, count JSON string bytes before serialization, preflight minimum verification records, and restore partial artifacts on every failure.
5. Add CLI/metadata contracts, regression tests, bilingual documentation, and repository validation rules.
6. Run focused Runner tests, repository validation/checks, compilation, compatibility smoke, and final diff review.

## Rollout, failure, and rollback

- Dry-run/preview: inspect CLI help, metadata schema, focused tests, and final diff.
- Mixed-version behavior: existing CLI invocations use defaults; artifact readers must accept the documented NDJSON/summary pair after upgrade.
- Failure detection: stable `PipelineError` before Review when Delta or artifact budgets are exceeded; structured verification budget flags and byte counts; bounded elapsed-time assertion.
- Rollback or compensation: before publication, revert the local candidate; after publication, prefer a new corrective release rather than rewriting published history. A failed pre-tag CI run leaves `main` repairable without a Release.
- Irreversible point: pushing annotated tag `v1.2.11` and creating the public GitHub Release; explicitly authorized by the user on 2026-07-12.

## Verification

- Original failure path: detached child quietly holds stdout while `timeout=3600`; Runner returns in a few seconds.
- Owning-boundary invariant: streamed Delta fails closed at small byte limits and never writes beyond configured budgets; NDJSON size equals recorded bytes and is appended once per command.
- Adjacent negative/alternate path: ordinary success, timeout, log-storm, inherited-process-group cleanup, visible untracked text, and protected-path tests remain green.
- Focused tests: `python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py`
- Contract tests: `python3 scripts/validate_repo.py`
- Type/lint/build/package: `python3 -m py_compile plugins/rootloom/skills/high-assurance-coding-change/scripts/run_pipeline.py`; `make check`
- Post-action verification: `git diff --check`; scoped `git status --short` and diff review.

## Risks

- Risk: safe but unusually large changes are rejected under defaults.
  - Mitigation: additive explicit positive byte-budget overrides and clear diagnostics.
  - Residual risk: increasing limits increases memory/disk exposure and remains operator-controlled.
- Risk: artifact-format consumers expect the old aggregate JSON filename.
  - Mitigation: repository search found no consumer and the former private filename was undocumented; the replacement NDJSON and summary formats now carry explicit versions.
  - Residual risk: external undocumented consumers may need adaptation.
- Risk: escaped new-session descendants survive process-group cleanup.
  - Mitigation: bounded local drain and explicit structured risk field.
  - Residual risk: hostile commands still require container/cgroup isolation.
- Risk: the complete run directory has no single host-enforced quota.
  - Mitigation: command logs, verification NDJSON, Delta captures, command counts, prompt summaries, and capture counts are independently bounded.
  - Residual risk: model structured-output files and metadata are not governed by one aggregate filesystem byte counter; use a quota-backed artifact root for hostile workloads.

## Decision log

- 2026-07-12 — Treat the review as authorization for local optimization, not release or publication.
- 2026-07-12 — Fail closed when full Delta review exceeds a hard budget; automatic PASS is forbidden for truncated content.
- 2026-07-12 — Use append-only NDJSON plus a bounded summary so actual serialized bytes, not an in-memory proxy, govern verification persistence.
- 2026-07-12 — Keep the plugin manifest at 1.2.10 because the user authorized local optimization, not publication; record Runner 2.13 under Unreleased.
- 2026-07-12 — Final verification passed: 41 repository tests, 61 focused Runner tests, repository validation, Python compilation, diff whitespace validation, and the `codex-cli 0.144.0-alpha.4` compatibility smoke with exact rollback and no managed leftovers.
- 2026-07-12 — Self-review reopened the candidate and found five implementation gaps: Runner-owned capture lifecycle, full Delta reload, pre-gate JSON expansion, post-command metadata failure, and partial-write compensation. The second pass repaired each owning boundary and added shared capture deadlines plus textconv suppression.
- 2026-07-12 — Accept and version the private Artifact/resource contract in `docs/decisions/2026-07-12-strict-runner-resource-artifacts.md` so future format or producer changes require explicit compatibility and budget analysis.
- 2026-07-12 — Final self-review verification passed with `ResourceWarning` promoted to an error: 41 repository tests, 71 focused Runner tests, repository/link/source validation, Python compilation, diff whitespace validation, and the `codex-cli 0.144.0-alpha.4` compatibility smoke with exact rollback and no managed leftovers.
- 2026-07-12 — User explicitly authorized “发布”. Publication target is `liyanqing90/rootloom` `main`, annotated tag `v1.2.11`, and a non-draft/non-prerelease GitHub Release. Force-push, package publication, deployment, and unrelated external mutation remain unauthorized.
- 2026-07-12 — Published code commit `dd773413e1201cee2fb71566deb14e41a3448fdb`; tree `1dc06b0d347fc67c8fe6839b08841faa8e9f0713` is the locally verified release tree and the remote `main` target before the publication-record commit.
- 2026-07-12 — GitHub Actions run `29196851454` passed for Python 3.11, 3.12, 3.13, 3.14, and pinned Codex CLI contracts at the exact release commit: `https://github.com/liyanqing90/rootloom/actions/runs/29196851454`.
- 2026-07-12 — Created annotated tag object `76f98dd5d92dddc5b552b8a555613d6a63b1f983`; `v1.2.11^{}` resolves exactly to `dd773413e1201cee2fb71566deb14e41a3448fdb` locally and remotely.
- 2026-07-12 — Published `https://github.com/liyanqing90/rootloom/releases/tag/v1.2.11` at `2026-07-12T14:49:42Z` as the Latest non-draft, non-prerelease Release with a `v1.2.10...v1.2.11` changelog link.

## Outcome

- Parent exit with an open stdout pipe now triggers immediate original-group cleanup and a one-second drain while preserving the direct-parent exit code for escaped-session holders.
- Git Delta and baseline tracked patches now stream into bounded artifacts; all commands in one capture share one deadline, external diff/textconv execution is disabled, partial writes are compensated, and only fixed excerpts enter prompt memory.
- Verification persistence is versioned append-only NDJSON with a small summary, pre-materialization JSON escape accounting, pre-command minimum-record checks, explicit UTF-8/JSON/artifact fields, and fail-closed truncation.
- Selector initialization, write failure, timeout, output-limit, parent-exit, and nonzero-exit paths all close owned descriptors/processes and restore incomplete artifacts.
- Public English/Chinese contracts, changelog, architecture, maturity disclosures, the accepted decision record, Runner metadata, and repository validation were updated together.
- Rootloom 1.2.11 is published from the exact verified code tree; remote `main`, CI, annotated tag, and the Latest formal GitHub Release were independently inspected after publication.

## Durable decision records

- [Bound Strict Runner resources at their owning artifact boundary](../../docs/decisions/2026-07-12-strict-runner-resource-artifacts.md) — accepted; owns the versioned private Artifact formats, producer-level budgets, and fail-closed incomplete-evidence rule.

# Rootloom 1.2 release hardening

## Status

- State: locally verified; awaiting GitHub CI and release publication
- Owner: Codex
- Last updated: 2026-07-12
- Task type: reliability, compatibility, and GitHub release
- Risk: Tier 2 (Governed)

## Goal and observable success

Remove every actionable whole-repository review finding before publishing Rootloom 1.2.0. Setup must be serializable and recoverable, project seeding must preserve concurrent user content and remain inside the repository boundary, high-assurance evidence must be attributable per fact without repeatedly reading ignored file contents, and both pinned and latest Codex CLIs must pass an offline plugin compatibility smoke.

Success requires focused fault-injection tests, `make check`, offline compatibility smoke, live smoke, a clean release diff, successful GitHub CI on `main`, and a published `v1.2.0` GitHub Release pointing at the verified commit.

## Non-goals

- Change Rootloom's five capability levels or enable delegation by default.
- Add a vendor-specific observability MCP server.
- Claim that provenance proves factual truth.
- Force-push, rewrite existing tags, or publish before CI passes.

## Baseline evidence

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| A failed `state.json` write leaves managed targets active without setup state | fact | local fault injection / isolated Codex home | 2026-07-12 | `setup_rootloom.py:594-653`; observed `SETUP_STATE_EXISTS False` with targets present | current local HEAD; synthetic paths only |
| Concurrent guidance/full applies can both succeed and make rollback fail | fact | local two-thread fault injection / isolated Codex home | 2026-07-12 | `setup_rootloom.py:554-653`; final state guidance with full assets, rollback hash failure | current local HEAD; synthetic paths only |
| Seeder can erase a concurrent user rule | fact | local pre-write edit injection / temporary Git repository | 2026-07-12 | `seed_project_guidance.py:688-707`; `SEED_PRESERVED_CONCURRENT_EDIT False` | current local HEAD; synthetic content only |
| A workflow symlink outside the repository crashes probe | fact | local temporary Git repository | 2026-07-12 | `seed_project_guidance.py:345-352`; symlink to `/etc/hosts` raised `ValueError` | current local HEAD; no external content retained |
| Rollback changes original mode 0644 to 0600 | fact | local isolated Codex home | 2026-07-12 | `setup_rootloom.py:751-761`; observed `ROLLBACK_MODE 0o600` | current local HEAD |
| Provenance records are not linked to individual facts | fact | schema and semantic-gate inspection | 2026-07-12 | `run_pipeline.py:53-138,318-341` | current local HEAD |
| Ignored files are fully content-hashed on every state capture | fact | source inspection | 2026-07-12 | `run_pipeline.py:666-688` | current local HEAD |
| Latest CLI workflow exercises only command policy | fact | workflow inspection | 2026-07-12 | `.github/workflows/codex-compatibility.yml:35-45` | current local HEAD |

## Governed defect diagnosis

- Observed failure: individual safety checks exist, but transaction metadata, concurrency, provenance relationships, evidence boundaries, and compatibility breadth are not governed as complete invariants.
- Competing hypotheses: documentation overstatement only; isolated test gaps; or missing ownership-level mechanisms.
- Ownership path: Setup owns Codex-home mutation and rollback; Seeder owns generated guidance writes and repository evidence; Runner owns stage evidence/state cost; CI owns upstream contract detection.
- Violated invariant: a mechanism advertised as transactional, preserving, attributable, bounded, or compatible must enforce that property at the owning boundary under failure and concurrency.
- Root cause: early releases validated happy-path artifacts and selected negative cases but did not test commit-point failure, competing writers, provenance referential integrity, symlinked evidence inputs, metadata preservation, or representative offline plugin loading against the selected CLI.
- Root-cause alignment: PASS

## Constraints and invariants

- Use only Python's standard library and existing repository tooling.
- Preserve the existing setup state schema where possible; new manifest fields must be backward-compatible when absent.
- Setup apply and rollback for one Codex home must be mutually exclusive.
- Rollback must restore content and mode, and a failed apply must restore prior targets and state.
- Seeder must never follow an evidence path outside the selected repository scope.
- Seeder must refuse rather than overwrite when `AGENTS.md` changes after it was read.
- Every structured observed fact must reference existing provenance records.
- Ignored paths remain mutation-detectable through metadata without repeated content reads.
- Stable CI remains pinned; latest CLI probing remains separate and informational.

## Impact map

- Producers: setup CLI, SessionStart seeder, high-assurance evidence agent, CI workflows.
- Consumers: user Codex homes, repository `AGENTS.md`, diagnosis/review stages, release maintainers.
- Persisted data: `.rootloom/state.json`, transaction manifests/backups, generated `AGENTS.md`, runner JSON artifacts.
- Public contracts: Setup apply/rollback behavior, evidence JSON Schema, compatibility workflow, plugin version 1.2.0.
- Generated artifacts: private Runner artifacts and temporary compatibility Codex homes.
- External systems: GitHub repository, Actions, tag, and Release.

## Design and decisions

- Use a non-blocking cross-platform advisory file lock for setup apply/rollback; a busy lock fails without mutation.
- Prepare backups and the transaction manifest before target mutation; compensate targets and prior state on every later failure.
- Store `before_mode` in new manifests and accept older manifests that lack it by falling back to backup mode.
- Lock Seeder instances through the Git common directory and compare the exact pre-write snapshot before replacement.
- Reject symlinked or resolved-outside evidence candidates before reading or listing them.
- Give provenance records stable IDs; facts and hypothesis evidence reference those IDs and semantic validation enforces referential integrity.
- Content-hash tracked/untracked deliverables; use mode/size/time metadata for ignored files so normal cache mutation remains visible without full reads.
- Add an offline compatibility smoke that installs the plugin, applies full setup, validates role/profile/config loading and Rules, then rolls back.
- Publish directly to the repository's established `main` release flow because the user explicitly authorized a new GitHub version; no force push or tag replacement.

## Implementation sequence

1. Add Setup lock, prepared transaction, complete compensation, and mode restoration tests.
2. Add Seeder safe-evidence predicates, lock/snapshot checks, and regressions.
3. Add provenance referential integrity and ignored metadata fingerprints with tests.
4. Add offline compatibility smoke; run it in pinned and latest CLI workflows.
5. Update architecture, setup, maturity, README, Changelog, validator, and ExecPlan evidence.
6. Run all focused and full verification; audit the final diff.
7. Commit, push `main`, wait for CI, create signed/annotated `v1.2.0` tag and GitHub Release, then verify remote state.

## Rollout, failure, and rollback

- Dry-run/preview: all local tests use temporary Codex homes and repositories.
- Mixed-version behavior: old transaction manifests remain readable; new manifests add optional mode metadata.
- Failure detection: fault-injection tests, offline smoke, live smoke, GitHub Actions.
- Rollback before publication: revert the hardening commit locally.
- Rollback after main push but before tag: push a normal revert commit.
- Rollback after release: do not rewrite `v1.2.0`; publish a corrective patch version if needed.
- Irreversible point: GitHub Release publication, explicitly authorized by the current request.

## Verification

- Original failure paths: new regression tests for state-write failure, lock contention, concurrent guidance drift, outside symlinks, and file modes.
- Owning-boundary invariants: `make check`, setup and seeder suites, Runner semantic gates.
- Adjacent negative/alternate paths: existing update-chain rollback, unrelated config preservation, idempotent seeding, ignored-file mutation detection, pinned CLI compatibility.
- Full local gates: `make check`, `make compatibility-smoke`, `make smoke`, `git diff --check`.
- External proof: GitHub Actions success on the pushed commit and Release/tag verification through `gh`.

### Local results (2026-07-12)

- `make check` — passed: repository contract validation, 41 repository tests, and 13 strict-runner tests.
- `make compatibility-smoke` — passed against `codex-cli 0.144.0-alpha.4`: local marketplace/plugin install, full setup/status, routing/profile parsing, `commit=allow`, `push=prompt`, `reset=forbidden`, complete rollback, no managed leftovers, and exact pre-existing config restoration.
- `make smoke` — passed with an isolated Codex home and a real authenticated `codex exec`: project guidance was seeded, `gpt-5.6-sol` was observed, all selected assets were ready, and rollback completed while preserving runtime-added project trust.
- `git diff --check` and `scripts/validate_repo.py` — passed.
- Additional fault injection — rollback state-commit failure now restores every pre-rollback target, mode, and installed state before re-raising the original failure.

## Risks

- Risk: lock implementation behaves differently on Windows.
  - Mitigation: use standard-library POSIX/Windows branches and keep lock scope small and non-blocking.
  - Residual risk: Windows behavior is structurally covered but not executed in current macOS/Linux CI.
- Risk: ignored metadata can miss adversarial same-size, restored-timestamp content edits.
  - Mitigation: ignored outputs are non-deliverable; tracked/untracked deliverables retain content hashes and the residual boundary is documented.
  - Residual risk: metadata is a bounded mutation signal, not cryptographic ignored-content attestation.
- Risk: evidence schema change affects hand-authored Runner fixtures.
  - Mitigation: Runner artifacts are private, versioned, and tested; document the 2.2 schema change in 1.2.0.

## Decision log

- 2026-07-12 — Keep release version at 1.2.0 because it has not been pushed, tagged, or released; hardening is part of the initial 1.2.0 publication.
- 2026-07-12 — Publish directly from verified `main`, matching the repository's existing release history and the user's explicit release authorization.

## Durable decision records

- None. These fixes strengthen existing ownership contracts without introducing a new long-term architecture choice beyond this release plan.

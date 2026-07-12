# Rootloom 1.2.5 Verification Boundary Hardening

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security
- Risk: Tier 2 (Governed)

## Goal and observable success

Close the Rootloom 1.2.4 verification execution boundary gap: a Writer must not be able to replace allowed paths or verification entrypoints with out-of-repository symlinks after preflight, and deletion-only runs must not enter incompatible repair or dirty-worktree states.

## Non-goals

- No GitHub publication or release without a separate explicit user authorization.
- No generic shell or CLI semantic parser.
- No OS/container sandbox for arbitrary verification commands.
- No full human accept/reject state machine.

## Baseline evidence

- `v1.2.4` points to code commit `4f094bb750aa8420afdbf171953a7d9879b1ea90`.
- Static review found that `validate_allowed_path_boundaries()` and `validate_verification_command_boundaries()` run before the Writer only.
- Verification commands run in the host process environment via Python `subprocess.Popen()`.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Writer-after symlink replacement is not revalidated before verification | fact | local source review | 2026-07-12 | `plugins/rootloom/skills/high-assurance-coding-change/scripts/run_pipeline.py` | fresh; no sensitive data |
| Deletion-only mode still allows repair-cycle configuration and dirty baseline | fact | local source review | 2026-07-12 | `plugins/rootloom/skills/high-assurance-coding-change/scripts/run_pipeline.py` | fresh |

## Governed Defect Diagnosis

- Observed failure: a Writer can modify an allowed verification entry path after preflight, before deterministic verification executes it.
- Competing hypotheses: final topology checks are sufficient; rejected because topology rejects nested Git repositories, not ordinary symlinks or modified Makefile/package entrypoints.
- Ownership path: strict Runner command-boundary and repository-contract gates.
- Violated invariant: the verification program authorized before the Writer must not be silently redirected or weakened by the Writer before execution.
- Root cause: verification command boundary checks are one-time preflight checks and do not bind observed verification entrypoint identities across the write stage.
- Root-cause alignment: PASS

## Constraints and invariants

- Preserve existing no-shell verification parsing.
- Do not claim complete command parsing; classify hidden CLI path detection as a documented boundary.
- Keep protected deletion as human-review-only.
- Keep ordinary repository tests modifiable when they are part of the task, but reject modification of detected verification entrypoints used to accept the task.

## Impact map

- Producers: `run_pipeline.py`, `test_run_pipeline.py`, public docs.
- Consumers: high-assurance Runner users, CI, compatibility smoke.
- Persisted data: run metadata and result artifacts.
- Public contracts: Runner version, protected-deletion semantics, verification-command safety boundary.
- Generated artifacts: none.
- External systems: none in this local change.

## Design and decisions

- Ownership: verification-entry identity belongs to the Runner, not prompts or Reviewer judgment.
- Interfaces: no new CLI flags; strengthen existing `--verify` behavior.
- Dependency direction: use existing `file_fingerprint()` and path normalization.
- Compatibility window: stricter checks may reject runs that modify Makefile/package/test-config entrypoints used by verification.
- Alternatives rejected: generic token parser, because it would be incomplete and misleading.

## Implementation sequence

1. Add verification-entrypoint discovery for explicit repo-relative path tokens and common command families (`make`, npm/pnpm/yarn/bun, pytest).
2. Fingerprint discovered entrypoints before the Writer and verify them after the Writer, before deterministic verification runs.
3. Re-run allowed-path and verification symlink boundary checks after every Writer/Repair and before verification.
4. Reject protected deletion mode with `--allow-dirty` or nonzero repair cycles.
5. Add focused regression tests and update docs/version contracts.

## Rollout, failure, and rollback

- Dry-run/preview: focused unit tests.
- Mixed-version behavior: 1.2.5 rejects a narrower set of self-modifying verification runs.
- Failure detection: `make check`, focused runner tests, compatibility smoke.
- Rollback or compensation: revert this scoped commit before release.
- Irreversible point: GitHub publication/release, not authorized in this task.

- Verification result: PASS.
- Original failure path: Writer replaces `scripts/check.sh` with an out-of-repo symlink; Runner fails before verification execution.
- Owning-boundary invariant: detected verification entrypoints remain unchanged from baseline through verification.
- Adjacent negative/alternate path: ordinary visible untracked content and existing protected deletion behavior still pass their current tests.
- Focused tests: `python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py` passed, 31 tests.
- Contract/migration tests: `make validate` passed.
- Type/lint/build/package: `make check` passed, including 41 repository tests and 31 Runner tests.
- Compatibility smoke: `make compatibility-smoke` passed against `codex-cli 0.144.0-alpha.4`.
- Diff hygiene: `git diff --check` passed.
- UI/browser evidence: not applicable.
- Security/dependency checks: repository validator secret scan via `make validate`.
- Post-action verification: local Git diff review.

## Risks

- Risk: commands that intentionally modify verification entrypoints will now fail.
  - Mitigation: require a separate external harness or split the task.
  - Residual risk: hidden command indirection remains outside this heuristic boundary.

## Decision log

- 2026-07-12 - Treat common verification entrypoints as acceptance harness inputs and bind their identity across the write stage.
- 2026-07-12 - Completed local implementation and verification; external publish/release remains out of scope until explicitly authorized.

## Durable decision records

- None; this is a security hardening of an existing Runner contract.

# Rootloom 1.2.6 Verification Entrypoint Closure

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security
- Risk: Tier 2 (Governed)

## Goal and observable success

Close the Rootloom 1.2.5 verification entrypoint gaps: missing candidate entrypoints must be bound, common command wrappers must be recognized, repository-internal symlink targets must be fingerprinted, directory selectors must not become over-broad entrypoints, explicit operator-bound harness paths must be supported, and successful stages must fail closed on leftover process groups.

## Non-goals

- No GitHub publication or release without explicit user authorization. The user authorized publication with `继续发布` on 2026-07-12.
- No complete shell or CLI semantic parser.
- No container, cgroup, or OS-level sandbox.
- No human accept/reject state machine.

## Baseline evidence

- `v1.2.5` points to code commit `c083f4c0ccd7db60cf419d566269bbc2f39d5beb`.
- Static review found missing candidate entrypoints were not included in the baseline.
- Static review found high-frequency command forms such as `./scripts/check.sh` and `python -m pytest` were not recognized.
- Static review found symlink entrypoint fingerprints did not include repository-internal target content.
- Static review found successful managed commands did not fail closed on leftover process groups.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Missing entrypoint candidates are not baseline-bound in 1.2.5 | fact | local source review | 2026-07-12 | `run_pipeline.py` | fresh; no sensitive data |
| Successful managed process groups can leave children | inference | local source review | 2026-07-12 | `run_managed()` | fresh |

## Governed Defect Diagnosis

- Observed failure: a Writer can create a previously missing higher-priority verification entrypoint, modify a symlink target, or leave a child process that mutates after checks.
- Competing hypotheses: documentation-only disclosure is enough; rejected because these are machine-checkable boundaries.
- Ownership path: strict Runner verification entrypoint discovery, fingerprinting, and managed process execution.
- Violated invariant: the verification program selected for acceptance must not silently change after the writer.
- Root cause: 1.2.5 bound only observed candidate files and direct entry paths, and only killed process groups on timeout/error.
- Root-cause alignment: PASS

## Constraints and invariants

- Do not bind directory selectors as executable entrypoints.
- Keep support explicit and documented; do not pretend to parse arbitrary CLI semantics.
- Preserve existing protected deletion semantics and human-review outcome.
- Avoid new dependencies.

## Impact map

- Producers: `run_pipeline.py`, `test_run_pipeline.py`, public docs.
- Consumers: high-assurance Runner users, CI, compatibility smoke.
- Persisted data: run metadata includes entrypoint fingerprints and optional bound paths.
- Public contracts: Runner version, plugin version, `--bind-verification-path`.
- Generated artifacts: none.
- External systems: none in this local change.

## Design and decisions

- Ownership: verification entrypoint closure is a Runner contract.
- Interfaces: add repeatable `--bind-verification-path` for explicit operator-owned harness binding.
- Dependency direction: use existing fingerprinting and subprocess management.
- Compatibility window: stricter checks may reject tasks that create/modify verification harness files in the same run.
- Alternatives rejected: generic command parser, because hidden indirection remains impossible to prove reliably.

## Implementation sequence

1. Include missing common candidate entrypoints in baseline snapshots.
2. Recognize `./path`, `python -m pytest`, `uv run pytest`, `poetry run pytest`, `make -f`, `pytest -c`, and `npm --prefix`.
3. Fingerprint repository-internal symlink chains and final targets.
4. Do not bind directory selectors as entrypoints.
5. Add `--bind-verification-path`.
6. Fail closed when a successful managed process leaves a live process group.
7. Update docs and regression tests.

## Rollout, failure, and rollback

- Dry-run/preview: focused unit tests.
- Mixed-version behavior: 1.2.6 rejects more verification-entrypoint drift.
- Failure detection: `make check`, focused Runner tests, compatibility smoke.
- Rollback or compensation: revert this scoped commit before release.
- Irreversible point: GitHub publication/release, completed after explicit user authorization.

## Verification

- Original failure path: creating `GNUmakefile` or `pytest.ini` after baseline must fail.
- Owning-boundary invariant: common entrypoint candidates and explicit bound paths remain unchanged, including symlink target content.
- Adjacent negative/alternate path: directory selectors are not over-bound and existing ordinary/protected tests still pass.
- Focused tests: `python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py` — PASS, 36 tests.
- Contract/migration tests: `make validate` — PASS.
- Type/lint/build/package: `make check` — PASS, 41 repository tests and 36 Runner tests.
- Compatibility smoke: `make compatibility-smoke` — PASS with `codex-cli 0.144.0-alpha.4`.
- UI/browser evidence: not applicable.
- Security/dependency checks: repository validator secret scan via `make validate`.
- Post-action verification: `git diff --check` — PASS.
- Publication verification: GitHub Release `v1.2.6` is live at `https://github.com/liyanqing90/rootloom/releases/tag/v1.2.6`; remote release commit CI passed at `https://github.com/liyanqing90/rootloom/actions/runs/29182662864`.

## Risks

- Risk: process-group leftover detection may be imperfect across platforms.
  - Mitigation: strict Runner already gates POSIX platforms; keep docs honest about container/cgroup superiority for production.
  - Residual risk: OS-level process isolation remains outside Rootloom.

## Decision log

- 2026-07-12 - Add explicit harness binding and entrypoint closure rather than expanding to a false-complete CLI parser.
- 2026-07-12 - User authorized publication with `继续发布`; published release commit `b4e6abf73834c6857420a2664e84943b43ad238d`, annotated tag object `df4b4d2f0868137851a877485a2e198d0051337f`, and GitHub Release `v1.2.6`.

## Durable decision records

- None; this is an implementation-level hardening of an existing Runner contract.

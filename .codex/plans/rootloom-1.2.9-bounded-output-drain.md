# Rootloom 1.2.9 bounded managed-output drain

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security
- Risk: Tier 2 (Governed)

## Goal and observable success

Guarantee that a managed stage returns within a bounded cleanup window when a descendant detaches from the original process group but retains the captured stdout pipe. The Runner must close its local pipe, preserve timeout failure, release repository resources, and document that detached descendants remain outside POSIX process-group control.

## Non-goals

- Claiming cgroup, container, job-object, or complete descendant-process isolation.
- Implementing content-lineage/DLP controls, incremental snapshots, or the broader 1.3 roadmap.
- Publishing or releasing without separate explicit authorization.

## Baseline evidence

- `terminate_process_group()` confirms the original PGID is gone and then calls `process.communicate()` without a timeout.
- A child can start a new session while retaining the inherited stdout descriptor, keeping that final `communicate()` open after the original process group has disappeared.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Final output drain has no deadline | fact | Rootloom 1.2.8 source | 2026-07-12 | `run_pipeline.py:terminate_process_group` | Published source; no sensitive payload |
| Detached inherited stdout can outlive the original PGID | strongly inferred and externally reviewed | POSIX subprocess data flow and supplied 1.2.8 review | 2026-07-12 | attachment `18d85a50-a470-4a76-ae56-f7d6e6e25493` | Review text only |

## Governed defect diagnosis

- Observed failure: stage timeout can become unbounded during the final output drain.
- Competing hypotheses: process-group disappearance implies pipe EOF. Rejected because file-descriptor ownership is independent of PGID membership.
- Ownership path: managed subprocess cleanup and output capture.
- Violated invariant: every stage timeout must have a finite cleanup bound and release the repository lock.
- Root cause: the cleanup path bounds signal escalation but not the final stdout drain.
- Root-cause alignment: PASS

## Constraints and invariants

- Preserve existing return codes: timed-out commands remain exit 124.
- Do not claim or attempt unsafe PID-tree discovery for detached descendants.
- Preserve captured output when available and add an explicit fail-closed diagnostic when the pipe deadline expires.
- Close only Runner-owned local stream descriptors.

## Impact map

- Producers: `run_managed()` and `terminate_process_group()`.
- Consumers: model-stage and verification command records, repository lock lifetime, CI jobs.
- Persisted data: Runner output artifacts and logs.
- Public contracts: Runner/plugin patch version and documented process boundary.
- Generated artifacts: none.
- External systems: none for local implementation.

## Design and decisions

- Ownership: add a dedicated bounded output-drain helper after process-group cleanup.
- Interfaces: retain the existing four-field `run_managed()` result and use output text to record detached-pipe cutoff.
- Dependency direction: cleanup owns pipe deadlines; callers continue consuming ordinary timeout failure.
- Compatibility window: no CLI or schema change.
- Alternatives rejected: scanning or killing arbitrary process trees by PID because identity can escape or be reused and the Runner lacks an OS job boundary.

## Implementation sequence

1. Add a fixed final drain deadline and safe local stream closure.
2. Replace the unbounded final `communicate()`.
3. Add a real `start_new_session=True` descendant test that inherits stdout and is explicitly released after the assertion.
4. Bump Runner/plugin patch versions and update public boundary documentation.
5. Run focused tests, full repository checks, compatibility smoke, and diff validation.

## Rollout, failure, and rollback

- Dry-run/preview: inspect the scoped local diff and test evidence.
- Mixed-version behavior: additive patch behavior; no stored format migration.
- Failure detection: elapsed-time assertion, timeout return code, explicit drain diagnostic, test-process completion marker.
- Rollback or compensation: revert the scoped local commit before publication.
- Irreversible point: none; publication requires explicit approval.

## Verification

- Original failure path: detached `start_new_session=True` child retains stdout after its parent exits.
- Owning-boundary invariant: `run_managed()` returns 124 within a fixed upper bound and includes a pipe-cutoff diagnostic.
- Adjacent negative/alternate path: ordinary timeout and SIGTERM/SIGKILL process-group tests remain green.
- Focused tests: `python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py`
- Contract/migration tests: `python3 scripts/validate_repo.py`
- Type/lint/build/package: `make check`
- UI/browser evidence: not applicable.
- Security/dependency checks: `make compatibility-smoke`
- Post-action verification: `git diff --check` and scoped status review.

## Risks

- Risk: detached descendants can continue running after the Runner closes its local pipe.
  - Mitigation: explicit failure text and documentation requiring container/cgroup/job isolation for hostile commands.
  - Residual risk: host-side effects from escaped processes remain outside Rootloom's repository acceptance boundary.

## Decision log

- 2026-07-12 — Bound local output drain rather than claiming descendant-process control that POSIX process groups cannot provide.
- 2026-07-12 — On macOS, signaling the original PGID can return `EPERM` after the direct process has already exited. Treat that combination as an unsignalable former group and continue to bounded drain; retain fail-closed behavior when the direct process is still live.
- 2026-07-12 — Verification passed: 41 repository tests, 49 Runner tests, repository validation, `git diff --check`, and the Codex CLI compatibility smoke on `codex-cli 0.144.0-alpha.4` with no managed leftovers and exact config restoration.
- 2026-07-12 — User explicitly authorized “发布最新版本”. Publication target is `liyanqing90/rootloom` `main`, annotated tag `v1.2.9`, and a non-draft GitHub Release; no force-push or pull request is required by the repository's established release sequence.
- 2026-07-12 — Published code commit `24ca68408be31cf6793d2bfa044d598af23c5d8c`. Its tree `09ca3dde3729d84689b866915c170ebdcc4854f7` exactly matches the locally verified release tree. GitHub CI passed at `https://github.com/liyanqing90/rootloom/actions/runs/29188936157`.
- 2026-07-12 — Created annotated tag object `41306d1bf0477d7b790081ab153597b38c250095` for `v1.2.9` and published `https://github.com/liyanqing90/rootloom/releases/tag/v1.2.9` as a non-draft, non-prerelease Release.

## Durable decision records

- None; this tightens an existing timeout contract without introducing a new architecture boundary.

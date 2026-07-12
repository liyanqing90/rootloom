# Rootloom 1.2.4 Protected Deletion Hardening

## Status

- State: published
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security
- Risk: Tier 2 (Governed)

## Goal and observable success

Close the Rootloom 1.2.3 protected deletion residual gap: an authorized protected deletion must not be mixable with ordinary content changes or used to move protected content into a visible path. Completion is proven by focused runner regression tests plus repository validation.

## Non-goals

- No force-push or tag mutation.
- No full human accept/reject state machine in this patch.
- No container or OS-level syscall sandboxing for verification commands.

## Baseline evidence

- Latest published code is `v1.2.3` at `fe1ee944`; `main` also has documentation evidence commit `14f50d99`.
- External review identified that `--allow-protected-path-delete .env` proves final absence only. A writer could move `.env` into an allowed visible path, making protected content enter normal delta artifacts.
- Current code validates unused/invalid protected deletion after the writer has already run.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Protected deletion can be mixed with ordinary path changes in 1.2.3 | inference | local source review | 2026-07-12 | `plugins/rootloom/skills/high-assurance-coding-change/scripts/run_pipeline.py` | fresh; no sensitive data |
| Existing tests do not cover protected rename into visible path | fact | local test review | 2026-07-12 | `plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py` | fresh |

## Governed defect diagnosis

- Observed failure: authorized protected deletion is a final-state gate, not an operation-type proof.
- Competing hypotheses: prompt strengthening would be sufficient; rejected because artifact capture and acceptance gates must not depend on model compliance.
- Ownership path: strict Runner repository-contract gate in `run_pipeline.py`.
- Violated invariant: metadata-only protected content must not enter content-bearing artifacts or automatic acceptance through rename/move side effects.
- Root cause: protected deletion authorization is validated after writer execution and permits net changes beyond the approved protected deletion set.
- Root-cause alignment: PASS

## Constraints and invariants

- Never read, hash, patch, or back up protected ignored/sensitive path content.
- Preserve existing ordinary tracked and visible-untracked delta capture behavior.
- Keep the successful protected deletion outcome as `HUMAN_REVIEW_REQUIRED`, not automated PASS.
- Use existing standard-library-only runner style.

## Impact map

- Producers: `run_pipeline.py`, strict runner CLI.
- Consumers: high-assurance skill users, CI, compatibility smoke, release docs.
- Persisted data: run artifacts and `result.json`.
- Public contracts: `--allow-protected-path-delete`, Runner version, plugin version, README/SKILL docs.
- Generated artifacts: none.
- External systems: GitHub `liyanqing90/rootloom` main branch, annotated tag, and Release.

## Design and decisions

- Ownership: protected deletion semantics live in the repository-contract gate, not prompts.
- Interfaces: keep the CLI flag but define it as deletion-only run semantics.
- Dependency direction: tests call local runner functions; no new dependency.
- Compatibility window: stricter behavior may reject previously accepted mixed runs; this is a security tightening.
- Alternatives rejected: model prompt-only restriction, because it would not block artifact leakage after a non-compliant writer.

## Implementation sequence

1. Add pre-writer protected deletion validation against baseline protected paths and diagnosis `allowed_paths`.
2. Enforce deletion-only net changes whenever protected deletion authorization is present.
3. Add symlink boundary checks for allowed paths and repository-relative verification command entries.
4. Recheck repository topology immediately after deterministic verification.
5. Add focused regression tests and update docs/version contracts.

## Rollout, failure, and rollback

- Dry-run/preview: focused unit tests for runner gates.
- Mixed-version behavior: older 1.2.3 accepts fewer constraints; 1.2.4 rejects mixed protected deletion runs.
- Failure detection: `make check` and focused runner tests.
- Rollback or compensation: publish a follow-up release; do not mutate the immutable `v1.2.4` tag.
- Irreversible point: GitHub push/tag/release, authorized by the user's `发布` request on 2026-07-12.

## Verification

- Verification result: PASS.
- Original failure path: protected `.env` rename into a visible allowed path fails before delta capture.
- Owning-boundary invariant: protected deletion authorization is preflighted before writer execution and is deletion-only.
- Adjacent negative/alternate path: ordinary visible untracked content still produces a patch; pure protected deletion still returns human-review metadata.
- Focused tests: `python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py` passed, 28 tests.
- Contract/migration tests: `make validate` passed.
- Type/lint/build/package: `make check` passed, including 41 repository tests and 28 Runner tests.
- Compatibility smoke: `make compatibility-smoke` passed against `codex-cli 0.144.0-alpha.4`.
- Diff hygiene: `git diff --check` passed.
- UI/browser evidence: not applicable.
- Security/dependency checks: repository validator secret scan via `make validate`.
- Post-action verification: release commit CI passed at `https://github.com/liyanqing90/rootloom/actions/runs/29180064999`; release is live at `https://github.com/liyanqing90/rootloom/releases/tag/v1.2.4`.

## Risks

- Risk: existing users may expect protected deletion and code edits in one run.
  - Mitigation: document deletion-only semantics and require two runs.
  - Residual risk: workflow friction for protected cleanup.

## Decision log

- 2026-07-12 - Treat protected deletion as a deletion-only strict run because final-state-only validation cannot prove operation semantics.
- 2026-07-12 - Completed local implementation and verification; external publish/release remains out of scope until explicitly authorized.
- 2026-07-12 - User authorized publication with `发布`; published release commit `4f094bb750aa8420afdbf171953a7d9879b1ea90`, annotated tag object `e1e75741914d964170115399ce39517688c024ee`, and GitHub Release `v1.2.4`.

## Durable decision records

- None; this is a security contract tightening within an existing runner design.

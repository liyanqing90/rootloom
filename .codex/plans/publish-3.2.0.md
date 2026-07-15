# Publish Rootloom Personal Core 3.2.0

## Status

- State: published; publication-record CI pending
- Owner: Codex
- Last updated: 2026-07-15
- Task type: security defect repair and external release
- Risk: Tier 2 (Governed)

## Goal and observable success

Publish the complete Reviewable Capture/privacy closure as Rootloom Personal Core 3.2.0 in `liyanqing90/rootloom`. Success requires the original six audit findings plus the index-suppression counterexample to pass focused regressions; local and clean-clone gates to pass; a release PR and merged-`main` run to pass all seven Linux/macOS/Windows/Codex jobs; an immutable annotated `v3.2.0` tag to peel to that passing merge; a public non-draft/non-prerelease GitHub Release; and a factual publication record whose own CI passes.

## Non-goals

- Do not mutate existing tags or Releases, force-push, rewrite shared history, publish a package registry artifact, or alter repository settings/credentials.
- Do not commit or publish `assets/rootloom-xiaohei-loom.png`; preserve SHA-256 `55ea78b17ac40b85cf347b478799dbda629ba8f4d52e7cea5044734c6ec1c0a6`.
- Do not modify `codex/enterprise-assurance` or reintroduce Assurance machinery.
- Do not add independent ignored-file content capture or change baseline-v4 fields.

## Baseline evidence

- `main` and `origin/main` start at `1114e06`; current formal release is immutable `v3.1.0` at `4e010ea`.
- The 3.1.0 audit fixes are present locally and previously passed 180 tests plus compatibility smoke, but review reproduced a remaining false-negative: a modified tracked `public.pem` marked `assume-unchanged` or `skip-worktree` produced empty Git Status, Git Diff, Rootloom Snapshot, and Patch while stable capture accepted the path.
- GitHub target is `liyanqing90/rootloom`, default branch `main`; `gh` 2.75.0 is authenticated as `liyanqing90`, and no open PR exists.
- The additive `reviewability_policy` Summary object makes the aggregate public-contract impact Minor; the next immutable version is 3.2.0.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Index flags suppress a changed tracked reviewable file | fact | local temporary Git repositories on macOS | 2026-07-15 | `git ls-files -v`, Status/Diff, `stable_repository_capture()` | synthetic content only |
| Current closure gates pass with the Index-state correction | fact | current checkout | 2026-07-15 | focused fail-before/pass-after; `make check`; `make compatibility-smoke`; `git diff --check` | 181 tests, 2 environment skips; Codex CLI 0.144.2 |
| GitHub target/auth/PR state is resolved | fact | GitHub CLI/API | 2026-07-15 | `gh auth status`; `gh repo view`; `gh pr list` | token redacted |
| Publication is authorized | supplied authority | current Codex task | 2026-07-15 | explicit request `修改并发布` | Single action for this repository/version workflow |

## Governed defect diagnosis

- Observed failure: `canonical_reviewable_paths()` treats `ls-files --cached` membership as capturable, but Index flags can suppress all ordinary change evidence.
- Competing hypotheses: metadata instability, Git-ignore behavior, or Index suppression. The file remained single-link and Git-listed, while both `h` and `S` tags independently produced empty Status/Diff and Rootloom evidence.
- Ownership path: `runner/state.py::canonical_reviewable_paths` owns Git eligibility and is called at Intake and each stable capture.
- Violated invariant: every sealed Reviewable exception must remain observable in ordinary evidence or fail closed before evidence acceptance.
- Root cause: the Git visibility guard checks membership and ignore state but not Index flags that alter Status/Diff semantics.
- Root-cause alignment: PASS for the planned shared-boundary rejection.

## Constraints and invariants

- Reject lowercase `git ls-files -v` tags and `S`/`s`; accept normal tracked and visible untracked files.
- Parse NUL-delimited Git output without reinterpreting paths, with existing byte/path/per-command/aggregate time budgets.
- Repeat the check at Intake and every stable capture; Finalizer cannot override it.
- Keep baseline v3 default, baseline v4 schema, Summary revision 5, and v2/v3/v4 readers unchanged.
- Stage only release-scope files; every PR/main check must pass before the next irreversible transition.

## Impact map

- Producers: Git visibility/index-state capture, Intake, Finalizer Summary, manifest/version metadata, changelog/release notes.
- Consumers: stable capture, baseline v4 users, CI on Python 3.11–3.14/macOS/Windows, Codex plugin installer.
- Persisted data: unchanged baseline v2/v3/v4 schemas; additive Summary field already in the candidate; Git commit/tag/Release/publication record.
- Public contracts: stricter `--reviewable-path` eligibility and plugin version 3.2.0.
- External systems: GitHub PR, Actions, `main`, annotated tag, GitHub Release.

## Design and decisions

- Ownership: one bounded NUL-safe Index-state query in `runner/state.py`, consumed by the existing canonical visibility decision.
- Interface: fail with `reviewable path is hidden by Git index flags and cannot be captured reliably`.
- Compatibility: valid tracked/untracked declarations and all baseline schemas remain supported; only previously unsafe declarations fail earlier.
- Alternatives rejected: persisting a new baseline fingerprint would change v4; clearing Index flags mutates user state; refreshing the Index is side-effectful and does not create durable evidence.

## Implementation sequence

1. Add fail-before Intake and post-Intake regressions for `assume-unchanged` and `skip-worktree` plus normal tracked/untracked controls.
2. Add bounded NUL-safe Index-state parsing and reject suppressed states at the canonical Git eligibility owner.
3. Update bilingual public docs, accepted decision, changelog, validator, release version metadata, and 3.2.0 release notes.
4. Run focused tests, `make check`, compatibility smoke, diff hygiene, and a clean-clone replay.
5. Create `codex/reviewable-capture-closure`, explicitly stage scope, commit, push, open a ready PR, and wait for all seven checks.
6. Merge without history rewrite, wait for exact merged-`main` CI, create/push annotated `v3.2.0`, and publish the public Release.
7. Record immutable publication facts on `main`, push, wait for final CI, and verify tag/Release/plugin state.

## Rollout, failure, and rollback

- Dry-run/preview: exact diff/status, local gates, clean clone, PR body, remote tag/Release namespace, and release notes are checked before each transition.
- Mixed-version behavior: 3.1.0 artifacts remain immutable/readable; 3.2.0 only tightens unsafe Intake/Capture eligibility and additively exposes the already-planned Summary policy.
- Failure detection: focused regression, local/clean-clone gate, any PR/main/final CI failure, unexpected tree path, image/ref drift, or tag/Release mismatch stops the next step.
- Rollback: before tag push, use ordinary corrective commits or leave the PR unmerged. After tag push, keep the immutable tag and use corrected Release metadata or a newer version for code defects.
- Irreversible point: pushing annotated `v3.2.0`, authorized by the current explicit publication request after exact merged-main CI passes.

## Verification

- Original failure path: focused temporary-repository `assume-unchanged` / `skip-worktree` Intake and capture-time tests.
- Owning-boundary invariant: bounded Index-state parser plus canonical rejection.
- Adjacent path: normal tracked, visible untracked, ignored, hardlink, case canonicalization, deletion, v2/v3/v4, default v3.
- Full gates: `make check`; `make compatibility-smoke`; `git diff --check`; clean-clone replay.
- Post-action: PR/main/final Actions, tag object/peeled commit, Release JSON, exact remote tree, image hash, and Enterprise ref.

## Executed publication evidence

- Candidate `e98b0871ac33f5533c3e39ebf97bc5107dccff03` passed local and clean-clone `make check` plus compatibility smoke; its tree is `91e51bd41647a5fbb1be7db0327249e8757e8940`.
- Ready PR [#9](https://github.com/liyanqing90/rootloom/pull/9) passed all seven jobs in run [29426683030](https://github.com/liyanqing90/rootloom/actions/runs/29426683030) and was squash-merged under the repository's enabled merge policy.
- Exact merged commit `9935bbd8f8ab80ae49f9e2e626a5c62e8e4ac51c` has the same tree and passed all seven jobs again in `main` run [29427110772](https://github.com/liyanqing90/rootloom/actions/runs/29427110772).
- Annotated tag object `b2a6bfa043847d9462607a67a84c7ac5f8f96611` peels to that passing commit and is published as `v3.2.0`.
- Public latest Release [Rootloom Personal Core 3.2.0](https://github.com/liyanqing90/rootloom/releases/tag/v3.2.0) is non-draft and non-prerelease with GitHub Release ID `RE_kwDOTVQo6M4VIbQT`.
- Publication-record CI remains pending; the next transition is to add the observed run ID and close this plan only after all seven jobs pass.

## Risks

- Risk: platform-specific `ls-files -v` parsing differs.
  - Mitigation: NUL records, strict tag/path validation, real Git fixtures, and Windows/macOS CI.
  - Residual risk: unsupported future Git tags fail closed if malformed.
- Risk: release races with remote changes.
  - Mitigation: fetch/rebase before branch publication and verify exact identities at every transition.
  - Residual risk: external GitHub unavailability may pause before tag publication.

## Decision log

- 2026-07-15 — Publish as 3.2.0 because the Summary field is additive Minor behavior and existing 3.1.0 is immutable.
- 2026-07-15 — Reject Index-suppressed reviewable paths rather than mutating user Index flags or changing baseline v4.
- 2026-07-15 — Treat `修改并发布` as Single action authority for this exact 3.2.0 workflow.

## Durable decision records

- [Sensitive material and capture bounds](../../docs/decisions/2026-07-15-sensitive-material-and-capture-bounds.md)

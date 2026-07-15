# Publish Rootloom Personal Core 3.1.0

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-15
- Task type: release and external publication
- Risk: Tier 2 (Governed)

## Goal and observable success

Publish the verified sensitive-material classification refinement as Rootloom Personal Core 3.1.0 in `liyanqing90/rootloom`. Success requires a passing release PR, a passing merged-`main` run, an immutable annotated `v3.1.0` tag that peels to that passing release commit, a public non-draft/non-prerelease GitHub Release, a factual publication record with passing CI, and verified local installed state without modifying the preserved Enterprise branch or unrelated image.

## Non-goals

- Do not move, delete, or rewrite any existing tag, Release, or shared history.
- Do not publish `assets/rootloom-xiaohei-loom.png`; preserve its SHA-256 `55ea78b17ac40b85cf347b478799dbda629ba8f4d52e7cea5044734c6ec1c0a6`.
- Do not modify or publish `codex/enterprise-assurance`.
- Do not add product behavior after release preparation begins; a code defect returns to implementation and full validation.
- Do not publish a package registry artifact or change repository settings, credentials, billing, or permissions.

## Baseline evidence

- Local release branch `codex/fix-reviewable-material-policy` is based on `origin/main` `7de74a40d98d0d9a9197c7dfe4d3c6ccaa898ef5`; candidate commit `5e205b2581c2127d5fde18925cafce1c87c894b0` contains the scoped 3.1.0 implementation, tests, bilingual documentation, ADR, changelog, and version metadata.
- The only worktree item outside the candidate is the unrelated untracked image above; staged and unstaged diffs are empty.
- Local and temporary clean-clone `make check` passed 174 tests with one environment-only non-UTF-8 filename skip. Compatibility Smoke passed with Codex CLI 0.144.2 and no install side effects or rollback leftovers.
- GitHub reports no open pull request, no `v3.1.0` Release, and no `refs/tags/v3.1.0`; the authenticated account `liyanqing90` has admin/push permission. Remote refs were refreshed successfully after a transient TLS timeout.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Candidate behavior and contracts pass local gates | fact | local macOS checkout and temporary clean clone | 2026-07-15 | commit `5e205b2`; `make check`; `make compatibility-smoke` | current; one environmental skip |
| PR, tag, and Release namespace is clear | fact | GitHub API and refreshed `origin` refs | 2026-07-15 | `gh pr list`; REST Git refs; `gh release view`; `git fetch --prune --tags` | current; credentials redacted |
| Remote target and permission are resolved | fact | authenticated GitHub REST API | 2026-07-15 | `liyanqing90/rootloom`, default branch `main`, admin/push true | current; token not persisted |
| Enterprise branch is unchanged | fact | GitHub Git-ref API | 2026-07-15 | `7da82dc8ad0faee0aa6a51c569bab8a60c233b8a` | current |
| User authorized publication | supplied authority | current Codex task | 2026-07-15 | explicit request `发布` | Single action for this 3.1.0 workflow only |

## Governed defect diagnosis

- Observed failure: 3.0.0 over-quarantines environment templates, unrelated `.env*` names, and public certificate formats, and lacks a sealed exact reviewability declaration.
- Competing hypotheses: Git discovery alone versus the shared classifier and immutable policy transport. Fail-before matrices reproduced the false positives directly in `rootloom_paths.py`, while the missing CLI/baseline path required producer/consumer expansion.
- Ownership path: shared path policy → Intake baseline/policy hash → capture and risk analyzer → Finalizer → public schema/docs.
- Violated invariant: privacy quarantine must hide likely secret material without preventing review of security-domain source and public artifacts.
- Root cause: material privacy and reviewable security naming remained over-broad at the shared policy owner, while sealed Intake had no exact negative declaration.
- Root-cause alignment: PASS

## Constraints and invariants

- Default Intake output remains field-compatible baseline v3; baseline v4 is emitted only when `--reviewable-path` is used, and v2/v3/v4 remain readable and sealable.
- Strong material and explicitly declared Sensitive roots remain non-overridable; Finalizer cannot add reviewable declarations.
- Every required PR check must pass before merge, and every merged-`main` check must pass before tagging.
- The annotated tag must peel to the exact passing merge commit and is immutable once pushed.
- The GitHub Release must be public, non-draft, and non-prerelease.

## Impact map

- Producers: plugin manifest, shared path classifier, Intake/baseline v4 producer, changelog, release notes.
- Consumers: capture, analyzer, Finalizer, baseline readers/sealers, Codex plugin installer, JSON/CLI consumers.
- Persisted data: opt-in baseline v4 evidence, Git commit, annotated tag, GitHub Release metadata, publication record.
- Public contracts: `begin_review.py --reviewable-path`, baseline v4, sensitive-policy hash semantics, plugin SemVer 3.1.0.
- Generated artifacts: GitHub Actions results and local managed-install state.
- External systems: GitHub repository/PR/Actions/tag/Release and local Codex plugin cache/preset.

## Design and decisions

- Ownership: the verified candidate remains unchanged through PR and release; factual post-publication evidence is recorded after the immutable tag.
- Interfaces: publish 3.1.0 as an additive Minor release; default v3 consumers do not opt into v4.
- Dependency direction: no dependency or package-registry changes.
- Compatibility window: baseline v2/v3/v4 coexist; Summary remains revision 5.
- Alternatives rejected: direct tag without PR/main CI, moving 3.0.0, publishing the unrelated image, or treating the optional v4 capability as a Patch.

## Implementation sequence

1. Commit this publication plan only, recheck the exact branch scope, and push the release branch.
2. Create a ready PR to `main`; require all seven Linux/macOS/Windows/Codex checks and merge without force or history rewrite.
3. Require the merged-`main` run to pass, then create and push annotated `v3.1.0` at that exact commit.
4. Create a public GitHub Release from curated 3.1.0 notes and verify tag/Release identity.
5. Add the factual publication record and validator contract on `main`, push it, require final CI, and verify local plugin/preset state.

## Rollout, failure, and rollback

- Dry-run/preview: inspect exact diff/status, local gates, PR body, checks, remote namespace, and release notes before each external transition.
- Mixed-version behavior: unchanged clients continue receiving baseline v3; only explicit v4 users require the 3.1.0 reader.
- Failure detection: local gate failure, unexpected path, PR/main/final CI failure, identity mismatch, namespace collision, install drift, or Enterprise/image hash change.
- Rollback or compensation: before tag push, add ordinary corrective commits or leave the PR unmerged. After tag push, retain the immutable tag; correct metadata in place or publish a newer patch for code defects.
- Irreversible point: pushing annotated tag `v3.1.0`, authorized once by the user's current explicit publication request.

## Verification

- Original failure path: classifier/capture matrices in `tests/test_engineering_change.py`.
- Owning-boundary invariant: v3 default, v4 policy hash/seal, strong-secret refusal, and Finalizer consumption tests.
- Adjacent negative/alternate path: ordinary `.env*`, public certificates, CamelCase strong names, Symlink/type replacement, rename non-transfer, and v2/v3 compatibility tests.
- Focused tests: relevant `tests.test_engineering_change.EngineeringChangeTests` cases.
- Contract/migration tests: `make check`.
- Type/lint/build/package: `make validate`; `git diff --check`.
- UI/browser evidence: not applicable.
- Security/dependency checks: `make compatibility-smoke`; exact staged/path/image/Enterprise identity checks.
- Post-action verification: PR/main/final Actions, tag object and peeled commit, public Release JSON, local plugin version/preset drift, image hash, and Enterprise ref.

Executed publication evidence as of 2026-07-15:

- PR #8 corrected review feedback at the symlink-validation boundary and merged as `4e010ea26c871a603a955b88ede8c5cea5066572`; corrected PR run `29408409629` and merged-main run `29408654603` each passed all seven Linux 3.11–3.14, macOS, Windows, and Codex CLI jobs.
- Annotated tag object `fe8c834d5e9d450210cfdb33de0d6e8f688a7ae3` peels to the passing merge commit. Public non-draft, non-prerelease Release `RE_kwDOTVQo6M4VH8wK` was published at 2026-07-15T11:58:09Z.
- Local `rootloom@rootloom` and the managed personal preset upgraded from 3.0.0 to 3.1.0; setup reports no drift or pending upgrade. Installed Rules preserve representative routine/high-risk allow decisions and catastrophic deletion denials.
- The preserved image hash and Enterprise branch ref remain unchanged. Publication-record run `29413872318` passed the same seven jobs after the factual release record and validator contract were committed to `main`.

## Risks

- Risk: a published tag identifies code that did not pass merged-main CI.
  - Mitigation: wait for the exact merge commit run before creating the tag and verify the peeled identity afterward.
  - Residual risk: post-release defects require a new patch rather than tag mutation.
- Risk: the unrelated 1.15 MB image enters the release.
  - Mitigation: explicit path staging and pre/post-commit tree checks against its known hash.
  - Residual risk: none if it remains untracked and absent from every commit.
- Risk: transient GitHub TLS failures produce an incomplete publication.
  - Mitigation: verify state after each command, retry idempotent steps, and never infer success from submission alone.
  - Residual risk: the task may pause before the irreversible tag boundary if GitHub remains unreachable.

## Decision log

- 2026-07-15 — Publish the additive exact-reviewability capability as 3.1.0 using PR → CI → merge → merged-main CI → annotated tag → public Release → publication-record CI.
- 2026-07-15 — Treat the current `发布` request as Single action authority for this exact repository/version workflow, not reusable Full authorization.
- 2026-07-15 — Preserve the Enterprise branch and unrelated image unchanged and outside all publication artifacts.
- 2026-07-15 — Publish annotated `v3.1.0` only after corrected PR and merged-main CI passed; retain the tag and record later evidence on `main` rather than moving it.

## Durable decision records

- [Sensitive material and capture bounds](../../docs/decisions/2026-07-15-sensitive-material-and-capture-bounds.md)

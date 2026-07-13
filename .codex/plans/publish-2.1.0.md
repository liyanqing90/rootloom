# Publish Rootloom Personal Core 2.1.0

## Status

- State: in progress
- Owner: Codex
- Last updated: 2026-07-14
- Task type: release and external publication
- Risk: Tier 2 (Governed)

## Goal and observable success

Publish the already verified Personal Core intelligence and Engineering Memory changes as Rootloom 2.1.0 on the existing `main` release line.

Success is observable when:

- the complete reviewed 2.1.0 scope is committed and pushed without force;
- GitHub Actions passes for the release commit before tagging;
- annotated tag `v2.1.0` resolves to that passing release commit;
- a public, non-prerelease GitHub Release exists at the tag;
- a follow-up publication record is pushed and its CI passes;
- remote `codex/enterprise-assurance` remains at the untouched 1.2.19 baseline.

## Authority, scope, and non-goals

- The user explicitly authorized publication on 2026-07-14.
- Target: `https://github.com/liyanqing90/rootloom`, branch `main`, version/tag `v2.1.0`.
- Release scope is the completed [Personal Core intelligence plan](./personal-core-intelligence.md), including synchronized English/Chinese documentation and architecture imagery.
- Do not force-push, rewrite an existing tag, publish a prerelease, change repository settings, or modify/publish the Enterprise Assurance branch.
- Do not add implementation changes after the release commit except a factual publication record; any code failure returns to implementation and requires fresh validation.

## Baseline and preflight evidence

- Local `main`, `origin/main`, and remote `main` resolve to `e39072af7c1cf59d3750533420b2e1583e464336` after `git fetch --prune --tags origin`.
- Remote `codex/enterprise-assurance` resolves to `7da82dc8ad0faee0aa6a51c569bab8a60c233b8a`.
- GitHub CLI 2.75.0 is authenticated as `liyanqing90`; the repository default branch is `main`.
- Neither local/remote tag nor GitHub Release `v2.1.0` exists at preflight.
- Manifest and changelog identify version 2.1.0 dated 2026-07-14.
- The implementation plan records passing focused tests, `make check`, compatibility smoke, diff validation, bundle finalization, and architecture-image inspection.

## Release sequence and gates

1. Run final repository validation and inspect the exact staged scope.
2. Commit the release scope on `main` and push it to `origin/main`.
3. Wait for every GitHub Actions workflow triggered for the release commit; a failure blocks tagging.
4. Create annotated tag `v2.1.0`, push only that tag, and create a public GitHub Release with curated notes.
5. Verify remote branch/tag identity, Release state, public README images, and the unchanged enterprise branch.
6. Record exact commit, CI run, tag, and Release evidence here; commit/push that record and wait for its CI.

## Failure, rollback, and irreversible boundary

- Before the tag is pushed, ordinary corrective commits and rerun CI are sufficient; never rewrite published history.
- If release-commit CI fails, do not tag or create the Release. Diagnose, fix, revalidate, push a new commit, and wait again.
- If tag push succeeds but Release creation fails, retain the immutable tag and retry Release creation against the same commit.
- If the published Release metadata is wrong, edit metadata without moving the tag. A defective published build requires a new patch version rather than tag replacement.
- External irreversibility begins when `v2.1.0` is pushed; every gate before that point must be green.

## Verification record

- Pending release commit and GitHub Actions evidence.
- Pending annotated tag and GitHub Release evidence.
- Pending post-publication CI and remote-state verification.

## Decision log

- 2026-07-14 — Use the established direct-`main` Rootloom release flow because the user authorized publication and 2.0 established the same branch/tag/Release model.
- 2026-07-14 — Require passing release-commit CI before the irreversible tag push.
- 2026-07-14 — Keep the Enterprise Assurance branch immutable during this release.

# Publish Rootloom Personal Core 2.2.2

## Status

- State: in progress
- Owner: Codex
- Last updated: 2026-07-14
- Task type: release and external publication
- Risk: Tier 2 (Governed)

## Goal and observable success

Publish the verified governed-evidence hardening as Rootloom Personal Core 2.2.2 on `liyanqing90/rootloom`.

Success requires a passing release PR, merge to `main`, annotated `v2.2.2` tag, public non-prerelease GitHub Release, factual publication record, passing post-record CI, and unchanged `codex/enterprise-assurance`.

## Non-goals

- Do not publish the unrelated `assets/rootloom-xiaohei-loom.png` file.
- Do not force-push, rewrite tags, change repository settings, or modify `codex/enterprise-assurance`.
- Do not add new product behavior after release preparation begins.

## Baseline evidence

- Local release candidate starts at `37b104cf4db43b012bf22e43ef4c396f71ec2c8c`, one commit ahead of remote `main` at `09711c348454a47093dc2e0cea699cacd3921fe3`.
- `v2.2.1` is the latest published tag; neither tag nor GitHub Release `v2.2.2` exists and no pull request is open.
- `make check` passed 144 tests with one platform-conditional skip; `make compatibility-smoke` passed without install side effects or rollback leftovers.
- GitHub CLI 2.75.0 is authenticated as `liyanqing90` with repository/workflow access.
- Remote `codex/enterprise-assurance` is `7da82dc8ad0faee0aa6a51c569bab8a60c233b8a`.
- The worktree contains unrelated untracked `assets/rootloom-xiaohei-loom.png`; every stage/commit gate must exclude it.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Release candidate passed local gates | fact | local macOS checkout | 2026-07-14 | `.codex/plans/personal-core-evidence-hardening-2.2.1.md` | current; no sensitive payloads |
| GitHub target and auth are available | fact | GitHub CLI against `liyanqing90/rootloom` | 2026-07-14 | `gh auth status`; `gh repo view` | current; token redacted by CLI |
| Version/tag/PR namespace is clear | fact | local Git and GitHub | 2026-07-14 | `git fetch --prune --tags`; `gh release view`; `gh pr list` | current |

## Governed defect diagnosis

- Observed failure: release is not yet published; the plugin manifest and producer metadata still identify 2.2.1.
- Competing hypotheses: reuse 2.2.1 versus publish a new version. Existing immutable tag/release and user confirmation require a new patch version.
- Ownership path: plugin manifest and producer metadata → changelog → release PR/CI → merge commit → annotated tag → GitHub Release → publication record.
- Violated invariant: published plugin behavior must have a unique version whose tag points to a fully passing release commit.
- Root cause: not applicable; this plan governs publication of an already repaired change.
- Root-cause alignment: NOT_APPLICABLE.

## Constraints and invariants

- Publish exactly `2.2.2` / `v2.2.2` from the reviewed scope.
- Require every PR check to pass before merge and every `main` check to pass before tagging.
- The tag must be annotated, must peel to the release merge commit, and must never be moved.
- The GitHub Release must be public, non-draft, and non-prerelease.
- Preserve the plugin marketplace source path and keep installation setup-free by default.

## Impact map

- Producers: `plugins/rootloom/.codex-plugin/plugin.json`, engineering summary/baseline producer versions, `CHANGELOG.md`.
- Consumers: Codex plugin marketplace installs/upgrades, GitHub release users, strict-review evidence readers.
- Persisted data: Git commit, annotated tag, GitHub Release metadata, publication record.
- Public contracts: plugin SemVer, governed evidence CLI/JSON behavior documented in the release notes.
- Generated artifacts: none.
- External systems: GitHub repository, PR, Actions, tag, and Release.

## Design and decisions

- Ownership: repository version surfaces define the candidate; GitHub tag and Release publish it.
- Interfaces: retain existing plugin path and evidence formats; publish the stricter behavior as patch version 2.2.2 per explicit user confirmation.
- Compatibility window: legacy evidence remains readable as self-declared; strict callers must use the documented sealed lifecycle and explicit bundle-only option when nonblocking output is required.
- Alternatives rejected: mutate `v2.2.1` (immutable release violation), bypass PR/CI (insufficient release evidence), or include the unrelated illustration (outside scope).

## Implementation sequence

1. Create `codex/release-2.2.2`; update version surfaces, changelog, and this plan.
2. Run repository, unit, compatibility, and diff gates; commit only the release scope.
3. Push the branch, open a ready PR, wait for every check, and merge without force.
4. Wait for the merged `main` checks, create/push annotated `v2.2.2`, and publish the public Release.
5. Verify remote identities and Release state; add a factual publication record, push it, and wait for final CI.

## Rollout, failure, and rollback

- Dry-run/preview: local manifest/changelog validation plus PR diff and Actions checks.
- Mixed-version behavior: existing 2.2.1 installs remain valid; marketplace refresh/reinstall selects 2.2.2.
- Failure detection: local command failure, PR/main Actions failure, identity mismatch, existing tag/release, or unexpected staged file.
- Rollback or compensation: before tag push, use corrective commits or close the PR; after tag push, retain the tag and correct Release metadata, or publish a newer patch for code defects.
- Irreversible point: pushing annotated tag `v2.2.2`.

## Verification

- Original failure path: `gh release view v2.2.2` reports absent before publication and present afterward.
- Owning-boundary invariant: manifest/changelog version match; remote tag peels to the passing merge commit.
- Adjacent negative/alternate path: enterprise branch hash unchanged and illustration remains outside commits.
- Focused tests: targeted version/validator checks.
- Contract/migration tests: `make compatibility-smoke`.
- Type/lint/build/package: `make check`; `git diff --check`.
- Security/dependency checks: no dependency changes; inspect exact release diff and staged paths.
- Post-action verification: PR/main Actions success, remote branch/tag identity, public Release JSON, marketplace source path, and publication-record CI.

### Executed pre-publication evidence

- `make check` passed repository validation and all 144 tests; one platform-conditional non-UTF-8 filename case was skipped because the current macOS filesystem rejects the fixture name.
- `make compatibility-smoke` passed with no plugin-install side effects, failed commands, or managed rollback leftovers.
- `git diff --check` passed, version surfaces agree on 2.2.2, and no dependency or marketplace source-path change is present.
- PR #4 CI run `29325918198` passed Linux Python 3.11–3.14, macOS, and Codex CLI but exposed four Windows-only test portability defects: executable-bit assumptions, `core.autocrlf` byte conversion, and an unescaped Windows path in the evidence-mutation command. Publication stopped before merge/tagging; focused test-only repairs make those fixtures deterministic without changing product behavior.
- After the test-only repair, all three focused regression methods passed with `ResourceWarning` promoted to errors and a complete local `make check` again passed 144 tests with one platform-conditional skip.

## Risks

- Risk: publishing a tag before CI proves the merge commit.
  - Mitigation: block tag creation on successful PR and merged-main checks.
  - Residual risk: GitHub availability can delay completion.
- Risk: strict callers observe intentionally tighter behavior.
  - Mitigation: synchronized bilingual docs, changelog, legacy self-declared reads, and explicit `--strict-bundle-only` compatibility path.
  - Residual risk: undocumented exact-exit consumers may require adjustment.
- Risk: unrelated local asset enters publication.
  - Mitigation: explicit staging and post-commit tree/path checks.
  - Residual risk: none if the staged-path gate passes.

## Decision log

- 2026-07-14 — User explicitly confirmed formal publication as `v2.2.2` after exact target and irreversible actions were presented.
- 2026-07-14 — Use the established PR → CI → merge → annotated tag → public Release → publication-record flow.
- 2026-07-14 — Keep the Enterprise Assurance branch and unrelated illustration outside the release.
- 2026-07-14 — Treat PR #4's first Windows failure as a test-portability blocker; repair observed mode/newline/path assumptions and require a completely green rerun before merge.

## Durable decision records

- No new architecture decision; the governed evidence contract remains recorded in `docs/decisions/2026-07-14-personal-intelligence-contract.md`.

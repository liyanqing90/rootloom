# Release Rootloom 1.2.13

## Status

- State: in progress
- Owner: Codex
- Last updated: 2026-07-13
- Task type: release/publication
- Risk: Tier 2 (Governed)

## Goal and observable success

Publish the verified current workspace as Rootloom `v1.2.13` from repository `liyanqing90/rootloom` branch `main`. Success requires one scoped release commit pushed to `origin/main`, all required GitHub Actions jobs successful for that exact commit, an annotated `v1.2.13` tag pointing to it, and a non-draft, non-prerelease GitHub Release whose target matches the tag commit.

## Non-goals

- No force-push, history rewrite, branch protection change, package-registry publication, deployment, or modification outside this repository and its GitHub Release.
- No claim that local launcher identity checks provide kernel isolation, WORM audit storage, or power-loss crash consistency.

## Baseline evidence

- Local `main` and `origin/main` both pointed to `0d18d69a5da3d183443aecb32515393f1254bbe0` before the release commit.
- `v1.2.13` and a `Rootloom 1.2.13` Release did not exist; latest published version was `v1.2.12`.
- Plugin manifest is `1.2.13`, Strict Runner is `2.18`, and `CHANGELOG.md` has a dated `1.2.13` section.
- Final implementation tree passed `make check` (52 repository tests and 87 Strict Runner tests), `make compatibility-smoke`, repository validation, and `git diff --check`.
- GitHub authentication is active as `liyanqing90` with `repo` and `workflow` scopes. `main` is not protected, so publication explicitly gates Tag creation on observed CI success rather than branch protection.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Repository target and credentials are valid | fact | GitHub CLI / github.com | 2026-07-13 | `gh auth status`, `gh repo view` | token value redacted by CLI |
| Previous release used annotated tag plus non-draft Release | fact | local Git + GitHub Release | 2026-07-13 | `git cat-file -p v1.2.12`, `gh release view v1.2.12` | current |
| Candidate checks pass | fact | local macOS workspace | 2026-07-13 | `make check`, `make compatibility-smoke`, `git diff --check` | current candidate |

## Governed defect diagnosis

- Observed failure: not applicable; this is publication of the completed governed repair.
- Competing hypotheses: publish before CI because local checks pass; rejected because the previous release history demonstrates platform-only failures can block a safe tag. Create the tag before push CI; rejected because moving/deleting a published tag is avoidable release ambiguity.
- Ownership path: Git commit/push and GitHub Actions own candidate provenance; annotated Git tag and GitHub Release own public version identity.
- Violated invariant: not applicable.
- Root cause: not applicable.
- Root-cause alignment: NOT_APPLICABLE

## Constraints and invariants

- Tag must point exactly to the CI-green release commit.
- Release must be non-draft and non-prerelease and target the annotated tag commit.
- No release action proceeds after a failing or incomplete required CI job.
- Preserve all scoped implementation, test, plan, and bilingual contract files; do not include unrelated changes.

## Impact map

- Producers: local Git commit, `origin/main`, GitHub Actions CI, annotated tag `v1.2.13`, GitHub Release.
- Consumers: Codex plugin marketplace users, repository readers, setup/recovery and Strict Runner users.
- Persisted data: Git history/tag and GitHub Release metadata.
- Public contracts: plugin version 1.2.13, Strict Runner 2.18, Human Review v3, Recovery schema v2, isolation-launcher CLI alias compatibility.
- Generated artifacts: none attached to the Release.
- External systems: `github.com/liyanqing90/rootloom` only.

## Design and decisions

- Ownership: one release commit contains the candidate; tag and Release reference that immutable commit.
- Interfaces: `main` remains the install source; `v1.2.13` is the stable version selector.
- Compatibility window: Human Review v2 results fail closed and require rerun/external handling; `--require-isolation` remains an alias for `--require-isolation-launcher`; Recovery retains the implicit 1.2.12 target schema.
- Alternatives rejected: draft Release after Tag is unnecessary because the candidate is already locally verified; direct Release from a dirty tree would break provenance.

## Implementation sequence

1. Reconfirm final diff/versions and create the scoped release commit.
2. Push `main`, capture the exact commit SHA, and wait for every required CI job on that SHA.
3. Create and push annotated tag `v1.2.13` only after CI success.
4. Create the non-draft, non-prerelease GitHub Release and verify tag, commit, Release metadata, and remote branch state.

## Rollout, failure, and rollback

- Dry-run/preview: local validation, release-note review, tag/Release absence checks, and exact diff inspection.
- Mixed-version behavior: documented in README, Changelog, and the existing decision record.
- Failure detection: Git command exit status, GitHub Actions conclusion, tag target comparison, and Release JSON verification.
- Rollback or compensation: before Tag, fix forward with a new commit or stop. After Tag/Release, do not rewrite history; publish a corrective patch release. Tag deletion or force-push is not authorized or planned.
- Irreversible point: pushing the annotated tag and publishing the GitHub Release; explicitly authorized by the user on 2026-07-13.

## Verification

- Original failure path: covered by the completed 1.2.13 hardening plan.
- Owning-boundary invariant: exact commit SHA must match `origin/main`, tag peeled commit, CI head SHA, and Release target.
- Adjacent negative/alternate path: verify `v1.2.12` remains unchanged and `v1.2.13` is unique.
- Focused tests: completed in `.codex/plans/rootloom-1.2.13-audit-hardening.md`.
- Contract/migration tests: completed Human Review v2/v3 and Recovery schema regressions.
- Type/lint/build/package: `make check`, `make compatibility-smoke`, `git diff --check` passed locally.
- UI/browser evidence: not applicable.
- Security/dependency checks: no dependency changes; `scripts/validate_repo.py` passed.
- Post-action verification: `git ls-remote`, `gh run view`, `git cat-file`, and `gh release view` against the exact release SHA.

## Risks

- Risk: cross-platform CI finds a candidate-only defect.
  - Mitigation: stop before Tag/Release and fix forward.
  - Residual risk: CI cannot prove model semantics or long-term reliability.
- Risk: Release metadata points at the wrong commit.
  - Mitigation: use an annotated tag created from the captured green SHA and compare peeled remote/local references after publication.
  - Residual risk: GitHub availability is external.

## Decision log

- 2026-07-13 — User explicitly authorized direct publication without further confirmation.
- 2026-07-13 — Gate Tag and Release on exact-sha GitHub Actions success because `main` has no branch protection.

## Durable decision records

- `docs/decisions/2026-07-12-human-review-and-setup-recovery.md` records the shipped security and compatibility decisions; no separate release-only ADR is warranted.

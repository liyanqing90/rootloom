# Publish Rootloom Personal Core 2.3.0

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-14
- Task type: governed authorization change, public documentation, release, and local upgrade
- Risk: Tier 2 (Governed)

## Goal and observable success

Publish the verified three-mode authorization model and evergreen bilingual architecture surfaces as Rootloom Personal Core 2.3.0 on `liyanqing90/rootloom`, then upgrade the locally installed plugin and any existing managed personal preset.

Success requires separate English and Chinese architecture images with no version binding, synchronized public documentation, a passing release PR, merge to `main`, annotated `v2.3.0` tag, public non-prerelease GitHub Release, factual publication record, passing post-record CI, verified local 2.3.0 installation, and unchanged `codex/enterprise-assurance`.

## Non-goals

- Do not publish the unrelated untracked `assets/rootloom-xiaohei-loom.png` file.
- Do not force-push, rewrite tags, change repository settings, or modify `codex/enterprise-assurance`.
- Do not reintroduce enterprise approval, audit, strict-runner, or recovery machinery into Personal Core.
- Do not bind the new architecture images or evergreen product table to a release number.

## Baseline evidence

- The release branch starts from `efdf713fadbe1427af8e9f9810b312e5f633e752`, matching `origin/main` before release preparation.
- The worktree already contains the verified three-mode authorization implementation and its documentation; the preceding strict finalizer returned `VERIFIED_CHANGE`, `make check` passed 145 tests with one platform-conditional skip, and compatibility smoke passed.
- The current shared `docs/diagram/architecture.svg` is stale: it names Personal Core 2.1 and Rootloom 1.2.19, exposes the former local-versus-external command model, and is reused by both language editions.
- `v2.2.2` is the latest published tag; neither tag nor GitHub Release `v2.3.0` exists and no pull request is open.
- GitHub CLI is authenticated as `liyanqing90` with repository/workflow access.
- Remote `codex/enterprise-assurance` is `7da82dc8ad0faee0aa6a51c569bab8a60c233b8a`.
- The unrelated untracked illustration has SHA-256 `55ea78b17ac40b85cf347b478799dbda629ba8f4d52e7cea5044734c6ec1c0a6`; every stage and commit gate must exclude it and preserve that hash.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Authorization change passed strict local review | fact | local macOS checkout | 2026-07-14 | `/private/tmp/rootloom-explicit-action-final-20260714-2/summary.json`; `.codex/plans/explicit-action-authorization.md` | current; no sensitive payloads |
| Existing architecture image is version-bound and semantically stale | fact | tracked README and SVG source | 2026-07-14 | `README.md`; `README.zh-CN.md`; `docs/diagram/architecture.svg` | current; no sensitive content |
| GitHub target and authentication are available | fact | GitHub CLI against `liyanqing90/rootloom` | 2026-07-14 | `gh auth status`; `gh repo view` | current; token redacted by CLI |
| Version/tag/PR namespace is clear | fact | local Git and GitHub | 2026-07-14 | `git fetch --prune --tags`; `gh release view`; `gh pr list` | current |

## Governed diagnosis

- Observed failure: public architecture surfaces communicate an obsolete version and obsolete command-safety boundary, while Chinese readers receive the English diagram.
- Competing hypotheses: update only the text around the old image, keep one bilingual image, or replace it with language-specific evergreen artifacts. The embedded labels prove the image itself owns the defect, and separate artifacts avoid mixed-language layouts.
- Ownership path: authorization semantics and product architecture → language-specific SVG sources → rendered PNG review artifacts → README/docs references → repository contract validation.
- Violated invariant: evergreen public architecture surfaces must match current behavior, keep language editions separate, and avoid release-number churn.
- Root cause: the canonical diagram encoded historical release numbers and a pre-authorization-model command boundary, then both READMEs shared it.
- Root-cause alignment: ALIGNED.

## Constraints and invariants

- Publish exactly `2.3.0` / `v2.3.0`; the minor increment reflects a new public authorization model.
- Keep every visible architecture label English-only or Chinese-only apart from the Rootloom brand name.
- Reject version-like release labels in either canonical SVG through `scripts/validate_repo.py`.
- Require every PR check to pass before merge and every `main` check to pass before tagging.
- The tag must be annotated, must peel to the release merge commit, and must never be moved.
- The GitHub Release must be public, non-draft, and non-prerelease.
- Preserve the plugin marketplace source path and keep installation setup-free by default.
- Standard authorization persists across tasks only for non-high-risk actions supporting an explicit goal; Full authorization remains task/scope bounded and platform controls remain authoritative.

## Impact map

- Producers: plugin manifest, engineering evidence producer versions, authorization guidance/rules/setup assets, canonical SVG diagrams, rendered PNGs, changelog.
- Consumers: Codex plugin installs/upgrades, managed personal presets, README/documentation readers, strict-review evidence readers, repository validators.
- Persisted data: setup state version, Git commit, annotated tag, GitHub Release metadata, publication record.
- Public contracts: plugin SemVer, authorization-mode semantics, installation behavior, architecture and brand asset paths.
- Generated artifacts: the two `@2x.png` files rendered from canonical SVG sources.
- External systems: GitHub repository, PR, Actions, tag, Release, and local Codex plugin marketplace/cache.

## Design and decisions

- Ownership: global guidance owns authorization semantics, static Rules provide deterministic command classification, and platform controls continue to override both.
- Interfaces: `Single action`, `Standard`, and `Full` are the English public names; `本条命令`, `普通权限`, and `所有权限` are the independent Chinese names.
- Visual contract: English and Chinese diagrams share geometry and visual hierarchy but contain separate language-specific text and no release numbers.
- Compatibility window: existing installs remain usable; refreshing the marketplace and reinstalling selects 2.3.0, while optional managed assets require an explicit setup upgrade.
- Alternatives rejected: retain the shared diagram (wrong language and stale content), place both languages in one image (mixed-language clutter), or name the images with 2.3.0 (immediate future staleness).

## Implementation sequence

1. Create `codex/release-2.3.0`, seal the dirty baseline, and record this governed plan.
2. Replace the shared version-bound diagram with independent English and Chinese canonical SVGs and rendered PNGs; update README, architecture, brand, maturity, and validator surfaces.
3. Update plugin and evidence producer versions to 2.3.0, add changelog notes, run strict review, visual inspection, repository tests, compatibility smoke, and diff gates.
4. Commit only the intended scope, push the branch, open a ready PR, wait for every check, and merge without force.
5. Wait for merged `main` checks, create/push annotated `v2.3.0`, publish the public Release, record facts, push the record, and wait for final CI.
6. Refresh the local marketplace, reinstall Rootloom, upgrade an existing managed personal preset if present, and verify version and drift status.

## Rollout, failure, and rollback

- Dry-run/preview: inspect both rendered diagrams, local manifest/changelog validation, exact staged paths, PR diff, and Actions checks.
- Mixed-version behavior: existing 2.2.2 installs remain valid; marketplace refresh/reinstall selects 2.3.0; copied optional assets remain old until setup upgrade.
- Failure detection: visual mismatch, local command failure, PR/main Actions failure, identity mismatch, existing tag/release, unexpected staged file, setup drift, or plugin version mismatch.
- Rollback or compensation: before tag push, use corrective commits or close the PR; after tag push, retain the tag and correct Release metadata, or publish a newer patch for code defects. Setup upgrade refuses drift and preserves its backup chain.
- Irreversible point: pushing annotated tag `v2.3.0`.

## Verification

- Original failure path: old diagram contains historical versions and is shared across language editions; new README/docs references resolve to independent, version-neutral assets.
- Owning-boundary invariant: validator checks both SVG contracts, forbids version labels, and verifies both PNG signatures.
- Adjacent negative/alternate path: Standard authorization refuses high-risk coverage; Full remains task-scoped; Enterprise branch hash and unrelated illustration remain unchanged.
- Authorization boundaries: exercise Single action, Standard cross-task ordinary scope, Full current-task scope, high-risk exclusion, and platform-authority wording through focused setup/compatibility tests.
- Consumer compatibility: validate plugin-only install and optional existing-preset upgrade paths.
- Type/lint/build/package: `make check`; `make compatibility-smoke`; `git diff --check`.
- Visual validation: render each canonical SVG at 2× and inspect both PNGs for clipping, language isolation, hierarchy, and legibility.
- Post-action verification: PR/main Actions success, remote branch/tag identity, public Release JSON, local installed plugin version, managed preset drift status, and publication-record CI.

### Executed pre-publication evidence

- `make check` passed repository validation and all 145 tests; one platform-conditional non-UTF-8 filename case was skipped because the current macOS filesystem rejects the fixture name.
- `make compatibility-smoke` passed with no plugin-install side effects, failed commands, or managed rollback leftovers. Represented routine and high-risk commands resolve to allow, while catastrophic recursive deletion remains forbidden.
- English and Chinese 3200×1800 rendered artifacts were inspected directly. Both use the final light professional architecture style, are legible and unclipped, share the same geometry, keep visible text language-isolated, and contain no release number.
- The user-requested local cleanup removed all `baoyu-*` Skills from both `~/.codex/skills` and `~/.agents/skills`; Rootloom diagrams now render through system tooling and have no runtime or repository dependency on those Skills.
- The first strict release finalizer stopped before executing commands because its sealed contract used exact directory paths instead of recursive globs and omitted the analyzer's destructive-effect claim. A fresh operator-sealed intake corrects both contract defects; no product file was changed to suppress the gate.

### Executed publication and installation evidence

- Release PR [#5](https://github.com/liyanqing90/rootloom/pull/5) was squash-merged as `bb35433fb938ac3bfdff5339954dff6b44472fc8` after PR run [29332224659](https://github.com/liyanqing90/rootloom/actions/runs/29332224659) passed all seven jobs.
- Merged `main` run [29332440333](https://github.com/liyanqing90/rootloom/actions/runs/29332440333) passed the same seven jobs before the release tag was created.
- Annotated tag object `eac0a9a07041a2b92b372f33ddfc8357ebdc3d62` peels to `bb35433fb938ac3bfdff5339954dff6b44472fc8`.
- Public, non-draft, non-prerelease GitHub Release `RE_kwDOTVQo6M4VFlGv` is available at <https://github.com/liyanqing90/rootloom/releases/tag/v2.3.0>.
- Local `rootloom@rootloom` is installed and enabled at 2.3.0. The managed personal preset upgraded from 2.1.0 to 2.3.0 and reports no drift or pending upgrade.
- Both user Skill roots contain no `baoyu-*` directories. The unrelated illustration remains untracked with its original SHA-256, and `codex/enterprise-assurance` remains unchanged.

## Risks

- Risk: persisted Standard authorization is interpreted as blanket autonomous authority.
  - Mitigation: bind it to explicit user goals, non-high-risk actions, and platform controls in guidance, setup assets, docs, tests, and diagram.
  - Residual risk: natural-language scope still requires contextual judgment.
- Risk: image text becomes unreadable or mixed between language editions.
  - Mitigation: separate source files, matched geometry, automated token checks, and direct rendered-image inspection.
  - Residual risk: downstream Markdown renderers may scale differently; SVG remains responsive and PNG fallback remains available.
- Risk: unrelated local asset enters publication.
  - Mitigation: explicit staging, SHA check, and post-commit tree/path checks.
  - Residual risk: none if the staged-path gate passes.
- Risk: local setup has user drift.
  - Mitigation: inspect status first and allow the setup tool to refuse replacement; never use conflict replacement without exact new authorization.
  - Residual risk: plugin can still be upgraded even if copied managed assets require later manual resolution.

## Decision log

- 2026-07-14 — User explicitly requested README refresh, independent version-neutral Chinese and English architecture images, GitHub publication, and local latest-plugin installation.
- 2026-07-14 — Treat the current shared architecture diagram as invalid because it embeds obsolete product versions and pre-change command-safety semantics.
- 2026-07-14 — Publish the authorization model as minor version 2.3.0 using the established PR → CI → merge → annotated tag → public Release → publication-record flow.
- 2026-07-14 — Keep Enterprise Assurance and the unrelated untracked illustration outside the release.
- 2026-07-14 — Final visual direction is a light, minimal, professional architecture diagram. Do not use dark technical panels, character illustration, or the previously referenced illustration Skill.

## Durable decision records

- Authorization semantics: `docs/decisions/2026-07-14-tiered-authorization-modes.md`.
- Personal intelligence and strict evidence contract: `docs/decisions/2026-07-14-personal-intelligence-contract.md`.

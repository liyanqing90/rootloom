# Split Rootloom Personal Core from Enterprise Assurance

## Status

- State: in progress
- Owner: Codex
- Last updated: 2026-07-13
- Task type: architecture and public product contract
- Risk: Tier 2 (Governed)

## Goal and observable success

Keep the complete Rootloom 1.2.19 assurance product available on a dedicated local branch while making `main` a coherent personal-first product. The personal product must preserve risk routing, evidence, root-cause diagnosis, scoped implementation, verification, review, project guidance, and durable decision memory while removing enterprise approval, protected-deletion, human-review transaction, hardened artifact, recovery-journal, and delegated-runner machinery from its default code and documentation.

Success is observable when:

- local branch `codex/enterprise-assurance` still points to the untouched Rootloom 1.2.19 baseline commit;
- `main` exposes a default single-agent `engineering-change` workflow and lightweight project memory;
- setup installs the personal preset by default and uses ordinary lock, backup, apply, status, and rollback behavior;
- no personal-product manifest, setup surface, Hook, CI job, README, or architecture page presents enterprise assurance as a bundled/default feature;
- English and Chinese public documentation describe the same product and migration path;
- the README hero and architecture imagery depict Personal Core rather than the retired Assurance runner;
- `make check` and the offline compatibility smoke pass.
- `origin/codex/enterprise-assurance` retains the untouched 1.2.19 baseline, `main` contains the verified Personal Core implementation, and an annotated `v2.0.0` tag plus GitHub Release identify the release commit.

## Non-goals

- Force-pushing or rewriting any published branch or tag.
- Releasing a hosted enterprise extension from `main`.
- Preserving the former high-assurance CLI or persisted setup/recovery contract on the personal branch.
- Adding network services, databases, telemetry, or mandatory subagents.

## Baseline evidence

- `main` and `origin/main` both pointed to `7da82dc8ad0faee0aa6a51c569bab8a60c233b8a` with a clean worktree before the split.
- The same commit is now retained by local branch `codex/enterprise-assurance`.
- The former default plugin contains a 5,627-line strict runner, a 4,569-line runner test, Human Review modules, protected-deletion approval, hardened lock code, setup recovery journals, custom agents, and a high-assurance profile.
- Public docs and validation currently require the high-assurance Skill and strict-runner CI.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Baseline branch and cleanliness | fact | local Git repository | 2026-07-13 | `git status --short --branch`; `git branch --all --verbose --no-abbrev` | current; no sensitive content |
| Assurance implementation dominates code size | fact | local repository | 2026-07-13 | `wc -l plugins/rootloom/skills/high-assurance-coding-change/scripts/*.py ...` | current; no sensitive content |
| Product split requirements | fact | user-provided plan | 2026-07-13 | `/Users/tangyuan/.codex/attachments/05861f1f-8278-4187-b731-14637d66af47/pasted-text.txt` | current; no sensitive content |

## Governed defect diagnosis

- Observed failure: the default product makes personal users carry enterprise audit, approval, protected-deletion, artifact, recovery, lock, and multi-agent machinery.
- Competing hypotheses: (1) documentation alone makes Rootloom feel heavy; (2) the bundled runtime and installation contract are structurally enterprise-first. File and line inventory supports (2): the public Skills, setup components, Hook, CI, runner, tests, and docs all encode assurance as a product capability.
- Ownership path: `plugins/rootloom/` owns the installable product; `scripts/validate_repo.py`, CI, README files, and architecture docs own its public contract.
- Violated invariant: personal users should receive the everyday engineering-quality loop by default without enterprise approval/audit mechanisms.
- Root cause: the Core workflow and Assurance mechanisms share one plugin, setup catalog, runner, verification contract, and product narrative.
- Root-cause alignment: PASS

## Constraints and invariants

- `plugins/rootloom/` remains the only installable plugin source and marketplace target.
- Preserve risk routing, attributable evidence, root-cause alignment, scoped change contracts, deterministic local verification, review, project guidance, and durable decision records.
- The personal path stays standard-library-only, local, network-free, and single-agent by default.
- Setup remains plan-first, conflict-refusing, backup-backed, mode-preserving, lock-serialized, and atomic per file; it no longer claims whole-transaction compensation or historical journal recovery.
- The enterprise snapshot must remain recoverable by switching to `codex/enterprise-assurance`.
- Public breaking changes require an explicit migration note and synchronized English/Chinese documentation.

## Impact map

- Producers: plugin manifest, Skills, setup script, Hook policy, system guidance, lightweight workflow runner, project-memory helper.
- Consumers: Codex plugin discovery, Codex-home setup, project users, repository validation, CI and compatibility smoke tests.
- Persisted data: Codex-home managed files and `.rootloom/state.json`; repository `.project-memory/*.json` files created only on explicit memory commands.
- Public contracts: plugin version/description, Skill names, setup CLI/presets, Hook set, workflow output summary, project-memory JSON formats.
- Generated artifacts: personal workflow `diff.patch`, `test.log`, and `summary.json`; setup backup manifest.
- External systems: GitHub repository `liyanqing90/rootloom`; authorized mutations are pushing `main`, publishing the preserved `codex/enterprise-assurance` branch, pushing annotated tag `v2.0.0`, and creating the matching GitHub Release.

## Design and decisions

- Ownership: `main` owns Personal Core; `codex/enterprise-assurance` retains the complete 1.2.19 Assurance product.
- Interfaces: `$engineering-change` is the default implementation workflow; `$project-memory` initializes and records local project knowledge; setup defaults to the `personal` preset.
- Dependency direction: workflow and memory use standard-library local helpers; no personal module depends on assurance code or custom-agent assets.
- Compatibility window: no in-place compatibility is promised for the removed high-assurance/recovery interfaces on `main`; users needing them switch/install from the enterprise branch. Existing personal setup can be rolled back with its original version before installing the new preset.
- Alternatives rejected: leaving assurance code dormant still imposes maintenance, validation, documentation, and discovery complexity; keeping a second installable plugin on `main` contradicts the requested branch separation.

## Implementation sequence

1. Preserve the 1.2.19 baseline on `codex/enterprise-assurance` and record the split decision.
2. Replace the strict high-assurance workflow with a single-agent `engineering-change` Skill, lightweight verification/artifact helper, and final summary contract.
3. Add explicit lightweight project/failure memory and strengthen task/verification intelligence in the global workflow guidance.
4. Simplify setup, locking, Hooks, assets, tests, validation, and CI around the personal capability set.
5. Rewrite synchronized English/Chinese README, setup, architecture, maturity, troubleshooting, and guidance surfaces; add migration and branch-selection guidance.
6. Run focused tests, `make validate`, `make test`, `make check`, compatibility smoke, and a fresh challenge/diff audit.

## Rollout, failure, and rollback

- Dry-run/preview: setup retains `plan`; all repository, compatibility, image, and release checks run locally before the first push. Remote branches and releases are inspected before mutation.
- Mixed-version behavior: the personal setup refuses unmanaged conflicts. Users should use the old branch/version to roll back an installed assurance setup before applying the personal preset.
- Failure detection: repository validation, unit tests, compatibility smoke, setup plan/apply/status/rollback tests, workflow helper tests, and memory format tests.
- Rollback or compensation: switch to `codex/enterprise-assurance` for the exact baseline product. A bad `main` publication is compensated with an ordinary revert and patch release rather than history rewriting. Setup keeps per-target backups and a manifest for explicit rollback.
- Irreversible point: the first public push/tag/release can be consumed immediately. The user explicitly authorized publication and push in the current request; no force-push, tag replacement, or history rewrite is authorized.

## Verification

- Original failure path: baseline inventory confirmed the installable plugin, setup, Hooks, CI, docs, and 10,000+ focused Runner/Human Review lines bundled Assurance with Core; the baseline remains on the enterprise branch.
- Owning-boundary invariant: `make validate` passed and asserts the Personal Core Skill/asset/Hook catalog while rejecting the former high-assurance Skill, profile, custom-agent TOMLs, and strict-runner CI job.
- Adjacent negative/alternate path: focused tests prove sensitive deletion/rename refusal, no-verification non-PASS, user-conflict refusal, symlink refusal, post-setup drift refusal, update rollback to the prior install, and `rollback --all` to pre-install state.
- Focused tests: `make test` passed 42 tests covering workflow helper, project memory, simple lock, setup, Hooks, and guidance, including verification drift, tracked/captured-untracked sensitive deletion, empty capability selection, unborn repositories, invalid `HEAD`, and Windows verification-command parsing.
- Contract/migration tests: `make compatibility-smoke` passed with local Codex CLI 0.144.2; plugin install, personal apply/status/rollback, zero managed leftovers, and Rules decisions (`commit=allow`, `push=prompt`, `reset=forbidden`) were observed.
- Type/lint/build/package: `make check` passed; `git diff --check` passed; the generated `AGENTS.md` validator returned `valid: true`.
- UI/browser evidence: the shared README brand artwork was inspected; `docs/diagram/architecture.svg` rendered successfully through the native macOS SVG path and its 2800×1680 PNG fallback was visually inspected with labels, spacing, arrows, and product boundaries intact. The bundled Sharp converter did not render local fonts correctly in this environment, so its malformed PNG was replaced by the native render rather than published.
- Security/dependency checks: standard-library imports only; validation scans for secret patterns and stale assurance surfaces.
- UI/browser evidence: render the replacement SVGs to PNG, inspect them, and verify every README-local image target resolves.
- Post-action verification: `git diff --check`, branch/tree comparison, final repository status, GitHub Actions result, remote branch/tag resolution, GitHub Release state, and fresh analogous-path/removable-complexity review.

## Risks

- Risk: removing assurance files leaves stale public references or validation assumptions.
  - Mitigation: repository-wide reference scan plus contract validation.
  - Residual risk: external links may still point to historical interfaces until a future release is published.
- Risk: simplified setup cannot compensate an abrupt process/host failure across multiple files.
  - Mitigation: preview, conflict refusal, ordinary process lock, per-file atomic replace, pre-mutation backups, explicit rollback.
  - Residual risk: a crash between file replacements can leave a partial apply; `plan`/`status` exposes drift and the backup manifest supports manual or command rollback.
- Risk: branch-only enterprise storage is undiscoverable to remote users before push.
  - Mitigation: document the exact branch purpose and publish the preserved baseline branch as part of 2.0.0 rollout.
  - Residual risk: branch installation remains more advanced than installing the default Personal Core product.
- Risk: verification commands mutate the tracked patch or captured path set after the dangerous-deletion snapshot.
  - Mitigation: fail verification bundles on captured-state drift and regression-test tracked and captured-untracked sensitive deletion plus ordinary mutation.
  - Residual risk: untracked file contents are intentionally unread and an external process can still race the helper outside its snapshot boundary; the summary claims only preservation of the captured patch/path evidence.

## Decision log

- 2026-07-13 — Retain the untouched 1.2.19 assurance product on local branch `codex/enterprise-assurance`; make `main` personal-first.
- 2026-07-13 — Treat the split as a breaking 2.0.0 product contract rather than silently preserving incompatible CLI/setup behavior.
- 2026-07-13 — Keep assurance out of the `main` plugin tree instead of shipping it disabled, because branch separation is the requested ownership boundary.
- 2026-07-13 — Fresh challenge found and fixed update→rollback state loss; simple backup manifests now retain prior setup state and complete target hashes without restoring recovery journals.
- 2026-07-13 — Final branch check confirmed `codex/enterprise-assurance` remains at `7da82dc8ad0faee0aa6a51c569bab8a60c233b8a` with the former Skill, Hook, and profile present in that tree.
- 2026-07-13 — Publication authorized: release Personal Core as `v2.0.0`, push `main`, publish the preserved enterprise branch, wait for required CI, then create and verify the GitHub Release.
- 2026-07-13 — Fresh challenge narrowed the verification claim to the evidence actually captured: tracked patch plus changed/untracked path set. It also added captured-untracked sensitive-deletion refusal and invalid-HEAD fail-closed coverage.
- 2026-07-13 — Initial publication CI run `29261348889` passed Linux 3.11–3.14, macOS, and Codex CLI contracts but exposed POSIX `shlex` consumption of Windows executable-path backslashes. Release tagging remained blocked while platform-aware parsing and a direct regression test were added.

## Durable decision records

- [Split Personal Core from Enterprise Assurance](../../docs/decisions/2026-07-13-personal-core-enterprise-assurance-split.md)

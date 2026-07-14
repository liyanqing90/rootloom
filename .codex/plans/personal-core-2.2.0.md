# Rootloom Personal Core 2.2.0: low-friction install, deep review, and release

## Status

- State: published; external facts recorded in `docs/releases/2.2.0.md`
- Owner: Codex
- Last updated: 2026-07-14
- Risk: Tier 2 (public CLI, installed policy, and release)
- Target: `liyanqing90/rootloom`, `main`, public release `v2.2.0`

## Goal and observable success

Publish the complete 2.1 review hardening without making a newly installed or upgraded plugin run analyzers, baselines, machine contracts, finalizers, memory queries, or planning gates for ordinary work.

Success requires:

- `codex plugin add rootloom@rootloom` is a complete usable installation and creates no Rootloom global policy/setup files;
- the installed global policy and `engineering-change` Skill make deep review explicitly opt-in;
- default finalization remains truthful but non-blocking: incomplete governed evidence is `UNVERIFIED` and `passed: false`, while explicit `--strict` enforces Tier 1/2 baseline, contract, claims, and nonzero failure;
- all 14 supplied P1/P2/P3 findings retain executable fixes and regression coverage;
- optional global setup has explicit install/upgrade, drift refusal, version-only updates, retired-target backup/removal, and rollback;
- English/Chinese public contracts and the accepted intelligence decision agree;
- local gates, Codex compatibility smoke, strict self-review, release-commit GitHub Actions, annotated tag, GitHub Release, and post-publication verification pass.

## Authority and non-goals

- The user explicitly authorized implementation and final publication in the current request.
- Do not force-push, rewrite tags, publish a prerelease, change repository settings, or mutate `codex/enterprise-assurance`.
- Do not remove bounded capture, sensitive deletion protection, process cleanup, memory locking, or truthful quality fields merely to reduce friction.
- Do not auto-run setup or silently overwrite user-owned Codex-home files.

## Baseline and diagnosis

- Local `main` and `origin/main` began at `62f8d16`; the working tree contains only the scoped 2.2 implementation started in this task.
- The 2.1 review supplied reproducible false-PASS, resource-bound, memory-race, and output-safety defects.
- The first implementation fixed those mechanics but made Tier 1/2 baseline/contract/finalizer mandatory and left installed global guidance routing every non-trivial task through `engineering-change`.
- The user's correction identifies that as a product-boundary failure: installing a Personal Core update must not convert optional review evidence into universal daily gates.
- Root cause: truth reporting and enforcement were coupled. A missing machine proof became a process failure even when the user did not request strict assurance, and the installed policy selected the deep workflow by default.
- Strongest alternative rejected: removing the review controls would lower cost but reintroduce the supplied false-PASS defects. The owning fix is an advisory/strict mode boundary plus opt-in routing.
- `ROOT_CAUSE_ALIGNMENT: PASS`.
- A correction-phase external baseline was captured at `/tmp/rootloom-2.2.0-correction-baseline.json` before changing the enforcement/routing boundary. It is local verification evidence, not a release artifact.

## Contract and compatibility

- Allowed scope: plugin runtime/Skills/assets, repository validation/tests, synchronized docs/decision/changelog/manifest, and release plans.
- Forbidden scope: Enterprise Assurance branch, marketplace/repository settings, production services, dependencies, and unrelated cleanup.
- Existing summary format, artifact filenames, `--verify`, `--risk`, `passed`, and advisory invocations remain readable.
- `passed` remains true only for `VERIFIED_CHANGE`; default exit zero means bundle execution succeeded, not that coverage is sufficient.
- `--strict` is additive and is the only mode that makes missing Tier 1/2 baseline/contract/coverage blocking.
- Plugin-only install remains state-free. Optional setup state and backup formats remain compatible.

## Implementation stages

1. Preserve bounded state/process/memory/sensitive-path fixes from the review.
2. Add advisory versus strict finalizer semantics and focused regressions.
3. Make installed policy and Skill routing explicitly opt-in and prove plugin install has no setup/review side effects.
4. Preserve and challenge optional setup upgrade/rollback behavior.
5. Update both languages, architecture, maturity, decision, changelog, manifest, and repository validation for 2.2.0.
6. Run focused/full/compatibility/strict checks and fresh counterexample review.
7. Commit and push a release branch, use GitHub CI as the pre-tag gate, merge to `main`, create/push annotated `v2.2.0`, publish a public non-prerelease GitHub Release, and verify remote/public state.

## Verification map

- Primary install path: compatibility smoke asserts plugin discovery and an empty Rootloom global side-effect set before optional setup.
- Owning invariant: advisory finalizer exits zero with `UNVERIFIED`/`passed: false`; strict mode refuses missing governed evidence.
- Adjacent path: supplied contract/baseline yields `VERIFIED_CHANGE`; explicit contract violations, sensitive deletion, capture drift, output overflow, process leakage, and no-change behavior remain blocking/truthful.
- Setup alternate paths: first install, same-version upgrade, version-only upgrade, drifted target refusal, retired target removal/rollback, unsafe state-path refusal.
- Memory alternate paths: concurrent writers, schema limit parity, symlink/descriptor drift.
- Repository: `make check`, `make compatibility-smoke`, `git diff --check`.
- Release: all GitHub Actions jobs on the release commit before tag; remote branch/tag/release identity and public HTTP verification afterward.

## Rollout and rollback

- Before tag: ordinary corrective commits; never rewrite shared history.
- After tag: metadata errors may be edited without moving the tag; a code defect requires a new patch release.
- Optional setup retains backup/rollback. Plugin-only users have no Rootloom global files to migrate.
- Enterprise branch identity must remain unchanged.

## Decision log

- 2026-07-14 — Version is 2.2.0 because installation/default workflow behavior changes additively while review and persisted formats remain compatible.
- 2026-07-14 — Keep every review hardening mechanism but make enforcement explicit with `--strict`.
- 2026-07-14 — Treat `codex plugin add` as complete installation; global setup is optional and separate.
- 2026-07-14 — Use a release branch and CI gate before the irreversible annotated tag and public Release.

## Verification record

- `make validate` passed the repository public-contract gate.
- `make check` completed 83 tests with one local filesystem-dependent non-UTF-8 skip; all remaining tests passed.
- `make compatibility-smoke` passed on `codex-cli 0.144.2`, reported `plugin_install_side_effects: []`, exercised optional install/status/upgrade/rollback, and left no managed residue.
- `git diff --check` passed.
- Strict self-review at `/tmp/rootloom-2.2.0-review/summary.json` reported Tier 2, `quality_status: VERIFIED_CHANGE`, complete five-behavior coverage, passing commands, preserved capture, valid scope, and valid root-cause alignment.
- Release-commit GitHub Actions, tag, Release, public HTTP, and post-publication records are pending.

## Durable decision

- Update [Keep Personal Intelligence Advisory, Local, and Evidence-Subordinate](../../docs/decisions/2026-07-14-personal-intelligence-contract.md) so future work preserves the advisory/strict and plugin/setup boundaries.

# Repair and publish Rootloom Personal Core 2.4.0

## Status

- State: in progress
- Owner: Codex
- Last updated: 2026-07-15
- Task type: governed defect repair, public contract release, and local upgrade
- Risk: Tier 2 (Governed)

## Goal and observable success

Repair the three verified gaps in Strict Review evidence attribution and bounded Git capture, publish the complete evidence-honesty work as Rootloom Personal Core 2.4.0, and upgrade the local plugin plus the already-installed personal preset.

Success requires fail-before/pass-after regressions for every reported trigger, task-only risk analysis and patch output where dirty-baseline evidence permits exact attribution, deterministic EOF for Git stdin consumers, separate candidate and classified-sensitive budgets, synchronized 2.4.0 version surfaces, passing local release gates, a passing release PR and merged-main CI, an annotated `v2.4.0` tag, a public non-prerelease GitHub Release, a factual publication record, and a verified drift-free local 2.4.0 installation.

## Non-goals

- Do not publish or modify the unrelated untracked `assets/rootloom-xiaohei-loom.png` file.
- Do not force-push, rewrite or delete tags, change repository settings, or modify `codex/enterprise-assurance`.
- Do not restore Enterprise Assurance machinery or claim semantic correctness from mechanical evidence.
- Do not invent exact tracked dirty-baseline attribution when baseline v2 lacks per-path patch bytes.

## Baseline evidence

- `main`, `origin/main`, and the release branch base resolve to `6447849ff402243a2c7e5826858f962483b92816`; the release work is isolated on `codex/release-2.4.0`.
- Review reproduced three defects: unchanged baseline text can affect analyzer claims and enter `diff.patch`; an unborn-repository empty-tree command inherits open stdin and times out; broad Git pathspec candidates consume the classified-sensitive result budget before reclassification.
- The worktree contains the intended Strict Review implementation and documentation plus the unrelated image. No staged changes existed at intake.
- `v2.3.0` is the latest published version. Local and remote `v2.4.0`, GitHub Release `v2.4.0`, release branch, and open PR namespace were empty after fetch.
- GitHub CLI is authenticated as repository administrator `liyanqing90` with repository and workflow access.
- Local `rootloom@rootloom` is installed and enabled at 2.3.0. The optional personal preset is installed at 2.3.0 with no drift.
- The unrelated image SHA-256 is `55ea78b17ac40b85cf347b478799dbda629ba8f4d52e7cea5044734c6ec1c0a6`; every staging, tag, and post-install gate must preserve and exclude it.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Three review findings are reproducible | fact | disposable local Git repositories on macOS | 2026-07-15 | review repros; `finalize_change.py`; `runner/state.py` | current; synthetic content only |
| Release target and authorization are resolved | fact | local Git and GitHub CLI for `liyanqing90/rootloom` | 2026-07-15 | `git fetch --prune --tags`; `gh auth status`; `gh repo view`; `gh release view`; `gh pr list` | current; token redacted by CLI |
| Local install is safe to upgrade | fact | Codex CLI and setup status | 2026-07-15 | `codex plugin list`; `setup_rootloom.py --json status` | current; no drifted paths |
| 2.4.0 is the appropriate release | inference | SemVer and public Summary/CLI/recovery contract delta | 2026-07-15 | `CHANGELOG.md`; prior hardening plan | current |

## Governed defect diagnosis

- Observed failure: the dirty-baseline partition is applied after risk analysis and not to bundle patch construction; `_empty_tree` invokes a stdin-reading Git command without supplying EOF; sensitive discovery applies the classified-result budget to deliberately overmatching Git candidates.
- Competing hypotheses: documentation-only clarification, broader time/path limits, or fixing each owning boundary. Documentation cannot prevent evidence contamination or process blocking, and larger limits only defer false failures. The producer boundaries must enforce task evidence, input closure, and budget semantics directly.
- Ownership path: task attribution and bundle construction in `finalize_change.py`; bounded subprocess input in `runner/process.py`/`runner/state.py`; candidate discovery and final classification in `runner/state.py`.
- Violated invariant: unchanged user state remains outside task analysis/evidence when exact exclusion is provable; every bounded child gets deterministic input and termination; a public sensitive-result ceiling counts classified sensitive results rather than false-positive candidates.
- Root cause: the first hardening pass corrected summary attribution but left earlier and later consumers on aggregate repository capture; its generic process wrapper omitted stdin ownership; and it reused one path limit for two semantically different collections.
- Root-cause alignment: PASS. The owning-boundary repairs pass the original triggers, adjacent changed-untracked and true-sensitive cases, and quoted-path/patch-like-content challenges.

## Constraints and invariants

- Keep helpers deterministic, local, network-free, Python 3.11+ standard-library-only, bounded, and repository-contained.
- Preserve baseline/contract/manifest/seal format names and conservative attribution for ambiguous tracked dirty overlap.
- Sensitive content remains unread and unserialized; candidate discovery retains finite byte, time, and path ceilings.
- Public behavior changes remain synchronized across English and Chinese documentation and changelog.
- Require all PR checks and merged-main checks before tagging. The annotated tag must peel to the passing release commit and must never be moved.
- GitHub Release must be public, non-draft, and non-prerelease.

## Impact map

- Producers: `finalize_change.py`, `runner/state.py`, `runner/process.py`, baseline fingerprints, plugin manifest, evidence producer versions, changelog, release plan and record.
- Consumers: strict/advisory CLI users, summary and bundle readers, CI quality exits, plugin marketplace installs, optional setup upgrades.
- Persisted data: review bundles, Git commit/PR, annotated tag, GitHub Release metadata, setup version state, publication record.
- Public contracts: task-attributed `changed_files`/risk/patch relationship, Git time and sensitive-result CLI budgets, plugin SemVer.
- Generated artifacts: `diff.patch`, `summary.json`, `test.log`; no new mandatory artifact format.
- External systems: GitHub repository/Actions/Release and local Codex plugin marketplace/cache/home.

## Design and decisions

- Ownership: derive one evidence partition before analyzer invocation and reuse it for scope, risk, and bundle patch construction.
- Interfaces: extend bounded process execution with explicit optional input; `_empty_tree` sends empty bytes. Retain `max_sensitive_paths` as a classified-result limit and use a distinct bounded candidate limit.
- Compatibility window: clean baselines and conservative tracked overlap retain existing behavior; exact unchanged untracked text stops influencing risk and bundle content. Existing 2.3.0 installations remain usable until refreshed.
- Alternatives rejected: filtering only summary metadata, using a shell redirection around Git, removing candidate bounds, or silently treating ambiguous tracked patches as exact.

## Implementation sequence

1. Add focused regressions for task-only analysis/bundle output, open stdin in unborn repositories, and non-sensitive pathspec overmatches.
2. Repair the owning boundaries, run focused regressions, and challenge adjacent dirty-baseline, Git-input, and sensitive-discovery cases.
3. Advance plugin/evidence producer versions and changelog to 2.4.0; synchronize any behavior documentation and repository contract assertions.
4. Run `make check`, `make compatibility-smoke`, `git diff --check`, strict governed finalization, scope/staging checks, and a fresh review pass.
5. Commit intended files only, push `codex/release-2.4.0`, open a ready PR, wait for all checks, and merge without force.
6. Wait for merged `main` CI, create and push annotated `v2.4.0`, publish the GitHub Release, record publication facts, push the record, and wait for final CI.
7. Upgrade the Rootloom marketplace/plugin and the existing personal preset, then verify version, enabled status, drift, rules, remote/tag identity, and preserved unrelated state.

## Rollout, failure, and rollback

- Dry-run/preview: focused tests, exact staged path list, release note preview, PR diff, setup status and upgrade plan.
- Mixed-version behavior: 2.3.0 bundles remain readable by schema revision; 2.3.0 plugin installs remain valid; marketplace reinstall selects 2.4.0 and copied optional assets update only through explicit setup upgrade.
- Failure detection: regression/local gate failure, unexpected staged path, PR/main CI failure, branch/tag identity mismatch, existing tag/release, setup drift, or installed-version mismatch.
- Rollback or compensation: before tag push, use corrective commits or leave the PR unmerged; after tag push, never move/delete the published tag for an ordinary defect—publish a newer patch. Setup upgrade uses its backup chain and refuses drift.
- Irreversible point: pushing annotated tag `v2.4.0`; explicitly authorized by the user's current publish request for this repository/version.

## Verification

- Original failure path: focused tests reproduce all three review scenarios before repair and pass afterward.
- Owning-boundary invariant: finalizer task scope, analyzer inputs, and patch headers/content agree; empty-tree Git receives EOF; sensitive result ceiling is checked after classification.
- Adjacent negative/alternate path: changed untracked baseline remains attributed; ambiguous tracked overlap remains conservative; true sensitive candidates still exceed the result budget; Git timeout/output/process-tree failures remain closed.
- Focused tests: `python3 -B -m unittest tests.test_engineering_change -v` plus individual new tests during development.
- Contract/migration tests: `make check`; strict governed finalization; revision-3 compatibility remains documented rather than rewritten.
- Type/lint/build/package: `make validate`; `git diff --check`; `make compatibility-smoke`.
- Security/dependency checks: synthetic sensitive-path quarantine and patch inspection; no dependency changes.
- Post-action verification: PR/main/final Actions success, tag object and peeled commit identity, public Release JSON, local plugin 2.4.0, setup status with no drift, unchanged Enterprise branch and image hash.

### Executed pre-publication evidence

- Fail-before reproductions confirmed unchanged baseline text contaminating analyzer/patch evidence, an unborn-repository Git stdin timeout, and false-positive discovery candidates exhausting the sensitive-result budget.
- Pass-after focused coverage completed 105 tests with one environment-only non-UTF-8 filename skip; the repository gate completed 155 tests with the same skip.
- `make compatibility-smoke` returned `passed: true` with no failed commands, managed rollback leftovers, or plugin-install side effects.
- The original sealed intake finalized with exit 0, summary revision 4, `REVIEW_EVIDENCE_COMPLETE`, `passed: true`, `change_partition: exact`, complete claim binding, and a valid hash chain.
- The unrelated image stayed in `preexisting_changes`, outside task changes and patch headers; its SHA-256 remains `55ea78b17ac40b85cf347b478799dbda629ba8f4d52e7cea5044734c6ec1c0a6`.

## Risks

- Risk: filtering the task patch could omit an ambiguous tracked baseline edit.
  - Mitigation: only exact unchanged untracked entries are subtractable under baseline v2; tracked patch drift remains conservative.
  - Residual risk: exact per-path tracked subtraction requires a future baseline format change.
- Risk: a candidate ceiling that is too small can still fail a repository with many false-positive names.
  - Mitigation: keep candidate and result ceilings distinct, bounded, and test their separate failure messages/semantics.
  - Residual risk: candidate capture remains intentionally fail-closed in exceptionally large matching repositories.
- Risk: external publication races or CI regressions.
  - Mitigation: refresh refs, require PR and merged-main CI, recheck tag/release absence, and verify identities after each external action.
  - Residual risk: post-release defects require a new patch release rather than tag mutation.
- Risk: local managed assets drift between plan and upgrade.
  - Mitigation: rerun status immediately before upgrade; do not replace conflicts or drift.
  - Residual risk: plugin installation can succeed while optional preset upgrade remains blocked and must be reported separately.

## Decision log

- 2026-07-15 — User explicitly authorized fixing the review findings, committing, publishing the current repository, and installing the result.
- 2026-07-15 — Select 2.4.0 because the accumulated change advances public evidence semantics and adds CLI/recovery contracts.
- 2026-07-15 — Use the established PR → CI → merge → merged-main CI → annotated tag → public Release → publication-record flow.
- 2026-07-15 — Preserve `assets/rootloom-xiaohei-loom.png` and `codex/enterprise-assurance` outside publication.

## Durable decision records

- Evidence contract: `docs/decisions/2026-07-15-evidence-honest-strict-review.md`.
- Personal intelligence boundary: `docs/decisions/2026-07-14-personal-intelligence-contract.md`.

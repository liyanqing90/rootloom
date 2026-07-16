# Reset Personal Core product boundaries

Status: accepted

Date: 2026-07-16

## Context

Personal Core was intended to reduce prompt debt, but its public surface accumulated presets, authorization terminology, automatic repository writes, optional evidence machinery, experimental memory, release records, and component-specific guidance in the repository root. The mechanisms remained individually bounded, yet their combined learning and trust cost contradicted the low-friction personal product.

The reset must preserve existing Baseline v2–v4 and Summary revision 5 consumers. It must not introduce Baseline v5, Summary revision 6, a separate Evidence plugin, a 4.0 release, or removal of Project Memory before comparative product evidence exists.

## Evidence

| Observation | Kind | Source | Date | Notes |
| --- | --- | --- | --- | --- |
| Global guidance was 9,147 bytes and 100 lines, and root guidance contained 17 component ownership rules | verified fact | pre-change `plugins/rootloom/assets/system/AGENTS.md` and root `AGENTS.md` | 2026-07-16 | local repository evidence |
| Setup publicly exposed four preset names and described command Rules as `command-safety` | verified fact | pre-change `setup_rootloom.py`, README, and setup docs | 2026-07-16 | `engineering` duplicated `personal` |
| SessionStart called the repository writer and could create or update `AGENTS.md` | verified fact | pre-change `seed_project_guidance.py` and tests | 2026-07-16 | enabled only by managed policy, but still implicit persistence |
| One-time plans and publication records duplicated facts already owned by GitHub | verified fact | tracked `.codex/plans/`, `docs/releases/`, and `scripts/validate_repo.py` | 2026-07-16 | included historical tag, Release, and CI identifiers |
| Product review identified configuration and code complexity as relocated prompt debt | product judgment | user-provided repository audit | 2026-07-16 | accepted direction, not a controlled quality measurement |

## Decision

Personal Core has four explicit layers:

1. **Core — Change, Review, Guidance.** Direct scoped implementation, review-only analysis, and project guidance are the everyday product.
2. **Optional Autonomy.** The three authorization modes and static command Rules are an optional low-confirmation layer. `autonomy` is the canonical capability name; `command-safety` remains input compatibility only and is not presented as a deterministic safety system.
3. **Optional Evidence.** Analyzer, Baseline, Contract, Seal, and Finalizer remain explicitly invoked tools. Their existing wire formats and states are frozen pending comparative evidence.
4. **Experimental Project Memory.** Memory remains available, explicit, advisory, and outside the stable Core claim.

Public trust language keeps three boundaries separate: model-guided workflow judgment, mechanically observed evidence/provenance, and semantic correctness or security. Personal Core may claim the first two only within their documented limits; it does not present itself as a verified-quality layer or claim that a completed evidence chain proves the third. The privacy classifier remains path-based so candidate secret contents stay unread. Content-aware secret detection, if later justified, must be a separate trusted local scanner boundary that returns only redacted findings. No independent security audit or fuzzing assurance is implied until durable external evidence exists.

The public preset list is `skills-only`, `guidance`, and `personal`. `engineering` remains a hidden compatibility alias for `personal`.

The SessionStart Hook may detect repository facts and inject temporary context, but it must not write repository files. Creating or refreshing `AGENTS.md` requires an explicit `seed-project-guidance` invocation.

Historical Baseline Readers validate wire structure and hashes separately from current execution policy. Finalizer applies current Reviewable policy and returns `reintake-required` before reading Reviewable content when a historical declaration is no longer allowed; no new Baseline or Summary revision is created for this correction.

Global guidance is constrained to root-cause repair, unrelated-work preservation, risk tiers, proportional verification, opt-in deep review, and minimal authorization semantics. Root repository guidance carries only repository-wide constraints; component invariants live in nearest nested `AGENTS.md` files.

Release facts are owned by GitHub PRs, Actions, tags, and Releases. `CHANGELOG.md` records user-observable changes. The repository does not retain one-time task plans, Publication Records, Final Records, historical Release IDs, tag object IDs, or CI run IDs. Formal releases batch compatible boundary fixes instead of publishing each classifier edge independently.

The preserved `codex/enterprise-assurance` branch is named **Archived Assurance Edition**. It is not described as an active product line unless independent maintenance and release policy resume.

## Alternatives rejected

- Split Evidence into another plugin now — rejected because packaging change precedes evidence that separation improves real work.
- Delete Project Memory now — rejected because experimental labeling and explicit invocation reduce the claim without destroying the experiment.
- Restore command-by-command prompts for all high-risk argv — rejected because static Rules cannot hold semantic task authorization and duplicate prompts do not establish safety.
- Add new Baseline, Summary, or quality-state versions while correcting compatibility — rejected because wire-format expansion is the problem being frozen.
- Keep automatic `AGENTS.md` writes only for trusted repositories — rejected because trust of a path does not equal user intent to persist generated guidance.
- Read repository contents inside the privacy classifier — rejected because content-aware scanning is a different trust boundary and would violate the current content-unread invariant. A future local scanner must be evaluated independently and expose only redacted findings.

## Consequences

- Positive: the everyday product and optional mechanisms are distinguishable before installation or use.
- Positive: repository startup becomes read-only, while explicit seeding remains available.
- Positive: historical Evidence artifacts can remain readable without weakening current execution policy.
- Positive: product language distinguishes inspectable workflow mechanics from semantic or security assurance.
- Negative: legacy names and Evidence formats still carry compatibility code until a later evidence-based contraction decision.
- Negative: unusual secrets stored under ordinary paths remain outside Rootloom's path-classifier guarantee unless a separate scanner is introduced.
- Operational: documentation, setup catalogs, Hook tests, nested guidance, validator contracts, and the changelog must remain aligned with these boundaries.

## Verification and revisit triggers

Repository validation must enforce the compact guidance bounds, three public presets, canonical `autonomy` capability, exact component-policy version, absence of tracked one-time plan/release-record trees, and frozen Evidence format markers. Focused tests must prove read-only SessionStart behavior and legacy alias compatibility.

Revisit plugin separation or Memory removal only after representative real tasks compare Vanilla Codex with the reduced Rootloom Core on completion quality, intervention cost, context size, and failure modes. Evaluate a separate content-aware scanner only when real tasks show material path-classifier misses and the scanner can emit redacted findings without expanding model exposure. Raise security-assurance language only after targeted independent review or fuzzing produces durable evidence. Revisit Archived status only after the branch gains an independent maintainer, release cadence, and compatibility policy.

This decision supersedes the active-product-line wording in [the original Personal/Enterprise split](2026-07-13-personal-core-enterprise-assurance-split.md) while preserving its branch separation. It refines the naming, not the authorization semantics, of [the tiered authorization decision](2026-07-14-tiered-authorization-modes.md).

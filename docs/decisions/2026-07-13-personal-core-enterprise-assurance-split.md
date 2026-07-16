# Split Personal Core from Enterprise Assurance

- Status: accepted
- Date: 2026-07-13
- Owners: Rootloom maintainer
- Scope: product branches, installable plugin boundary, and public workflow contract
- Supersedes: none
- Superseded by: none

## Context

Rootloom 1.2.19 combined an everyday engineering-quality loop with enterprise-oriented Human Review, protected-deletion approval, Artifact binding, hardened locking, recovery journals, and controlled multi-agent execution. That combination made assurance machinery part of the plugin, setup catalog, Hook surface, CI, documentation, and maintenance cost for individual users even when they never selected the audited route.

The accepted product direction is to keep the personal loop—risk classification, attributable evidence, root-cause diagnosis, scoped change contracts, implementation, behavior-derived verification, review, and memory—without making enterprise approval and audit mechanisms the default product.

## Evidence

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| The complete Assurance baseline is retained independently | fact | local Git repository | 2026-07-13 | branch `codex/enterprise-assurance` at commit `7da82dc8ad0faee0aa6a51c569bab8a60c233b8a` | current; no sensitive data |
| Assurance machinery dominated the former implementation and public contract | fact | local repository baseline | 2026-07-13 | former `plugins/rootloom/skills/high-assurance-coding-change/`, setup, Hooks, tests, CI, and 1.2.19 docs on the retained branch | current baseline; no sensitive data |
| The requested direction is default Core with separated enterprise capability | fact | user-provided product plan | 2026-07-13 | accepted decision context and branch implementation | current; no sensitive data |
| Both product branches and the Personal Core release are public | fact | GitHub `liyanqing90/rootloom` | 2026-07-13 | `main` at `7667ae5`; `codex/enterprise-assurance` at `7da82dc`; annotated tag and Release `v2.0.0`; CI run `29261706308` | current; no sensitive data |

## Decision

`main` owns Rootloom Personal Core 2.x. It ships a single-agent `engineering-change` loop, optional `.project-memory/`, project guidance, durable decision records, command Rules, a single project-guidance Hook, lightweight verification artifacts, and simple backup/rollback setup.

The complete pre-split Rootloom Assurance 1.2.19 product is preserved on `codex/enterprise-assurance`. Enterprise approval, Human Review, protected-deletion state, strict multi-agent Runner, hardened Artifact transactions, and recovery journals do not ship in the `main` plugin by default.

This is a breaking product and setup boundary. Personal Core does not silently migrate, infer, or remove an existing Assurance installation; users roll it back with the 1.2.19 product before installing Personal Core.

## Alternatives considered

- Keep Assurance code dormant behind flags on `main` — rejected because code discovery, validation, CI, documentation, security claims, and maintenance would remain coupled even when runtime defaults changed.
- Ship a second installable Assurance plugin inside `main` immediately — deferred because the requested ownership boundary is a separate branch, and publishing/maintaining a second plugin is outside this local restructuring scope.
- Delete the Assurance implementation — rejected because it already represents substantial reusable enterprise capability and the branch snapshot preserves it without burdening Personal Core.

## Consequences

- Positive: individual users get a smaller default product centered on daily engineering decisions and reusable memory.
- Positive: the archived Assurance implementation remains recoverable if independent maintenance resumes.
- Negative: high-assurance Skill, Runner CLI, Human Review formats, and setup/recovery interfaces are not compatible on `main`.
- Negative: Archived Assurance Edition is preserved as a branch rather than maintained as an independently versioned plugin, so it is not an active product line.
- Operational: public behavior changes require synchronized English/Chinese documentation; migration must instruct users to roll back with the product version that created their setup.
- Operational: release 2.0.0 publishes both `main` and `codex/enterprise-assurance`; future changes must keep their contracts and versions visibly separate.

## Verification

- `codex/enterprise-assurance` must continue to resolve to the untouched 1.2.19 baseline tree.
- `plugins/rootloom/` on `main` must contain only Personal Core Skills, assets, and Hook surfaces.
- `make check` and `make compatibility-smoke` must pass before release or publication.
- Repository validation must reject reintroduction of the former high-assurance Skill, profile, custom-agent TOMLs, or strict-runner CI job on `main`.

## Revisit when

- users need the Archived Assurance Edition restored as an actively maintained, independently versioned plugin rather than a branch;
- Personal Core usage evidence shows that one removed mechanism is necessary for ordinary individual workflows;
- the platform provides a substantially simpler native approval, immutable audit, or multi-agent enforcement boundary.

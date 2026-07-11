# Release Rootloom 1.0

## Status

- State: release candidate
- Owner: Codex
- Last updated: 2026-07-11
- Risk: R3

## Goal and observable success

Launch a clean, bilingual `rootloom` v1 repository with no predecessor commit or tag history. One plugin must deliver selectable global policy, project context, command safety, delegation control, and deterministic high-assurance capabilities without forcing optional subagent behavior on ordinary users.

The release is complete only when the local validator, unit tests, deterministic-runner tests, isolated plugin/setup smoke test, GitHub Actions, remote marketplace installation, tag, release, and remote tree identity are all verified. The predecessor GitHub repository may be deleted only after those checks pass.

## Non-goals

- Auto-overwrite user-owned global guidance, config, Rules, or custom-agent files.
- Add an MCP server when local files and Codex-native mechanisms already provide the required capability.
- Claim Hooks can hard-cap cumulative subagents or replace sandboxing, Rules, CI, or external orchestration.
- Adopt mandatory file-header documentation, repository-wide file inventories, or persona-heavy prompt scaffolding.
- Preserve predecessor repository history, tags, release metadata, or upgrade-only behavior in the v1 product contract.

## Constraints and invariants

- Use one public identity for the repository, marketplace, and plugin: `rootloom`.
- Use deterministic, standard-library-only local setup and Hook scripts; do not add runtime network calls.
- Default setup to planning/status and require explicit apply for Codex-home writes.
- Keep lifecycle Hooks disabled until an explicit managed component policy enables them.
- Back up every replaced file and refuse unmanaged or user-modified conflicts without exact authorization.
- Keep one write-capable agent in controlled workflows and distinguish concurrent thread caps from cumulative delegation budgets.
- Treat delegation control as one optional atomic capability: limits, four roles, and the audit Hook install together.
- Keep stable policy in global guidance, repository facts in project guidance, reusable procedures in Skills, runtime settings in config/Agent TOML, command policy in Rules, and executable proof in tests and CI.

## Impact map

- Producers: plugin manifest, setup assets/scripts, seeder, lifecycle Hooks, operating Skills, high-assurance runner, documentation, CI.
- Consumers: Codex desktop/CLI/IDE users and trusted repositories receiving managed project guidance.
- Persisted data: explicit setup writes under the user's Codex home and advisory Hook state under plugin data.
- Public contracts: repository/plugin ID, install commands, Skill names, setup CLI, Hook definitions, generated guidance markers, v1 tag and release.
- External systems: the new GitHub repository, Actions, release metadata, and deletion of the predecessor repository after validation.

## Design decisions

- Capability levels are the primary installation unit: `skills-only` → `guidance` → `engineering` → `delegated` → `full`.
- `engineering` is the recommended single-agent default; `delegated` and `full` are explicit opt-ins.
- Missing, malformed, or symlinked component policy fails closed, so plugin installation alone has no automatic lifecycle side effect.
- Custom Agent TOMLs own role/model defaults; Skills own workflow; Hooks audit; Rules own command policy; the runner owns strict stage order and scope gates.
- The strict route remains a sequential `codex exec` pipeline because native subagent Hooks cannot cancel a child or prove a cumulative lifetime cap.
- No core MCP server is shipped because it would add process and trust surface without adding a missing local capability.
- The GitHub v1 repository starts with one root commit. Historical prototype commits and tags are intentionally excluded.

## Implementation and release sequence

1. Finalize the v1 identity, least-privilege Hook default, bilingual docs, manifest, changelog, tests, and generated project guidance.
2. Run `make check`, `make smoke`, diff checks, secret/path validation, and visual inspection.
3. Create the empty public GitHub repository and upload the verified snapshot as one root commit.
4. Verify the remote tree equals the local tree and wait for GitHub Actions to pass.
5. Run a remote marketplace install/setup smoke test and publish `v1.0.0`.
6. Clone the released repository into the user's Codex project directory.
7. Delete the predecessor GitHub repository only after every previous gate passes.

## Rollout, failure, and rollback

- Before publication, all changes remain local and reversible.
- If repository creation or object upload fails, delete the incomplete new repository or repair it before any predecessor deletion.
- If CI or remote install fails, keep the predecessor repository and do not publish the v1 release.
- Setup rollback restores the pre-install baseline only when managed values still match; `rollback --all` unwinds the full transaction chain while preserving unrelated config additions semantically.
- The irreversible point is deletion of the predecessor GitHub repository; user authorization is recorded, and the action occurs only after the new release is independently usable.

## Verification

- Repository and unit contracts: `make check`
- Isolated real-install contract: `make smoke`
- Patch hygiene: `git diff --check`
- Remote identity: compare the GitHub root commit tree SHA with the verified local tree SHA.
- Publication: GitHub Actions success, remote marketplace install, capability plan/apply/status/rollback smoke, tag and release inspection.
- Visual evidence: inspect the generated brand hero and render the icon, wordmarks, capability map, and architecture SVGs.

## Risks

- User configuration replacement: mitigated by plan-first setup, managed ownership, backups, hashes, atomic writes, and conflict refusal.
- Misleading subagent limits: mitigated by calling the Hook advisory and using the deterministic runner when exact order or count matters.
- Prompt bloat: mitigated by concise global policy, progressive-disclosure Skills, and evidence-only project guidance.
- Remote data loss: mitigated by publishing and verifying the clean v1 repository before deleting the predecessor.

## Decision log

- 2026-07-11 — Ship one complete system with five selectable capability levels rather than a seeder-only product.
- 2026-07-11 — Keep ordinary engineering single-agent by default; make delegation an atomic opt-in capability.
- 2026-07-11 — Use least-privilege Hook defaults: no managed component policy means no Hook execution.
- 2026-07-11 — Retain useful GEB ideas—hierarchical local context and feedback—but reject mandatory L2/L3 documentation and persona-heavy prompting.
- 2026-07-11 — Launch `rootloom` as a clean v1 repository with one root commit, then delete the predecessor repository after verification.
- 2026-07-11 — Name the product Rootloom: repository truth forms the roots; Codex mechanisms are woven into selectable capability layers.

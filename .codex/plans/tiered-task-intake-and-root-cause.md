# Tiered task intake and root-cause gates

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-12
- Risk: Tier 2 (Governed)

## Goal and observable success

Absorb the durable advantages of the standalone `ai-task-gatekeeper` into Rootloom's existing workflow layers without adding another always-on routing Skill. Rootloom must classify work as Direct, Scoped, or Governed; scale context and user-visible ceremony with risk; require evidence-backed root-cause alignment for behavioral fixes; and keep high-assurance delegation opt-in.

Success requires the public plugin, bilingual documentation, global policy, operating Skills, review contract, deterministic validator, and local installation to agree on one tier vocabulary. The standalone `~/.codex/skills/ai-task-gatekeeper` may be removed only after repository validation and a local Rootloom migration succeed.

## Non-goals

- Require a full task packet for trivial or ordinary scoped work.
- Add a new Gatekeeper Skill, Hook, MCP server, dependency, or always-on subagent.
- Expose internal reasoning or verbose planning by default.
- Turn every feature, documentation change, or mechanical edit into a root-cause investigation.
- Publish, push, tag, or release the change without separate authorization.

## Baseline evidence

- `plugins/rootloom/skills/operating-coding-change/SKILL.md` already requires reproduction or path tracing and a symptom-to-root-cause chain, but uses the separate R1/R2 vocabulary and has no explicit tiered entry gate.
- `plugins/rootloom/skills/operating-high-risk-change/SKILL.md` uses R3/R4 and has no shared Software 3.0 completeness contract.
- `plugins/rootloom/skills/operating-code-review/SKILL.md` checks behavior and tests but does not require a root-cause-alignment verdict.
- `plugins/rootloom/skills/high-assurance-coding-change/SKILL.md` has a real GO/NO_GO diagnosis gate but remains intentionally opt-in and is not installed by the `engineering` preset.
- The standalone `/Users/tangyuan/.codex/skills/ai-task-gatekeeper/SKILL.md` owns Direct/Scoped/Governed classification, progressive context, concise questioning, Software 3.0 completeness, and user-facing packet rules.
- The working tree was clean at task start.

## Constraints and invariants

- Keep Rootloom's existing seven public Skill names and five installation presets compatible.
- Use one public risk vocabulary: Tier 0 Direct, Tier 1 Scoped, Tier 2 Governed.
- Treat behavioral bugs as Tier 1 or higher unless the correction is demonstrably mechanical.
- Use task packets internally for Tier 0/1; expose a governed packet only for Tier 2, blockers, explicit handoffs, or user requests.
- A mitigation must never be reported as a root-cause fix.
- Hooks cannot enforce semantic diagnosis; deterministic proof belongs in tests, validation, CI, and the high-assurance runner.
- Preserve unrelated Codex configuration and user files during local migration.

## Impact map

- Producers: global policy template, ordinary coding/review/high-risk/high-assurance Skills, plugin manifest, validator, bilingual README and architecture docs.
- Consumers: all Rootloom users; existing automation invoking the same Skill names remains compatible.
- Persisted data: managed Rootloom files under `~/.codex`; the standalone local Skill directory is removed after successful migration.
- Public contracts: tier vocabulary, workflow routing, Skill behavior, manifest version and documentation.
- Generated artifacts: none.
- External systems: none in scope; GitHub publication is explicitly excluded.

## Design and decisions

- Ownership: task classification is a small stable policy in global guidance; detailed behavior remains in progressive-disclosure Skills.
- Interfaces: keep existing Skill names and presets; change their shared risk vocabulary and acceptance contracts.
- Dependency direction: global policy routes to Skills; Skills use repository truth; tests/CI provide proof; Hooks remain non-semantic.
- Compatibility window: existing prompts naming Skills continue to work; R1-R4 terminology is removed from active public workflow surfaces.
- Alternatives rejected: a new implicit Gatekeeper Skill would duplicate routing and increase prompt/tool contention; copying the standalone Skill wholesale would preserve generic sections Rootloom already owns elsewhere.

## Implementation sequence

1. Add concise tier and Software 3.0 intake rules to the managed global agreement.
2. Refactor operating Skills to Direct/Scoped/Governed and add tiered root-cause and mitigation gates.
3. Add root-cause-alignment review and high-assurance consistency requirements.
4. Update manifest/version, changelog, bilingual README/architecture documentation, and deterministic repository validation.
5. Run focused validation, full tests, smoke tests, and diff hygiene checks.
6. Migrate the local Rootloom marketplace/install and apply the existing `engineering` preset update.
7. Remove the standalone Gatekeeper Skill and verify Rootloom remains installed and complete.

## Rollout, failure, and rollback

- Dry-run/preview: inspect diffs and run `make validate` before any local installation change.
- Mixed-version behavior: do not remove the standalone Skill while the installed Rootloom plugin is still 1.0.1.
- Failure detection: validator/test/smoke failure, setup conflict, missing installed Skills, or stale global guidance blocks cleanup.
- Rollback or compensation: keep the standalone Skill until the new local plugin is verified; Rootloom setup provides transactional backup and rollback for managed global assets.
- Irreversible point: permanent deletion of the standalone Skill directory, explicitly authorized by the current request and delayed until verification.

## Verification

- Focused contracts: `python3 scripts/validate_repo.py`
- Unit and runner tests: `make check`
- Real isolated plugin/setup smoke: `make smoke`
- Patch hygiene: `git diff --check`
- Local migration: Rootloom setup `plan`, `apply`, and `status`; plugin list must show the new local version and no standalone Gatekeeper discovery path.
- Documentation: search active public surfaces for legacy R1-R4 terms and contradictory tier definitions.

## Risks

- Risk: classification bureaucracy on small work.
  - Mitigation: Tier 0 executes directly; Tier 0/1 packets remain internal by default.
  - Residual risk: models may still over-explain unless output rules remain explicit.
- Risk: two tier vocabularies survive.
  - Mitigation: validator rejects R1-R4 in active plugin workflow surfaces.
  - Residual risk: historical release plans may retain old terms as historical evidence.
- Risk: deleting the standalone Skill before absorption is active locally.
  - Mitigation: cleanup is the final step after local plugin and managed-policy verification.
  - Residual risk: a new Codex task is required to rediscover the changed plugin Skill set.

## Decision log

- 2026-07-12 — Classify this as Tier 2 because it changes Rootloom's public workflow and local installed behavior.
- 2026-07-12 — Integrate intake into existing policy and operating Skills rather than ship a second implicit Gatekeeper.
- 2026-07-12 — Make behavioral bugs Tier 1 minimum while keeping mechanical work Tier 0.
- 2026-07-12 — Keep governed work single-agent by default; high-assurance delegation remains explicit.
- 2026-07-12 — Repository validation, 34 unit tests, 10 runner tests, and isolated live plugin smoke passed before local migration.
- 2026-07-12 — Migrated the local `engineering` installation and local marketplace to Rootloom 1.1.0, then removed the superseded standalone Gatekeeper Skill.

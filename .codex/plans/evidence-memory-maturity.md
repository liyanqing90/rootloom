# Rootloom evidence, memory, and maturity hardening

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-12
- Task type: architecture and public workflow contract
- Risk: Tier 2 (Governed)

## Goal and observable success

Turn the external assessment's valid criticisms into a coherent Rootloom 1.2 release candidate: workflows carry attributable evidence, behavioral fixes derive verification from the violated invariant, durable engineering decisions have a repository-owned memory format, maturity claims distinguish mechanisms from outcomes, and CI detects upstream Codex drift.

Success is proven by repository contract validation, unit tests, the high-assurance runner test suite, link and workflow validation, and a clean diff review.

## Non-goals

- Build a universal observability MCP server or vendor-specific integration.
- Claim that schemas, agents, or process gates prove a diagnosis true.
- Make decision records mandatory for routine changes.
- Promise enterprise maturity, adoption, or measured quality improvement without evidence.
- Publish, release, or push changes.

## Baseline evidence

- The plugin already separates guidance, Skills, Agents, Hooks, Rules, and a deterministic runner.
- `plugins/rootloom/skills/high-assurance-coding-change/scripts/run_pipeline.py` validates structured stage output and stage mechanics, not factual correctness.
- Workflows require root-cause alignment but do not define a consistent provenance record for runtime or external evidence.
- `refine-project-guidance` can point to durable documents, but the plugin ships no decision-record workflow or template.
- `.github/workflows/ci.yml` exercises a pinned Codex CLI contract, but no scheduled latest-version compatibility probe exists.
- The repository is early-stage and single-maintainer; public outcome evidence is not yet established.

## Governed defect diagnosis

- Observed failure: project language can be read as an outcome guarantee, while important evidence, memory, and upstream-drift boundaries remain implicit.
- Competing hypotheses: documentation-only clarification; build a large MCP/memory platform; or add small repository-owned contracts and automated checks.
- Ownership path: public docs and manifest own claims; operating Skills and role instructions own evidence/verification discipline; CI and `scripts/validate_repo.py` own executable compatibility and repository contracts.
- Violated invariant: enforcement strength and evidence provenance must be explicit, portable facts must remain repository-owned, and public claims must not exceed observed proof.
- Root cause: the first release optimized installation and execution mechanics before defining maturity, provenance, and durable decision-memory contracts.
- Root-cause alignment: PASS

## Constraints and invariants

- Preserve the five capability presets and single-agent `engineering` default.
- Keep core runtime local and MCP-free; external evidence adapters remain narrow and optional.
- Keep structured-output gates, but explicitly distinguish shape/process validation from truth validation.
- Keep all new docs and public workflow changes bilingual where applicable.
- Pin baseline dependencies while probing latest upstream behavior separately.

## Impact map

- Producers: operating Skills, custom role instructions, decision-record Skill, CI.
- Consumers: Codex users, reviewers, high-assurance runner stages, maintainers.
- Persisted data: optional repository-owned decision Markdown records.
- Public contracts: plugin Skill inventory, workflow documentation, security response language, compatibility policy.
- Generated artifacts: none.
- External systems: GitHub Actions and npm registry in the scheduled compatibility probe.

## Design and decisions

- Evidence provenance is a lightweight record: source, environment, observed time/window, artifact/query/correlation reference, redaction/freshness, and fact-versus-inference status.
- Verification for a behavioral fix maps directly to the violated invariant: original failure path, owning-boundary invariant, and adjacent negative/edge path.
- Decision memory is an opt-in Skill and Markdown template, not an always-on database or MCP server.
- Maturity is documented qualitatively so fast-changing repository metrics are not hardcoded.
- Codex compatibility uses a pinned required baseline plus a non-blocking scheduled latest probe.

## Implementation sequence

1. Add the decision-record Skill and template.
2. Add evidence provenance, invariant-derived verification, and decision-memory routing to workflows and roles.
3. Add bilingual maturity documentation, compatibility policy, and honest security response targets.
4. Add a scheduled latest-Codex compatibility workflow and extend repository validation.
5. Update the manifest, READMEs, architecture, changelog, and version.
6. Run all repository checks and inspect the final diff.

## Rollout, failure, and rollback

- Dry-run/preview: repository validation and tests operate without installation or publication.
- Mixed-version behavior: 1.1 setup remains compatible; 1.2 adds a bundled Skill and documentation, not a new installed user-home artifact.
- Failure detection: `make check`, `make smoke`, `git diff --check`, and GitHub compatibility workflow.
- Rollback or compensation: revert the focused 1.2 diff before release.
- Irreversible point: none in this task.

## Verification

- Focused tests: `python3 scripts/validate_repo.py`
- Contract/migration tests: `python3 -m unittest discover -s tests -p 'test_*.py' -v`
- Runner tests: `python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py`
- Full gate: `make check`
- Live smoke: `make smoke`
- Diff hygiene: `git diff --check`

Observed results:

- `python3 scripts/validate_repo.py` — passed.
- `make check` — passed: 34 component/setup tests and 12 strict-runner tests.
- `make smoke` — passed in an isolated Codex home, including marketplace install, engineering/full setup transactions, role creation, commit-rule policy, SessionStart seeding, and rollback.
- Skill Creator `quick_validate.py` — new decision-record Skill passed.
- Ruby YAML parse — compatibility workflow parsed successfully.
- `git diff --check` — passed.
- Local migration — plugin cache and `engineering` setup report installed version 1.2.0; all managed targets match.

## Risks

- Risk: added ceremony for small projects.
  - Mitigation: decision records are optional and routine changes are explicitly excluded.
  - Residual risk: users still need to learn when a decision is durable.
- Risk: scheduled latest probe becomes noisy during upstream transitions.
  - Mitigation: keep the pinned baseline required and the latest probe informational.
  - Residual risk: upstream changes may still require rapid maintenance.
- Risk: provenance fields create false confidence.
  - Mitigation: docs state they improve auditability, not factual truth.
  - Residual risk: evidence can still be incomplete or misinterpreted.

## Decision log

- 2026-07-12 — Keep Rootloom Codex-specific and add portable repository-owned evidence/decision contracts instead of a generic platform abstraction.
- 2026-07-12 — Treat deterministic as a property of selected mechanics and stage order, never as a guarantee of diagnosis or outcome.

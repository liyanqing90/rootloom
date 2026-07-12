<!-- rootloom:managed-start version=1 fingerprint=e146cce65aa48c7e7f20 scope=. -->
# Project guidance for Rootloom

## Scope and sources of truth

- Project purpose: Rootloom lets a team install only the Codex capabilities it actually wants—without forcing every project to adopt subagents, Hooks, or a monolithic prompt (from `README.md`).
- Detected sources of truth: `CONTRIBUTING.md`, `CONTRIBUTING.zh-CN.md`, `README.md`, `README.zh-CN.md`, `docs/architecture.md`, `docs/architecture.zh-CN.md`, `Makefile`, `.github/workflows/ci.yml`.

## Repository map

- `docs/` — canonical project documentation.
- `scripts/` — project automation.
- `tests/` — test suites.

## Canonical commands

- `make validate` — detected from `Makefile target validate`.
- `make test` — detected from `Makefile target test`.
- `make check` — detected from `Makefile target check`.

## Verification contract

- Run the smallest detected command set that proves the changed behavior, then expand with blast radius.
- If a required command cannot run, report the exact gap and do not convert it into a passing claim.
- Keep generated guidance factual: project-only invariants belong below the managed block and must cite real paths.
<!-- rootloom:managed-end -->

<!-- Add durable project-only rules below this line. The seeder preserves content outside the managed block. -->

## Project-specific invariants

- `plugins/rootloom/` is the only installable plugin source; `.agents/plugins/marketplace.json` must continue to point to that exact directory.
- `plugins/rootloom/skills/seed-project-guidance/scripts/seed_project_guidance.py` owns automatic evidence collection and must remain deterministic, bounded, standard-library-only, and network-free.
- `plugins/rootloom/skills/refine-project-guidance/SKILL.md` owns semantic project-guidance judgment; do not move model-dependent inference into the `SessionStart` Hook or deterministic scanner.
- `plugins/rootloom/skills/record-engineering-decision/SKILL.md` owns portable decision memory; create records only for accepted durable choices and keep `AGENTS.md` references concise rather than duplicating rationale.
- `plugins/rootloom/skills/setup-rootloom/scripts/setup_rootloom.py` owns Codex-home writes and capability-to-artifact mapping; it must remain plan-first, dependency-closing, transactional, conflict-refusing, atomic, backed up, and hash-aware.
- `plugins/rootloom/hooks/run_component_hook.py` owns lifecycle-Hook enablement. Absent, malformed, or symlinked policy must fail closed; setup is the only supported way to enable a component.
- `plugins/rootloom/hooks/subagent_budget.py` is an advisory audit because `SubagentStart` cannot cancel children; documentation and messages must never present it as a hard cumulative agent limit.
- `plugins/rootloom/skills/high-assurance-coding-change/scripts/run_pipeline.py` owns the strict local stage graph; changes to its Git-state, path, structured-output, or repair-cycle gates require regression coverage in its bundled test module.
- Changes to installation, public behavior, safety gates, or user configuration must update both `README.md` and `README.zh-CN.md`.
- `scripts/validate_repo.py` is the repository contract gate. Extend it when adding public assets, workflows, or manifest fields instead of relying only on prose review.

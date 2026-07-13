<!-- rootloom:managed-start version=1 fingerprint=50ce962cc909f27dd01e scope=. -->
# Project guidance for Rootloom

## Scope and sources of truth

- Project purpose: Rootloom Personal Core keeps the part an individual developer uses every day (from `README.md`).
- Detected sources of truth: `CONTRIBUTING.md`, `CONTRIBUTING.zh-CN.md`, `README.md`, `README.zh-CN.md`, `docs/architecture.md`, `docs/architecture.zh-CN.md`, `Makefile`, `.github/workflows/ci.yml`, `.github/workflows/codex-compatibility.yml`.

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
- `plugins/rootloom/skills/seed-project-guidance/scripts/seed_project_guidance.py` owns automatic evidence collection and must remain deterministic, bounded, standard-library-only, network-free, repository-contained, lock-serialized, and snapshot-preserving.
- `plugins/rootloom/skills/refine-project-guidance/SKILL.md` owns semantic project-guidance judgment; do not move model-dependent inference into the `SessionStart` Hook or deterministic scanner.
- `plugins/rootloom/skills/record-engineering-decision/SKILL.md` owns portable decision memory; create records only for accepted durable choices and keep `AGENTS.md` references concise rather than duplicating rationale.
- `plugins/rootloom/skills/setup-rootloom/scripts/setup_rootloom.py` owns Personal Core Codex-home writes and capability-to-artifact mapping; it must remain plan-first, ordinary-lock-serialized, mode-preserving on rollback, conflict-refusing, atomic per file, backed up, and hash-aware without claiming whole-transaction crash recovery.
- `plugins/rootloom/hooks/run_component_hook.py` owns lifecycle-Hook enablement. Absent, malformed, or symlinked policy must fail closed; setup is the only supported way to enable a component.
- `plugins/rootloom/skills/engineering-change/scripts/finalize_change.py` owns the lightweight personal review bundle; changes to changed-path capture, dangerous-deletion confirmation, command execution, output bounds, or summary format require focused regression coverage.
- `plugins/rootloom/skills/engineering-change/scripts/runner/intelligence.py` owns advisory risk floors and verification planning; it must remain local, explainable, bounded, standard-library-only, subordinate to semantic evidence, and unable to auto-execute suggestions. See `docs/decisions/2026-07-14-personal-intelligence-contract.md`.
- `plugins/rootloom/skills/project-memory/scripts/project_memory.py` owns optional `.project-memory/` formats; updates must remain explicit, reviewable, standard-library-only, and subordinate to current repository evidence. Keep its advisory/relevance boundary aligned with `docs/decisions/2026-07-14-personal-intelligence-contract.md`.
- The complete pre-split Assurance 1.2.19 product is retained on `codex/enterprise-assurance`; do not reintroduce its approval, audit, strict-runner, or recovery machinery into the `main` plugin by default.
- Changes to installation, public behavior, safety gates, or user configuration must update both `README.md` and `README.zh-CN.md`.
- `scripts/validate_repo.py` is the repository contract gate. Extend it when adding public assets, workflows, or manifest fields instead of relying only on prose review.

---
name: seed-project-guidance
description: Explicitly create, refresh, and validate a concise evidence-backed AGENTS.md managed block for a Git repository or a genuine nested module boundary. Use only when the user asks to persist project guidance. The SessionStart Hook provides temporary read-only context and never invokes this writer. Preserve unmarked existing guidance and route semantic polishing to refine-project-guidance.
---

# Seed Project Guidance

Build a useful project map from repository evidence while keeping code, tests, schemas, and manifests as the executable source of truth. Do not mirror every file or add mandatory file-header contracts.

## Invariants

- Never overwrite an existing `AGENTS.md` that lacks the seeder-managed markers.
- Never modify `AGENTS.override.md`, symlinked guidance, untrusted projects, temporary paths, vendor/cache trees, or projects with `.codex/disable-project-guidance-seeding`.
- Never read evidence through a symlink or from a resolved path outside the selected repository scope.
- Keep the generated block deterministic. Route semantic notes outside the managed block to `$refine-project-guidance`.
- Do not add personality text, generic engineering advice, private-reasoning instructions, file inventories, speculative architecture, or L3 comments.
- Stay single-agent. This workflow does not justify delegation.

## 1. Probe and seed the repository root

Resolve this Skill directory, then run:

```bash
python3 <skill-dir>/scripts/seed_project_guidance.py probe --cwd "$PWD"
python3 <skill-dir>/scripts/seed_project_guidance.py seed --cwd "$PWD"
```

The script derives only observable facts from manifests, lockfiles, package scripts, Make/Just targets, canonical docs, CI files, and bounded module discovery. It serializes Rootloom writers through the Git common directory, verifies that `AGENTS.md` still matches its initial snapshot, writes atomically, and updates only its managed block. A concurrent edit causes a safe skip instead of an overwrite.

If the result is `user_owned_guidance`, `override_exists`, `untrusted_project`, `disabled`, or another skip reason, respect it. Do not bypass the gate unless the user explicitly asks to seed that exact project and the project has been reviewed as safe.

## 2. Hand off semantic refinement

For a non-trivial first task, invoke `$refine-project-guidance` when the generated facts are insufficient. That workflow may read the smallest relevant set of:

- the generated `AGENTS.md`;
- the nearest README or product document;
- manifests and CI named by the managed block;
- the task's source entry point and nearest tests.

Do not add semantic prose inside this workflow. Keeping deterministic collection and model judgment separate makes refreshes auditable and avoids rewriting user-owned guidance.

## 3. Seed nested guidance lazily

Use `module_candidates` from the probe. Create nested guidance only when the current work enters a module that has its own manifest and materially different commands, architecture, or invariants.

```bash
python3 <skill-dir>/scripts/seed_project_guidance.py seed \
  --cwd "$PWD" \
  --target path/to/module
```

Create at most three nested guidance files in one repository pass and never go deeper than three directories from the Git root. Do not seed every candidate preemptively.

## 4. Validate before continuing

Run validation for every created or refreshed file:

```bash
python3 <skill-dir>/scripts/seed_project_guidance.py validate \
  --file path/to/AGENTS.md
```

Validation must pass before treating the guidance as complete. It checks size, managed-block drift, placeholders, symlinks, and secret-like content.

## Completion

Continue the user's original task after seeding. Mention project-guidance creation only when it changed the working tree or when a gate prevented seeding. Do not make the seeding process the main deliverable unless the user asked about it.

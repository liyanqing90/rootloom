---
name: setup-rootloom
description: Plan, install, inspect, update, or roll back Rootloom Personal Core in a user's Codex home. Supports Skills-only, guidance, and the recommended personal preset. Use when the user explicitly asks to install, configure, bootstrap, repair, audit, update, reduce, or remove Rootloom. Never overwrite user-owned files without showing the plan and obtaining exact replacement authorization.
---

# Set up Rootloom Personal Core

Resolve this Skill directory and use its deterministic setup script.

## Choose a preset

```bash
python3 <skill-dir>/scripts/setup_rootloom.py list-components
```

| Preset | Result |
| --- | --- |
| `skills-only` | Plugin Skills only; the project-guidance Hook is disabled |
| `guidance` | Global working agreement plus project-guidance Hook |
| `personal` | Guidance plus command safety; recommended and default |
| `engineering` | Compatibility alias for `personal` |

Exact capabilities are `global-policy`, `project-context`, and `command-safety`.

## Inspect, then apply

```bash
python3 <skill-dir>/scripts/setup_rootloom.py plan --preset personal
python3 <skill-dir>/scripts/setup_rootloom.py apply --preset personal
python3 <skill-dir>/scripts/setup_rootloom.py status
```

The personal preset manages only:

- `~/.codex/AGENTS.md`;
- `~/.codex/rules/rootloom.rules`;
- `~/.codex/.rootloom/components.json`;
- `~/.codex/.rootloom/state.json` and a simple backup manifest.

Setup is serialized by an ordinary local lock, refuses symlinked or user-owned targets, backs up every replaced file before mutation, writes each file atomically, and preserves original content and mode for rollback. It does not claim whole-transaction crash compensation or hostile shared-filesystem locking.

If the plan contains `conflict`, show the exact paths. Use `--replace-conflicts` only after the user authorizes those replacements. A backup does not replace authorization.

## Verify command safety

When `command-safety` is selected, run `codex execpolicy check` for at least:

- `git commit` → allow;
- `git push` → prompt;
- `git reset --hard` → forbidden.

Start a new Codex task after setup or plugin update so assets and Hooks are rediscovered.

## Roll back or change preset

```bash
python3 <skill-dir>/scripts/setup_rootloom.py rollback
```

Rollback first validates that managed files still match the installed hashes. It refuses to overwrite post-setup edits, then restores the backed-up content and mode or removes files created by setup. A normal rollback returns to the previous simple backup; `rollback --all` follows the available backup chain to the pre-install state.

To change presets, roll back, plan the new selection, and apply it. Enterprise Assurance 1.2.19 uses a different branch and installation contract; roll it back with that version before installing Personal Core.

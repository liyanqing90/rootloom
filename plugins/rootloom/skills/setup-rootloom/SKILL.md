---
name: setup-rootloom
description: Plan, install, inspect, update, or roll back Rootloom's selectable capability layers in a user's Codex home. Supports Skills-only, guidance, ordinary engineering, controlled delegation, and full high-assurance presets plus exact capability selection. Use when the user explicitly asks to install, configure, bootstrap, repair, audit, update, reduce, or remove this system. Never overwrite user-owned files without showing the plan and obtaining explicit replacement authorization.
---

# Set up Rootloom

Resolve this Skill directory and use its deterministic setup script. Do not recreate the files manually.

## 1. Choose a capability layer, not a file pile

Run:

```bash
python3 <skill-dir>/scripts/setup_rootloom.py list-components
```

Use one of these valid presets:

| Preset | Capability result |
| --- | --- |
| `skills-only` | Plugin Skills remain available; no global assets; both lifecycle Hooks disabled |
| `guidance` | Global working agreement plus automatic project-context guidance |
| `engineering` | Guidance plus command safety; recommended for normal single-agent coding |
| `delegated` | Engineering plus the atomic four-role Agent set, limits, and subagent audit |
| `full` | Delegated plus the quality-first profile and deterministic high-assurance route |

The user may instead select exact capability dimensions with `--capabilities`:

- `global-policy`
- `project-context`
- `command-safety`
- `delegation-control`
- `high-assurance` (automatically includes `delegation-control`)

Do not split `delegation-control` into individual Agent files. Its four roles, runtime limits, and audit Hook form one valid control boundary.

## 2. Inspect first

Run:

```bash
python3 <skill-dir>/scripts/setup_rootloom.py plan --preset engineering
```

Use `--preset full` when the user asks for the complete system. Explain every `CONFLICT`. The complete mapping is:

- `~/.codex/AGENTS.md` — stable global working agreement;
- `~/.codex/config.toml` — only `[agents]` limits (`max_threads = 4`, `max_depth = 1`, interruption visibility);
- `~/.codex/high-assurance.config.toml` — quality-first CLI profile;
- `~/.codex/agents/*.toml` — evidence, diagnosis, implementation, and verification roles;
- `~/.codex/rules/rootloom.rules` — local commit allowed, destructive and remote actions separated.
- `~/.codex/.rootloom/components.json` — managed Hook enablement and selected capability record.

The script preserves unrelated `config.toml` keys. It refuses symlinks and unmanaged files, except when an existing file exactly matches the managed template before ownership markers. Apply and rollback hold one non-blocking lock per Codex home; a competing transaction stops before mutation.

## 3. Apply only with authority

An explicit request to install or configure this system authorizes the conflict-free apply:

```bash
python3 <skill-dir>/scripts/setup_rootloom.py apply --preset engineering
```

Apply the same preset or exact capability set that was reviewed in the plan. Changing an installed capability selection requires `rollback --all` first; do not silently leave assets from the previous layer behind.

The transaction prepares backups and its manifest before mutation. If target or state commit fails, it restores the prior files, state, and file modes before reporting failure.

If the plan contains user-owned conflicts, do not use `--replace-conflicts` until the user has seen the exact affected paths and explicitly authorizes replacement. Every replacement is backed up, but backup is not a substitute for authorization.

Do not change the user's default model, reasoning effort, sandbox, approval policy, MCP servers, plugins, or apps. The profile carries high-assurance defaults without changing ordinary sessions.

## 4. Verify

Run:

```bash
python3 <skill-dir>/scripts/setup_rootloom.py status
```

When `command-safety` is selected, use `codex execpolicy check` against the installed Rules for at least `git commit`, `git push`, and `git reset --hard`.

When `delegation-control` is selected, verify that status lists `agent-limits`, `custom-agents`, and `subagent-audit-hook`, and state clearly that `agents.max_threads` is a concurrent open-thread cap while the cumulative four-child budget is advisory.

When `high-assurance` is selected, also run:

```bash
python3 <plugin-root>/skills/high-assurance-coding-change/scripts/validate_setup.py
```

For `skills-only`, `guidance`, or `engineering`, do not report missing custom agents or a missing profile as failures; those assets were intentionally not selected.

Start a new Codex task after setup or plugin update so global guidance, Skills, Agents, Rules, and Hooks are rediscovered.

## 5. Roll back or change layers

When the user asks to undo the most recent setup transaction, preview status and run:

```bash
python3 <skill-dir>/scripts/setup_rootloom.py rollback
```

Rollback refuses to overwrite managed files changed after setup. For `config.toml`, it restores only the three setup-owned `[agents]` keys and preserves unrelated settings that Codex or the user added later; it still stops if one of those managed keys changed. Exact file restoration also restores the recorded pre-setup mode. Resolve real conflicts manually with the user instead of forcing them.

To change from one installed preset/capability set to another, run `rollback --all`, plan the new selection, then apply it. A normal rollback restores only the latest update; `--all` follows the safe transaction chain to the original pre-install baseline and avoids ambiguous partial removal.

If the user wants to keep the plugin's Skills but disable all active global behavior, apply `skills-only` after `rollback --all`. If the user explicitly wants to uninstall the whole plugin, complete the global rollback and then remove `rootloom@rootloom`; plugin removal is separate from setup rollback.

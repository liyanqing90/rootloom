# Setup, update, and rollback

Installing the plugin exposes Skills and the reviewed `SessionStart` Hook definition. It does not install global policy, enable the Hook, or trigger engineering review tools. Applying global Personal Core assets is a separate optional operation.

## Install

```bash
codex plugin marketplace add liyanqing90/rootloom
codex plugin add rootloom@rootloom
```

Start a new task and inspect `/hooks`. The only Hook is local project-guidance seeding. It does nothing until a valid managed component policy enables it.

The plugin is fully usable at this point. No setup command, analyzer, baseline, contract, finalizer, or project-memory lookup is required.

## Presets

| Preset | Capabilities |
| --- | --- |
| `skills-only` | Skills only; Hook disabled |
| `guidance` | `global-policy`, `project-context` |
| `personal` | Guidance plus `command-safety`; default |
| `engineering` | Compatibility alias for `personal` |

The empty capability selection used by `skills-only` is persisted as an intentional installed state. `status`, `plan`, and compatibility `apply` without a new explicit selection preserve it.

Only when the user explicitly wants a cross-project global layer, inspect and install:

```bash
python3 <setup-skill>/scripts/setup_rootloom.py list-components
python3 <setup-skill>/scripts/setup_rootloom.py plan --preset personal
python3 <setup-skill>/scripts/setup_rootloom.py install --preset personal
python3 <setup-skill>/scripts/setup_rootloom.py status
```

`install` refuses an already installed setup. `apply` remains available for compatibility and expert use, but explicit `install`/`upgrade` makes lifecycle and rollback intent visible.

Exact capability selection is also available:

```bash
python3 <setup-skill>/scripts/setup_rootloom.py plan \
  --capabilities global-policy,project-context,command-safety
```

## Managed targets

| Path | Purpose |
| --- | --- |
| `~/.codex/AGENTS.md` | Personal engineering working agreement |
| `~/.codex/rules/rootloom.rules` | Command safety policy |
| `~/.codex/.rootloom/components.json` | Hook enablement |
| `~/.codex/.rootloom/state.json` | Installed selection and target hashes |
| `~/.codex/.rootloom/backups/` | Pre-mutation file copies and manifest |

Rootloom does not modify ordinary model, reasoning, sandbox, approval, provider, MCP, plugin, or app configuration.

## Safety contract

Setup:

- shows a plan before the Skill applies it;
- uses an ordinary create-exclusive local lock;
- refuses symlinked targets and unmarked user-owned conflicts;
- requires exact authorization before `--replace-conflicts`;
- copies every replaced file before the first managed target write;
- writes each target atomically;
- records post-apply hashes for drift detection;
- refuses upgrade when a managed target no longer matches its installed hash, even when `--replace-conflicts` is present;
- restores original content and POSIX mode during rollback.

This personal contract does not promise whole-transaction crash compensation. If the process stops between file replacements, run `status`, inspect `.rootloom/backups/`, and reconcile the visible mismatch. It also does not defend against a hostile same-user process replacing lock or target paths concurrently.

## Command Rules check

```bash
codex execpolicy check --pretty --rules ~/.codex/rules/rootloom.rules -- git commit -m test
codex execpolicy check --pretty --rules ~/.codex/rules/rootloom.rules -- git push origin main
codex execpolicy check --pretty --rules ~/.codex/rules/rootloom.rules -- git reset --hard
```

Expected decisions are `allow`, `prompt`, and `forbidden`. Rules are argv-prefix policy, not a complete shell security boundary.

## Change preset or roll back

Changing capability selection requires rollback first:

```bash
python3 <setup-skill>/scripts/setup_rootloom.py rollback
python3 <setup-skill>/scripts/setup_rootloom.py plan --preset guidance
python3 <setup-skill>/scripts/setup_rootloom.py install --preset guidance
```

Rollback preflights every managed file. If a target changed after setup, it stops rather than overwriting the edit. A normal rollback returns to the previous simple backup; `rollback --all` follows that backup chain to the pre-install state.

To remove plugin Skills after global rollback:

```bash
codex plugin remove rootloom@rootloom
```

## Update

```bash
codex plugin marketplace upgrade rootloom
codex plugin add rootloom@rootloom
```

Codex owns the marketplace snapshot and plugin package update. Start a new task so the refreshed Skills are loaded. The normal upgrade is complete and does not trigger any Rootloom review gate.

If an optional global preset was previously installed and its copied assets should also be refreshed, run one explicit command:

```bash
python3 <setup-skill>/scripts/setup_rootloom.py upgrade
```

Optional setup `upgrade` always preserves the installed capability selection. It reports `up_to_date` when the current plugin and assets already match. If only the plugin version changed, it updates setup state without creating a redundant asset backup; if managed content changed, it creates the normal backup before writing. A managed target retired by the new catalog is removed only when it still matches its installed hash, and it is backed up so rollback restores it. Installed state paths are normalized and checked before access. `status` reports `installed_version`, `upgrade_available`, and `drifted_paths`. Drift is never overwritten by upgrade: restore the expected content or roll back first. `--replace-conflicts` is reserved for a newly introduced user-owned target after exact authorization.

## Migrate from Enterprise Assurance 1.2.19

The setup contracts are intentionally incompatible. Use the 1.2.19 code on `codex/enterprise-assurance` to roll back its setup before installing Personal Core. Do not ask the Personal Core setup to infer or remove custom agents, the high-assurance profile, configuration limits, Human Review state, or recovery journals.

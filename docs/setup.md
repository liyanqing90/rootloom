# Setup, update, and rollback

Installing the plugin exposes Skills and reviewed lifecycle Hooks. Applying the global engineering baseline is a separate explicit operation so a plugin update cannot silently replace personal policy.

## Install the plugin

```bash
codex plugin marketplace add liyanqing90/rootloom
codex plugin add rootloom@rootloom
```

Start a new task, open `/hooks`, and review both bundled commands:

- `SessionStart` runs the local project-guidance scanner.
- `SubagentStart` records an advisory cumulative child count and audits named role/model routing.

Plugin Hooks do not run until their current definition is trusted.

An absent component policy disables both bundled Hooks. Choose and apply a capability preset before trusting the Hook definition. Once setup writes `components.json`, each Hook follows its explicit boolean; malformed or symlinked policy also fails closed and emits a warning.

## Choose a capability level

The installer exposes stable capability layers instead of asking users to understand individual files:

| Preset | Capabilities | Subagent control |
| --- | --- | --- |
| `skills-only` | Bundled Skills only; no global assets; lifecycle Hooks disabled | No |
| `guidance` | Global policy + automatic project context | No |
| `engineering` | Guidance + command safety | No; recommended for normal coding |
| `delegated` | Engineering + four-role configuration and advisory audit | Configured; native routing not attested |
| `full` | Delegated + strict sequential-runner profile | Configured; runner provides attested routing |

`delegation-control` is deliberately one unit: four role TOMLs, the concurrent/depth limits, and the advisory audit Hook. Installing only one role or only the counter would create a misleading half-control, so the supported installer does not expose those files as separate user-facing levels.

Inspect the catalog:

```bash
python3 <skill-dir>/scripts/setup_rootloom.py list-components
```

The default remains `full` for an explicit “install the complete system” request. The recommended normal-development preset is `engineering`, which does not install subagent control.

## Install a level without hand-editing files

Invoke:

```text
$setup-rootloom
Show the capability levels, then plan and apply the engineering preset.
```

The Skill resolves its own script. For diagnostics, the equivalent direct commands are:

```bash
python3 <skill-dir>/scripts/setup_rootloom.py plan --preset engineering
python3 <skill-dir>/scripts/setup_rootloom.py apply --preset engineering
python3 <skill-dir>/scripts/setup_rootloom.py status
```

For the entire system, replace `engineering` with `full`. For a custom capability combination:

```bash
python3 <skill-dir>/scripts/setup_rootloom.py plan \
  --capabilities global-policy,project-context,command-safety
```

Available dimensions are `global-policy`, `project-context`, `command-safety`, `delegation-control`, and `high-assurance`. Selecting `high-assurance` automatically closes its `delegation-control` dependency.

The setup transaction writes only:

| Target | Ownership |
| --- | --- |
| `~/.codex/AGENTS.md` | Complete managed global working agreement |
| `~/.codex/config.toml` | Only the three `[agents]` limit keys; every other key is preserved |
| `~/.codex/high-assurance.config.toml` | Managed quality-first profile |
| `~/.codex/agents/*.toml` | Four managed custom-agent roles |
| `~/.codex/rules/rootloom.rules` | Managed command policy |
| `~/.codex/.rootloom/components.json` | Selected capability record and independent Hook enablement |
| `~/.codex/.rootloom/` | Private state and rollback backups |

It does not change the default model, reasoning effort, approval policy, sandbox, providers, MCP servers, plugins, or apps.

Setup and rollback take a non-blocking cross-process lock under `~/.codex/.rootloom/`; a competing operation fails without touching managed targets. Apply prepares all backups and the transaction manifest before its first target mutation. Apply target writes, rollback target writes, and their final state commits each share a compensation boundary, so a failure restores the previous files and state. Manifests record original file modes, and rollback restores those modes instead of inheriting a temporary-file default.

This compensation covers failures that return control to Python; it is not a crash-consistent transaction. `SIGKILL`, host failure, power loss, and parent-directory durability can interrupt between target replacement and state commit, and there is no automatic orphan-transaction recovery command yet. Inspect managed state and backups before retrying after an abrupt termination.

## Conflicts

The default apply is atomic and refuses:

- user-owned files without the system's managed marker;
- managed files edited since the previous apply;
- symlink targets;
- invalid `config.toml`;
- any plan containing an unresolved conflict.

An unmarked file that exactly matches the template is adopted safely by adding ownership markers. `--replace-conflicts` exists only for an explicitly reviewed replacement request; the Skill must show the affected paths before using it.

## Command policy

When `command-safety` is selected, the installed Rules intentionally separate local history from publication:

- `git commit` → `allow`;
- `git push` and release/package publication → `prompt`;
- destructive reset/forced clean/bulk discard → `forbidden` or `prompt`, depending on recoverability.

Rules use the most restrictive matching decision. A separate broad `git` prompt rule will therefore override the narrower allow. Inspect every active `.rules` file when commits still ask for approval. In a non-interactive run with `approval_policy = "never"`, a `prompt` action cannot be approved and fails; use an allow rule for safe local operations or an interactive profile for genuinely approval-gated actions.

Rules match command argv prefixes, not the contents of nested shell strings. For example, `bash -c 'git push'` is governed first as `bash`, not as a direct `git push`; it can fall through to a broader policy. Treat Rules as defense in depth, not a shell security boundary, and keep dangerous external effects behind sandbox, credentials, branch protection, CI, and human authorization.

Verify the installed policy:

```bash
codex execpolicy check --pretty --rules ~/.codex/rules/rootloom.rules -- git commit -m test
codex execpolicy check --pretty --rules ~/.codex/rules/rootloom.rules -- git push origin main
codex execpolicy check --pretty --rules ~/.codex/rules/rootloom.rules -- git reset --hard
```

## Subagent limits

When `delegation-control` is selected, `agents.max_threads = 4` is a hard cap on concurrently open agent threads. It is not a lifetime count, so a task may close four children and later create more.

The `SubagentStart` Hook keeps an advisory cumulative count per parent session only when `delegation-control` is selected. After four unique children it injects a stop-and-report instruction, but the current Hook API cannot cancel the child. The global working agreement and controlled Skills provide the behavioral total limit. Use the deterministic high-assurance runner when stage order and agent count must be enforced by code.

The strict high-assurance runner supports Linux, macOS, and WSL, not native Windows. Setup and project seeding have separate Windows code paths, but current public CI validates Linux only.

## Update

```bash
codex plugin marketplace upgrade rootloom
codex plugin add rootloom@rootloom
```

Review the changed Hook definition, start a new task, then run `$setup-rootloom` again. The plan will show only changed managed assets.

Changing from one installed capability set to another is intentionally two-step: run `rollback --all`, then plan and apply the new preset. A normal rollback restores the latest update; `--all` follows the transaction chain to the original pre-install baseline instead of guessing whether deselected files should be deleted or preserved.

## Roll back

```bash
python3 <skill-dir>/scripts/setup_rootloom.py rollback
```

Use `rollback --all` when removing the global setup or changing capability levels. Applying `skills-only` afterward keeps the workflow Skills while installing a policy that disables both Hooks. To remove Skills and Hook definitions too, then run:

```bash
codex plugin remove rootloom@rootloom
```

Rollback requires each fully managed file to retain its recorded post-apply hash. `config.toml` is handled semantically: the installer verifies that its three managed `[agents]` values are intact, restores their previous values, and preserves unrelated settings added later—including Codex project-trust entries. Restored files recover their recorded pre-apply mode. If a managed file or managed config value changed, rollback stops instead of deleting that work.

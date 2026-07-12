# Troubleshooting

## The plugin is installed but no hook runs

1. Start a new Codex task; plugins and hooks are loaded at task startup.
2. Run `/hooks` and inspect the `SessionStart` entry.
3. Trust the exact command if Codex reports that review is required.
4. Confirm the plugin is enabled:

   ```bash
   codex plugin list --json
   ```

Do not use `--dangerously-bypass-hook-trust` for normal operation.

## No `AGENTS.md` was created

Probe the repository directly:

```bash
python3 plugins/rootloom/skills/seed-project-guidance/scripts/seed_project_guidance.py \
  probe --cwd /path/to/repository
```

Common skip reasons are intentional:

- `not_a_git_repository`
- `untrusted_project`
- `override_exists`
- `user_owned_guidance`
- `disabled`
- `guidance_is_symlink`
- `unsafe_path`
- `plan_mode`

## The repository is trusted but reports `untrusted_project`

Use `/debug-config` to confirm which Codex configuration layer is active and whether the repository or a parent root has `trust_level = "trusted"`. Do not add a broad trust root merely to make the hook pass; review the repository first.

## My existing `AGENTS.md` was not updated

This is expected when the file lacks seeder markers. Unmarked guidance is user-owned. The plugin will not adopt or rewrite it. If you want a managed baseline, move the existing content aside, run the seeder once, then place your custom rules below the managed block.

## Validation reports `managed_block_drift`

The managed section was edited manually or no longer matches repository evidence. Keep custom content outside the markers and run `seed` again to regenerate the managed block.

## Validation reports secret-like content

Remove credentials, tokens, private keys, or secret-looking examples from guidance. Store secrets in the repository's approved secret manager or environment, never in `AGENTS.md`.

## The hook works in normal mode but not Plan mode

This is by design. Plan mode is read-only for automatic seeding. Run the Skill after returning to a write-capable mode.

## Nested guidance is not created

Nested seeding is lazy. The target must be inside the Git root, no more than three directories deep, and have an independent recognized manifest. Ordinary folders do not receive their own `AGENTS.md`.

## Setup reports a user-owned conflict

Run `$setup-rootloom` in plan mode and inspect the exact paths. The installer refuses unmanaged files and managed files edited after the last apply. Prefer merging useful personal policy into the managed template through a reviewed change. Use `--replace-conflicts` only after explicitly authorizing those paths; the installer creates backups but will replace their contents.

## I do not need subagents

Install `--preset engineering`, not `delegated` or `full`. It keeps global/project guidance and command safety but does not write `[agents]` limits, custom Agent TOMLs, the quality profile, or active subagent auditing. `skills-only` and `guidance` are even smaller. Use `list-components` to inspect the exact mapping.

If another preset is already installed, run `rollback --all` before applying the smaller level. The installer refuses an in-place capability switch so omitted assets cannot become ambiguous leftovers.

## `git commit` is rejected under `approval_policy = "never"`

Check every active Rules file, not only the suite file. Rules choose the most restrictive match, so a broad `git → prompt` rule overrides `git commit → allow`. A non-interactive `never` policy cannot answer the prompt and the command fails.

```bash
codex execpolicy check --pretty \
  --rules ~/.codex/rules/rootloom.rules \
  -- git commit -m test
```

The suite result should be `allow`. If combined policy still prompts, remove or narrow the conflicting rule after reviewing why it exists. Do not change `git push` to allow merely to fix local commits.

## `max_threads = 4` but the task shows ten agents

`max_threads` caps concurrently open threads, not the cumulative total. Completed/closed children free slots. The advisory Hook counts unique children for the parent session and warns after four, but `SubagentStart` cannot cancel a child. Use the deterministic runner when a hard stage count is required.

## A custom Agent appears to use the wrong model

First confirm that `delegation-control` or `full` was intentionally selected. Then confirm the custom role file exists under `~/.codex/agents/`, start a new task, and run the setup status and high-assurance validator. A thread label or nickname is not proof that the role TOML was selected. If the current spawn surface cannot explicitly select and attest the role, use the deterministic runner instead of relying on natural-language routing.

## High-assurance validation says native routing is not ready

This can be the correct result. The runner and native route have separate readiness. If Agent files and the profile pass but the local spawn tool cannot attest `agent_type`, the deterministic sequential runner remains supported while native model routing stays disabled.

## The strict runner exits 10 with `HUMAN_REVIEW_REQUIRED`

This is the intended result after an explicitly authorized `--allow-protected-path-delete` operation. The authorization is checked before the writer runs and makes the run deletion-only, so ordinary edits, renames, moves, and visible file creations must be handled separately. Verification and model review passed, but the old protected content was deliberately never read, so the Runner cannot issue automated PASS. A human must confirm the exact deletion and decide whether to accept the working-tree change. Do not convert exit 10 to success in automation.

If the Runner instead reports an unauthorized protected-path change, acceptance stopped after the writer returned; the sandbox did not prevent the filesystem mutation. Inspect and recover that path manually. Rootloom does not read or back up ignored/sensitive content for automatic rollback.

## Python reports that `tomllib` is missing

Use Python 3.11 or newer:

```bash
python3 --version
```

## Updating the plugin

```bash
codex plugin marketplace upgrade rootloom
codex plugin add rootloom@rootloom
```

Then start a new Codex task. If the hook definition changed, review and trust the new definition through `/hooks`.

Run `$setup-rootloom` again after upgrading so new managed global assets are planned and applied. Plugin installation alone never overwrites Codex-home policy files.

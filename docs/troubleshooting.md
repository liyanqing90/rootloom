# Troubleshooting

## The project-guidance Hook does nothing

Check that the personal or guidance preset is installed and that `~/.codex/.rootloom/components.json` contains a managed boolean `project-guidance-hook: true`. Missing, malformed, or symlinked policy disables the Hook. Start a new Codex task after plugin or setup changes and review `/hooks` again.

The scanner also skips untrusted repositories unless the platform marks them trusted. `ROOTLOOM_ALLOW_UNTRUSTED=1` is intended only for controlled tests.

## Setup reports a conflict

Run `plan` and inspect every affected path. Unmarked content is user-owned. Use `--replace-conflicts` only after exact authorization; Rootloom will create a backup first.

Symlinked targets are always refused. Move or resolve the symlink explicitly rather than asking setup to follow it.

## Setup stopped partway through

Personal Core has per-file atomic writes and pre-mutation backups, not a recovery journal. Run:

```bash
python3 <setup-skill>/scripts/setup_rootloom.py status
```

Inspect the newest `~/.codex/.rootloom/backups/*/manifest.json`, compare target hashes, and restore only the affected paths. Do not re-run with conflict replacement until the partial state is understood.

## Rollback refuses a changed file

Rollback protects post-setup edits. Preserve or merge the current file manually, restore it to the recorded managed version, then run rollback again. Do not delete the state or backup merely to bypass the check.

## Commands still prompt unexpectedly

Use `codex execpolicy check` against every active Rules file. The most restrictive matching decision wins, so a broader `git` prompt may override Rootloom's local `git commit` allow. Rules inspect argv prefixes; nested shell commands need their own policy and approval boundary.

## Verification helper rejects a command

`finalize_change.py` parses commands with platform-aware `shlex` rules and does not run a shell. Windows parsing preserves backslash paths and removes matching outer quotes from arguments; quote an executable path when it contains spaces. Pipelines, redirects, `&&`, environment assignment, or command substitution are not interpreted. Put complex verification in a reviewed repository-owned script or Make target and invoke that executable directly.

Exit 124 is timeout. Exit 125 means the bounded output tail was exceeded. Increase budgets only when the larger evidence is necessary and safe to retain.

## Sensitive deletion returns exit 10

The helper detected an exact `.env`, secret, migration, or database path deletion. Obtain confirmation for that exact path and repeat it with `--confirm-dangerous-delete`. This is a lightweight guard, not an approval ledger.

## Project memory is stale or malformed

Repository evidence wins. Correct the `.project-memory/` file in a reviewed change. The helper refuses unknown formats or non-list `entries`; it never silently migrates ambiguous content.

## I need the old Human Review or strict Runner

Those features are not hidden flags in Personal Core. Use `codex/enterprise-assurance`, which preserves Rootloom 1.2.19. Roll back one product's setup with its own version before installing the other.

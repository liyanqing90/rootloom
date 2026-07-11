# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| Latest release | Yes |
| Older releases | Best effort |

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's private vulnerability reporting flow:

1. Open the repository's **Security** tab.
2. Choose **Report a vulnerability**.
3. Include affected versions, reproduction steps, impact, and a suggested mitigation if available.

Do not include real credentials, proprietary repository content, or personal data. Use synthetic fixtures wherever possible.

You should receive an acknowledgement within 7 days and an initial assessment within 14 days. Timelines may vary for reports that depend on Codex platform behavior outside this repository.

## Security boundaries

The automatic project-guidance path:

- reads bounded local repository metadata;
- writes only `AGENTS.md` through an atomic replacement path;
- does not execute repository-provided commands during scanning;
- does not access the network;
- refuses untrusted repositories, symlink targets, overrides, unsafe paths, and secret-like output.

The explicit global setup path:

- previews all targets before writing;
- maps coherent capability selections to documented Codex-home files and at most three `[agents]` config keys;
- gates the two lifecycle Hooks independently through a managed, fail-closed component policy;
- refuses unmanaged conflicts and symlinks;
- backs up replacements and records pre/post hashes;
- writes atomically, refuses rollback over later managed edits, and preserves unrelated `config.toml` additions during semantic rollback;
- does not change credentials, providers, MCP servers, plugins, apps, or remote systems.

When `delegation-control` is selected, the SubagentStart budget Hook is advisory. It records opaque session hashes and child IDs under the plugin's private data directory, but the current Hook API cannot cancel a newly starting child. The deterministic runner provides stronger local stage gates; neither path replaces external OS/container, credential, network, branch, review, or CI controls.

It does not replace Codex trust decisions, hook review, sandboxing, command Rules, operating-system permissions, code review, or CI. A report that demonstrates bypass of one of the plugin's documented safety gates is in scope.

## Disclosure

Please allow reasonable time for a fix and coordinated disclosure. Contributors who report valid issues in good faith will be credited unless they prefer to remain anonymous.

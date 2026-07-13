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

The current single maintainer targets acknowledgement within 7 days and an initial assessment within 14 days. These are best-effort response targets, not a service-level guarantee; timing may vary with maintainer availability or reports that depend on Codex platform behavior outside this repository.

## Security boundaries

The automatic project-guidance path:

- reads bounded local repository metadata;
- writes only `AGENTS.md` through an atomic replacement path;
- does not execute repository-provided commands during scanning;
- does not access the network;
- refuses untrusted repositories, symlink targets, overrides, unsafe paths, and secret-like output.

The explicit global setup path:

- previews all targets before writing;
- maps the Personal Core capability selection to documented Codex-home files;
- gates the project-guidance Hook through a managed, fail-closed component policy;
- refuses unmanaged conflicts and symlinks;
- backs up replacements and records pre/post hashes;
- serializes setup/rollback with an ordinary local lock, writes each target atomically, refuses rollback over later managed edits, and restores recorded content and modes;
- serializes project-guidance writes, rejects symlinked/out-of-repository evidence, and rechecks the exact guidance snapshot before replacement;
- does not change credentials, providers, MCP servers, plugins, apps, or remote systems.

Personal setup is not cross-file crash-atomic and does not defend against a hostile same-user process. Its review bundle is mutable local evidence, not an immutable audit record. Enterprise approval, protected deletion, signed/attributable decisions, hardened Artifact binding, and recovery journals belong to the separately retained Assurance product and are not security claims of `main`.

It does not replace Codex trust decisions, hook review, sandboxing, command Rules, operating-system permissions, code review, or CI. A report that demonstrates bypass of one of the plugin's documented safety gates is in scope.

## Disclosure

Please allow reasonable time for a fix and coordinated disclosure. Contributors who report valid issues in good faith will be credited unless they prefer to remain anonymous.

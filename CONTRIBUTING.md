# Contributing

Thank you for helping improve Rootloom. The project favors small, evidence-backed changes over broad automation or speculative abstraction.

中文说明见 [CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md).

## Before opening an issue

- Search existing issues and discussions.
- Use the bug template for reproducible failures.
- Include the Codex version, operating system, Python version, probe output, and the smallest safe repository fixture that demonstrates the problem.
- Remove tokens, private paths, proprietary source, and other sensitive data.

Security vulnerabilities must follow [SECURITY.md](SECURITY.md), not the public issue tracker.

## Development setup

Requirements: Git, Python 3.11+, and `make`.

```bash
git clone https://github.com/liyanqing90/rootloom.git
cd rootloom
make check
```

There are no runtime or test dependencies outside the Python standard library.

## Repository layout

```text
.agents/plugins/marketplace.json       Git marketplace catalog
plugins/rootloom/       Installable Codex plugin
  .codex-plugin/plugin.json            Plugin metadata
  assets/system/                       Installable global guidance, Agents, profile, and Rules
  hooks/                               SessionStart seeding and SubagentStart advisory audit
  skills/                              Setup, guidance, operating, review, risk, and assurance workflows
tests/                                 Unit and live integration checks
scripts/validate_repo.py               Repository contract validation
docs/                                  Design and troubleshooting docs
assets/                                README visuals
```

## Design rules

Changes should preserve these invariants:

1. Automatic startup behavior remains deterministic and local.
2. Unsafe or ambiguous state results in a skip, not an overwrite.
3. Unmarked guidance remains user-owned.
4. Scanner claims are supported by inspectable repository evidence.
5. Repository code is never executed during scanning.
6. Traversal, file count, file size, and nested depth stay bounded.
7. The runtime remains Python-standard-library only unless a strong, reviewed need proves otherwise.
8. Semantic judgment stays in Skills, outside the deterministic automatic core.
9. Global setup remains plan-first, transactional, backed up, and conflict refusing.
10. Hooks never claim stronger enforcement than the current event API provides.
11. Local `git commit` remains distinct from remote publication and destructive Git operations.

## Making a change

1. Create a focused branch.
2. Add or update a regression test for behavior changes.
3. Update both READMEs when installation, public behavior, or user-facing configuration changes.
4. Update architecture or troubleshooting docs when their contracts change.
5. Run `make check`.
6. Review the final diff for secrets, temporary files, generated noise, and unrelated edits.

Commit messages should be short and imperative, for example:

```text
Handle Cargo workspace module boundaries
```

## Testing guidance

Prefer real temporary Git repositories and behavioral assertions. Avoid network calls, arbitrary sleeps, fixture snapshots tied to incidental whitespace, and mocks when a small filesystem fixture can prove behavior directly.

The manual live smoke test requires a logged-in local Codex session. It installs the current checkout into a disposable `CODEX_HOME` and does not mutate the user's main Codex configuration:

```bash
make smoke
```

Do not make the live smoke test part of normal CI because it depends on a logged-in Codex installation and performs a real model turn. Hook trust is bypassed only inside the disposable test home.

## Pull requests

Pull requests should explain:

- the observable problem or improvement;
- the owning boundary and design choice;
- user-visible or compatibility impact;
- exact verification performed;
- remaining risks or intentionally unsupported cases.

By contributing, you agree that your contribution is licensed under the project's MIT License.

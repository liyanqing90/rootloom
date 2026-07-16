# Use Persistent Standard and Task-Scoped Elevated Authorization

- Status: accepted
- Date: 2026-07-14
- Owners: Rootloom maintainers
- Scope: Personal Core global authorization guidance and optional command Rules
- Supersedes: none
- Superseded by: none

## Context

Personal Core's global agreement treated remote publication and other external actions as categories that always required confirmation. Its optional Rules independently returned `prompt` for Git push, package publication, registry push, deployment, infrastructure mutation, and GitHub Release changes. A user could therefore explicitly request a publication or deployment and still be asked again for individual commands.

Authorization needs to express user intent at a useful level without making a persistent unrestricted grant. Static argv-prefix Rules cannot know the current task, operation type, target scope, or conversational authorization mode.

## Evidence

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Global guidance required category-wide confirmation for external mutation and publication | fact | local `main` baseline | 2026-07-14 | `plugins/rootloom/assets/system/AGENTS.md` before this decision | current task baseline; no sensitive data |
| Bundled Rules returned `prompt` for ordinary push, publication, deployment, and infrastructure commands | fact | local Codex CLI against bundled Rules | 2026-07-14 | `plugins/rootloom/assets/system/rules/rootloom.rules`; pre-change `execpolicy check` output | synthetic command arguments only |
| Pull-request commands had no Rootloom Rule while push and Release creation prompted | fact | local Codex CLI against bundled Rules | 2026-07-14 | pre-change `execpolicy check` matrix in the governed task | synthetic command arguments only |
| The accepted product requirement is a three-choice model with cross-task ordinary permission | fact | maintainer direction | 2026-07-14 | current task: Single command, ordinary permission, all permission; ordinary permission may cross tasks | current; no sensitive data |

## Decision

`plugins/rootloom/assets/system/AGENTS.md` owns three semantic authorization modes:

- **Single action** authorizes only one displayed command or action and then expires.
- **Standard** is the persistent cross-task default once global guidance is installed. It authorizes all non-high-risk implementation, publication, deployment, infrastructure, and verification steps normally required by each explicit user goal. Every task must still have a user goal and independently resolve its operation type, repository, account, service, and environment; Standard never authorizes self-initiated work.
- **Full** authorizes routine and high-risk steps only inside the current task's explicitly stated operation type and scope. It is never inferred and expires with the task.

Under Standard, irreversible loss, history rewrite or force-push, destructive local discard or remote deletion, production teardown, purchases or billing, credential or permission changes, incompatible contracts, and material scope expansion require Single action or Full authorization. A current request that already names the exact high-risk action counts as Single action authorization.

The bundled `rootloom.rules` does not attempt to persist or infer these semantic modes. The optional `autonomy` capability therefore always includes `global-policy`. Covered commands return `allow` so the Rules do not ask a second time after the global agreement has made the authorization decision. Catastrophic recursive deletion of root, the current directory, or its parent remains `forbidden`. Platform, sandbox, organization, credential, and other active Rules remain authoritative. Legacy `command-safety` remains an input alias only; the Rules are a low-confirmation authorization layer, not a deterministic safety system.

## Alternatives considered

- Confirm every external or destructive command — rejected because it duplicates explicit user intent and makes publication/deployment workflows unnecessarily interactive.
- Authorize only an operation type for the current task — rejected because the maintainer wants ordinary non-high-risk permission to persist across tasks.
- Persist Full across tasks — rejected for now because it would silently carry high-risk authority into a future context whose targets and blast radius have not been established.
- Encode modes only in argv Rules — rejected because Rules cannot represent conversational state, task lifetime, semantic risk, or repository/account/environment scope.
- Remove every hard deny — rejected because catastrophic recursive deletion is a non-contextual failure mode for which a bundled last-resort stop remains useful.

## Consequences

- Positive: ordinary coding, publication, deployment, and verification steps proceed without repeated authorization across tasks.
- Positive: high-risk actions have two useful escalation paths: one action or all in-scope actions for the current task.
- Negative: semantic enforcement depends on agents following installed global guidance; argv Rules alone cannot prove that Standard or Full is active.
- Negative: Full does not persist across tasks, and catastrophic recursive deletion remains unavailable through Rootloom Rules.
- Operational: existing optional global installations must run `$setup-rootloom upgrade` after refreshing the plugin to receive the new copied guidance and Rules. A legacy exact `command-safety` selection normalizes to `autonomy` and includes its required `global-policy`; plugin-only installations remain unchanged.

## Verification

- `codex execpolicy check` must return `allow` for representative routine and high-risk Git, GitHub, package, registry, deployment, infrastructure, and local-discard commands.
- The same check must return `forbidden` for representative catastrophic recursive deletion.
- `tests/compatibility_smoke.py` verifies the installed optional assets and decision matrix in a disposable Codex home.
- `scripts/validate_repo.py`, `make check`, and `make compatibility-smoke` keep guidance, Rules, setup instructions, and bilingual public documentation aligned.

## Revisit when

- Codex exposes a native authorization API that can persist Standard, scope Full to a task, and avoid a second platform prompt;
- maintainers explicitly accept persistent cross-task Full authorization;
- evidence shows the catastrophic hard deny blocks a legitimate common workflow or misses equivalent catastrophic forms;
- operation types or high-risk boundaries need a versioned machine-readable contract.

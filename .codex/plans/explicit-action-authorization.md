# Explicit action authorization without duplicate prompts

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-14
- Task type: security and external-action policy
- Risk: Tier 2 (Governed)

## Goal and observable success

Rootloom exposes three clear authorization choices. Single action covers one displayed command/action. Standard is the persistent cross-task default for all non-high-risk steps of each explicit goal. Full covers routine and high-risk steps only in the current task's stated operation type and scope. Static command Rules do not duplicate that semantic decision; catastrophic recursive deletion remains a hard deny.

## Non-goals

- Do not bypass Codex platform, sandbox, organization, credential, or account approval controls.
- Do not authorize an action that the current user request did not ask for.
- Do not remove the non-contextual hard stop for catastrophic recursive deletion of root, home, the current directory, or its parent.
- Do not publish or install this source change as part of this task.

## Baseline evidence

- The pre-change `plugins/rootloom/assets/system/AGENTS.md` says to confirm every publication or external mutation even after the current request already authorized it.
- `plugins/rootloom/assets/system/rules/rootloom.rules` returns `prompt` for targeted Git restore/clean operations, GitHub publication, package and registry publication, cluster and infrastructure mutation, and Release deletion.
- `tests/compatibility_smoke.py` encodes `git push` → `prompt` as the expected product contract.
- `gh pr create` and `gh pr merge` have no Rootloom rule; their remaining approval behavior therefore depends on other active Rules or the platform.
- The pre-change worktree contains the user-owned untracked `assets/rootloom-xiaohei-loom.png`; it is outside scope and must remain untouched.
- The installed 2.2.0 strict finalizer reports every pre-existing untracked path as a current change for scope matching. The contract therefore lists that image only as a machine-compatibility exception: its intake and final SHA-256 are both `55ea78b17ac40b85cf347b478799dbda629ba8f4d52e7cea5044734c6ec1c0a6` and its size remains `1153042` bytes. It is not an implementation change.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Rootloom duplicates explicit publication authorization | fact | local `main` worktree | 2026-07-14 | pre-change `plugins/rootloom/assets/system/AGENTS.md` | current task baseline; no sensitive data |
| Multiple action categories prompt after explicit authorization | fact | bundled Rules plus Codex CLI `execpolicy check` | 2026-07-14 | `plugins/rootloom/assets/system/rules/rootloom.rules` and baseline command output | current; synthetic command arguments |
| Pull-request operations are unmatched | fact | Codex CLI `execpolicy check` against bundled Rules | 2026-07-14 | baseline command output in this task | current; synthetic command arguments |

## Governed defect diagnosis

- Observed failure: an explicit request such as “发布插件” or an exact deployment command can still trigger a second Rootloom confirmation based only on its action category.
- Competing hypotheses: the prompt is required by the external service or Codex itself; or Rootloom's semantic policy and optional Rules add it.
- Ownership path: global authorization semantics live in `assets/system/AGENTS.md`; installed command decisions live in `assets/system/rules/rootloom.rules`.
- Violated invariant: the current explicit user goal and authorized scope should be task authority, and one authorization should not be converted into two approvals without a new decision.
- Root cause: Rootloom classifies multiple action categories as `confirm`/`prompt` without distinguishing an already explicit current request from an unrequested or ambiguous action.
- Root-cause alignment: PASS

## Constraints and invariants

- Standard persists across tasks but never authorizes self-initiated work; every task still needs an explicit goal and current evidence for operation type and scope.
- Single action applies once. Full is never inferred and expires with the current task.
- Static Rules cannot infer authorization mode, task lifetime, or semantic scope, so global guidance owns those decisions and Rules remove duplicate prompts.
- Platform-enforced approval remains authoritative. Catastrophic recursive deletion remains a static hard deny.
- English and Chinese public documentation must describe the same contract.

## Impact map

- Producers: bundled global guidance, command Rules, high-risk workflow, setup Skill.
- Consumers: users who install the optional `global-policy` or `command-safety` capability; Codex agents executing Git, publication, deployment, infrastructure, or deletion commands.
- Persisted data: copied `~/.codex/AGENTS.md` and `~/.codex/rules/rootloom.rules` after an explicit setup upgrade.
- Public contracts: three authorization modes, Standard persistence, Full task lifetime, and command Rules decisions.
- Generated artifacts: copied global guidance and command Rules after explicit optional setup.
- External systems: none mutated by this implementation task.

## Design and decisions

- Ownership: semantic mode and scope live in global guidance and the high-risk Skill; `rootloom.rules` only prevents duplicate command prompts and keeps the catastrophic hard deny.
- Interfaces: Single action is one-use; Standard persists across tasks for non-high-risk work required by explicit goals; Full covers high-risk work for the current task/scope. Every non-catastrophic Rules decision becomes `allow`; catastrophic recursive deletion remains `forbidden`.
- Dependency direction: setup copies reviewed assets; tests and docs consume rather than redefine the policy.
- Compatibility window: existing installations keep their copied Rules until an explicit `$setup-rootloom upgrade`; plugin-only users are unaffected by optional global assets.
- Capability dependency: selecting `command-safety` automatically includes `global-policy`, including when a legacy exact selection is normalized during upgrade, so permissive static Rules never ship without semantic authorization guidance.
- Alternatives rejected: GitHub-only exceptions remain inconsistent; per-command confirmation remains too interactive; task-local Standard does not satisfy cross-task ordinary permission; persistent Full silently carries high-risk authority into unknown future scopes.

## Implementation sequence

1. Define Single action, persistent Standard, and task-scoped Full in the global agreement and high-risk workflow.
2. Remove every Rootloom `prompt` decision and every non-catastrophic hard deny so Full can be represented semantically.
3. Record the durable security decision and update setup guidance, bilingual docs, validator contracts, and compatibility smoke expectations.
4. Verify primary, invariant, and adjacent decisions, then run repository-wide checks and strict finalization.

## Rollout, failure, and rollback

- Dry-run/preview: use `codex execpolicy check` against the source Rules before any setup or external action.
- Mixed-version behavior: old copied assets continue prompting; new source assets take effect only after plugin refresh plus explicit setup upgrade. A legacy exact `command-safety` selection expands to include its required `global-policy` during normalization.
- Failure detection: unexpected `execpolicy` decisions, validation failures, compatibility-smoke failure, or policy/docs contract mismatch.
- Rollback or compensation: revert the scoped source diff; installed users can roll back the optional setup backup chain.
- Irreversible point: none; this task performs no remote publication or installed-asset mutation.

## Verification

- Original failure path: representative GitHub, package publication, registry, cluster, infrastructure, targeted restore, and deletion commands return `allow` instead of `prompt` or a non-catastrophic hard deny.
- Owning-boundary invariant: validator and compatibility smoke require aligned global guidance, setup expectations, and Rules decisions.
- Adjacent negative/alternate path: high-risk Git/remote/infrastructure commands return `allow` at the static Rules layer but remain semantically gated by Single action or Full; catastrophic recursive deletion remains `forbidden`.
- Focused tests: `python3 scripts/validate_repo.py`; direct `codex execpolicy check` matrix.
- Contract/migration tests: `python3 tests/compatibility_smoke.py`.
- Type/lint/build/package: `make check`.
- UI/browser evidence: not applicable.
- Security/dependency checks: assert that the Rules file has no `prompt` decision and inspect representative overlapping `allow`/`forbidden` matches.
- Post-action verification: not applicable; no external action is authorized by this task.

## Risks

- Risk: an agent could invoke an allowed high-risk command while only Standard is active.
  - Mitigation: global guidance and the high-risk Skill explicitly require Single action or Full and state that Rules never grant authority.
  - Residual risk: Rules are argv-prefix policy and cannot evaluate conversation semantics; platform and agent policy remain part of the boundary.
- Risk: static Rules cannot prove that the current conversation authorized an action.
  - Mitigation: global guidance and the high-risk Skill make exact current authority mandatory, while Rules state explicitly that `allow` never grants task authority.
  - Residual risk: a violated agent-policy instruction will no longer be caught by a category-wide Rootloom prompt; platform and organization controls remain part of the boundary.
- Risk: the installed 2.2.0 strict finalizer cannot subtract an unchanged pre-existing untracked file from scope.
  - Mitigation: bind the image's intake and final size/hash in the plan and keep it out of every source edit, stage, and publication action.
  - Residual risk: the machine summary lists the unchanged image under `changed_files`; manual hash evidence is required to interpret that entry correctly.

## Decision log

- 2026-07-14 — Offer Single action, Standard, and Full instead of command-by-command confirmation.
- 2026-07-14 — Make Standard persistent across tasks while resolving goal and scope separately for every task; keep Full task-scoped and explicit.
- 2026-07-14 — Remove static `prompt` and non-catastrophic `forbidden` decisions; retain platform controls and catastrophic recursive-deletion hard stops.

## Durable decision records

- [Use Persistent Standard and Task-Scoped Elevated Authorization](../../docs/decisions/2026-07-14-tiered-authorization-modes.md) — accepted.

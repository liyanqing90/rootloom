# Architecture

Rootloom is a layered plugin, not a monolithic prompt. Each Codex mechanism owns the kind of control it can express reliably, and executable gates remain outside model prose.

![Rootloom architecture](diagram/architecture.svg)

## Design goals

- Start every trusted repository with concise, evidence-backed project context.
- Ship the refined global and project `AGENTS.md` results, not only a generator.
- Route ordinary, review-only, high-risk, and controlled multi-agent work consistently.
- Use strong models for judgment and a cheaper read-only model only for bounded evidence collection.
- Separate local reversible Git history from remote publication and destructive operations.
- Preserve user-owned configuration through plan-first setup, backups, hashes, and rollback.
- Be honest about the difference between behavioral guidance and hard enforcement.

## Layer model

| Layer | Owned responsibility | Enforcement level |
| --- | --- | --- |
| Global `AGENTS.md` | Stable authority, autonomy, engineering, evidence, routing, delegation, and communication policy | Model-visible working agreement |
| Project `AGENTS.md` | Verified repository facts, commands, map, and durable local invariants | Hierarchical project guidance |
| Decision records | Accepted architecture, contract, dependency, security, data, and operational decisions | Repository-owned durable memory; prose, not enforcement |
| Skills | Reusable procedures for setup, seeding, refinement, coding, review, high-risk work, and controlled multi-agent work | Progressive-disclosure workflow |
| Custom agents | Role description, model, reasoning, sandbox default, apps, and developer instructions | Spawned-session configuration |
| Config/profile | Concurrent thread cap, nesting depth, default runtime mode for high-assurance CLI work | Native runtime configuration |
| Rules | Command prefixes that are allowed, prompted, or forbidden outside the sandbox | Native command policy; most restrictive match wins |
| Hooks | Deterministic lifecycle actions and advisory audits | Scripted lifecycle guardrail; event-specific limits apply |
| Runner, tests, CI | Stage order, diff scope, command results, and release gates | Deterministic executable evidence |

## Capability levels

Mechanism layers explain ownership; capability levels explain what a user actually installs:

```text
skills-only
    └─ guidance       = global-policy + project-context
         └─ engineering = guidance + command-safety
              └─ delegated = engineering + delegation-control
                   └─ full = delegated + high-assurance
```

`engineering` is the recommended single-agent default. `delegation-control` is optional and atomic: its four custom roles, config limits, and subagent audit Hook are installed together. `high-assurance` depends on it. The bottom-level artifact map remains visible in `list-components`, but the supported user choice is a coherent capability, not an arbitrary partial file set.

## Plugin contents

The repository, marketplace, and plugin use the same public ID: `rootloom`.

```text
plugin
├── assets/system/
│   ├── AGENTS.md
│   ├── agents/*.toml
│   ├── profiles/high-assurance.config.toml
│   └── rules/rootloom.rules
├── hooks/
│   ├── hooks.json
│   ├── run_component_hook.py
│   └── subagent_budget.py
└── skills/
    ├── setup-rootloom/
    ├── seed-project-guidance/
    ├── refine-project-guidance/
    ├── record-engineering-decision/
    ├── operating-coding-change/
    ├── operating-code-review/
    ├── operating-high-risk-change/
    └── high-assurance-coding-change/
```

## Setup flow

Plugin installation does not silently adopt global policy. The explicit setup Skill runs a deterministic transaction:

```text
process lock → plan → conflict gate → prepared backups + manifest
                                                ↓
                      atomic writes + state commit → status
                                                ↓ failure
                  complete compensation + mode restoration
```

The transaction manages only the assets mapped from the selected capability set, plus a private component policy that independently gates the two lifecycle Hooks. A non-blocking cross-process lock serializes setup and rollback for one Codex home. Backups and a recovery manifest are durable before the first target mutation; state commit is part of the same compensation boundary, and rollback restores recorded file modes. A `full` transaction includes the global `AGENTS.md`, one profile, four custom-agent files, one Rules file, and only three keys inside the user's existing `[agents]` config table. Every unrelated config key is preserved. An unmanaged conflict blocks the whole apply unless the user explicitly authorizes replacement.

Absent policy disables both Hooks. An explicit managed policy controls them independently; malformed or symlinked policy also fails closed. Users therefore get no automatic lifecycle behavior until setup applies a selected capability level.

Changing capability levels requires `rollback --all` followed by a new plan/apply. The chained rollback restores the pre-install baseline and avoids guessing whether an asset omitted by the new level should be deleted or retained.

## Project-guidance flow

When `project-context` is selected, the automatic path remains deliberately narrower:

```text
SessionStart
    ↓
bounded repository evidence
    ↓
trust / path / ownership / secret / size gates
    ↓
atomic managed AGENTS.md facts
    ↓
$refine-project-guidance only when semantic invariants add value
```

The scanner is standard-library-only, local, deterministic, bounded, and network-free. It never executes repository code or follows symlinked evidence outside the repository. A lock in the Git common directory serializes worktree writers; the scanner reprobes under that lock and compares the exact guidance snapshot immediately before writing, safely skipping if another tool changed it. It owns only its marker-delimited range and skips unmarked guidance, overrides, symlinks, untrusted repositories, temporary/vendor/cache trees, and opted-out projects.

Semantic refinement lives in a separate Skill so model judgment cannot rewrite the managed block on every session. Nested guidance is lazy and limited to real module boundaries.

## Workflow routing

The global working agreement first completes the smallest useful `Intent + Context + Tools + Constraints + Verification` contract, then routes by one shared tier vocabulary:

- Tier 0 Direct mechanical work → execute directly through `$operating-coding-change` with minimum context and proof;
- Tier 1 Scoped bugs, features, refactors, and bounded multi-file work → `$operating-coding-change` with an internal task packet and tiered root-cause gate;
- Tier 2 Governed public/persisted contracts, security, migrations, infrastructure, deployment, release, or materially uncertain root cause → `$operating-high-risk-change` with a user-visible governed packet and ExecPlan;
- review-only work → `$operating-code-review`;
- user-requested controlled multi-agent change → `$high-assurance-coding-change`.

Behavioral fixes are Tier 1 or higher unless demonstrably mechanical. Ordinary diagnosis must align the repair with the violated invariant at its owning boundary. Governed diagnosis adds competing hypotheses and a GO/NO_GO gate. The code-review workflow emits `ROOT_CAUSE_ALIGNMENT: PASS | FAIL | NOT_APPLICABLE`; a transparent `MITIGATION` never satisfies a complete-fix claim.

Material runtime or external evidence carries a compact provenance record: stable ID, source, environment, observed time/window, stable reference, freshness/redaction, and fact-versus-inference status. Every strict-runner observed fact and reproduction links to those IDs. Behavioral verification is derived from the violated invariant and covers the original failure path, the owning-boundary invariant, and an adjacent negative or alternate path.

Accepted durable decisions route to `$record-engineering-decision`. The record preserves context, alternatives, evidence, consequences, and revisit triggers in the repository; `AGENTS.md` may point to it but must not duplicate it.

No separate always-on Gatekeeper Skill is needed. Stable classification lives in global policy, detailed behavior lives in progressive-disclosure operating Skills, and deterministic proof lives in tests, validation, CI, and the optional high-assurance runner. Hooks do not decide semantic root cause.

The high-assurance roles are:

| Role | Model | Reasoning | Default access |
| --- | --- | --- | --- |
| Evidence explorer | `gpt-5.6-terra` | medium | read-only |
| Root-cause reviewer | `gpt-5.6-sol` | xhigh | read-only |
| Implementation worker | `gpt-5.6-sol` | high | workspace-write |
| Verification reviewer | `gpt-5.6-sol` | xhigh | read-only |

Only one role is write-capable. Parent live permission overrides can still be reapplied to children, so native role isolation is not treated as a hard sandbox boundary.

## Optional subagent control has three levels

These controls exist only in the `delegation-control` capability:

1. `agents.max_threads = 4` hard-limits concurrently open threads.
2. Global guidance, Skills, and the `SubagentStart` Hook maintain an advisory total of four children per parent session. The fifth child has already started; the Hook only asks it to stop and cannot enforce that request.
3. The high-assurance runner hard-codes the stage graph, one writer, allowed paths, structured outputs, repair-cycle count, and verification order.

The Hook cannot cancel a newly started subagent. It can only warn the UI and inject developer context. This is why a screenshot can show ten completed agents even when `max_threads = 4`: the cap applies concurrently, not cumulatively.

## Deterministic high-assurance route

Native multi-agent orchestration is useful for interactive work but remains model-driven. The bundled runner uses sequential `codex exec` stages with the custom role TOMLs as configuration input. It enforces:

- a repository lock and private artifact directory;
- clean baseline and Git state snapshots;
- full content fingerprints for tracked and ordinary visible-untracked deliverables;
- pre-fingerprint classification and metadata-only capture for every ignored path plus known or caller-configured sensitive visible-untracked path, with no content hash and with those contents excluded from artifacts and reviewer prompts;
- default rejection of any writer change to those metadata-only paths before Delta capture; an exact pre-authorized deletion is the only exception and forces a nonzero human-review-required outcome;
- an explicit fail-closed ignored-path enumeration budget;
- no mutation by evidence, diagnosis, or review stages;
- one writer with an unchanged Git index;
- exact allowed-path and writer-report agreement, checked before content-bearing Delta capture;
- deterministic verification commands without a shell, stable command IDs, successful command-record coverage for every diagnosis verification item, at least one mapped user-supplied command beyond formatting-only `verify-0`, explicit operator-bound harness paths, and fingerprint stability for detected verification entrypoints such as explicit repository-relative path tokens, `make` files, JavaScript package manifests, pytest configuration files, missing common candidates, and repository-internal symlink targets;
- structured semantic gates for GO, completion, PASS, and findings;
- topology checks at startup, after every writer, after deterministic verification, and after final review, without repeating the full traversal after read-only stages;
- at most one targeted repair cycle;
- process-group termination on timeout or interruption.

This is process determinism, not result determinism. JSON Schema enforces output shape and local semantic gates enforce selected consistency; neither proves that evidence is true, the diagnosed root cause is correct, the selected verification command is adequate, or the change is safe in production. Built-in sensitive-name detection is finite; custom exact/recursive rules and opt-in dotfile redaction close repository-specific gaps. Verification entrypoint fingerprinting covers explicit and common entrypoints plus operator-bound paths; it is not a generic parser for hidden CLI path references such as response files or module-specific indirection. Directory selectors are treated as selection scope, not executable entrypoints. Artifact redaction is not file-access isolation because every model stage still receives a readable repository sandbox. An authorized protected deletion can prove only path removal, not the old content, and therefore cannot receive automated acceptance; Rootloom keeps that case deletion-only so protected content cannot be mixed into ordinary deltas through a rename or move in the same run. The strict runner supports Linux, macOS, and WSL. Native Windows is explicitly rejected because repository locking and process-group termination use POSIX semantics.

OS/container, credential, network, branch protection, and CI policy still belong outside the runner for production-critical work.

## Why no core MCP server

The core system needs local Git/filesystem evidence and native Codex configuration. An MCP server would add another process, protocol, trust decision, and failure mode without adding a capability.

MCP remains the correct extension point when a role genuinely needs an external system, such as authoritative internal documentation, issue tracking, observability, or deployment control. Add it to that narrow custom agent and configure its approval policy; do not make every coding task inherit it.

Because the strict runner disables external tools and network access, authorized runtime evidence must be collected before a run and passed as bounded, sanitized material. Rootloom standardizes provenance, not the vendor-specific collection mechanism.

## Maturity and compatibility boundary

Rootloom is early-stage and currently single-maintainer. The pinned Codex CLI contract in normal CI is the supported reproducible baseline; a non-blocking scheduled latest-version probe detects upstream drift. Both exercise offline marketplace installation, plugin discovery, full setup/status/validation, profile parsing, Rules decisions, rollback, and preservation of pre-existing config. See [Maturity, guarantees, and compatibility](maturity.md) for adoption, learning-cost, platform-coupling, and governance boundaries.

## Threat model

The plugin treats repository content, existing configuration, and child-agent routing as untrusted inputs. Defenses include bounded parsing, no repository command execution during seeding, secret-like checks, symlink/path refusal, user-owned conflict refusal, atomic writes, restrictive modes, backups, post-apply hashes, one-time Hook trust review, least-privilege roles, Rules, and deterministic tests.

These controls do not supersede platform policy, sandboxing, operating-system permissions, managed admin configuration, branch protection, code review, or CI.

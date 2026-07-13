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

The transaction manages only the assets mapped from the selected capability set, plus a private component policy that independently gates the two lifecycle Hooks. A non-blocking cross-process lock serializes setup and rollback for one Codex home. Setup, guidance, and Runner repository locks share one hardened cooperative lock owner: `plugins/rootloom/lib/rootloom_lock.py`. It opens through stable no-follow/reparse-aware parent and target handles, rejects non-regular or multi-linked targets and identity replacement, acquires non-blockingly, and only then writes owner data. This inode lock is not an irreplaceable lease or hostile-process mutex: a same-UID process can rename/unlink the locked inode, recreate the pathname, and lock that replacement inode independently. Apply and rollback each persist a Manifest-bound phase journal, complete pre-operation snapshots, Hashes, and Modes before the first target mutation. Recovery validates the complete unique managed-target plan and every restoration source before writing; state commit is part of the same compensation boundary. A `full` transaction includes the global `AGENTS.md`, one profile, four custom-agent files, one Rules file, and only three keys inside the user's existing `[agents]` config table. Every unrelated config key is preserved. An unmanaged conflict blocks the whole apply unless the user explicitly authorizes replacement.

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

Audit depth is carried by the existing workflow rather than another stage: reported findings are leads; Evidence checks an analogous sibling and tries to falsify a competing hypothesis; Diagnosis rejects a serious alternative; Review starts from the diff and records the strongest counterexample, analog checked, and complexity value. Review output distinguishes confirmed leads, novel findings, cleared surfaces, and unreviewed gaps. A mechanism that cannot name the decision it changes does not pass the value gate.

Every material fact has a stable ID, precise reference, and `repository` or `runtime_external` source type. Stable local source facts stop there; runtime or external evidence also records environment, observed time/window, stable artifact/query/trace/correlation reference when available, freshness/redaction, and fact-versus-inference status. Every strict-runner observed fact and reproduction links to those IDs. Behavioral verification is derived from the violated invariant and covers the original failure path, the owning-boundary invariant, and an adjacent negative or alternate path.

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

The durable resource and private-artifact contract for this route is recorded in [Bound Strict Runner resources at their owning artifact boundary](decisions/2026-07-12-strict-runner-resource-artifacts.md).

Native multi-agent orchestration is useful for interactive work but remains model-driven. The bundled runner uses sequential `codex exec` stages with the custom role TOMLs as configuration input. It enforces:

- a repository lock and private artifact directory;
- clean baseline and Git state snapshots;
- full content fingerprints for tracked and ordinary visible-untracked deliverables;
- pre-fingerprint classification and metadata-only capture for every ignored path plus known or caller-configured sensitive visible-untracked path, with a baseline-derived monotonic floor that prevents later declassification, no content hash, and those contents excluded from artifacts and reviewer prompts;
- default rejection of any writer change to those metadata-only paths before Delta capture; an exact pre-authorized deletion is the only exception and forces a nonzero human-review-required outcome;
- an explicit fail-closed ignored-path enumeration budget;
- no mutation by evidence, diagnosis, or review stages;
- one writer with an unchanged Git index;
- exact allowed-path and writer-report agreement, checked before content-bearing Delta capture;
- deterministic verification commands without a shell, stable command IDs, successful command-record coverage for every diagnosis verification item, at least one mapped user-supplied command beyond formatting-only `verify-0`, command-scoped existing operator-bound harness paths, and per-command fingerprint stability for detected verification entrypoints such as directly executed repository scripts, `make` files, JavaScript package manifests, pytest configuration files, missing common candidates, and every repository-internal symlink component plus the final target;
- structured semantic gates for reproduced competing hypotheses with contradiction evidence, rejected alternatives before GO, completion, and a challenged PASS;
- topology checks at startup, after every writer, after deterministic verification, and after final review, without repeating the full traversal after read-only stages;
- at most one targeted repair cycle;
- process-group termination on timeout, interruption, successful parent exit, failed parent exit when children remain, or command-output budget exhaustion, with SIGTERM-to-SIGKILL escalation, explicit group-exit confirmation, and a bounded final output drain;
- selector-based merged-output streaming into a bounded tail, with separate raw command, Runner-effective, and final persisted exit codes plus structured observed/retained byte counts, truncation, output-limit, drain-cutoff, and detached-descendant fields;
- immediate original-group cleanup and a one-second local drain when the direct parent exits with stdout still open, without consuming the remaining stage timeout; a drain cutoff makes the Runner-effective result exit 125 and fails every model or deterministic stage even when the direct parent returned 0;
- streamed complete-or-fail Git Delta artifacts with a 32 MiB aggregate default per capture and an additional 8 MiB ordinary-untracked patch default; Runner-owned capture shares the stage deadline/drain, disables external diff and textconv drivers, completes valid short writes, rejects invalid progress, verifies file-size growth, rolls back a failed complete untracked batch, and loads only fixed prompt excerpts;
- structured per-model-stage command sidecars, a 32 MiB retained-output verification-batch budget, append-only version-2 NDJSON governed by a 64 MiB actual serialized-byte default with pre-materialization escape counting, pre-command minimum-record checks, and partial-append compensation, a 64-command ceiling, and a 120,000-character compact verification prompt ceiling;
- bounded visible-path, status, Git index/control, and model structured-output producers; a locked-run digest cache reuses content hashes only across unchanged device/inode/size/mode/mtime/ctime identity;
- an optional absolute isolation-launcher argv prefix outside the repository/run root, with a required mode that fails before stages, stable no-follow configured identity, and an actual identity recheck immediately before every spawn; containment remains owned by the launcher/platform;
- a Human Review v4 binding/decision protocol over the canonical final Result core and canonical run-directory identity, the complete final validated metadata-only floor, an exact final-checkpoint worktree/index/Git-control commitment, exact-missing protected targets plus parent boundaries, and private Artifact hashes with source-enforced count/per-file/aggregate/time budgets; each Result/Artifact read binds its canonical name to the read descriptor and Artifact names are enumerated before and after hashing, while pinned regular single-link Terminal and Summary descriptors form one compensating transaction whose final gate re-hashes their exact payloads and checks canonical name, inode, one link, mode, size, and SHA-256;
- a read-only Decision Pair verifier with typed outcomes: complete Result Envelope/Binding/Pair invalidity is `INVALID`/9, completed current-state mismatch is `STALE`/12, and Git, permission/I/O, topology, deadline, or local consumer-ceiling failure is `UNVERIFIED`/13; persisted budgets cannot raise independent verifier ceilings, Git recapture disables optional locks/fsmonitor/untracked-cache writes, stdout is one status word, and bounded stderr carries the reason;
- Manifest-bound apply/rollback setup journals with complete preflighted restoration plans, hash-aware orphan recovery, ambiguous-edit refusal, and versioned historical target schemas independent of the current plugin catalog;
- a minimal deterministic-verification environment, with additional existing variables available only through explicit name-based authorization and values omitted from metadata.

This is process determinism, not result determinism. JSON Schema enforces output shape and local semantic gates enforce selected consistency; neither proves that evidence is true, the diagnosed root cause is correct, the selected verification command is adequate, or the change is safe in production. Built-in sensitive-name detection is finite; custom exact/recursive rules and opt-in dotfile redaction close repository-specific gaps. Verification entrypoint fingerprinting consumes the repository's ignored/sensitive classification and rejects a protected harness before content access. It covers direct and common entrypoints plus command-scoped operator stability dependencies, but it is not a generic parser for hidden CLI path references or proof that a command semantically uses a bound dependency. Pytest positional paths are treated as selection scope, not executable entrypoints. Every verification command is bracketed by entrypoint and repository-state checks, so a mutating command stops the batch before the next command runs. Artifact redaction is not file-access isolation because every model stage still receives a readable repository sandbox. An authorized protected deletion can prove only path removal, not the old content, and therefore cannot receive automated acceptance; Rootloom keeps that case deletion-only so protected content cannot be mixed into ordinary deltas through a rename or move in the same run. Human Review is attributable local finalization for trusted personal or small-team environments, not hostile local approval; immutable snapshots, independent workers/UIDs, external signatures, remote immutable Artifact stores, and WORM audit storage own stronger guarantees. Cleanup controls only the original POSIX process group; a descendant that creates a new session can survive, though a detected inherited-output drain cutoff now fails closed with exit 125 before any automatic acceptance. A detached process can still act after failure or escape detection by closing inherited output. Delta limits require complete content and fail before Review rather than treating a truncated patch as reviewable. Hostile commands require container, cgroup, or equivalent job isolation. The strict runner supports Linux, macOS, and WSL. Native Windows is explicitly rejected because repository locking and process-group termination use POSIX semantics.

OS/container, credential, network, branch protection, and CI policy still belong outside the runner for production-critical work.

Human Review composition is split under `scripts/human_review/`: `schema.py` owns the exact Result Envelope and persisted Binding validation, `binding.py` owns current-state preflight/recomputation, `pinned_io.py` owns pair reads through stable private descriptors, `decision.py` owns one canonical identity/time schema plus the compensating producer transaction, and `verify.py` owns typed outcome classification. Neutral `runner/errors.py`, `runner/contracts.py`, and `runner/git_capture.py` own shared failures, resource/status contracts, and verifier-only Git behavior. Human Review receives remaining Runner primitives through an explicit runtime interface and never imports `run_pipeline.py`; the top-level command is the composition and compatibility boundary.

## Why no core MCP server

The core system needs local Git/filesystem evidence and native Codex configuration. An MCP server would add another process, protocol, trust decision, and failure mode without adding a capability.

MCP remains the correct extension point when a role genuinely needs an external system, such as authoritative internal documentation, issue tracking, observability, or deployment control. Add it to that narrow custom agent and configure its approval policy; do not make every coding task inherit it.

Because the strict runner disables external tools and network access, authorized runtime evidence must be collected before a run and passed as bounded, sanitized material. Rootloom standardizes provenance, not the vendor-specific collection mechanism.

## Maturity and compatibility boundary

Rootloom is early-stage and currently single-maintainer. The pinned Codex CLI contract in normal CI is the supported reproducible baseline; a non-blocking scheduled latest-version probe detects upstream drift. Both exercise offline marketplace installation, plugin discovery, full setup/status/validation, profile parsing, Rules decisions, rollback, and preservation of pre-existing config. See [Maturity, guarantees, and compatibility](maturity.md) for adoption, learning-cost, platform-coupling, and governance boundaries.

## Threat model

The plugin treats repository content, existing configuration, and child-agent routing as untrusted inputs. Defenses include bounded parsing, no repository command execution during seeding, secret-like checks, symlink/path refusal, user-owned conflict refusal, atomic writes, restrictive modes, backups, post-apply hashes, one-time Hook trust review, least-privilege roles, Rules, and deterministic tests.

These controls do not supersede platform policy, sandboxing, operating-system permissions, managed admin configuration, branch protection, code review, or CI.

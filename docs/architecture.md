# Architecture

Rootloom `main` is Personal Core. Its architecture optimizes for a daily single-agent engineering loop rather than enterprise audit and approval.

![Rootloom Personal Core and Enterprise Assurance product split](diagram/architecture.svg)

## Product boundary

```text
Rootloom Personal Core
├── Task Intelligence
│   ├── Tier detection
│   ├── Risk signals
│   └── Workflow selection
├── Engineering Workflow
│   ├── Evidence
│   ├── Diagnosis
│   ├── Change Contract
│   ├── Implementation
│   ├── Verification Intelligence
│   └── Final Review Summary
├── Memory
│   ├── Project guidance
│   ├── Failure lessons
│   └── Durable decisions
└── Local Runtime
    ├── Optional SessionStart seeding
    ├── Command Rules
    ├── Simple setup backup/rollback
    └── Lightweight verification artifacts
```

The complete pre-split Assurance implementation is retained on `codex/enterprise-assurance`. `main` does not contain Human Review, Decision Pair, protected-deletion approval, custom-agent routing, strict audit Runner, hardened Artifact transactions, or recovery journals.

## Ownership paths

| Concern | Owner |
| --- | --- |
| Global task policy and risk signals | `plugins/rootloom/assets/system/AGENTS.md` |
| Personal end-to-end change loop | `plugins/rootloom/skills/engineering-change/` |
| Tier 0/1 implementation discipline | `plugins/rootloom/skills/operating-coding-change/` |
| Tier 2 governed change | `plugins/rootloom/skills/operating-high-risk-change/` |
| Review-only workflow | `plugins/rootloom/skills/operating-code-review/` |
| Project/failure memory | `plugins/rootloom/skills/project-memory/` |
| Durable decision records | `plugins/rootloom/skills/record-engineering-decision/` |
| Deterministic project facts | `plugins/rootloom/skills/seed-project-guidance/` |
| Semantic guidance refinement | `plugins/rootloom/skills/refine-project-guidance/` |
| Codex-home setup | `plugins/rootloom/skills/setup-rootloom/` |
| Lifecycle Hook gate | `plugins/rootloom/hooks/run_component_hook.py` |

## Task intelligence

Risk classification uses effects rather than task size alone. Persisted state, money, authentication/authorization, concurrency, state machines, migrations, shared APIs, destructive operations, and many consumers raise the tier. Small mechanical changes stay Tier 0; bounded behavior and defects use Tier 1; public/persisted or materially uncertain changes use Tier 2.

Semantic judgment remains in Skills and the model. Deterministic Hooks never infer task risk.

## Engineering workflow

`engineering-change` is an instruction workflow, not an autonomous multi-agent state machine. The active Codex agent owns evidence, diagnosis, scope, implementation, verification, and final acceptance.

For defects, `ROOT_CAUSE_ALIGNMENT: PASS` requires the observed trigger, owning boundary, violated invariant, evidence-backed cause, and rejection of the strongest plausible alternative. For features and mechanical work, alignment is `NOT_APPLICABLE` and the intended invariant is explicit.

Verification maps to behavior: the primary path, owning invariant, and an adjacent negative or alternate path. Passing one convenient command is not automatically adequate.

## Lightweight artifact helper

`engineering-change/scripts/finalize_change.py` runs operator-supplied commands without a shell and writes:

```text
run/
├── diff.patch
├── test.log
└── summary.json
```

It captures tracked Git changes and lists untracked paths without reading their contents. Repositories without a first commit use Git's empty tree as the tracked baseline. Output is bounded. Verification commands must preserve the tracked patch and captured changed/untracked path set; otherwise the bundle is marked failed and dangerous deletions are checked again. Sensitive deletions require exact confirmation. This is a review bundle, not an immutable audit record.

Runner helpers are deliberately small:

- `process.py` — bounded subprocess execution;
- `state.py` — changed paths and tracked patch;
- `verification.py` — command parsing and ordered checks;
- `contracts.py` — summary/result formats;
- `errors.py` — stable local failures.

## Memory

The project-guidance scanner writes reproducible facts to managed `AGENTS.md` blocks. `.project-memory/` stores optional reviewable architecture, risks, decision indexes, and failure lessons. Memory is explicitly created/updated and never outranks current executable evidence.

Accepted durable architecture and contract decisions still belong in repository decision records. The memory decision file is only a compact index.

## Setup and Hook boundary

Personal setup manages global guidance, command Rules, the Hook policy, state, and backups. It is plan-first, conflict-refusing, serialized by a create-exclusive local lock, and atomic per target. Rollback preflights current hashes and backup hashes before writing and refuses post-setup edits.

This design does not provide cross-file crash atomicity, hostile same-user protection, or recovery-journal replay. A partial interrupted apply is visible through `status`; backup contents remain inspectable.

The only lifecycle Hook is `SessionStart` project-guidance seeding. Missing, malformed, or symlinked component policy disables it. The scanner stays deterministic, bounded, standard-library-only, network-free, repository-contained, and snapshot-preserving.

## Dependency and portability boundary

Runtime helpers use Python 3.11+ standard library only. Normal tests cover Linux, macOS, and Windows-compatible contracts. The optional live smoke needs an installed, logged-in Codex CLI and runs only against a disposable `CODEX_HOME`.

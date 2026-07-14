# Architecture

Rootloom `main` is Personal Core. Its architecture optimizes for a daily single-agent engineering loop rather than enterprise audit and approval.

![Rootloom Personal Core and Enterprise Assurance product split](diagram/architecture.svg)

## Product boundary

```text
Rootloom Personal Core
├── Task Intelligence
│   ├── Static task / path / diff signals
│   ├── Relevant memory signals
│   ├── Explainable minimum Tier
│   └── Workflow selection
├── Engineering Workflow
│   ├── Evidence
│   ├── Diagnosis
│   ├── Change Contract
│   ├── Implementation
│   ├── Verification Intelligence
│   └── Final Review Summary
├── Memory
│   ├── Architecture invariants
│   ├── Known risks and failure lessons
│   ├── Durable decision index
│   └── Relevance / lifecycle filtering
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
| Global task policy and semantic risk rules | `plugins/rootloom/assets/system/AGENTS.md` |
| Static risk and verification intelligence | `plugins/rootloom/skills/engineering-change/scripts/runner/intelligence.py` |
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

Risk classification uses effects rather than task size alone. `analyze_change.py` inspects task text, anticipated/current paths, Git operations, a bounded tracked patch, repository-owned commands, and relevant active project memory. It reports concrete signals, detected/effective risk, a minimum Tier, confidence, matching/stale memory, and a verification plan.

Path context prevents obvious over-classification: `docs/auth.md` or an auth test alone stays documentation/test scope, while product code such as `src/auth/token.py` raises the floor. Persisted state, money, authentication/authorization, concurrency, state machines, migrations, public contracts, infrastructure, destructive operations, or broad ownership span raise Tier. A declared risk can increase but never reduce the static floor.

The result is advisory. Semantic judgment remains in Skills and the model and may raise the Tier when consumers or effects are unknown. Deterministic Hooks never infer task risk, and the analyzer never authorizes an action.

## Engineering workflow

`engineering-change` is an opt-in instruction workflow, not an autonomous multi-agent state machine or an installation-time gate. The active Codex agent owns evidence, diagnosis, scope, implementation, verification, and final acceptance. Routine Tier 0/1 work uses repository evidence and proportional tests directly; installing Rootloom never starts the analyzer or finalizer.

For defects, `ROOT_CAUSE_ALIGNMENT: PASS` requires the observed trigger, owning boundary, violated invariant, evidence-backed cause, and rejection of the strongest plausible alternative. For features and mechanical work, alignment is `NOT_APPLICABLE` and the intended invariant is explicit.

Verification maps to behavior: the primary path, owning invariant, and an adjacent negative or alternate path. Risk-specific recommendations add auth boundaries, migration coexistence, financial idempotency, state ordering, deployment rollback, or consumer compatibility when relevant. Detected Make/test commands are suggestions only. Passing one convenient command is not automatically adequate, and a generated plan is never recorded as executed evidence.

## Lightweight artifact helper

`engineering-change/scripts/finalize_change.py` runs operator-supplied commands without a shell and writes:

```text
run/
├── diff.patch
├── test.log
└── summary.json
```

When strict Tier 1/2 evidence is explicitly requested, the analyzer writes `rootloom-change-baseline-v1` outside the repository before implementation. It binds bounded Git/untracked state and metadata-only ignored/secret-like state so the finalizer can detect an intake-sensitive deletion that Git status cannot see. Ordinary untracked regular files receive streaming hashes and bounded text patches; binary/large files receive type, size, and hash. Sensitive files, directories, and symlinks are never content-read.

`rootloom-change-contract-v1` binds actual paths to allowed/forbidden globs, requires root-cause alignment for defect work, and maps primary/invariant/adjacent plus risk-specific claims to explicitly executed commands. Commands declared only in the contract are not execution authority. The v1 summary retains `risk_assessment` and separates command exit success, capture preservation, verification coverage, and `quality_status`; the compatibility `passed` field is true only for `VERIFIED_CHANGE`. Advisory mode may omit baseline/contract and exits successfully after stable passing commands while reporting `UNVERIFIED`; explicit `--strict` turns incomplete Tier 1/2 evidence into a blocking nonzero result.

Status and Git diff are streamed through byte/path ceilings before retention. Verification output is consumed incrementally and timeout, output overflow, or leaked descendants terminates the controlled POSIX process group or Windows Job Object. Output must be outside the repository and absent, empty, or Rootloom-owned. The complete patch has a configurable 16 MiB default refusal ceiling. Sensitive deletions require exact confirmation. This remains a mutable review bundle, not an immutable audit record.

Runner helpers are deliberately small:

- `process.py` — bounded subprocess execution;
- `state.py` — bounded Git state, untracked fingerprints, and patches;
- `baseline.py` — pre-change sensitive/state producer-consumer contract;
- `change_contract.py` — path scope and verification-claim enforcement;
- `verification.py` — command parsing and ordered checks;
- `intelligence.py` — advisory risk, memory matching, and verification planning;
- `contracts.py` — summary/result formats;
- `errors.py` — stable local failures.

## Memory

The project-guidance scanner writes reproducible facts to managed `AGENTS.md` blocks. `.project-memory/` stores optional reviewable architecture, risks, decision indexes, and failure lessons. `project_memory.py context` selects relevant entries lexically by task/path, bounds output, and separates expired/resolved/superseded matches from active context. New records have deterministic identity, evidence references, lifecycle state, and optional expiry; exact duplicates are suppressed. Memory is explicitly created/updated and never outranks current executable evidence.

The persisted envelope remains `rootloom-project-memory-v1`. Legacy entries without identity or lifecycle metadata remain readable and context never rewrites them. The CLI and analyzer share one strict no-follow descriptor reader, schema, entry limit, legacy identity, relevance, status, and expiry contract; malformed or over-limit files are never silently truncated by one consumer. Explicit writers reload, deduplicate, and atomically replace while holding `.project-memory/memory.lock`.

Accepted durable architecture and contract decisions still belong in repository decision records. The memory decision file is only a compact index.

## Setup and Hook boundary

Plugin installation is complete after Codex adds the plugin: Skills become available, while global guidance, command Rules, Hook policy, and setup state remain absent. Optional Personal setup manages those copied global assets only after an explicit user request. Its `install` handles first setup; `upgrade` preserves the installed capability selection, records version-only changes without redundant asset backups, backs up changed assets, and safely retires pristine targets that disappear from the catalog. Both status and upgrade validate installed paths, compare targets with installed hashes, and refuse post-install drift. Compatibility `apply` remains available. Setup is plan-first, conflict-refusing, serialized by a create-exclusive local lock, and atomic per target.

This design does not provide cross-file crash atomicity, hostile same-user protection, or recovery-journal replay. A partial interrupted apply is visible through `status`; backup contents remain inspectable.

The only lifecycle Hook is `SessionStart` project-guidance seeding. Missing, malformed, or symlinked component policy disables it. The scanner stays deterministic, bounded, standard-library-only, network-free, repository-contained, and snapshot-preserving.

## Dependency and portability boundary

Runtime helpers use Python 3.11+ standard library only. Normal tests cover Linux, macOS, and Windows-compatible contracts. The optional live smoke needs an installed, logged-in Codex CLI and runs only against a disposable `CODEX_HOME`.

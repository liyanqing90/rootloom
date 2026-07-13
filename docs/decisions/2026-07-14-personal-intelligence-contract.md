# Keep Personal Intelligence Advisory, Local, and Evidence-Subordinate

- Status: accepted
- Date: 2026-07-14
- Owners: Rootloom maintainers
- Scope: Personal Core task intelligence, verification planning, and engineering-memory contracts
- Supersedes: none
- Superseded by: none

## Context

Personal Core 2.0 removed enterprise approval and audit machinery, but its highest-value next capabilities—risk classification, verification intelligence, and long-term project learning—remained primarily Skill instructions. The executable finalizer accepted a manually declared risk, project-memory context returned every entry, and no local contract separated suggested verification from executed evidence.

The personal product needs consistent daily decisions without recreating an orchestration platform, trusting stale history, silently writing memory, or requiring a database/network service.

## Evidence

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Finalizer risk was entirely operator-declared | fact | local 2.0 source | 2026-07-14 | `plugins/rootloom/skills/engineering-change/scripts/finalize_change.py` at baseline `e39072a` | baseline source; no sensitive content |
| Memory context returned all entries and had no lifecycle/relevance fields | fact | local 2.0 source/tests | 2026-07-14 | `plugins/rootloom/skills/project-memory/scripts/project_memory.py`; `tests/test_project_memory.py` at baseline `e39072a` | baseline source; no sensitive content |
| Personal users requested stronger long-term memory, machine-assisted risk, and behavior-derived verification | fact | user-provided product review | 2026-07-14 | current task and `.codex/plans/personal-core-intelligence.md` | current; no sensitive content |
| Static rules can distinguish documented auth references from auth product code and can keep stale memory out of active signals | fact | local tests | 2026-07-14 | `tests/test_engineering_change.py`; `tests/test_project_memory.py` | current working tree; no sensitive content |

## Decision

Personal Core owns one bounded advisory intelligence layer in `engineering-change/scripts/runner/intelligence.py`:

- it combines task text, paths/operations, a bounded tracked diff, repository commands, and relevant active memory into explainable signals, a minimum Tier, effective risk, and a verification plan;
- it may raise a declared risk floor but never lower explicit or semantic judgment;
- it never authorizes actions and never executes suggested commands;
- finalization keeps suggestions separate from commands actually run and from `passed`.

Engineering memory remains a small repository-owned file system managed by `project_memory.py`:

- `rootloom-project-memory-v1` envelopes and legacy entries remain readable;
- new fields are additive: deterministic ID, paths, evidence, lifecycle status, and optional expiry;
- context is read-only, bounded, relevance-selected, and stale-aware;
- writes and lifecycle transitions are always explicit and reviewable;
- current repository evidence always outranks memory.

Both owners remain Python-standard-library-only, local, network-free, and single-agent. No Hook performs risk inference or memory writes.

## Alternatives considered

- Model/Skill prose only — rejected because it does not make underestimated risk, stale history, or suggested-versus-executed verification mechanically inspectable.
- Path-only Tier promotion — rejected because documentation/test paths such as `docs/auth.md` produce obvious false positives and path names alone do not capture task or diff semantics.
- Vector database, embeddings, or background index — rejected because the current memory volume and lexical path/task use case do not justify dependencies, privacy surface, operational state, or daemon lifecycle.
- Automatically run detected repository commands — rejected because discovery is not execution authorization and a suggested broad command may be unsafe, expensive, or insufficient.
- New orchestration runner or approval gate — rejected because it would reintroduce Enterprise Assurance complexity into the default personal product.

## Consequences

- Positive: users get consistent, inspectable minimum-risk and verification decisions plus relevant historical reminders in the daily loop.
- Positive: existing memory and summary consumers retain their envelopes and established fields.
- Negative: lexical heuristics can miss domain meaning or over-promote unusual naming; they cannot prove root cause or test sufficiency.
- Negative: additive JSON keys can affect undocumented consumers that require exact key sets.
- Operational: maintain focused positive and counterexample tests for each signal; ordinary Git revert restores 2.0 behavior; no data migration, service rollout, or destructive contraction is required.

## Verification

- `tests/test_project_memory.py` covers legacy reads, relevance, no-write context, provenance/expiry, deduplication, stale exclusion/history inclusion, lifecycle transition, and unsafe-path refusal.
- `tests/test_engineering_change.py` covers documentation false positives, auth and migration promotion, active/stale memory, automatic/manual risk floors, risk-specific plans, artifact behavior, dangerous deletion, verification drift, unborn Git, invalid `HEAD`, and Windows parsing.
- `scripts/validate_repo.py` requires the analyzer, memory lifecycle, additive summary, synchronized documentation, and 2.1 diagram surfaces.
- `make check` and `make compatibility-smoke` remain release gates.

## Revisit when

- repository memory regularly exceeds the bounded JSON/file model or measured lexical retrieval misses useful lessons at an unacceptable rate;
- false-positive/negative evidence supports a different deterministic signal contract;
- a safe platform-native command planner can separate discovery, authorization, execution, and evidence better;
- exact-key summary consumers require an explicit summary format version transition;
- Personal Core begins to require server, team, compliance, approval, or immutable-audit semantics, which belong on the separate Assurance product line.

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
| 2.1 path-only capture permits same-path untracked rewrites, ignored sensitive deletion, unrelated passing commands, and out-of-contract paths to escape a verified result | fact | supplied 2.1 review plus local source/tests | 2026-07-14 | `.codex/plans/personal-core-hardening.md`; `engineering-change/scripts/runner/` | current; sensitive values redacted/not read |
| Making baseline, contract, and finalizer mandatory for every Tier 1/2 task raises installation-time and daily operating cost beyond the Personal Core boundary | fact | explicit maintainer product direction plus installed global-policy/Skill inspection | 2026-07-14 | current task; `plugins/rootloom/assets/system/AGENTS.md`; `plugins/rootloom/skills/engineering-change/SKILL.md` | current; no sensitive data |

## Decision

Personal Core owns one bounded advisory intelligence layer in `engineering-change/scripts/runner/intelligence.py`:

- it combines task text, paths/operations, a bounded tracked diff, repository commands, and relevant active memory into explainable signals, a minimum Tier, effective risk, and a verification plan;
- it may raise a declared risk floor but never lower explicit or semantic judgment;
- it never authorizes actions and never executes suggested commands;
- plugin installation never starts analysis, creates evidence files, enables global policy, or makes the deep review loop a default requirement;
- advisory analysis/finalization remains opt-in and non-blocking; stable passing commands may produce an `UNVERIFIED` summary without turning compatibility `passed` true;
- explicit `--strict` Tier 1/2 finalization requires a pre-change `rootloom-change-baseline-v1` outside the repository plus `rootloom-change-contract-v1` and blocks incomplete governed evidence;
- ordinary untracked files are content-fingerprinted and may contribute a bounded text patch, while sensitive/ignored/user-declared sensitive paths are metadata-only;
- finalization keeps suggestions, executed command results, capture preservation, declared verification coverage, and authoritative quality status separate; compatibility `passed` is true only for `VERIFIED_CHANGE`;
- verification runs inside a bounded process tree and cannot report verified quality after output overflow, timeout, descendant leakage, repository drift, partial coverage, scope violation, or an unapproved protected deletion.

Engineering memory remains a small repository-owned file system managed by `project_memory.py`:

- `rootloom-project-memory-v1` envelopes and legacy entries remain readable;
- new fields are additive: deterministic ID, paths, evidence, lifecycle status, and optional expiry;
- context is read-only, bounded, relevance-selected, and stale-aware;
- writes and lifecycle transitions are always explicit and reviewable;
- the CLI and analyzer use one strict no-follow descriptor reader/schema/relevance contract, and all writers reload/deduplicate/write while holding `.project-memory/memory.lock`;
- current repository evidence always outranks memory.

Both owners remain Python-standard-library-only, local, network-free, and single-agent. No Hook performs risk inference or memory writes.

## Alternatives considered

- Model/Skill prose only — rejected because it does not make underestimated risk, stale history, or suggested-versus-executed verification mechanically inspectable.
- Path-only Tier promotion — rejected because documentation/test paths such as `docs/auth.md` produce obvious false positives and path names alone do not capture task or diff semantics.
- Vector database, embeddings, or background index — rejected because the current memory volume and lexical path/task use case do not justify dependencies, privacy surface, operational state, or daemon lifecycle.
- Automatically run detected repository commands — rejected because discovery is not execution authorization and a suggested broad command may be unsafe, expensive, or insufficient.
- New orchestration runner, installation-time validation, or default approval gate — rejected because it would reintroduce Enterprise Assurance cost into the default personal product.

## Consequences

- Positive: users get consistent, inspectable minimum-risk and verification decisions plus relevant historical reminders in the daily loop.
- Positive: existing memory and summary consumers retain their envelopes and established fields.
- Negative: lexical heuristics can miss domain meaning or over-promote unusual naming; they cannot prove root cause or test sufficiency.
- Negative: additive JSON keys can affect undocumented consumers that require exact key sets.
- Positive: existing Tier 1/2 finalizer calls can keep producing a bundle without new setup files or blocking exit codes; incomplete evidence is visible as `UNVERIFIED` and `passed: false`.
- Negative: callers that treat exit code zero as proof of engineering sufficiency must inspect `quality_status`; only `--strict` makes completeness an execution gate.
- Operational: maintain focused positive and counterexample tests for each signal; ordinary Git revert restores 2.0 behavior; no data migration, service rollout, or destructive contraction is required.

## Verification

- `tests/test_project_memory.py` covers legacy reads, relevance, no-write context, provenance/expiry, deduplication, stale exclusion/history inclusion, lifecycle transition, concurrent writers, descriptor-read drift, and unsafe-path refusal.
- `tests/test_engineering_change.py` covers advisory non-blocking behavior, strict evidence refusal, documentation/dependency classification, active/stale/oversized memory, baselines, ignored-sensitive deletion, untracked text/binary fingerprints, contract scope, partial coverage, output ownership, no-change, streaming output, descendant cleanup, dangerous deletion, verification drift, unborn Git, invalid `HEAD`, non-UTF-8 paths, and Windows parsing.
- `tests/compatibility_smoke.py` proves plugin installation creates no global AGENTS, command Rules, component policy, setup state, or review-gate side effects before separately exercising optional setup.
- `scripts/validate_repo.py` requires the analyzer, memory lifecycle, additive summary, synchronized documentation, and 2.1 diagram surfaces.
- `make check` and `make compatibility-smoke` remain release gates.

## Revisit when

- repository memory regularly exceeds the bounded JSON/file model or measured lexical retrieval misses useful lessons at an unacceptable rate;
- false-positive/negative evidence supports a different deterministic signal contract;
- a safe platform-native command planner can separate discovery, authorization, execution, and evidence better;
- exact-key summary consumers require an explicit summary format version transition;
- Personal Core begins to require server, team, compliance, approval, or immutable-audit semantics, which belong on the separate Assurance product line.

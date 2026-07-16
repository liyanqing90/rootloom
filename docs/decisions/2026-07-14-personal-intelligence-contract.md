# Keep Personal Intelligence Advisory, Local, and Evidence-Subordinate

- Status: accepted
- Date: 2026-07-14
- Owners: Rootloom maintainers
- Scope: Personal Core task intelligence, verification planning, and engineering-memory contracts
- Supersedes: none
- Superseded by: summary-status, Git-capture, sensitive-discovery, and seal-recovery clauses are superseded by [Keep Strict Review Evidence-Honest and Resource-Bounded](2026-07-15-evidence-honest-strict-review.md); all other decisions remain active

## Context

Personal Core 2.0 removed enterprise approval and audit machinery, but its highest-value next capabilities—risk classification, verification intelligence, and long-term project learning—remained primarily Skill instructions. The executable finalizer accepted a manually declared risk, project-memory context returned every entry, and no local contract separated suggested verification from executed evidence.

The personal product needs consistent daily decisions without recreating an orchestration platform, trusting stale history, silently writing memory, or requiring a database/network service.

## Evidence

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Finalizer risk was entirely operator-declared | fact | local 2.0 source | 2026-07-14 | `plugins/rootloom/skills/engineering-change/scripts/finalize_change.py` at baseline `e39072a` | baseline source; no sensitive content |
| Memory context returned all entries and had no lifecycle/relevance fields | fact | local 2.0 source/tests | 2026-07-14 | `plugins/rootloom/skills/project-memory/scripts/project_memory.py`; `tests/test_project_memory.py` at baseline `e39072a` | baseline source; no sensitive content |
| Personal users requested stronger long-term memory, machine-assisted risk, and behavior-derived verification | fact | user-provided product review | 2026-07-14 | accepted decision context and current repository implementation | current; no sensitive content |
| Static rules can distinguish documented auth references from auth product code and can keep stale memory out of active signals | fact | local tests | 2026-07-14 | `tests/test_engineering_change.py`; `tests/test_project_memory.py` | current working tree; no sensitive content |
| 2.1 path-only capture permits same-path untracked rewrites, ignored sensitive deletion, unrelated passing commands, and out-of-contract paths to escape a verified result | fact | supplied 2.1 review plus local source/tests | 2026-07-14 | `engineering-change/scripts/runner/` and regression tests | current; sensitive values redacted/not read |
| Making baseline, contract, and finalizer mandatory for every Tier 1/2 task raises installation-time and daily operating cost beyond the Personal Core boundary | fact | explicit maintainer product direction plus installed global-policy/Skill inspection | 2026-07-14 | current task; `plugins/rootloom/assets/system/AGENTS.md`; `plugins/rootloom/skills/engineering-change/SKILL.md` | current; no sensitive data |
| 2.2 strict evidence could be internally consistent without proving the baseline and contract came from an operator-sealed intake | fact | supplied 2.2 review plus local source/tests | 2026-07-14 | `baseline.py`, `change_contract.py`, `finalize_change.py`, `/tmp/rootloom-2.2.1-prechange-baseline.json` | current; no sensitive content |
| 2.2.1 allowed an edited contract skeleton to invalidate its own manifest seal, strict incomplete evidence to exit zero, same-size sensitive rewrites and nested sensitive files to escape capture, slash-crossing globs, semantically unknown `VERIFIED_CHANGE`, and unbound repository-base movement | fact | supplied 2.2.1 review plus local source/regressions | 2026-07-14 | `begin_review.py`, `seal_contract.py`, `runner/`, `tests/test_engineering_change.py` | current; synthetic sensitive values only |
| A fresh post-fix challenge found mixed-time captures, sensitive replacement/ancestor/quarantine escapes, ignored-sensitive scope omission, partial command execution, non-exclusive intake publication, untracked-risk omission, Windows fallback misclassification, and invalid empty/CR-only patches | fact | local state-machine tracing plus fail-before counterexamples | 2026-07-14 | `runner/{state,intelligence,verification,process,strict_json}.py`, `begin_review.py`, `finalize_change.py`, `tests/test_engineering_change.py` | current; synthetic sensitive values only |
| Final review reproduced a newly ignored sensitive addition entering an ordinary patch before quarantine and linked-worktree evidence being created inside the external Git common directory | fact | local macOS temporary repositories and fail-before counterexamples | 2026-07-14 | `runner/{state,evidence_paths}.py`, `begin_review.py`, `finalize_change.py`, `tests/test_engineering_change.py` | current; synthetic values only; temporary repositories removed |

## Decision

Personal Core owns one bounded advisory intelligence layer in `engineering-change/scripts/runner/intelligence.py`:

- it combines task text, paths/operations, bounded tracked and non-sensitive untracked diffs, repository commands, and relevant active memory into explainable signals, a minimum Tier, effective risk, and a verification plan;
- it may raise a declared risk floor but never lower explicit or semantic judgment;
- it never authorizes actions and never executes suggested commands;
- plugin installation never starts analysis, creates evidence files, enables global policy, or makes the deep review loop a default requirement;
- advisory analysis/finalization remains opt-in and non-blocking; stable passing commands may produce an `UNVERIFIED` summary without turning compatibility `passed` true;
- default advisory finalizer exit policy is `bundle`: exit zero means a stable bundle was generated, not that engineering quality was verified;
- automation that must stop on incomplete quality uses `--exit-policy quality` or `--require-verified`;
- explicit `--strict` Tier 1/2 finalization uses an atomic no-replace transactional intake followed by editable contract draft → explicit immutable seal; operator-sealed evidence binds the canonical contract, final contract bytes, and review-manifest bytes to baseline hash, `run_id`, `nonce`, `task_sha256`, repository identity, HEAD, symbolic HEAD ref, and index;
- repository state is accepted only after two identical bounded captures; evidence bytes, seals, Git base, and output target are revalidated after verification;
- evidence JSON rejects duplicate keys and non-finite/out-of-range values, and all commands are parsed before any command executes;
- strict mode defaults to quality exit codes so only `VERIFIED_CHANGE` returns zero; `--strict-bundle-only` is the explicit non-blocking alternative;
- changed dirty baselines use conservative scope attribution, and disappearance of pre-existing dirty paths is a gate failure rather than `NO_CHANGE`;
- ordinary untracked files are content-fingerprinted and may contribute an applyable bounded text patch, while sensitive exact-name/suffix and user-declared directory trees are recursively classified and remain metadata-observed/content-unread;
- before ordinary content reads, the reference-aware union of known and currently discovered sensitive paths is captured as metadata; changed, missing, or newly ignored additions quarantine all changed endpoints, disable extra repository reads, and become explicit task changes for risk, scope, and summaries;
- the worktree and resolved Git common directory are both repository-owned storage; intake, baseline, seal, evidence, and bundle paths must remain outside both boundaries and are rechecked before publication;
- repository scope globs are segment-aware; only structured claims from the sealed contract can complete strict claim binding, and CLI claims cannot promote quality;
- finalization keeps suggestions, executed command results, capture preservation, qualifying versus declared claims, operator-asserted semantic review, evidence provenance, hash-chain validity, and authoritative quality status separate; semantic coverage `unknown` reaches at most `MECHANICALLY_VERIFIED`, while compatibility `passed` is true only when sealed mechanical evidence and explicit semantic review yield `VERIFIED_CHANGE`;
- verification runs inside a bounded process tree and cannot report verified quality after output overflow, timeout, descendant leakage, repository/evidence drift, partial claim binding, scope violation, or an unapproved protected deletion;
- Personal Core reports `isolation: process-group-only` and is not a sandbox for untrusted commands.

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
- Treating all complete claim mappings as `VERIFIED_CHANGE` — rejected because self-declared claims can be backfilled after a diff; the summary must distinguish `MECHANICALLY_VERIFIED` from operator-sealed `VERIFIED_CHANGE`.

## Consequences

- Positive: users get consistent, inspectable minimum-risk and verification decisions plus relevant historical reminders in the daily loop.
- Positive: existing memory and summary consumers retain their envelopes and established fields.
- Negative: lexical heuristics can miss domain meaning or over-promote unusual naming; they cannot prove root cause or test sufficiency.
- Negative: additive JSON keys can affect undocumented consumers that require exact key sets.
- Positive: existing advisory Tier 1/2 finalizer calls can keep producing a bundle without new setup files or blocking exit codes; incomplete evidence is visible as `UNVERIFIED` and `passed: false`.
- Negative: strict callers that relied on bundle-style zero exits must adopt the explicit `--strict-bundle-only` option; this intentional incompatibility prevents CI from silently continuing on incomplete quality.
- Positive: strict evidence no longer depends on manually rewriting `review.json`; seal creation and finalization enforce the lifecycle and base identity.
- Positive: sensitive replacement/rename states are quarantined before any changed content or auxiliary repository file is read, and ignored sensitive paths cannot bypass scope.
- Positive: newly ignored sensitive additions trigger quarantine before ordinary reads, while linked-worktree evidence cannot be published into Git refs, objects, or other common administration paths.
- Negative: verification argv/output are retained verbatim; non-sensitive ignored files, Git administrative state, external state, detached managers, and copy-only secret movement remain outside the Personal Core capture boundary.
- Negative: callers that treat exit code zero as proof of engineering sufficiency must inspect `quality_status` or switch to `--exit-policy quality`.
- Operational: maintain focused positive and counterexample tests for each signal; ordinary Git revert restores 2.0 behavior; no data migration, service rollout, or destructive contraction is required.

## Verification

- `tests/test_project_memory.py` covers legacy reads, relevance, no-write context, provenance/expiry, deduplication, stale exclusion/history inclusion, lifecycle transition, concurrent writers, descriptor-read drift, and unsafe-path refusal.
- `tests/test_engineering_change.py` covers advisory non-blocking behavior, atomic no-replace intake and draft sealing, contract/manifest post-seal tamper refusal, strict quality/bundle exits, legacy-evidence downgrade, strict JSON, stable two-pass HEAD/ref/index capture, dirty-overlap binding, recursive sensitive ancestors, symlink-target hashing, sensitive replacement/rename/new-ignored-addition quarantine and scope, linked-worktree Git-common-directory refusal, untracked risk signals/applyable patches, segment-aware globs, qualifying structured claims, semantic caps, gate priority, output/evidence symlink chains, all-command preflight, streaming output, descendant cleanup, Windows fallback, dangerous deletion, unborn Git, and non-UTF-8 paths.
- `tests/compatibility_smoke.py` proves plugin installation creates no global AGENTS, command Rules, component policy, setup state, or review-gate side effects before separately exercising optional setup.
- `scripts/validate_repo.py` requires the analyzer, memory lifecycle, additive summary, synchronized documentation, and bilingual version-neutral diagram surfaces.
- `make check` and `make compatibility-smoke` remain release gates.

## Revisit when

- repository memory regularly exceeds the bounded JSON/file model or measured lexical retrieval misses useful lessons at an unacceptable rate;
- false-positive/negative evidence supports a different deterministic signal contract;
- a safe platform-native command planner can separate discovery, authorization, execution, and evidence better;
- exact-key summary consumers require an explicit summary format version transition;
- Personal Core begins to require server, team, compliance, approval, or immutable-audit semantics, which belong on the separate Assurance product line.

## Follow-up

Summary revision 5, baseline v3, identity-neutral provenance, the secret-material/security-domain classifier split, and the aggregate stable-capture deadline are governed by [Separate secret material from security code and bound stable capture](2026-07-15-sensitive-material-and-capture-bounds.md). This record retains the historical revision-3 and revision-4 terminology; new artifacts do not emit `operator-sealed`.

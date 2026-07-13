---
name: high-assurance-coding-change
description: Orchestrate model-routed, high-assurance code changes with evidence collection, an independent root-cause gate, exactly one write-capable implementation agent, deterministic verification, and an independent final review. Use when the user explicitly invokes this skill or asks for a controlled multi-agent coding workflow where a wrong first implementation would cause expensive rework. Do not use for trivial edits, documentation-only changes, review-only requests, or production mutation that still requires user authorization.
---

# High-assurance coding change

Use the installed custom roles as a controlled pipeline. Keep the parent agent responsible for scope, decisions, deterministic verification, and final acceptance.

## Stage 0: Route risk and authority

Apply active repository and global risk rules before this orchestration:

- For Tier 1 Scoped work, use the active `operating-coding-change` workflow as the implementation discipline inside this pipeline. Tier 0 Direct work should not use this pipeline.
- For Tier 2 Governed work involving public APIs, schemas, persisted data, security boundaries, architecture ownership, production dependencies, releases, destructive effects, or materially uncertain root cause, `operating-high-risk-change` owns the task packet, plan, compatibility, rollback, authorization, and execution gate when available.
- Do not let this skill turn a blocked high-risk change into an authorized one. Start its evidence stages only within the scope that the governing workflow permits, and start implementation only after all required user decisions exist.

## Preconditions

- Read the active repository instructions and inspect the working tree before delegating.
- Resolve this Skill directory from the path Codex exposes, then run `python3 <skill-dir>/scripts/validate_setup.py` when the role files or model catalog may have changed.
- Require the named roles `evidence_explorer`, `root_cause_reviewer`, `implementation_worker`, and `verification_reviewer`. Do not silently substitute a built-in or differently configured role.
- In CLI sessions, start Codex with `codex --profile high-assurance`. In the desktop app or IDE, select Sol with High reasoning and the least-privilege parent mode that still permits the requested work.
- Do not run this native workflow from Ultra, `danger-full-access`, or a bypass-permissions mode. Those parent-turn settings can enable extra delegation or override a child role's safer defaults.
- The strict sequential runner supports Linux, macOS, and WSL. Do not run it on native Windows; setup/seeding platform support is a separate boundary.
- Treat desktop and IDE role isolation as behavioral, not hard sandboxing: composer-level live permission choices may be reapplied to children. Use staged `codex exec` runs when hard read-only enforcement is required.
- Respect higher-risk workflow gates. This skill does not authorize production changes, destructive operations, migrations, releases, credential changes, or breaking contracts.
- The strict runner rejects gitlinks, submodules, and nested Git repositories because their ignored files and control metadata require repository-specific recursive isolation. Use an isolated flattened worktree or an external repository-specific pipeline instead of weakening this gate.
- For answer, explanation, diagnosis, planning, or review-only requests, do not start the implementation stage.

## Choose the execution route

Use the native stages below only when the current `spawn_agent` tool schema exposes an `agent_type` argument and a smoke test confirms the child metadata uses the configured role model. A matching `task_name` is not sufficient.

On installations where `agent_type` is unavailable, including the locally verified 0.144 multi-agent v2 surface, use the deterministic sequential runner:

```bash
python3 <skill-dir>/scripts/run_pipeline.py \
  --repo /absolute/path/to/repo \
  --task /absolute/path/to/task.md \
  --sensitive-path 'private/**' \
  --max-command-output-bytes 8388608 \
  --max-verification-output-bytes 33554432 \
  --max-verification-artifact-bytes 67108864 \
  --max-delta-bytes 33554432 \
  --max-untracked-patch-bytes 8388608 \
  --max-human-review-artifact-bytes 67108864 \
  --max-human-review-total-bytes 536870912 \
  --max-human-review-binding-seconds 120 \
  --verify 'your focused test command' \
  --verify 'your broader verification command'
```

The runner reads model, reasoning, and sandbox settings from the same four custom-agent TOML files. It requires a clean worktree by default, uses structured stage outputs, disables user config/plugins/apps for every stage, blocks network in the workspace-write sandbox, and allows at most one targeted repair cycle. Verification commands are parsed without a shell; place pipelines or compound commands in a repository-owned script. Detected verification entrypoints are fingerprinted before the writer and rechecked per command for directly executed repository scripts, command-scoped `--bind-verification-path verify-N:path` stability dependencies, `make` files, JavaScript package manifests, pytest configuration files, missing common candidates, and every repository-internal symlink component plus final target content. Explicit harnesses must be existing regular files, and ignored or sensitive-untracked harnesses are rejected before content access. Pytest positional selectors are not executable entrypoints. This is an entrypoint stability gate, not complete command semantic parsing or proof that a command uses every bound dependency.

Merged command output is streamed into a bounded tail with an 8 MiB default per-command
budget. `--max-command-output-bytes` accepts another positive budget. Exceeding it
terminates the original process group and records structured output metadata.
Model stages persist a `*-command.json` sidecar. Verification additionally has a 32 MiB
retained-output batch budget, a 64 MiB actual serialized-NDJSON budget, a fixed
64-command ceiling, and a 120,000-character model-prompt summary ceiling.
`--max-verification-output-bytes` and `--max-verification-artifact-bytes` change the
positive batch budgets. One record is appended per command, followed by a small summary
index; JSON escape bytes are counted before rejected output is materialized, minimum
record space is preflighted before command execution, and exhaustion is structured and
fail-closed.
Verification receives a minimal environment; repeat `--verify-env NAME` only for an
existing variable that the command genuinely requires. Names are recorded, values are
not. Model stages retain the parent environment for Codex authentication compatibility.

Known secret-like visible-untracked paths are classified before content fingerprinting. Every path protected at the baseline remains metadata-only for the complete run, even after ignore configuration changes, and declassification of an existing protected path is rejected before Delta capture. Add repeatable exact-path or `directory/**` rules with `--sensitive-path`; use `--redact-untracked-dotfiles` when every untracked dotfile should remain metadata-only. Built-in matching is finite. These options protect runner-generated artifacts and prompts, not repository file access: all four model stages can still read files. Use a secret-free worktree or OS/container isolation when deny-read behavior is required.

This classification is path-based, not content-lineage tracking or DLP. Copied bytes at
an ordinary allowed path can still enter content fingerprints and Delta artifacts.
Complete Delta patches stream to private artifacts under a 32 MiB aggregate budget per
capture and an additional 8 MiB ordinary-untracked budget. Override them with
`--max-delta-bytes` and `--max-untracked-patch-bytes` only after reviewing the resource
cost. A partial or oversized Delta stops before automated Review and cannot receive PASS.
All Git commands in one Runner-owned capture share the stage deadline and immediate
parent-exit drain, disable external diff and textconv drivers, complete valid short
writes, reject invalid progress, verify actual Artifact growth, roll back a failed
ordinary-untracked batch, and retain
only a fixed excerpt from each complete patch in model-facing memory.

After the writer returns, reject detected creation, modification, or deletion of metadata-only ignored/sensitive paths by default. This is an acceptance gate, not OS-level write prevention or rollback; inspect and recover the filesystem after failure. A necessary deletion requires one exact operator-supplied `--allow-protected-path-delete path`; directory/glob rules fail, the path must pass pre-writer checks against the baseline protected set and diagnosis `allowed_paths`, and the run must use a clean baseline with `--max-repair-cycles 0`. Any authorized protected deletion makes the run deletion-only: no ordinary code edits, renames, moves, or visible file creations are accepted in the same run. The Runner never reads or backs up the former content and, even after Reviewer PASS, exits 10 with `HUMAN_REVIEW_REQUIRED`. Human Review v4 binds the original Run directory and complete final metadata-only floor, safely re-reads the full canonical Result after writing, bounds private Artifact hashing by count, per-file bytes, aggregate bytes, and time, and re-hashes the exact Terminal and Summary payloads through pinned descriptors at the final commit gate. Do not translate that state into automated acceptance. Topology is checked after every writer, after deterministic verification, and after final review.

The runner also injects each role TOML's `developer_instructions` as model-visible
developer instructions and enforces the following locally, without trusting model prose:

- one hardened cooperative, non-blocking inode lock per Git common directory; a same-UID process can replace the locked pathname with a new inode, so this is not an irreplaceable lease or hostile-process mutex;
- content fingerprints for tracked and ordinary visible-untracked deliverables; pre-classified metadata-only fingerprints without `sha256` for ignored and known/configured sensitive visible-untracked paths; plus separate Git-index and HEAD/refs/config snapshots;
- an ignored-path enumeration budget and allowed-path gate before any content-bearing Delta capture;
- streamed, complete-or-fail staged, unstaged, HEAD-to-worktree, and ordinary-untracked Delta artifacts under explicit byte budgets;
- bounded Runner-owned Git capture lifecycle, disabled repository diff/textconv execution, failure compensation, and fixed model-facing patch excerpts;
- no Git-visible mutation by evidence, diagnosis, verification, or review stages;
- no Git-index mutation by the writer;
- exact `allowed_paths` enforcement (`path` or `directory/**`) including untracked files;
- protected metadata-only path rejection before Delta capture, with only exact preflighted deletion-only exceptions and mandatory human acceptance;
- exact agreement between the writer's `files_changed` report and its real stage delta;
- semantic consistency for GO, completed, PASS, FAIL, and finding severity;
- process-group termination on timeout, interruption, or any parent exit that leaves children, with bounded SIGTERM waiting, SIGKILL escalation, group-exit confirmation, and an immediate final hard deadline for draining inherited output pipes after direct-parent exit; a drain cutoff forces effective exit 125 for Evidence, Diagnosis, Implementation, Review, and deterministic verification while retaining the direct process status separately;
- `0700` run directories and `0600` artifacts under an effective `umask 077`.
- source-bounded repository topology, visible paths, status, Git control/index, task/role input, and model structured-output capture through the shared `--max-state-paths` and `--max-state-bytes` controls;
- optional isolation-launcher wrapping outside the repository/run root, a required-isolation preflight, and stable no-follow identity checks at configuration plus immediately before every spawn; the launcher, not Rootloom, owns host containment;
- Human Review v4 accept/reject records for protected-deletion results, requiring Result Envelope v1 and bound under the hardened cooperative repository lock to canonical bounded repository state, original mode-0700 Run identity, the complete final metadata-only floor, exact-missing targets and parent boundaries, and bounded Artifact hashes captured through stable directory-relative no-follow descriptors, with complete Result re-reads, exact pinned Terminal/Summary content hashes, and compensating post-write drift checks. Producer and consumer share a 1 MiB limit for each Pair file and canonical control-free 4096-byte reviewer/local-account identities; both payloads are preflighted before either file is created. Use `review_decision.py verify --repo ... --run-dir ...` for read-only verification: invalid evidence is `INVALID`/9, completed current-state drift is `STALE`/12, and Git, permission/I/O, topology, deadline, or independent verifier-limit failure is `UNVERIFIED`/13. Persisted policy cannot raise consumer ceilings; verifier Git commands disable optional locks, fsmonitor, and untracked-cache writes. Stdout is the status word and bounded stderr carries a reason without Artifact bytes. Treat this as attributable final review for trusted personal or small-team environments; hostile local approval requires external immutable execution, signing, or audit infrastructure.

The artifact root must be outside the target repository. The runner saves staged,
unstaged, and HEAD-to-worktree patches for tracked content, an ordinary visible-untracked
patch, and metadata-only manifests for ignored or sensitive visible-untracked paths.
The complete patch artifacts remain private on disk; prompts receive bounded excerpts and
structured byte/completeness state rather than reloading each complete patch into memory.
The process boundary is the original POSIX process group. A descendant that creates a
new session can survive outside it; the Runner closes local output capture at a bounded
deadline and fails closed with effective exit 125 so that such a descendant cannot hold
the stage or repository lock forever or preserve automatic PASS through an early parent
exit. The escaped process can still act after failure or evade this signal by closing
inherited output.
Use container, cgroup, or equivalent job isolation for hostile verification commands.
Treat these artifacts as sensitive source material and delete old runs according to the
repository's retention policy.

## Invariants

- Keep model and reasoning selection in the custom agent TOML files. Do not override those settings in prompts.
- In every spawn call, set `agent_type` to the exact custom role name. `task_name` only labels a thread and does not apply the role configuration. If the current spawn surface has no `agent_type`, stop native routing and use staged `codex exec` calls with explicit model settings.
- Verify the spawned child's actual role and model metadata before trusting its result. A matching thread label is not sufficient evidence.
- Never run more than one write-capable agent. The parent and worker must not edit concurrently.
- Do not stage or unstage files. The deterministic runner requires the Git index to remain byte-for-byte equivalent at the entry level.
- Keep `allowed_paths` machine-readable: exact normalized repository-relative files or `directory/**`; list both endpoints of a rename.
- Treat subagent output as evidence, not truth. Recheck material claims against source, runtime behavior, or tests.
- Structured schemas validate required shape and cross-stage process semantics; they do not establish factual truth, root-cause correctness, or production safety.
- Prefer repository-owned verification commands. A model statement that tests passed is not evidence.
- Use parallelism only for independent read-heavy scopes.
- Do not treat hooks as a security or routing boundary.
- Choose the parent turn's permission mode before delegation. Live parent overrides can supersede custom-agent defaults.

## Stage 1: Collect evidence

Spawn one agent with `agent_type = "evidence_explorer"`. Spawn a second only when two scopes are genuinely independent, such as runtime reproduction and a separate persistence path. Give non-overlapping scopes and wait for all results.

Require each explorer to return:

- observed facts with file, symbol, log, or test references;
- the execution or data path;
- reproduction evidence or the exact verification gap;
- direct, possible, and excluded impact scope;
- unknowns and competing hypotheses.

Treat the request and prior reviews as leads rather than scope. Inspect at least one analogous sibling path and attempt to contradict the leading hypothesis. A reproduced defect requires at least two serious hypotheses and evidence that falsifies or contradicts one.

The evidence provenance contract classifies every material claim as `repository` or `runtime_external` and gives it a stable ID and precise reference. Stable local source facts do not need synthetic timestamps or environment prose. Runtime or external evidence additionally requires source environment, observed time or window, stable artifact/query/trace/correlation reference when available, freshness/redaction notes, and fact-versus-inference status. Every observed fact, reproduction item, and hypothesis evidence entry must reference an existing provenance ID. The strict runner is offline and disables external tools; collect authorized external evidence in the parent, sanitize or materialize the necessary artifact outside the run directory, and pass only the bounded evidence required by the task.

Do not edit source during this stage.

## Stage 2: Gate the diagnosis

Spawn exactly one agent with `agent_type = "root_cause_reviewer"`. Provide the original request, acceptance criteria, repository constraints, and raw explorer summaries. The reviewer must independently inspect material evidence and return:

- `DECISION: GO` or `DECISION: NO_GO`;
- the root cause and violated invariant;
- rejected alternatives;
- an explicit change contract with allowed and forbidden scope;
- required tests and material risks.

Before `GO`, reject at least one serious alternative with evidence. A new guard, flag, journal, abstraction, or workflow step must name the observable failure, owning boundary, executable enforcement, regression proof, and decision it changes; otherwise delete it or use a smaller native control.

The diagnosis must also establish `ROOT_CAUSE_ALIGNMENT: PASS`. A mitigation, unsupported hypothesis, or downstream symptom patch cannot receive `GO` as a complete fix.

Required tests must map to the original failure path, the violated invariant at its owning boundary, and at least one adjacent negative or alternate path.

On `NO_GO`, do not edit. Gather one bounded round of missing read-only evidence when safe and useful, then rerun the gate once. If the gate still returns `NO_GO`, stop and report the missing evidence or decision.

## Stage 3: Implement with one writer

Only after `DECISION: GO`, spawn exactly one agent with `agent_type = "implementation_worker"`. Pass the approved change contract verbatim along with the original task and repository constraints.

The worker owns the complete focused diff and targeted tests. The parent must wait and must not edit while the worker is active. If the worker needs to exceed the contract, stop and return to the diagnosis gate.

## Stage 4: Verify deterministically

After the worker returns, the parent inspects the actual diff and reruns the strongest proportional repository checks. Capture exact commands, exit status, relevant counts, and failure output. Classify failures as introduced, pre-existing, environmental, or unresolved.

Do not proceed to acceptance when a required deterministic check is failing or was not run without a documented reason.

In the strict runner, every diagnosis verification item must reference one or more stable command IDs and each mapped command must have a successful machine record. At least one mapping must reference a user-supplied command; formatting-only `verify-0` cannot be the entire verification contract. This proves execution linkage, not that the chosen command adequately covers the business requirement; the final reviewer must still assess test adequacy.

## Stage 5: Review independently

Spawn exactly one agent with `agent_type = "verification_reviewer"`. Provide the original task, approved diagnosis and contract, current diff, and verification logs. Require `VERDICT: PASS` or `VERDICT: FAIL`, findings ordered by severity, contract compliance, test adequacy, residual risk, and a concrete challenge record naming the strongest counterexample attempted, analogous implementation checked, and whether the change earns its complexity. The reviewer must start from the actual diff rather than replaying reported findings.

Any blocker or high-severity finding requires `FAIL`. Permit one targeted repair cycle through the same implementation worker, then rerun deterministic verification and independent review. If review fails again, stop with the unresolved findings instead of entering an open-ended loop.

## Final acceptance

The parent performs the final diff review and reports:

- observable result and root cause;
- important files and behavior changed;
- exact verification and outcomes;
- independent review verdict;
- only material remaining risks or unrun checks.

If the accepted change creates a durable architecture, contract, dependency, security, data, or operational decision, record it through `record-engineering-decision` when installed after the implementation is verified. The record is repository memory, not evidence that the implementation is correct.

## Determinism boundary

This native workflow strongly guides Codex but is not an unbypassable state machine. Use `scripts/run_pipeline.py` for explicit model routing and stage order. Its determinism covers selected mechanics—stage order, repository state, allowed paths, structured shape, command execution, and repair-cycle bounds—not whether a diagnosis is true or an outcome is correct. For production-critical work, also enforce external OS/container, credential, network, and CI boundaries; model prompts, sandbox labels, and hooks alone are not a complete security boundary.

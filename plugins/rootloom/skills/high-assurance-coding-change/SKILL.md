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
  --verify 'your focused test command' \
  --verify 'your broader verification command'
```

The runner reads model, reasoning, and sandbox settings from the same four custom-agent TOML files. It requires a clean worktree by default, uses structured stage outputs, disables user config/plugins/apps for every stage, blocks network in the workspace-write sandbox, and allows at most one targeted repair cycle. Verification commands are parsed without a shell; place pipelines or compound commands in a repository-owned script.

The runner also injects each role TOML's `developer_instructions` as model-visible
developer instructions and enforces the following locally, without trusting model prose:

- one non-blocking lock per Git common directory;
- content fingerprints for tracked/untracked deliverables, metadata fingerprints for ignored paths, plus separate Git-index and HEAD/refs/config snapshots;
- no Git-visible mutation by evidence, diagnosis, verification, or review stages;
- no Git-index mutation by the writer;
- exact `allowed_paths` enforcement (`path` or `directory/**`) including untracked files;
- exact agreement between the writer's `files_changed` report and its real stage delta;
- semantic consistency for GO, completed, PASS, FAIL, and finding severity;
- process-group termination on timeout or interruption;
- `0700` run directories and `0600` artifacts under an effective `umask 077`.

The artifact root must be outside the target repository. The runner saves full staged,
unstaged, HEAD-to-worktree, and untracked patches plus manifests for every gate. Treat
these artifacts as sensitive source material and delete old runs according to the
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

For runtime or external evidence, require an evidence provenance record with a stable ID, source, environment, observed time or window, stable artifact/query/trace/correlation reference when available, freshness/redaction notes, and fact-versus-inference status. Every observed fact, reproduction item, and hypothesis evidence entry must reference an existing provenance ID. The strict runner is offline and disables external tools; collect authorized external evidence in the parent, sanitize or materialize the necessary artifact outside the run directory, and pass only the bounded evidence required by the task.

Do not edit source during this stage.

## Stage 2: Gate the diagnosis

Spawn exactly one agent with `agent_type = "root_cause_reviewer"`. Provide the original request, acceptance criteria, repository constraints, and raw explorer summaries. The reviewer must independently inspect material evidence and return:

- `DECISION: GO` or `DECISION: NO_GO`;
- the root cause and violated invariant;
- rejected alternatives;
- an explicit change contract with allowed and forbidden scope;
- required tests and material risks.

The diagnosis must also establish `ROOT_CAUSE_ALIGNMENT: PASS`. A mitigation, unsupported hypothesis, or downstream symptom patch cannot receive `GO` as a complete fix.

Required tests must map to the original failure path, the violated invariant at its owning boundary, and at least one adjacent negative or alternate path.

On `NO_GO`, do not edit. Gather one bounded round of missing read-only evidence when safe and useful, then rerun the gate once. If the gate still returns `NO_GO`, stop and report the missing evidence or decision.

## Stage 3: Implement with one writer

Only after `DECISION: GO`, spawn exactly one agent with `agent_type = "implementation_worker"`. Pass the approved change contract verbatim along with the original task and repository constraints.

The worker owns the complete focused diff and targeted tests. The parent must wait and must not edit while the worker is active. If the worker needs to exceed the contract, stop and return to the diagnosis gate.

## Stage 4: Verify deterministically

After the worker returns, the parent inspects the actual diff and reruns the strongest proportional repository checks. Capture exact commands, exit status, relevant counts, and failure output. Classify failures as introduced, pre-existing, environmental, or unresolved.

Do not proceed to acceptance when a required deterministic check is failing or was not run without a documented reason.

## Stage 5: Review independently

Spawn exactly one agent with `agent_type = "verification_reviewer"`. Provide the original task, approved diagnosis and contract, current diff, and verification logs. Require `VERDICT: PASS` or `VERDICT: FAIL`, findings ordered by severity, contract compliance, test adequacy, and residual risk.

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

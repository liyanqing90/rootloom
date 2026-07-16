---
name: operating-high-risk-change
description: Plan and execute high-risk engineering changes involving public APIs, schemas, migrations, persisted data, security, architecture, production dependencies, infrastructure, release, deployment, or destructive effects. Requires impact analysis, compatibility, rollout, rollback, and explicit authorization for external actions; plans stay task-local unless durable planning is explicitly requested.
---

# High-Risk Change Workflow

Use this Skill for Tier 2 Governed work. **Standard** is the persistent cross-task default for non-high-risk steps of each explicit user goal. **Single action** covers one displayed command/action, and **Full** covers high-risk plus routine steps only for the current task's stated operation type and scope. Never infer Full or reuse a previous task's repository, account, service, or environment without current-task evidence. Static Rules do not carry this authorization state.

When a Standard workflow reaches a high-risk boundary, present Single action, Standard, and Full once with the exact scope. If the user chooses Standard, do not execute that high-risk step; continue only with safe alternatives or report the remaining blocker. A current request that explicitly names the exact high-risk action counts as Single action authorization, so do not ask for it twice. Platform-enforced approvals remain separate and cannot be bypassed.

## 1. Establish authority and risk

Identify:

- task type and the complete `Intent + Context + Tools + Constraints + Verification` execution contract;
- requested observable outcome and non-goals;
- exact environment, repository, branch, service, data set, account, or resource;
- public and persisted contracts;
- producers, consumers, automation, generated clients, stored data, and mixed-version behavior;
- security, privacy, regulatory, cost, performance, availability, and operational constraints;
- irreversible point, rollback path, and required approvals.

Ask only when missing authorization or a materially ambiguous product/operational decision remains. Do not ask for ordinary reversible implementation details.

Produce a concise governed task packet for Tier 2. It must be executable now, identify the exact missing prerequisite or user decision, or route to the repository workflow that makes it executable. Do not produce a prose-only plan.

## 2. Maintain a task-local execution plan

Use `assets/EXECPLAN.template.md` as a checklist when its gates materially change implementation, rollout, rollback, or stop decisions. Keep the active plan in the current task by default. Persist it only when the user explicitly requests a durable plan or the repository already requires a tracked planning artifact; do not create a one-time `.codex/plans/` file merely because the change is Tier 2.

The plan must be self-contained, grounded in verified paths and commands, and updated as evidence changes. Include observable success, baseline, invariants, impact map, staged implementation, compatibility, migration, rollout, rollback, verification, and decision log.

The template is a routing aid, not a section quota. Omit inapplicable prose. A plan is invalid if its gates would not change an implementation, rollout, rollback, or stop decision.

For material runtime or external evidence, include source, environment, observation time or window, stable artifact/query/issue/trace/correlation reference when available, freshness and redaction notes, and fact-versus-inference status. Keep sensitive raw payloads outside the plan and reference a sanitized repository-owned artifact when durable evidence is required. These fields support auditability; they do not prove the diagnosis.

Read context progressively: start with active project guidance, then the relevant requirement or contract, target ownership paths, and verification rules. Expand only when the impact map or unresolved evidence requires it.

## 3. Gate governed defect repair

For bugs, incidents, regressions, data repair, or incorrect runtime behavior, record observed evidence, competing hypotheses, ownership path, violated invariant, and root cause before implementation. A GO decision requires evidence that explains the material symptoms and rejects plausible alternatives.

If root cause remains unknown, either stop as `NO_GO` or explicitly govern a reversible `MITIGATION` with residual risk, observability, rollback, and a removal or follow-up condition. Never present symptom suppression as a complete root-cause fix.

Before adding a control, pass the mechanism-value gate: identify the concrete failure, owning boundary, executable enforcement, regression proof, and operator decision changed. If the proposal only adds a flag, record, wrapper, score, or approval step without changing a decision, delete it or keep the limitation explicit.

## 4. Preserve compatibility deliberately

For API, schema, config, CLI, event, or persisted-format changes:

1. state the old and new contract explicitly;
2. inventory every known producer and consumer;
3. prefer additive expansion before contraction;
4. define old/new application coexistence and compatibility window;
5. use adapters, dual-read/write, versioning, feature flags, or staged rollout only when they reduce real risk;
6. identify the gate that permits removal of the old path;
7. document migration and rollback or compensating recovery.

Pre-release status is not automatic permission to break contracts.

## 5. Data and migration discipline

Evaluate:

- backup, recovery, transactionality, locks, timeouts, retries, idempotency, re-entrancy, and partial failure;
- data volume, online migration, rolling deployment, old/new code coexistence, and observability;
- forward migration and rollback or compensating repair;
- destructive contraction timing.

Prefer expand → migrate/backfill → verify → contract. Avoid destructive contraction in the same rollout unless explicitly authorized and operationally justified.

## 6. Dependency and supply-chain discipline

For a new or materially changed production dependency:

- prove existing platform code and dependencies are insufficient;
- inspect maintenance, security, license, transitive dependencies, install scripts/binaries, runtime/bundle cost, and supported platforms;
- minimize manifest and lockfile changes;
- avoid broad upgrade commands that refresh unrelated packages;
- verify build, tests, packaging, deployment, and rollback assumptions.

## 7. External actions

Before external or irreversible execution:

1. verify the authorized operation type, target, scope, branch/environment/account and blast radius from the current request and evidence; ask only when a material part is missing or ambiguous;
2. use plan, preview, dry-run, backup, canary, staged rollout, or reversible mode where available;
3. verify credentials and permissions without exposing them;
4. define detection and rollback criteria;
5. if the active mode does not cover the next action, offer Single action, Standard, and Full with the exact operation type and scope; never confirm each routine command separately;
6. verify the resulting external state—command submission alone is not success.

## 8. Verification

Use all applicable layers:

- focused regression and unit tests;
- integration and contract tests;
- migration dry-run/forward/rollback or compensation tests;
- typecheck, lint, build, packaging and generated artifacts;
- security and dependency checks;
- mixed-version, rollout and observability checks;
- browser/screenshot evidence for affected formal UI;
- post-action verification for authorized external changes.

For defect repair, require `ROOT_CAUSE_ALIGNMENT: PASS` before closeout. Prefer fail-before/pass-after regression evidence; when impractical, document equivalent trace or contract proof and the residual verification gap.

Map behavioral verification to the violated invariant: prove the original trigger, the invariant at its owning boundary, and an adjacent negative or alternate path. A check that exercises only the newly added patch branch is insufficient evidence of a root-cause fix.

After the requested checks pass, perform one fresh challenge pass that does not use the reported findings as its checklist: inspect an analogous producer/consumer, attempt the strongest counterexample, and audit the diff for removable complexity. Reopening the task after this pass is expected when it finds a material gap.

When implementation accepts a durable architecture, contract, dependency, security, data, or operational choice, invoke `record-engineering-decision` when installed and link the accepted record from the ExecPlan. Do not turn transient task history into permanent documentation.

Classify failures as introduced, pre-existing, environmental, or unverified. Do not hide gaps.

## 9. Report

Report the final design and staged impact, exact changes, verification evidence, compatibility/migration status, external effects actually performed, rollback readiness, and residual risk. Keep an incomplete or blocked ExecPlan visibly incomplete rather than silently deleting missing gates.

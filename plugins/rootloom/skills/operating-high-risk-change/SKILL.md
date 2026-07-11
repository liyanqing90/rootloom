---
name: operating-high-risk-change
description: Plan and execute high-risk engineering changes involving public APIs, schemas, migrations, persisted data, security, architecture, production dependencies, infrastructure, release, deployment, or destructive effects. Requires impact analysis, an ExecPlan, compatibility, rollout, rollback, and explicit authorization for external actions.
---

# High-Risk Change Workflow

Use this Skill for R3 and R4 work. Do not execute production mutation, deployment, publication, release, force-push, credential change, billing action, or destructive data operation unless the current request clearly authorizes the exact target and scope.

## 1. Establish authority and risk

Identify:

- requested observable outcome and non-goals;
- exact environment, repository, branch, service, data set, account, or resource;
- public and persisted contracts;
- producers, consumers, automation, generated clients, stored data, and mixed-version behavior;
- security, privacy, regulatory, cost, performance, availability, and operational constraints;
- irreversible point, rollback path, and required approvals.

Ask only when missing authorization or a materially ambiguous product/operational decision remains. Do not ask for ordinary reversible implementation details.

## 2. Create an ExecPlan

Use `assets/EXECPLAN.template.md`. Store the active plan in the repository's established planning location, or `.codex/plans/<task>.md` when none exists.

The plan must be self-contained, grounded in verified paths and commands, and updated as evidence changes. Include observable success, baseline, invariants, impact map, staged implementation, compatibility, migration, rollout, rollback, verification, and decision log.

## 3. Preserve compatibility deliberately

For API, schema, config, CLI, event, or persisted-format changes:

1. state the old and new contract explicitly;
2. inventory every known producer and consumer;
3. prefer additive expansion before contraction;
4. define old/new application coexistence and compatibility window;
5. use adapters, dual-read/write, versioning, feature flags, or staged rollout only when they reduce real risk;
6. identify the gate that permits removal of the old path;
7. document migration and rollback or compensating recovery.

Pre-release status is not automatic permission to break contracts.

## 4. Data and migration discipline

Evaluate:

- backup, recovery, transactionality, locks, timeouts, retries, idempotency, re-entrancy, and partial failure;
- data volume, online migration, rolling deployment, old/new code coexistence, and observability;
- forward migration and rollback or compensating repair;
- destructive contraction timing.

Prefer expand → migrate/backfill → verify → contract. Avoid destructive contraction in the same rollout unless explicitly authorized and operationally justified.

## 5. Dependency and supply-chain discipline

For a new or materially changed production dependency:

- prove existing platform code and dependencies are insufficient;
- inspect maintenance, security, license, transitive dependencies, install scripts/binaries, runtime/bundle cost, and supported platforms;
- minimize manifest and lockfile changes;
- avoid broad upgrade commands that refresh unrelated packages;
- verify build, tests, packaging, deployment, and rollback assumptions.

## 6. External actions

Before R4 execution:

1. reconfirm target, scope, branch/environment/account and blast radius;
2. use plan, preview, dry-run, backup, canary, staged rollout, or reversible mode where available;
3. verify credentials and permissions without exposing them;
4. define detection and rollback criteria;
5. obtain explicit approval for the exact action if not already present;
6. verify the resulting external state—command submission alone is not success.

## 7. Verification

Use all applicable layers:

- focused regression and unit tests;
- integration and contract tests;
- migration dry-run/forward/rollback or compensation tests;
- typecheck, lint, build, packaging and generated artifacts;
- security and dependency checks;
- mixed-version, rollout and observability checks;
- browser/screenshot evidence for affected formal UI;
- post-action verification for authorized external changes.

Classify failures as introduced, pre-existing, environmental, or unverified. Do not hide gaps.

## 8. Report

Report the final design and staged impact, exact changes, verification evidence, compatibility/migration status, external effects actually performed, rollback readiness, and residual risk. Keep an incomplete or blocked ExecPlan visibly incomplete rather than silently deleting missing gates.

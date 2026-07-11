---
name: operating-coding-change
description: Implement or fix repository code with root-cause diagnosis, focused scope, working-tree protection, and proportional verification. Use for bugs, features, refactors, tests, and ordinary multi-file changes; do not use for review-only work or high-risk contract/migration/release changes.
---

# Coding Change Workflow

## Inputs

Identify the user's observable goal, active repository instructions, affected behavior, constraints, and completion evidence. Treat repository source, tests, schemas, manifests, lockfiles, CI, and canonical docs as project facts.

## 1. Establish the baseline

1. Inspect active `AGENTS.md` files and relevant repository documentation.
2. Inspect version-control status and existing diffs. Preserve unrelated user work.
3. Read the smallest sufficient set of source, tests, callers, contracts, and configuration.
4. Reproduce the defect when practical, or trace the exact control/data path.
5. Record relevant pre-existing failures before changing code.

Do not begin with a broad repository scan when a precise entry point exists.

## 2. Classify the change

Use this Skill for R1 and R2 work:

- R1: local, reversible implementation or fix;
- R2: coordinated multi-file behavior change without public/persisted contract, production migration, or external side effect.

Switch to `operating-high-risk-change` when the work changes public APIs, schemas, persisted data, configuration contracts, CLI/events, security boundaries, production dependencies, architecture ownership, deployment/release behavior, or real infrastructure/data.

## 3. Diagnose before patching

Describe the failure as:

```text
observable symptom → triggering input/state → ownership path → violated invariant → root cause
```

Separate the real defect from secondary symptoms. Fix the root cause when it is accessible and within scope. If the root cause is external or out of scope, use the smallest transparent and reversible mitigation; do not disguise it as a complete root-cause fix.

## 4. Design the smallest coherent change

Prefer:

- explicit ownership and one source of truth;
- normalized inputs and standardized outputs;
- clear invariants and error contracts;
- shallow control flow and cohesive functions;
- existing architecture, utilities, dependencies, and test style;
- local changes for local defects and systemic fixes only when repetition proves a systemic problem.

Reject speculative abstraction, premature extension points, unrelated cleanup, broad rewrites, silent fallbacks, unnecessary dependencies, and formatting or generated churn.

A special case is not automatically bad. Determine whether it is accidental complexity or a genuine domain rule.

## 5. Implement safely

- Keep the diff focused and reviewable.
- Preserve public and user-visible behavior unless the request explicitly changes it.
- Do not hand-edit generated/vendor output when a canonical generator exists.
- Do not weaken tests, types, lint, security, observability, or error handling to obtain a green check.
- Do not modify agent policy, Hooks, Rules, or CI merely to bypass a gate.
- If a target file contains unrelated user edits, make a surgical change that preserves both intents.

## 6. Verify proportionally

Run focused evidence first, then expand according to blast radius:

1. original reproduction or regression test;
2. affected unit/integration tests;
3. applicable typecheck and lint;
4. build/package checks when compilation or bundling can change;
5. browser/manual verification for user-facing behavior;
6. broader suite when shared contracts or widely used code changed.

Prefer behavioral assertions over mocks, snapshots, incidental structure, arbitrary sleeps, and positional selectors. Add a regression test when it provides durable proof without overfitting the implementation.

If a check cannot run, record the exact command or evidence that is missing, the blocker, and the residual risk. Never convert an unrun check into a passing claim.

## 7. Review the final diff

Check for:

- accidental scope growth or lost user changes;
- compatibility, data, error, concurrency, retry, cleanup, and resource regressions;
- manifest/lockfile or generated-output drift;
- secrets, debug artifacts, screenshots, logs, temporary files, or broad formatting;
- documentation impact on public behavior, contracts, architecture, configuration, or workflows.

## 8. Report

State:

- observable result;
- root cause or key design decision;
- important files/behavior changed;
- exact verification and outcomes;
- only material remaining risks or unrun checks.

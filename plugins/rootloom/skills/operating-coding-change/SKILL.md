---
name: operating-coding-change
description: Implement or fix repository code with root-cause diagnosis, focused scope, working-tree protection, and proportional verification. Use for bugs, features, refactors, tests, and ordinary multi-file changes; do not use for review-only work or high-risk contract/migration/release changes.
---

# Direct and scoped coding workflow

## Inputs

Classify the task type and tier before editing. Complete this internal execution contract:

```text
Software 3.0 = Intent + Context + Tools + Constraints + Verification
```

- Intent: observable outcome or failure.
- Context: active guidance and the smallest sufficient source-of-truth paths.
- Tools: repository scripts, tests, logs, runtime checks, or relevant Skills.
- Constraints: scope, non-goals, compatibility, safety, and preserved user work.
- Verification: the evidence that proves completion.

Read or ask only when a missing part materially changes correctness, safety, cost, scope, or destructive impact. Keep this packet internal unless the user requests it, needs a handoff, or the task escalates to Tier 2.

## 1. Establish the baseline

1. Inspect active `AGENTS.md` files and relevant repository documentation.
2. Inspect version-control status and existing diffs. Preserve unrelated user work.
3. Read the smallest sufficient set of source, tests, callers, contracts, and configuration.
4. Reproduce the defect when practical, or trace the exact control/data path.
5. Record relevant pre-existing failures before changing code.

Do not begin with a broad repository scan when a precise entry point exists.

## 2. Classify the task and tier

Use this Skill for:

- Tier 0 Direct: trivial, low-risk, reversible mechanical work with an unambiguous target and minimal verification;
- Tier 1 Scoped: ordinary bugs, feature slices, refactors, tests, or coordinated changes across one bounded surface.

Tier 0 executes directly without a formal plan or root-cause packet. A behavioral defect is Tier 1 unless the correction is demonstrably mechanical.

Escalate to Tier 2 and `operating-high-risk-change` when the task changes public APIs, schemas, persisted data, configuration contracts, CLI/events, security boundaries, production dependencies, architecture ownership, deployment/release behavior, or real infrastructure/data. Also escalate when the root cause remains materially uncertain, multiple hypotheses remain plausible, the failure crosses ownership boundaries, previous repairs failed, or a wrong first fix would have substantial blast radius.

## 3. Gate behavioral fixes before patching

Apply this gate to bugs, regressions, failing tests, incidents, and incorrect runtime behavior. Features, documentation, and mechanical edits need a clear design or ownership decision, not an invented root cause.

Describe the failure as:

```text
observable symptom → triggering input/state → ownership path → violated invariant → root cause
```

Before editing a Tier 1 behavioral defect, material evidence must support the ownership path, violated invariant, and root cause. Separate the real defect from secondary symptoms. If this gate cannot be satisfied within one bounded investigation, escalate instead of guessing.

Fix the violated invariant at its owning boundary. A downstream special case, swallowed exception, arbitrary retry/delay, widened timeout, default value, duplicated state, weakened assertion, or bypassed validation is not a root-cause fix unless repository evidence proves it is the correct domain boundary.

If the root cause is external or out of scope, use only the smallest transparent and reversible mitigation. Report it as `MITIGATION`, including the protected failure mode, known gap, residual risk, and removal or follow-up condition; never disguise it as a complete root-cause fix.

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

Prefer behavioral assertions over mocks, snapshots, incidental structure, arbitrary sleeps, and positional selectors. For a behavioral fix, prefer evidence that the original path fails before the change and passes afterward. When that is impractical, record the equivalent trace, contract, or runtime evidence and the remaining verification gap. Add a regression test when it provides durable proof without overfitting the implementation.

If a check cannot run, record the exact command or evidence that is missing, the blocker, and the residual risk. Never convert an unrun check into a passing claim.

## 7. Review the final diff

Check for:

- accidental scope growth or lost user changes;
- compatibility, data, error, concurrency, retry, cleanup, and resource regressions;
- manifest/lockfile or generated-output drift;
- secrets, debug artifacts, screenshots, logs, temporary files, or broad formatting;
- documentation impact on public behavior, contracts, architecture, configuration, or workflows.

For behavioral fixes, explicitly check `ROOT_CAUSE_ALIGNMENT`: does the diff repair the violated invariant at its owning boundary, or merely suppress a downstream symptom? A mitigation presented as a complete fix fails this gate.

## 8. Report

State:

- observable result;
- root cause or key design decision;
- task tier and `ROOT_CAUSE_ALIGNMENT` outcome when a behavioral defect was fixed;
- important files/behavior changed;
- exact verification and outcomes;
- only material remaining risks or unrun checks.

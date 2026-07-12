---
name: operating-code-review
description: Perform a review-only analysis of code, diffs, pull requests, migrations, or architecture changes. Report evidence-backed findings first by severity with exact locations and concrete fixes; do not modify code unless the user explicitly asks for fixes.
---

# Code Review Workflow

## Scope

Review the requested diff and enough surrounding callers, contracts, tests, configuration, schemas, and generated behavior to assess actual failure modes. Do not turn review into implementation unless asked.

## Review order

1. security, authorization, secret exposure, injection, unsafe deserialization, and unintended external effects;
2. data loss/corruption, migrations, transactions, concurrency, retries, idempotency, recovery, and resource leaks;
3. incorrect behavior, edge cases, error handling, cancellation, timeout, and partial failure;
4. public API/schema/config/CLI/event/persisted-format and user-visible compatibility;
5. build, packaging, generated code, dependency, deployment, and mixed-version behavior;
6. test gaps, nondeterminism, brittle selectors/waits, weak assertions, and missing observability;
7. maintainability only when it creates a concrete correctness or change-risk problem.

## Evidence standard

A finding must identify:

- severity: Critical, High, Medium, or Low;
- exact file and line/symbol;
- failure mode and triggering conditions;
- evidence from code path, contract mismatch, reproduction, or missing durable test;
- smallest concrete correction;
- confidence: verified, strongly inferred, or uncertain.

For material runtime or external evidence, also identify its source, environment, observed time or window, stable artifact/query/trace/correlation reference when available, and freshness/redaction constraints. Treat an unattributed model summary as an unverified lead rather than direct evidence.

Do not report personal style preferences as defects. Separate questions and optional improvements from findings.

## Review procedure

- Start from the failure surface, not from the supplied explanation. Treat reported issues and prior reviews as leads. Build a small risk map of the owning path, its callers/consumers, and at least one analogous sibling implementation that could contain the same class of defect.
- Attempt to disprove the strongest completion claim. For a fix, look for a trigger that still violates the invariant; for a new mechanism, ask what decision changes when it fires and whether deletion or a native control gives the same protection.
- Read the full relevant diff and affected callers, not only the changed function.
- Compare behavior against source-of-truth schemas, manifests, docs, CI, and tests.
- Check negative paths, cleanup, retries, cancellation, timeouts, partial failure, and mixed versions.
- Verify tests assert behavior rather than only mocks or incidental implementation.
- For migrations, inspect volume assumptions, lock behavior, old/new coexistence, rollback/compensation, and destructive timing.
- For UI, inspect rendered evidence, accessibility, interaction states, responsive behavior, console/runtime failures, and screenshot coverage when available.
- Do not claim a test, reproduction, screenshot, or external check was performed unless it was.

### Discovery yield

Do not stop after confirming the user's reported issues. Separate:

- confirmed leads — supplied findings independently verified;
- novel findings — defects found by caller, sibling, negative-path, or contract exploration;
- cleared surfaces — concrete high-risk paths inspected without a finding;
- unreviewed surfaces — gaps that limit the conclusion.

An audit may legitimately have no novel finding, but “no material findings” requires the cleared and unreviewed surfaces. Generic statements such as “reviewed thoroughly” are not evidence.

### Mechanism value

Treat a proposed guard, flag, journal, abstraction, or workflow step as unjustified unless the review can name: the observable failure, owning boundary, executable enforcement, regression proof, and decision it changes. If one is missing, prefer deletion, a smaller native mechanism, or an honest documented limitation.

## Root-cause alignment

For a bug fix, regression, incident repair, or behavior-changing workaround, trace the observed failure to its owning boundary and ask whether the diff repairs the violated invariant or only suppresses a downstream symptom.

Treat these as evidence of a possible false fix unless the repository proves they belong at the owning boundary: caller-only special cases, swallowed exceptions, arbitrary retries or delays, widened timeouts, silent defaults, duplicated state, weakened tests or validation, and checks that exercise only the new patch branch rather than the original failure path.

Require one outcome:

```text
ROOT_CAUSE_ALIGNMENT: PASS | FAIL | NOT_APPLICABLE
```

- `PASS`: the evidence supports the stated root cause and the repair belongs at the owning boundary.
- `FAIL`: root cause is unsupported, a plausible alternative remains, the change only masks a symptom, or a mitigation is presented as a complete fix.
- `NOT_APPLICABLE`: the change is not a defect repair.

Report a failed alignment as a severity-ranked finding according to its actual impact. Verify that regression evidence exercises the original failure path; if fail-before/pass-after evidence is impractical, require an equivalent trace or contract proof and record the gap.

Also require the verification set to cover the violated invariant at its owning boundary and an adjacent negative, edge, or alternate path. Passing a test written only around the new conditional can still be a false fix.

## Output

Start with `## Findings`, ordered by severity. Each finding should be concise but complete. Then state `ROOT_CAUSE_ALIGNMENT`. Include `## Questions` and `## Optional Improvements` only when useful. Finish with `## Verification Gaps` when relevant.

If no material findings exist, state that explicitly and list cleared surfaces, the strongest counterexample attempted, the analogous implementation checked, and unavailable evidence.

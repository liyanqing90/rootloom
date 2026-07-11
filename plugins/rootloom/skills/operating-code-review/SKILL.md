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

Do not report personal style preferences as defects. Separate questions and optional improvements from findings.

## Review procedure

- Read the full relevant diff and affected callers, not only the changed function.
- Compare behavior against source-of-truth schemas, manifests, docs, CI, and tests.
- Check negative paths, cleanup, retries, cancellation, timeouts, partial failure, and mixed versions.
- Verify tests assert behavior rather than only mocks or incidental implementation.
- For migrations, inspect volume assumptions, lock behavior, old/new coexistence, rollback/compensation, and destructive timing.
- For UI, inspect rendered evidence, accessibility, interaction states, responsive behavior, console/runtime failures, and screenshot coverage when available.
- Do not claim a test, reproduction, screenshot, or external check was performed unless it was.

## Output

Start with `## Findings`, ordered by severity. Each finding should be concise but complete. Then include `## Questions` and `## Optional Improvements` only when useful. Finish with `## Verification Gaps` when relevant.

If no material findings exist, state that explicitly and list any unreviewed surfaces or checks that were unavailable.

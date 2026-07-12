---
name: record-engineering-decision
description: Create or update a durable repository-owned engineering decision record with alternatives, evidence provenance, consequences, verification, and supersession links. Use when architecture ownership, public or persisted contracts, dependencies, security posture, data strategy, or operational policy changes in a way future agents and maintainers must remember; do not use for routine bug fixes, mechanical edits, transient incidents, or plans that have not been accepted.
---

# Record an engineering decision

Capture the smallest durable decision that will change future implementation, review, migration, or operational choices.

## 1. Decide whether a record is warranted

Create or update a record only when the decision is accepted and at least one applies:

- it establishes or changes architecture ownership or dependency direction;
- it changes a public, persisted, security, data, deployment, or operational contract;
- it adopts or rejects a material dependency or platform strategy;
- a future maintainer could reasonably reopen the same tradeoff without this context;
- it supersedes a previous durable decision.

Do not record routine implementation details, speculative options, task status, raw incident logs, or facts already owned by a stronger canonical document.

## 2. Find the repository convention

Inspect active `AGENTS.md`, contribution guidance, documentation indexes, and existing ADR or decision directories. Reuse the repository's naming, numbering, status vocabulary, and template.

When no convention exists, copy `assets/DECISION.template.md` to:

```text
docs/decisions/YYYY-MM-DD-<short-kebab-title>.md
```

Create only the target record and the minimum directory/index update needed to make it discoverable.

## 3. Ground the record in evidence

Separate observed facts from interpretation. For material runtime or external evidence, record:

- source and environment;
- observation time or time window;
- stable artifact, query, issue, trace, or correlation reference when available;
- freshness and redaction notes;
- whether the statement is verified fact, inference, or unresolved uncertainty.

Reference durable repository paths, tests, schemas, manifests, or sanitized artifacts. Never copy credentials, personal data, proprietary payloads, or raw logs merely to make the record self-contained.

## 4. Write the decision, not a meeting transcript

Complete the template with:

- context and constraints;
- the decision and its owning boundary;
- serious alternatives and why they were rejected;
- positive, negative, and operational consequences;
- verification and revisit triggers;
- superseded or superseding records.

State unknowns honestly. Evidence provenance improves auditability; it does not prove the conclusion true.

## 5. Connect guidance without duplication

If future agents must consult this decision, add one concise pointer to the nearest appropriate user-owned `AGENTS.md` section or canonical documentation index. Do not paste the record's rationale into `AGENTS.md`, and never edit a generated managed block directly.

## 6. Verify and report

Check links, naming, status, dates, referenced paths, redaction, and compatibility with the repository convention. Run the repository's documentation or validation command when available.

Report the decision path, status, key consequence, verification, and any unresolved evidence gap. Do not claim that recording a decision enforces it; source, schemas, tests, Rules, CI, and runtime controls remain the executable boundaries.

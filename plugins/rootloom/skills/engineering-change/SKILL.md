---
name: engineering-change
description: Execute a personal, single-agent engineering change from risk classification through evidence, root-cause diagnosis, a scoped change contract, implementation, intelligent verification, and a final review summary. Use for non-trivial repository changes when the user wants Rootloom's everyday quality loop without enterprise approval or audit machinery.
---

# Engineering change

Run one focused engineering loop. Stay single-agent unless the user explicitly asks for delegation.

Default sequence: Evidence → Diagnosis → Change Contract → Implementation → Verification → Final Review Summary.

## 1. Route the task

Classify the request before editing:

- **Tier 0 Direct** — mechanical, local, reversible, and directly verifiable;
- **Tier 1 Scoped** — behavioral change or defect with a bounded ownership path;
- **Tier 2 Governed** — public or persisted contracts, schemas, migrations, security, infrastructure, destructive effects, or materially uncertain blast radius.

Use `operating-coding-change` for Tier 0/1 discipline and `operating-high-risk-change` for Tier 2. Do not use this Skill to bypass an approval gate.

## 2. Load project intelligence

Read the closest `AGENTS.md` plus `.project-memory/architecture.md`, `.project-memory/known-risks.json`, `.project-memory/failures.json`, and `.project-memory/decisions.json` when they exist. Treat memory as leads and repository evidence as truth. Never create or update memory silently; use `project-memory` only when the knowledge is durable and verified.

## 3. Establish evidence and diagnosis

Inspect the observable path and its owning boundary before editing. For a defect, record:

- the trigger and observed failure;
- at least two plausible causes when the root cause is uncertain;
- evidence that rejects the strongest alternative;
- the violated invariant and evidence-backed root cause;
- `ROOT_CAUSE_ALIGNMENT: PASS` before implementation.

For a feature or mechanical change, use `ROOT_CAUSE_ALIGNMENT: NOT_APPLICABLE` and state the intended invariant instead.

## 4. Form the change contract

Keep an internal contract for ordinary work and expose it for Tier 2 or when asked. It must name:

- allowed files or module boundary;
- forbidden or explicitly excluded scope;
- public/persisted compatibility expectations;
- required verification for the original path, owning invariant, and an adjacent path;
- rollback and remaining risk.

## 5. Implement once, in scope

Use existing architecture and dependencies. Preserve unrelated user changes. Fix the invariant at its owner, not a downstream symptom. Do not add a wrapper, flag, record, or approval step unless it changes a concrete decision.

Before deleting a secret-like file, `.env`, migration, or database artifact, stop and obtain confirmation for the exact path. Ordinary source-file deletion still requires careful diff review but not a separate state machine.

## 6. Verify intelligently

Choose checks from the changed behavior, not only from convenient commands. Map each material change to:

- the original or primary behavior;
- the owning-boundary invariant;
- an adjacent negative or alternate path;
- the smallest focused test, then broader checks proportional to blast radius.

Run repository-owned commands and observe their exit status. Classify failures as introduced, pre-existing, environmental, or unverified.

For a machine-readable local summary, run:

```bash
python3 <skill-dir>/scripts/finalize_change.py \
  --repo /absolute/path/to/repository \
  --output /absolute/path/to/run \
  --risk medium \
  --verify 'python3 -m unittest tests.test_example' \
  --remaining-risk 'Describe only a material remaining risk'
```

The helper does not run a shell. It writes ordinary `diff.patch`, `test.log`, and `summary.json` files, and it supports repositories before their first commit. Verification commands must preserve the tracked patch and captured changed/untracked path set; any drift makes the bundle fail, and dangerous deletions are checked again. It refuses sensitive deletions unless every exact path is repeated with `--confirm-dangerous-delete` after the user has confirmed it.

## 7. Challenge and summarize

Inspect the actual diff, one analogous path, and the strongest plausible counterexample. Remove complexity that does not earn its keep.

Finish with:

```json
{
  "changed_files": [],
  "risk": "low | medium | high",
  "tests": [],
  "verification_preserved_capture": true,
  "remaining_risks": []
}
```

Report the observable outcome first, then exact verification and only material remaining risk.

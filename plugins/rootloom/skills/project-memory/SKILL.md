---
name: project-memory
description: Initialize, inspect, and update Rootloom's lightweight repository-owned project memory for architecture, known risks, durable decisions, and evidence-backed failure lessons. Use when a user asks Rootloom to remember project knowledge or when a verified change produces reusable failure or risk knowledge.
---

# Project memory

Project memory is optional, explicit, local, and reviewable. It lives in `.project-memory/` so teams can version it like documentation.

## Rules

- Read memory as a lead; verify it against current source, tests, schemas, and runtime evidence.
- Record only durable facts or explicitly labeled hypotheses. Do not copy task transcripts or raw sensitive payloads.
- Never update memory merely because a task completed. Update it only when the lesson will change a future engineering decision.
- Prefer the existing `record-engineering-decision` Skill for accepted architecture or contract decisions; keep `decisions.json` as a concise index.

## Commands

Initialize:

```bash
python3 <skill-dir>/scripts/project_memory.py --repo /path/to/repo init
```

Show a compact context bundle:

```bash
python3 <skill-dir>/scripts/project_memory.py --repo /path/to/repo context
```

Record an evidence-backed failure lesson:

```bash
python3 <skill-dir>/scripts/project_memory.py --repo /path/to/repo record-failure \
  --summary 'Relay reconnect failed' \
  --root-cause 'Connection state transition race' \
  --fix 'Serialize transitions in the connection state machine' \
  --path src/relay.py
```

Record a known risk or decision index entry with the corresponding subcommand. Inspect the diff before accepting the update.

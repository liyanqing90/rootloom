# Guidance design

The system uses a small instruction hierarchy instead of one giant prompt. The exact installable global result is [`plugins/rootloom/assets/system/AGENTS.md`](../plugins/rootloom/assets/system/AGENTS.md); a polished project example is [`examples/AGENTS.project.md`](../examples/AGENTS.project.md).

## What comes from OpenAI's current guidance

OpenAI's [GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model) recommends lean prompts, stating each rule once, defining autonomy and approval boundaries, and keeping domain context, hard constraints, and success criteria explicit. Codex's [AGENTS.md documentation](https://developers.openai.com/codex/agent-configuration/agents-md) adds a natural hierarchy: one global file, then root-to-current-directory project guidance, with closer files taking precedence.

That leads to four design rules:

1. Put stable personal operating policy in global `AGENTS.md`.
2. Put repository facts and commands in project `AGENTS.md`.
3. Put reusable multi-step procedures in Skills rather than repeating them in every task.
4. Keep executable policy and proof in Rules, sandboxing, scripts, tests, and CI.

The default 32 KiB project-instruction budget is a ceiling, not a target. This project's managed global template stays below 16 KiB, and generated project guidance is intentionally much smaller.

## What we retain from GEB

The [GEB system](https://chunxiang.space/geb-system) contains two valuable ideas:

- documentation should stay locally aligned with the code and contracts it describes;
- global, module, and local context should form a hierarchy rather than a flat encyclopedia.

This project translates those ideas into Codex-native layers:

| GEB idea | Rootloom form |
| --- | --- |
| Project constitution | Root `AGENTS.md` managed facts plus durable invariants |
| Local module map | Nested `AGENTS.md` only at genuine module boundaries |
| Code/document feedback loop | Update guidance when commands, contracts, ownership, or architecture change |
| Cold-start seeding | Deterministic `SessionStart` scanner |

## What we reject from GEB

The system does not copy the GEB prompt wholesale. It deliberately rejects:

- identity role-play and mandatory forms of address;
- instructions about hidden reasoning language or internal thought structure;
- universal file-length rules unrelated to repository evidence;
- one-line inventories of every file;
- mandatory L3 header comments in every source file;
- blocking all work until documentation has been expanded;
- claims that prose and code can be perfectly isomorphic.

Those patterns create prompt weight, stale duplication, noisy diffs, and false confidence. Source, schemas, tests, manifests, and CI remain the executable truth; `AGENTS.md` points to them and records only decisions an agent would otherwise miss.

## The refined global result

The global working agreement has seven compact concerns:

- authority and source-of-truth precedence;
- autonomy boundaries for answer/review versus implementation requests;
- focused engineering defaults and working-tree protection;
- evidence and completion standards;
- workflow routing to installed Skills;
- automatic project-guidance behavior;
- delegation and communication limits.

It intentionally contains no repository commands, framework preferences, project architecture, personality prose, or duplicated tool manuals.

## The refined project result

The deterministic managed block owns facts that can be regenerated safely:

- purpose from canonical metadata;
- source-of-truth paths;
- top-level map;
- package manager and canonical commands;
- verification contract.

The user-owned section below it may contain only durable, evidence-cited invariants such as ownership direction, generated-code boundaries, public or persisted contracts, and canonical architecture or migration documents.

Nested guidance is created lazily. A folder deserves its own `AGENTS.md` only when it has a distinct manifest, commands, ownership, contracts, or operational rules. Ordinary directories and individual files do not.

## Maintenance test

Keep a guidance sentence only if it changes a future implementation, review, verification, or safety decision; remains useful across ordinary code changes; is supported by a real path; belongs at that scope; and is not already stated by a stronger source of truth.

When any answer is no, delete the sentence or leave it in the source document that already owns it.

<p align="center">
  <img src="plugins/rootloom/assets/icon.svg" width="112" alt="Rootloom logo">
</p>

<h1 align="center">Rootloom</h1>

<p align="center">
  <strong>Reliable Codex engineering, woven from the roots up.</strong>
</p>

<p align="center">
  <a href="README.zh-CN.md">简体中文</a> · <strong>English</strong>
</p>

<p align="center">
  <a href="https://github.com/liyanqing90/rootloom/actions/workflows/ci.yml"><img src="https://github.com/liyanqing90/rootloom/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/liyanqing90/rootloom?color=6D5EF7" alt="MIT license"></a>
  <a href="https://github.com/liyanqing90/rootloom/releases"><img src="https://img.shields.io/github/v/release/liyanqing90/rootloom?display_name=tag&sort=semver" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-39B98F" alt="Python 3.11+">
</p>

![Rootloom brand: evidence roots woven through capability frames into verified delivery](assets/rootloom-brand.webp)

Rootloom lets a team install only the Codex capabilities it actually wants—without forcing every project to adopt subagents, Hooks, or a monolithic prompt:

| Capability | Shipped result |
| --- | --- |
| Global policy | A refined, installable global [`AGENTS.md`](plugins/rootloom/assets/system/AGENTS.md) |
| Project context | Automatic evidence-backed root guidance plus lazy nested guidance |
| Guidance quality | `$refine-project-guidance` for durable semantic invariants without file-level documentation churn |
| Engineering workflows | Ordinary change, review-only, high-risk, and opt-in high-assurance Skills |
| Model routing | Four custom Agent TOMLs with explicit model, reasoning, role, and sandbox defaults |
| Runtime and commands | A quality-first profile, four-thread concurrent cap, and tested command Rules |
| Evidence and memory | Attributable runtime/external evidence plus optional repository-owned engineering decision records |
| Deterministic process | A staged `codex exec` runner with one writer, scope gates, verification, and independent review |

The repository, marketplace, and plugin share one stable public ID: `rootloom`.

> **Maturity:** Rootloom is an early-stage, single-maintainer project. “Reliable” is the design goal, not a claim of proven defect reduction. Deterministic gates cover selected process mechanics, not whether a model's evidence or root-cause diagnosis is true. Read [Maturity, guarantees, and compatibility](docs/maturity.md).

## Why Rootloom

**Root** is repository truth: source, schemas, tests, project guidance, and root-cause evidence. **Loom** is the structure that weaves Skills, Hooks, Rules, Agents, and verification into coherent capability layers. Seeding context is the first thread, not the whole product.

![Rootloom capability map: five selectable levels](assets/hero.svg)

## Why a system instead of a longer prompt

OpenAI's current [GPT-5.6 guidance](https://developers.openai.com/api/docs/guides/latest-model) recommends lean prompts, stating rules once, and defining autonomy, approval boundaries, constraints, and success criteria clearly. Codex already gives each concern a better home:

- [`AGENTS.md`](https://developers.openai.com/codex/agent-configuration/agents-md) for stable global and local guidance;
- [Skills](https://developers.openai.com/codex/build-skills) for reusable procedures with progressive disclosure;
- [custom agents](https://developers.openai.com/codex/agent-configuration/subagents) for role, model, reasoning, sandbox, MCP, and app configuration;
- [Rules](https://developers.openai.com/codex/agent-configuration/rules) for command policy;
- [Hooks](https://developers.openai.com/codex/hooks) for deterministic lifecycle work and audits;
- profiles, scripts, tests, and CI for runtime defaults and executable proof.

Putting everything into `AGENTS.md` wastes context and turns advice into fake enforcement. This project keeps each layer narrow and makes its actual enforcement boundary explicit.

## Install

Requirements:

- Codex CLI or the Codex desktop app with plugin and lifecycle-Hook support;
- Git;
- Python 3.11 or newer.

Add the GitHub marketplace and install the stable package ID:

```bash
codex plugin marketplace add liyanqing90/rootloom
codex plugin add rootloom@rootloom
```

Start a new Codex task and choose the capability level before trusting optional Hooks:

| Preset | What it enables | Subagents |
| --- | --- | --- |
| `skills-only` | Bundled Skills only; no user policy/runtime assets; lifecycle Hooks disabled | No |
| `guidance` | Global policy + automatic project context | No |
| `engineering` | Guidance + command safety; recommended for normal coding | No |
| `delegated` | Engineering + four-role configuration and advisory delegation audit | Configured; native role/model routing is not attested on the verified spawn surface |
| `full` | Delegated + strict sequential-runner profile | Configured; use the runner for attested routing |

Then ask Codex to plan and apply the level—no hand-editing required:

```text
$setup-rootloom
Show the capability levels, then plan and apply the engineering preset.
```

Use `full` when you want this repository's complete system. Advanced users can compose the stable dimensions `global-policy`, `project-context`, `command-safety`, `delegation-control`, and `high-assurance`; dependencies are closed automatically.

After setup, open `/hooks` and review the two bundled commands. Trust the current definition if the selected layer enables either Hook:

- `SessionStart` performs safe local project-guidance seeding only in `project-context`.
- `SubagentStart` audits the cumulative child budget and named role/model routing only in `delegation-control`.

The setup Skill is plan-first and serializes each Codex-home transaction with a process lock. It prepares backups and a recovery manifest before mutation, writes atomically, records hashes and modes, and compensates the complete transaction—including state-commit failures. It refuses user-owned conflicts unless you explicitly authorize those exact replacements.

See [Setup, update, and rollback](docs/setup.md) for the full contract.

## What the setup installs

| Capability | Path | Purpose |
| --- | --- | --- |
| `global-policy` | `~/.codex/AGENTS.md` | Lean global working agreement for authority, autonomy, engineering, evidence, routing, delegation, and communication |
| `project-context` / Hooks | `~/.codex/.rootloom/components.json` | Independently enable project seeding and subagent auditing |
| `delegation-control` | `~/.codex/config.toml` | Only `agents.max_threads = 4`, `max_depth = 1`, and interruption visibility; all unrelated keys are preserved |
| `high-assurance` | `~/.codex/high-assurance.config.toml` | Sol/high, on-request, workspace-write quality-first CLI profile |
| `delegation-control` | `~/.codex/agents/*.toml` | Atomic Terra evidence + Sol diagnosis, implementation, and verification role set |
| `command-safety` | `~/.codex/rules/rootloom.rules` | Local commit allowed; publication, infrastructure, and destructive commands governed separately |

Setup deliberately leaves your ordinary model, reasoning level, approval policy, sandbox, providers, MCP servers, plugins, and apps unchanged. It will not split `delegation-control` into a misleading partial role set.

## The two `AGENTS.md` results

The repository contains the actual polished outputs, not only prose about them:

- [Global working agreement](plugins/rootloom/assets/system/AGENTS.md) — installed across projects.
- [Polished project example](examples/AGENTS.project.md) — managed facts plus concise user-owned invariants.
- [This repository's own AGENTS.md](AGENTS.md) — a live generated-and-refined example.

### Global guidance owns stable behavior

It defines authorization, reversible autonomy, tiered task intake, working-tree protection, root-cause and scope defaults, evidence standards, workflow routing, automatic project guidance, delegation limits, and concise communication. It contains no repository commands, framework preferences, project architecture, or personality role-play.

### Project guidance owns repository facts

The `SessionStart` Hook deterministically extracts purpose, source-of-truth files, top-level structure, package manager, canonical commands, CI, and module boundaries. It writes only a marker-delimited block and preserves everything outside it.

`$refine-project-guidance` adds only durable, evidence-cited invariants that change future decisions: ownership direction, generated-code boundaries, public or persisted contracts, and canonical architecture/migration/verification documents.

Nested guidance is seeded only for a real module boundary with distinct manifests, commands, ownership, or invariants. The system never creates mandatory per-file L3 comments.

## Tiered task intake and root-cause gates

Rootloom uses one risk vocabulary across its operating workflows:

| Tier | Use | Intake and proof |
| --- | --- | --- |
| Tier 0 Direct | Trivial, low-risk, reversible mechanical work | Execute directly with the smallest relevant check |
| Tier 1 Scoped | Ordinary bugs, feature slices, refactors, and bounded multi-file work | Keep `Intent + Context + Tools + Constraints + Verification` internal; require targeted evidence |
| Tier 2 Governed | Cross-boundary, high-risk, externally mutating, or materially uncertain work | Expose a governed task packet, impact map, compatibility/rollback, and explicit gates |

Behavioral defects are Tier 1 or higher unless the correction is demonstrably mechanical. Tier 1 diagnosis traces symptom → trigger → ownership path → violated invariant → root cause. Tier 2 adds competing hypotheses and a GO/NO_GO gate. A reversible workaround is reported as `MITIGATION`; it is never presented as a complete root-cause fix.

The task packet stays internal for Tier 0 and Tier 1 unless the user requests it, needs a handoff, or a blocker requires a decision. This preserves the useful intake discipline without turning small changes into ceremony.

## Workflow series

| Skill | When it runs | Key contract |
| --- | --- | --- |
| `$setup-rootloom` | Explicit install, update, audit, layer change, or rollback | Choose a capability preset; plan first; never silently replace user policy |
| `$seed-project-guidance` | Missing or structurally stale guidance | Deterministic facts only |
| `$refine-project-guidance` | First non-trivial task, repeated mistakes, or architecture/contract changes | Durable project-specific invariants only |
| `$record-engineering-decision` | An accepted architecture, contract, dependency, security, data, or operational choice must survive the task | Repository-owned context, alternatives, provenance, consequences, and revisit triggers |
| `$operating-coding-change` | Tier 0 Direct and Tier 1 Scoped implementation | Software 3.0 intake, tiered root-cause gate, focused diff, proportional verification |
| `$operating-code-review` | Review-only requests | Evidence-backed findings first; no edits |
| `$operating-high-risk-change` | Tier 2 Governed APIs, schemas, data, security, infrastructure, deploy, release, or uncertain root cause | Governed task packet, ExecPlan, diagnosis, compatibility, rollback, authorization gates |
| `$high-assurance-coding-change` | Explicit controlled multi-agent request | Evidence → diagnosis gate → one writer → deterministic verification → independent review |

Normal tasks stay single-agent. The high-assurance workflow is opt-in because multiple agents add token use, latency, and coordination risk.

## Model routing

When `delegation-control` is selected, the role split optimizes total delivery cost, not per-call price:

```text
evidence_explorer       gpt-5.6-terra / medium / read-only
root_cause_reviewer     gpt-5.6-sol   / xhigh  / read-only
implementation_worker   gpt-5.6-sol   / high   / workspace-write
verification_reviewer   gpt-5.6-sol   / xhigh  / read-only
```

Terra compresses bounded evidence. Sol makes the expensive decisions, writes the code, and verifies the result. A weaker model never owns the final root cause, implementation, or acceptance decision.

Custom Agent TOMLs are the intended model-routing source of truth. On the currently verified native multi-agent v2 surface, Rootloom cannot attest that a spawned child actually received a requested custom `agent_type`; setup validation therefore reports native routing `NOT_READY`. The files remain useful configuration input, but only the sequential runner explicitly applies and records each role/model today. Skills own sequence and gates; Hooks only audit. Parent live permissions can override child defaults, so use the runner when hard stage isolation matters.

## Why four can still look like ten

`agents.max_threads = 4` limits **concurrently open threads**. It does not limit how many children a task can create over its lifetime. Four agents can finish, close, and be replaced by six more while never exceeding four open threads.

The optional `delegation-control` layer adds two more controls:

- a global and Skill-level behavioral total budget of four children per task;
- a `SubagentStart` advisory counter that warns the UI and tells the fifth child to stop and report.

The current Hook API cannot cancel a child at start. The over-budget child has already started; the Hook can only inject a stop-and-report instruction and depends on that model following it. This is visibility and behavioral guidance, not prevention. The deterministic high-assurance runner is the strict path.

## Git commit no longer falls into the approval trap

The Rules are tested to produce:

```text
git commit          → allow
git push            → prompt
git reset --hard    → forbidden
```

A local commit is reversible repository history; it is not remote publication. Push, release, package publication, infrastructure mutation, and destructive operations remain separately governed.

Rules use the most restrictive matching result. If another broad rule says `git → prompt`, it overrides `git commit → allow`. Also, `approval_policy = "never"` cannot answer a prompt, so prompt-gated commands fail in non-interactive execution. Codex command Rules are an evolving argv-prefix policy surface: a wrapped command such as `bash -c 'git ...'` is matched as `bash`, not as the nested Git argv, and may fall through to broader policy. Rootloom does not treat Rules as a shell security boundary. The setup guide explains how to inspect decisions with `codex execpolicy check`.

## High-assurance deterministic route

When the native spawn surface cannot attest the requested custom role/model—or when exact order matters—run the bundled sequential pipeline:

```bash
python3 <high-assurance-skill-dir>/scripts/run_pipeline.py \
  --repo /absolute/path/to/repo \
  --task /absolute/path/to/task.md \
  --sensitive-path 'private/**' \
  --bind-verification-path verify-1:scripts/acceptance.sh \
  --verify 'make focused-test' \
  --verify 'make check'
```

The runner loads the same four Agent TOMLs and enforces a repository lock, clean baseline, read-only stage snapshots, one writer, exact allowed paths, unchanged Git index, structured outputs, deterministic verification, independent review, and at most one repair cycle. It fingerprints detected verification entrypoints before the writer, rechecks the relevant entrypoints before each verification command, and confirms repository immutability immediately afterward. Bound entrypoints include directly executed repository scripts, command-scoped `--bind-verification-path` stability dependencies, `make` files, JavaScript package manifests, pytest configuration files, missing common candidates that could take precedence later, and every repository-internal symlink component plus final target contents. Operator bindings and direct scripts must resolve to existing regular files. With multiple user commands, use `verify-N:path`; the bare path form is retained only when one user command makes the association unambiguous. It supports Linux, macOS, and WSL; native Windows is not supported. Artifacts are private and must live outside the target repository.

Known secret-like untracked names are metadata-only before any content fingerprinting. Use repeatable `--sensitive-path path` or `--sensitive-path 'directory/**'` rules for repository-specific names, and `--redact-untracked-dotfiles` when every untracked dotfile should be metadata-only. These controls redact automatic artifacts and supplied prompts; they do not prevent read-capable Evidence, Diagnosis, Implementation, or Review stages from opening repository files. Use a secret-free worktree or OS/container mounts when access denial is required.

Metadata-only paths are also acceptance-protected: after the writer returns, the Runner rejects any detected creation, modification, or deletion of ignored or sensitive visible-untracked paths even when `allowed_paths` includes them. This is a post-write machine gate, not OS-level write prevention or rollback; a failed run may leave the protected filesystem change in place for operator recovery. A necessary deletion requires one exact `--allow-protected-path-delete path`; globs and directories are rejected, the path is preflighted before the writer runs, `--allow-dirty` and repair cycles are rejected, the old content is never read or backed up, and the run becomes deletion-only: ordinary code edits, renames, moves, or visible file creations must happen in a separate run. A successful model review ends with `HUMAN_REVIEW_REQUIRED` exit 10 rather than automated PASS. Repository topology is checked at startup, after every writer, after deterministic verification, and after final review.

See [Architecture](docs/architecture.md) for the complete enforcement boundary.

## GEB: keep the insight, remove the prompt debt

The [GEB system](https://chunxiang.space/geb-system) correctly emphasizes hierarchical local context and a code/document feedback loop. This project retains those ideas as global → root → genuine-module guidance and automatic seeding.

It rejects identity role-play, hidden-thinking instructions, universal file-length laws, exhaustive L2 inventories, mandatory L3 source headers, and documentation expansion that blocks unrelated work. Those patterns conflict with lean prompting and create stale duplicated terrain.

Read the detailed [official-guidance and GEB analysis](docs/guidance-design.md).

## Why there is no core MCP server

The core needs local Git/filesystem evidence and native Codex configuration. An MCP server would add another process and trust surface without adding a missing capability.

Use MCP narrowly when a custom role genuinely needs an external source—internal docs, issue tracking, observability, or deployment—and configure that role's tools and approvals. Record environment, observation time/window, a stable artifact/query/trace reference, freshness/redaction, and fact-versus-inference status for material evidence. Do not make every coding task inherit an integration merely to complete an architecture checklist.

The strict runner remains offline. Collect authorized runtime evidence before the run and pass only bounded, sanitized material. Facts and reproductions must reference stable provenance IDs; this proves reference integrity, not that the referenced path, test, line, or claim is true. Repository snapshots content-hash tracked and ordinary visible-untracked deliverables. Ignored paths and known or configured sensitive visible-untracked paths are classified first, remain metadata-only without a content hash, and never enter runner patches or Reviewer prompts. Verification entrypoints consume that same classification: a protected harness or resolved target is rejected before any content read or hash. Built-in name matching is intentionally finite and cannot discover every secret. Ignored enumeration fails closed above a configurable path budget. Each diagnosis requirement must map to a successful machine command ID, including at least one user-supplied verification command rather than only `git diff --check`; this proves execution linkage and stability dependencies, not semantic adequacy, actual dependency use, or complete hidden-argument parsing. Pytest positional paths such as `pytest tests/unit` and `pytest tests/test_new.py` are selection scope rather than executable entrypoints.

## Safety model

- Project seeding is local, bounded, deterministic, standard-library-only, and network-free. It excludes symlinked/out-of-repository evidence, serializes writers through the Git common directory, and skips safely if guidance changes during generation.
- Unmarked guidance, overrides, symlinks, untrusted repositories, opted-out projects, temporary/vendor/cache trees, secret-like content, and malformed managed blocks are preserved or rejected.
- Global setup is explicit, process-locked, pre-manifested, hash-checked, mode-preserving, rollback-aware, and compensates caught apply/rollback failures. It is not yet crash-consistent across `SIGKILL`, host failure, or power loss.
- Read-only roles disable apps by default; only one standard role is write-capable.
- Rules, sandboxing, Hooks, Skills, and model instructions are defense in depth, not a substitute for OS policy, credentials, branch protection, review, or CI.

## Compatibility policy

Normal CI tests a pinned Codex CLI baseline on Linux. A separate scheduled Linux workflow probes the latest CLI and is informational until maintainers review and adopt an upstream change. Both run an offline integration-shape smoke covering local marketplace installation, plugin discovery, full setup/status/validation, profile parsing, command Rules, complete rollback, and preservation of pre-existing config. They do not execute live models, attest model aliases, exercise interactive Hooks, or certify Windows/macOS behavior. See [Maturity, guarantees, and compatibility](docs/maturity.md).

## Update

```bash
codex plugin marketplace upgrade rootloom
codex plugin add rootloom@rootloom
```

Review the updated Hook definition, start a new task, and invoke `$setup-rootloom` again. Its plan shows only changed managed assets.

## Development

```bash
git clone https://github.com/liyanqing90/rootloom.git
cd rootloom
make check
make compatibility-smoke
```

`make check` validates the marketplace, plugin, Hooks, all Skills and UI metadata, setup assets, Python/SVG syntax, links, release hygiene, secret-like content, command Rules, seeder behavior, setup/rollback, subagent budget, and deterministic runner gates. `make compatibility-smoke` exercises the installed plugin lifecycle against the active Codex CLI without credentials or network-dependent model calls.

The live smoke test uses a disposable `CODEX_HOME`:

```bash
make smoke
```

## Documentation

- [Brand system and asset usage](docs/brand.md)
- [Architecture and enforcement boundaries](docs/architecture.md)
- [Guidance design and GEB analysis](docs/guidance-design.md)
- [Setup, update, rollback, commit policy, and subagent limits](docs/setup.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## License

[MIT](LICENSE) © 2026 liyanqing.

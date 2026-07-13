<p align="center">
  <img src="plugins/rootloom/assets/icon.svg" width="112" alt="Rootloom logo">
</p>

<h1 align="center">Rootloom</h1>

<p align="center">
  <strong>A personal quality layer that helps Codex write code to engineering standards.</strong>
</p>

<p align="center">
  <a href="README.zh-CN.md">简体中文</a> · <strong>English</strong>
</p>

<p align="center">
  <a href="https://github.com/liyanqing90/rootloom/actions/workflows/ci.yml"><img src="https://github.com/liyanqing90/rootloom/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/liyanqing90/rootloom?color=6D5EF7" alt="MIT license"></a>
  <a href="https://github.com/liyanqing90/rootloom/releases"><img src="https://img.shields.io/github/v/release/liyanqing90/rootloom?display_name=tag&amp;sort=semver" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-39B98F" alt="Python 3.11+">
</p>

<p align="center">
  <img src="assets/rootloom-brand.webp" width="920" alt="Rootloom weaving repository context into a verified engineering change">
</p>

Rootloom Personal Core keeps the part an individual developer uses every day:

1. decide how risky a task really is;
2. trace defects to the owning invariant instead of accepting a surface patch;
3. constrain the change before editing;
4. choose verification from changed behavior;
5. keep reusable project and failure knowledge.

It is single-agent by default. Human approval state machines, protected-deletion commitments, immutable Artifact chains, hardened shared-environment locks, multi-agent audit runners, and setup recovery journals are not part of `main`.

## Product split

| Product | Branch | Purpose |
| --- | --- | --- |
| Rootloom Personal Core 2.x | `main` | Everyday risk-aware engineering for individual Codex users |
| Rootloom Enterprise Assurance 1.2.19 | [`codex/enterprise-assurance`](https://github.com/liyanqing90/rootloom/tree/codex/enterprise-assurance) | Preserved audited workflow with Human Review, protected deletion, strict Runner, and recovery machinery |

The split is intentional, not a feature downgrade. Enterprise Assurance remains available as a separate product line; personal users no longer pay its complexity cost.

<p align="center">
  <img src="docs/diagram/architecture.svg" width="980" alt="Rootloom Personal Core and Enterprise Assurance product architecture">
</p>

> Rootloom is early-stage and single-maintainer. It makes workflow mechanics inspectable; it cannot prove that a model's evidence or diagnosis is true. See [maturity and guarantees](docs/maturity.md).

## The personal engineering loop

```text
Task
  ↓
Risk Analyzer ── Tier 0 Direct / Tier 1 Scoped / Tier 2 Governed
  ↓
Evidence → Diagnosis → Change Contract → Implementation
  ↓
Verification Intelligence → Final Review Summary
  ↓
Optional Project / Failure Memory
```

The observable final summary stays small:

```json
{
  "changed_files": ["src/example.py"],
  "risk": "medium",
  "tests": [{"command": ["python3", "-m", "unittest"], "passed": true}],
  "verification_preserved_capture": true,
  "remaining_risks": []
}
```

## What ships

| Capability | Result |
| --- | --- |
| Task intelligence | Tier detection, concrete risk signals, and workflow selection |
| Engineering workflow | Evidence, diagnosis, change contract, implementation, verification, and review |
| Verification intelligence | Primary behavior, owning invariant, and adjacent-path coverage |
| Project guidance | Deterministic root `AGENTS.md` seeding plus semantic refinement |
| Project memory | Optional `.project-memory/` architecture, risks, decisions, and failure lessons |
| Decision memory | Repository-owned engineering decision records for accepted durable choices |
| Command safety | Rules that separate reversible local work from destructive or external actions |
| Lightweight artifacts | Ordinary `diff.patch`, `test.log`, and `summary.json` bundles |

All runtime helpers use the Python standard library and work locally without a network service or database.

## Install

Requirements: Codex CLI or desktop with plugin support, Git, and Python 3.11+.

```bash
codex plugin marketplace add liyanqing90/rootloom
codex plugin add rootloom@rootloom
```

Start a new Codex task, then ask:

```text
$setup-rootloom
Plan and apply the personal preset.
```

The setup presets are:

| Preset | What it enables |
| --- | --- |
| `skills-only` | Plugin Skills only; project-guidance Hook disabled |
| `guidance` | Global working agreement plus automatic project guidance |
| `personal` | Guidance plus command safety; recommended and default |
| `engineering` | Compatibility alias for `personal` |

`skills-only` is a real empty capability selection. Status and later no-argument setup operations preserve it instead of silently expanding it to `personal`.

The personal preset manages only `~/.codex/AGENTS.md`, `~/.codex/rules/rootloom.rules`, and Rootloom's small component/state files. It does not change the default model, reasoning effort, sandbox, approval policy, MCP servers, providers, plugins, or apps.

Review the one bundled `SessionStart` Hook before trusting it. The Hook only runs deterministic project-guidance seeding when the installed component policy enables it; absent, malformed, or symlinked policy disables it.

See [setup, update, and rollback](docs/setup.md).

## Use

For a non-trivial repository change:

```text
$engineering-change
Fix the reconnect race and verify both reconnect and clean disconnect paths.
```

For lightweight reusable project knowledge:

```text
$project-memory
Initialize project memory, then record the verified reconnect failure lesson.
```

For project guidance:

```text
$seed-project-guidance
$refine-project-guidance
```

Risk-sensitive workflow Skills remain available:

| Skill | Use |
| --- | --- |
| `$operating-coding-change` | Tier 0/1 implementation discipline |
| `$operating-code-review` | Evidence-backed review only |
| `$operating-high-risk-change` | Tier 2 impact, compatibility, rollout, rollback, and approval gates |
| `$record-engineering-decision` | Accepted durable architecture or contract memory |

Subagents are never a default requirement. If a user explicitly asks for delegation, the active platform and repository policy still govern it; Personal Core does not install custom roles or audit Hooks.

## Verification artifacts

`$engineering-change` can call its helper after implementation:

```bash
python3 <engineering-change-skill>/scripts/finalize_change.py \
  --repo /absolute/path/to/repo \
  --output /absolute/path/to/run \
  --risk medium \
  --verify 'make test'
```

The helper does not execute a shell. It records a tracked Git patch, bounded test output, changed paths, verification results, and remaining risks. Untracked file contents are intentionally omitted, and repositories before their first commit are supported. Verification must preserve the tracked patch and captured changed/untracked path set; drift makes the bundle fail instead of allowing stale changed-file or deletion evidence. Exact `.env`, secret, migration, or database deletions—including captured untracked paths removed during verification—require an explicit `--confirm-dangerous-delete` path after human confirmation.

## Project memory

`.project-memory/` is optional and reviewable:

```text
.project-memory/
├── architecture.md
├── known-risks.json
├── decisions.json
└── failures.json
```

Memory is a lead, not authority. Current source, schemas, tests, manifests, CI, and runtime evidence win when they disagree. Rootloom never updates memory silently.

## Setup safety boundary

Personal setup remains plan-first, conflict-refusing, lock-serialized, backup-backed, mode-preserving on rollback, and atomic per file. It deliberately does not claim whole-transaction crash compensation or hostile multi-user filesystem protection. If setup stops between file replacements, `status` exposes the mismatch and the backup manifest remains available for explicit recovery.

## Migrating from 1.2.19

Personal Core 2.0 is a breaking product split:

1. use Rootloom 1.2.19 to roll back an installed Assurance setup;
2. switch/install `main`;
3. plan and apply the `personal` preset;
4. start a new Codex task.

If you still require Human Review, Decision Pair, protected-deletion approval, strict multi-agent routing, hardened Artifact binding, or setup recovery journals, stay on `codex/enterprise-assurance`.

## Development

```bash
make validate
make test
make check
make compatibility-smoke
```

See [architecture](docs/architecture.md), [guidance design](docs/guidance-design.md), [troubleshooting](docs/troubleshooting.md), and [contributing](CONTRIBUTING.md).

## License

[MIT](LICENSE)

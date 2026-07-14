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
  <img src="assets/rootloom-xiaohei-loom-en.png" width="920" alt="Rootloom weaving risk, defects, context, evidence, contracts, and tests into a verified engineering change">
</p>

Rootloom Personal Core keeps the part an individual developer uses every day:

1. decide how risky a task really is;
2. trace defects to the owning invariant instead of accepting a surface patch;
3. constrain the change before editing;
4. choose verification from changed behavior;
5. retrieve reusable project and failure knowledge when it is relevant.

It is single-agent by default. Human approval state machines, protected-deletion commitments, immutable Artifact chains, hardened shared-environment locks, multi-agent audit runners, and setup recovery journals are not part of `main`.

## Product split

| Product | Branch | Purpose |
| --- | --- | --- |
| Rootloom Personal Core 2.2.x | `main` | Low-friction daily engineering with opt-in deep review |
| Rootloom Enterprise Assurance 1.2.19 | [`codex/enterprise-assurance`](https://github.com/liyanqing90/rootloom/tree/codex/enterprise-assurance) | Preserved audited workflow with Human Review, protected deletion, strict Runner, and recovery machinery |

The split is intentional, not a feature downgrade. Enterprise Assurance remains available as a separate product line; personal users no longer pay its complexity cost.

<p align="center">
  <img src="docs/diagram/architecture.svg" width="980" alt="Rootloom Personal Core and Enterprise Assurance product architecture">
</p>

> Rootloom is early-stage and single-maintainer. It makes workflow mechanics inspectable; it cannot prove that a model's evidence or diagnosis is true. See [maturity and guarantees](docs/maturity.md).

## The opt-in deep engineering loop

```text
Task
  ↓
Risk Scanner ── explainable minimum Tier 0 / Tier 1 / Tier 2
  ↓
Evidence → Diagnosis → Change Contract → Implementation
  ↓
Verification Intelligence → Final Review Summary
  ↖                         ↗
Relevant Engineering Memory
```

Rootloom does not run this deep loop merely because the plugin is installed. Ordinary work stays on the repository's direct edit-and-test path; invoke the analyzer, baseline, contract, memory, and finalizer only when their evidence is explicitly useful.

The observable final summary stays small:

```json
{
  "changed_files": ["src/example.py"],
  "risk": "medium",
  "risk_assessment": {"minimum_tier": 1, "signals": [{"id": "behavioral-code"}]},
  "tests": [{"command": ["python3", "-m", "unittest"], "passed": true}],
  "verification_plan": {"status": "suggested-not-executed"},
  "commands_passed": true,
  "capture_preserved": true,
  "claim_binding": "complete",
  "verification_coverage": "complete",
  "semantic_coverage": "reviewed",
  "evidence_provenance": {
    "baseline": "operator-sealed",
    "change_contract": "operator-sealed",
    "verification_claims": "operator-sealed",
    "semantic_review": "operator-asserted"
  },
  "quality_status": "VERIFIED_CHANGE",
  "remaining_risks": []
}
```

## What ships

| Capability | Result |
| --- | --- |
| Task intelligence | Static task/path/diff/memory signals, an explainable minimum Tier, and workflow selection |
| Engineering workflow | Evidence, diagnosis, change contract, implementation, verification, and review |
| Verification intelligence | Risk-specific behavior checklist plus detected repository commands, kept separate from executed proof |
| Project guidance | Deterministic root `AGENTS.md` seeding plus semantic refinement |
| Engineering memory | Relevant, stale-aware `.project-memory/` architecture, risks, decisions, and failure lessons |
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

Installation is complete after those two commands. Start a new Codex task to load the Skills. Plugin installation does not write `~/.codex/AGENTS.md`, install command Rules, enable the Hook, or run analyzers, baselines, contracts, finalizers, and project-memory reads.

The optional `$setup-rootloom` Skill adds a cross-project policy layer only when you explicitly ask for it:

```text
$setup-rootloom
Plan and install the optional personal preset.
```

The setup presets are:

| Preset | What it enables |
| --- | --- |
| `skills-only` | Plugin Skills only; project-guidance Hook disabled |
| `guidance` | Global working agreement plus automatic project guidance |
| `personal` | Guidance plus command safety; recommended and default |
| `engineering` | Compatibility alias for `personal` |

`skills-only` is a real empty capability selection. Status and later no-argument setup operations preserve it instead of silently expanding it to `personal`.

The optional personal preset manages only `~/.codex/AGENTS.md`, `~/.codex/rules/rootloom.rules`, and Rootloom's small component/state files. It does not change the default model, reasoning effort, sandbox, approval policy, MCP servers, providers, plugins, or apps. Its policy keeps deep review opt-in rather than turning it into a default gate.

Review the one bundled `SessionStart` Hook before trusting it. The Hook only runs deterministic project-guidance seeding when the installed component policy enables it; absent, malformed, or symlinked policy disables it.

See [setup, update, and rollback](docs/setup.md).

For normal upgrades, refresh the marketplace, reinstall the plugin, and start a new task. Nothing else is required. If you previously installed the optional global preset and want its copied assets refreshed, run one explicit `$setup-rootloom` `upgrade`; it preserves the installed preset and refuses post-install drift.

## Use

When you explicitly want a deep review bundle, or for governed high-risk/release work:

```text
$engineering-change
Fix the reconnect race and verify both reconnect and clean disconnect paths.
```

The Skill first runs a local advisory scan. You can inspect the same JSON directly before editing:

```bash
python3 <engineering-change-skill>/scripts/analyze_change.py \
  --repo /absolute/path/to/repo \
  --task 'Fix the reconnect race' \
  --path src/relay.py
```

The result explains the signals, minimum Tier, matching active memory, stale history, and required verification behaviors. It is deliberately advisory: semantic evidence may raise the Tier further.

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

`$engineering-change` can call its helper after implementation in advisory mode:

```bash
python3 <engineering-change-skill>/scripts/finalize_change.py \
  --repo /absolute/path/to/repo \
  --output /absolute/path/to/run \
  --task 'Fix the reconnect race' \
  --verify 'make test'
```

Advisory mode does not block a normal change for missing machine evidence. With the default `--exit-policy bundle`, a stable bundle exits zero while incomplete coverage remains honest as `quality_status: UNVERIFIED` and compatibility `passed: false`. Automation that must stop on anything short of verified quality should use `--exit-policy quality` or `--require-verified`.

For a strict Tier 1/2 release or explicitly governed review, create the intake before implementation with `begin_review.py --repo ... --task ... --output ... --path ...`. Edit `change-contract.draft.json`, remove every `TODO`, then run `seal_contract.py --review-dir ...` to exclusively create `change-contract.json` and `contract.seal.json`; `review.json` is not edited by hand. The seal binds canonical contract content, final contract and review-manifest bytes, baseline hash, task hash, run ID, and nonce. Intake publication uses an atomic no-replace directory transition. Strict finalization requires unchanged baseline HEAD, symbolic HEAD ref, and index; it rereads evidence and Git identity after verification before assigning quality. `begin_review` requires a clean worktree/index unless `--allow-dirty-baseline` is explicit, and whole-repository scope requires `--allow-all-paths`. When a dirty baseline changes, overlapping current paths are scoped conservatively; a pre-existing dirty path that disappears fails closed instead of being reported as `NO_CHANGE`.

`analyze_change.py --write-baseline ...` remains available for analyzer-only/self-declared evidence, but it does not become operator-sealed without the intake and seal lifecycle above.

Repository state is accepted only after two consecutive bounded captures agree on the snapshot, tracked/untracked patch, HEAD/ref, and index. Ordinary untracked files receive streaming SHA-256 fingerprints and bounded, applyable text patches; their non-sensitive text also participates in risk analysis. Binary/large files receive type, size, and hash. Built-in and user-declared sensitive directory ancestors recursively protect all descendants. Sensitive content remains unread; symlink targets are represented only by byte length and SHA-256. Any observed sensitive metadata change—including a newly discovered ignored addition relative to the baseline or pre-verification capture—activates quarantine before ordinary content capture, makes every changed endpoint metadata-only, disables extra repository-memory/command discovery, and synthesizes ignored sensitive additions, changes, and deletions into contract scope. The summary reports `sensitive_integrity: metadata-observed` rather than claiming content integrity.

Evidence JSON rejects duplicate keys, non-standard constants, and out-of-range numbers. All verification commands are parsed before the first command runs; Git/status/patch capture and aggregate command output are bounded while read, and timeout, output overflow, or leaked descendants terminate the controlled process tree. The summary separates executed commands, capture preservation, sealed structured claim binding, broader declarations, and `semantic_coverage`. `semantic_coverage: reviewed` is an operator assertion rather than machine proof. Unknown semantic coverage can reach at most `MECHANICALLY_VERIFIED`; `VERIFIED_CHANGE` requires sealed mechanical evidence plus the semantic-review assertion. Strict mode uses quality exit codes by default, so only `VERIFIED_CHANGE` returns zero; `--strict-bundle-only` is the explicit non-blocking alternative. Pure verification requires `--allow-no-change`; gate errors still take priority over `NO_CHANGE`. Protected deletions include secret-like, migration, and database artifacts and require exact `--confirm-dangerous-delete` authorization.

Personal Core reports `isolation: process-group-only`; it is not a sandbox for untrusted commands. Evidence and bundle paths must remain outside both the repository worktree and its resolved Git common directory, including for linked worktrees. A reused Rootloom-owned output invalidates its old summary before the new run, so an early refusal cannot leave a stale authoritative result. Verification argv and output are retained in the local bundle, so never place credentials directly in commands or print them. Non-sensitive ignored files, Git administrative files, external state, and a secret copied to an ordinary path without an observable sensitive-source change are outside capture guarantees.

## Engineering memory

`.project-memory/` is optional and reviewable:

```text
.project-memory/
├── architecture.md
├── known-risks.json
├── decisions.json
└── failures.json
```

Memory is a lead, not authority. Current source, schemas, tests, manifests, CI, and runtime evidence win when they disagree. Rootloom never updates memory silently.

Retrieve only the relevant active entries:

```bash
python3 <project-memory-skill>/scripts/project_memory.py \
  --repo /absolute/path/to/repo context \
  --path src/relay.py \
  --query 'reconnect ordering'
```

New explicit records can carry evidence and expiry. They receive deterministic IDs, exact duplicates are suppressed, and `set-status` resolves or supersedes lessons without deleting history. Existing `rootloom-project-memory-v1` files and legacy entries remain readable; context never migrates or rewrites them.

## Setup safety boundary

Plugin installation and upgrades are setup-free by default. Optional Personal setup distinguishes first `install` from `upgrade`; compatibility `apply` remains available. Upgrade preserves the installed preset, records version-only updates without redundant asset backups, refuses post-install drift instead of overwriting it, and backs up/removes pristine targets retired by the new catalog so rollback can restore them. Setup remains plan-first, conflict-refusing, lock-serialized, backup-backed, mode-preserving on rollback, and atomic per file. It deliberately does not claim whole-transaction crash compensation or hostile multi-user filesystem protection.

## Migrating from 1.2.19

Personal Core 2.0 is a breaking product split:

1. use Rootloom 1.2.19 to roll back an installed Assurance setup;
2. switch/install `main`;
3. optionally plan and apply the `personal` preset;
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

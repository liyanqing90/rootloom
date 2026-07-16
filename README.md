<p align="center">
  <img src="plugins/rootloom/assets/icon.svg" width="112" alt="Rootloom logo">
</p>

<h1 align="center">Rootloom</h1>

<p align="center">
  <strong>Make Codex show its work.</strong>
</p>

<p align="center">
  A local OpenAI Codex plugin for scoped code changes, root-cause review,<br>
  explicit project guidance, and evidence-honest verification.
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

Coding agents can run a test and still leave the wrong invariant unfixed. They can suggest a verification command without executing it, or execute it after the repository state has changed. Rootloom gives Codex a small engineering workflow that makes those distinctions visible.

Rootloom helps an individual developer:

- trace a defect to the boundary that owns the behavior before editing;
- keep the change inside an explicit, reviewable scope;
- derive verification from the changed behavior and risk;
- separate suggested checks, executed commands, captured state, and human semantic judgment;
- keep reusable `AGENTS.md` guidance and project memory explicit rather than silently persistent.

> Rootloom makes workflow mechanics inspectable. It does not prove that a model's diagnosis is correct, that a change is secure, or that passing tests establish semantic correctness. See [maturity and guarantees](docs/maturity.md).

## A real case: the command passed, the review failed

During Rootloom's own development, a verification command returned exit code 0 after creating a newly ignored `.env` file and copying its synthetic value into an ordinary file. Treating command success as task success would have accepted a capture that no longer represented the reviewed state.

Rootloom's post-verification capture changed the decision:

- the new sensitive path activated quarantine;
- changed content stayed out of `diff.patch`;
- the copied file became metadata-only;
- `capture_preserved` became false;
- the strict review returned failure instead of a passing completion claim.

The focused regression is executable today:

```bash
python3 -m unittest \
  tests.test_engineering_change.EngineeringChangeTests.test_new_ignored_sensitive_path_is_a_scoped_task_change \
  tests.test_engineering_change.EngineeringChangeTests.test_verification_new_ignored_sensitive_path_quarantines_before_recapture
```

Read the complete, evidence-linked [case study](docs/case-studies/passing-command-failed-review.md).

## Start in 60 seconds

Requirements: Codex CLI or desktop with plugin support, Git, and Python 3.11+.

```bash
codex plugin marketplace add liyanqing90/rootloom
codex plugin add rootloom@rootloom
```

Installation is complete after those two commands. The plugin does not silently enable any optional layer.

Start a new Codex task, then choose the lightest workflow that fits:

```text
$operating-coding-change
Fix the reconnect race and verify reconnect, clean disconnect, and cancellation.
```

For an explicitly requested machine evidence bundle:

```text
$engineering-change
Audit the reconnect change and report what verification actually ran.
```

Plugin installation only makes the Skills available. It does not write `~/.codex/AGENTS.md`, install command Rules, enable a Hook, run analyzers, or read Project Memory.

## Choose the lightest workflow

| Need | Rootloom Skill | Default |
| --- | --- | --- |
| Ordinary implementation or defect repair | `$operating-coding-change` | Core |
| Review a diff, PR, migration, or architecture change | `$operating-code-review` | Core |
| Govern a public API, migration, security, infrastructure, release, or destructive change | `$operating-high-risk-change` | Core |
| Produce bounded capture and a machine-readable evidence summary | `$engineering-change` | Explicit opt-in |
| Create or refine repository `AGENTS.md` guidance | `$seed-project-guidance`, `$refine-project-guidance` | Explicit write |
| Retrieve or record durable project lessons | `$project-memory` | Experimental and explicit |

Ordinary work stays on the repository's normal edit-and-test path. The deep evidence loop is not an installation-time gate.

## How Rootloom works

```text
Task
  ↓
Risk and scope
  ↓
Evidence → Diagnosis → Change Contract → Implementation
  ↓
Behavior-based verification → Honest completion claim
```

For routine Tier 0/1 work, the active Codex agent applies the workflow directly with repository evidence and proportional tests. For a high-risk or explicitly governed review, Rootloom can additionally bind:

- repository and Git state before the change;
- allowed and forbidden paths;
- behavior claims to commands that actually ran;
- final repository capture after verification;
- machine-observed evidence separately from operator semantic judgment.

<p align="center">
  <img src="docs/diagram/architecture-en.svg" width="980" alt="Rootloom Personal Core architecture: Change, Review, Guidance, optional Autonomy and Evidence, and experimental Project Memory">
</p>

## What evidence-honest means

- A generated verification plan is labeled suggested, not executed.
- A command appears as passed only after Rootloom observes a successful run.
- A passing command is insufficient when repository state, scope, evidence, or capture changed.
- Sensitive material is classified by path and retained as metadata-only; Rootloom is not a content-aware secret scanner.
- `REVIEW_EVIDENCE_COMPLETE` means the documented evidence chain is complete. It does not mean correctness has been proven.
- Verification commands are trusted operator input and run with bounded process-tree controls, not an untrusted-code sandbox.

The wire formats and detailed limits live in [architecture](docs/architecture.md), [maturity and guarantees](docs/maturity.md), and [troubleshooting](docs/troubleshooting.md).

<details>
<summary><strong>Technical contract reference</strong></summary>

Rootloom Personal Core remains **An inspectable personal engineering workflow for Codex.** Its optional layers are Optional Autonomy, Optional Evidence, and Experimental Project Memory (also exposed through `$project-memory`). Project Memory is advisory; repository evidence remains authoritative.

The opt-in `$engineering-change` path uses `analyze_change.py` for advisory analysis. `analyze_change.py --write-baseline` can write analyzer-only evidence, while governed intake publishes an exact contract with `seal_contract.py`. Strict review uses `--strict`; machine consumers should read `quality_status` and the stable capability field `evidence_complete`. `REVIEW_EVIDENCE_COMPLETE` means the evidence chain is complete, while `REVIEW_REQUIRED_WITH_REDACTIONS` means material redaction prevents that claim.

Repository state is accepted only after **two consecutive bounded captures** agree. Each capture lifecycle is bounded by `--max-capture-seconds`. A **material metadata change**, including a **newly discovered ignored addition**, activates metadata-only quarantine before ordinary content capture. Classification uses `is_sensitive_material_path`; Rootloom is not a content-aware secret scanner.

`--reviewable-path` is an intake-only declaration for exact eligible files. It rejects ignored files, symlinks, hardlinks, ambiguous duplicates, strong secret material, and Git entries marked `assume-unchanged` or `skip-worktree`. The summary's `reviewability_policy` reports exact paths and `policy_provenance`; historical declarations that no longer meet current policy return `reintake-required` before content is read.

Evidence and bundle paths must be outside both the repository worktree and the resolved Git common directory. Optional authorization modes are Single action, Standard, and Full: Standard is **Persistent across tasks**, but every task still needs an explicit goal and resolved scope; **Full is never inferred**. The Archived Assurance Edition remains available at `codex/enterprise-assurance` without an active maintenance promise.

</details>

## Optional personal setup

The plugin is useful without setup. If you explicitly want a cross-project working agreement, invoke:

```text
$setup-rootloom
Plan and install the optional personal preset.
```

| Preset | Adds |
| --- | --- |
| `skills-only` | No global assets; project-guidance Hook disabled |
| `guidance` | Global working agreement and bounded read-only project context |
| `personal` | Guidance plus optional low-confirmation Autonomy |

The managed preset touches only `~/.codex/AGENTS.md`, `~/.codex/rules/rootloom.rules`, and Rootloom's small component/state files. It does not change the model, reasoning effort, sandbox, approval policy, MCP servers, providers, plugins, or apps. Setup is plan-first, backup-backed, conflict-refusing, and reversible within its documented limits.

## Product boundaries

```text
Rootloom Personal Core
├── Core: Change / Review / Guidance
├── Optional Autonomy: authorization modes / Command Rules
├── Optional Evidence: Analyzer / Baseline / Contract / Seal / Finalizer
└── Experimental: Project Memory
```

Rootloom is single-agent by default. Human approval state machines, immutable audit chains, multi-agent audit runners, and recovery journals are not part of `main`. The unmaintained 1.2.19 implementation is preserved as the [Archived Assurance Edition](https://github.com/liyanqing90/rootloom/tree/codex/enterprise-assurance), not as an active product line.

## Where Rootloom fits

Rootloom complements adjacent AI coding workflows:

| If your primary need is... | Start with... |
| --- | --- |
| Specification-driven planning and task decomposition | [GitHub Spec Kit](https://github.com/github/spec-kit) or [OpenSpec](https://github.com/Fission-AI/OpenSpec) |
| A broad, multi-agent software-development methodology | [Superpowers](https://github.com/obra/superpowers) |
| Codex-specific scope control, root-cause review, project guidance, and evidence-honest completion | Rootloom |
| Test execution, linting, security scanning, or CI | The native tool; Rootloom records and reasons over its evidence |

Rootloom does not replace specifications, tests, linters, security scanners, CI, or human review.

## FAQ

### Is Rootloom an OpenAI Codex plugin?

Yes. It packages Codex Skills, optional global guidance, optional command Rules, and one bounded read-only SessionStart Hook. Runtime helpers are local, network-free, and Python-standard-library-only.

### Does Rootloom support Claude Code, Cursor, or other coding agents?

Not currently. Rootloom targets the Codex plugin and `AGENTS.md` model deliberately. The engineering ideas are portable, but the shipped integration is Codex-specific.

### Is Rootloom an alternative to Spec Kit, OpenSpec, or Superpowers?

No. Spec Kit and OpenSpec focus on specification-driven development; Superpowers provides a broader development methodology. Rootloom focuses on the execution and review boundary: what changed, why, what actually ran, and what evidence supports completion.

### Does Rootloom prove that a change is correct or secure?

No. It can mechanically observe bounded repository state, command results, scope, provenance, and drift. Diagnosis, semantic review, correctness, and security still require trustworthy evidence and human judgment.

### Does installing Rootloom modify my global Codex configuration?

No. Installation exposes the Skills only. Global guidance, Rules, and Hook enablement require an explicit `$setup-rootloom` request and a reviewed plan.

### Can I use only the lightweight workflow?

Yes. Core Change, Review, and Guidance are the everyday path. Analyzer, Baseline, Contract, Seal, Finalizer, Autonomy, and Project Memory remain optional or experimental.

## Documentation

- [Architecture](docs/architecture.md)
- [Setup, update, and rollback](docs/setup.md)
- [Maturity and guarantees](docs/maturity.md)
- [Guidance design](docs/guidance-design.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Contributing](CONTRIBUTING.md)

## Development

```bash
make validate
make test
make check
make compatibility-smoke
```

## License

[MIT](LICENSE)

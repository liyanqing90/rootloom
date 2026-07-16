<p align="center">
  <img src="plugins/rootloom/assets/icon.svg" width="112" alt="Rootloom logo">
</p>

<h1 align="center">Rootloom</h1>

<p align="center">
  <strong>An inspectable personal engineering workflow for Codex.</strong>
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

Rootloom Personal Core keeps the part an individual developer uses every day:

1. make and review scoped changes by tracing defects to the owning invariant;
2. keep reusable project guidance concise, evidence-backed, and explicit;
3. choose proportional verification from changed behavior and risk.

It is single-agent by default. Human approval state machines, protected-deletion commitments, immutable Artifact chains, hardened shared-environment locks, multi-agent audit runners, and setup recovery journals are not part of `main`.

## Product split

| Product | Branch | Purpose |
| --- | --- | --- |
| Rootloom Personal Core | `main` | Low-friction daily engineering with opt-in deep review |
| Archived Assurance Edition | [`codex/enterprise-assurance`](https://github.com/liyanqing90/rootloom/tree/codex/enterprise-assurance) | Unmaintained 1.2.19 snapshot with Human Review, protected deletion, strict Runner, and recovery machinery |

The archived branch is recoverable source, not an active product line. It receives no implied fixes, compatibility work, or releases unless an independent maintenance policy resumes.

Personal Core now exposes four boundaries instead of presenting every mechanism as one product:

| Layer | Scope | Default |
| --- | --- | --- |
| Core | Change, Review, and Guidance | Everyday path |
| Optional Autonomy | Three authorization modes plus low-confirmation command Rules | Setup opt-in |
| Optional Evidence | Analyzer, Baseline, Contract, Seal, and Finalizer | Explicit invocation |
| Experimental | Project Memory | Explicit and advisory |

<p align="center">
  <img src="docs/diagram/architecture-en.svg" width="980" alt="Rootloom Personal Core authorization and engineering architecture">
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
  "schema_revision": 5,
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
  "semantic_review": "operator-asserted",
  "evidence_provenance": {
    "baseline": "intake-sealed",
    "change_contract": "workflow-sealed",
    "verification_claims": "workflow-sealed",
    "semantic_review": "operator-asserted"
  },
  "capture_limits": {"max_capture_seconds": 90, "max_git_seconds": 30},
  "capture_duration_seconds": 2.41,
  "quality_status": "REVIEW_EVIDENCE_COMPLETE",
  "evidence_complete": true,
  "passed": true,
  "remaining_risks": []
}
```

## What ships

| Capability | Result |
| --- | --- |
| Task intelligence | Static task/path/diff signals, explicitly included Memory signals, an explainable minimum Tier, and workflow selection |
| Engineering workflow | Evidence, diagnosis, change contract, implementation, verification, and review |
| Verification intelligence | Risk-specific behavior checklist plus detected repository commands, kept separate from executed proof |
| Project guidance | Read-only session context plus explicit `AGENTS.md` seeding and semantic refinement |
| Experimental Project Memory | Relevant, stale-aware `.project-memory/` architecture, risks, decisions, and failure lessons |
| Decision memory | Repository-owned engineering decision records for accepted durable choices |
| Optional Autonomy | Three authorization modes plus Rules that reduce duplicate command confirmation; not a deterministic safety system |
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
| `guidance` | Global working agreement plus read-only project context |
| `personal` | Guidance plus optional Autonomy; recommended and default |

`skills-only` is a real empty capability selection. Status and later no-argument setup operations preserve it instead of silently expanding it to `personal`.

`autonomy` depends on and automatically includes `global-policy`; Rules are never installed without the guidance that owns authorization semantics. Legacy `engineering` and `command-safety` inputs remain accepted compatibility aliases but are not public recommendations.

The optional personal preset manages only `~/.codex/AGENTS.md`, `~/.codex/rules/rootloom.rules`, and Rootloom's small component/state files. It does not change the default model, reasoning effort, sandbox, approval policy, MCP servers, providers, plugins, or apps. Its policy keeps deep review opt-in rather than turning it into a default gate.

Rootloom uses three authorization modes:

| Mode | Lifetime | Coverage |
| --- | --- | --- |
| Single action | Once | Only the displayed command or action |
| Standard | Persistent across tasks | All non-high-risk steps needed by each explicit goal; each task resolves its own operation type, repository, account, service, and environment |
| Full | Current task | Routine and high-risk steps inside that task's stated operation type and scope |

Standard is the installed default, so requests such as “publish this plugin” or “deploy this service” do not trigger command-by-command confirmation for routine implementation, publication, rollout, or verification steps. Full is never inferred. Static Rules allow commands so they do not repeat the semantic authorization decision; only catastrophic recursive deletion remains a bundled hard deny. Rules never create authority, Standard never permits self-initiated work, and platform, sandbox, organization, credential, and other active Rules remain authoritative.

Review the one bundled `SessionStart` Hook before trusting it. When enabled by exact managed component policy version 1, it injects at most 4 KiB of incremental read-only project identity, primary-manifest, and guidance-presence facts, plus up to three verification commands only when project guidance is absent. It skips Plan sessions and never creates or refreshes `AGENTS.md`. Persisting guidance requires an explicit `$seed-project-guidance` request. Missing, malformed, symlinked, wrong-type, or unsupported-version policy disables the Hook.

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

The result explains the signals, minimum Tier, and required verification behaviors. Experimental Project Memory is excluded by default; pass `--include-project-memory` to Analyzer and Finalizer only when the user explicitly requests relevant active/stale memory for that review. The result remains advisory: semantic evidence may raise the Tier further.

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

Advisory mode does not block a normal change for missing machine evidence. With the default `--exit-policy bundle`, a stable bundle exits zero while incomplete coverage remains honest as `quality_status: UNVERIFIED` and compatibility `passed: false`. Automation that must stop short of incomplete governed review evidence should use `--exit-policy quality` or the compatibility spelling `--require-verified`; neither option asserts semantic correctness.

For a strict Tier 1/2 release or explicitly governed review, create the intake before implementation with `begin_review.py --repo ... --task ... --output ... --path ...`. Edit `change-contract.draft.json`, replace every exact Rootloom contract placeholder, then run `seal_contract.py --review-dir ...` to exclusively create `change-contract.json` and `contract.seal.json`; `review.json` is not edited by hand. To seal an exact file as reviewable—whether an already-reviewable `.env.example` / public `.crt` or ambiguous material such as a public `.pem` or `.der`—add `--reviewable-path exact/file` only to `begin_review`. It resolves declarations to Git's actual repository spelling, accepts no more than 64, and requires each to be an existing, single-link regular non-symlink file whose changes remain visible to Git Status and Diff. Ignored paths, `assume-unchanged` / `skip-worktree` entries, globs, case-fold ambiguity or duplicates, hardlinks, strong material, and explicitly declared secrets are rejected. The declaration remains a high-risk security signal and is sealed into Intake; Finalizer cannot add or alter it. If a process interruption left an exact contract without its seal, `seal_contract.py --review-dir ... --recover` validates the baseline, manifest, draft-derived contract, and existing bytes before completing publication; it never overwrites mismatched evidence. The seal binds canonical contract content, final contract and review-manifest bytes, baseline hash, task hash, run ID, and nonce. Intake publication uses an atomic no-replace directory transition. Strict finalization requires unchanged baseline HEAD, symbolic HEAD ref, and index; it rereads evidence and Git identity after verification before assigning quality. `begin_review` requires a clean worktree/index unless `--allow-dirty-baseline` is explicit, and whole-repository scope requires `--allow-all-paths`. When a dirty baseline changes, aggregate tracked-patch overlap remains conservatively scoped, while exact unchanged per-path untracked fingerprints stay pre-existing and outside task scope, risk analysis, and `diff.patch`; changed untracked fingerprints remain conservatively attributed. A pre-existing dirty path that disappears fails closed instead of being reported as `NO_CHANGE`.

`analyze_change.py --write-baseline ...` remains available for analyzer-only/self-declared evidence, but it does not become intake-sealed without the intake and seal lifecycle above. Default new intakes still write `rootloom-change-baseline-v3`; an Intake with at least one `--reviewable-path` writes opt-in `rootloom-change-baseline-v4` and includes the exact declaration set in the sensitive-policy hash. Baseline v2, v3, and v4 Readers validate their historical wire structure and hashes without applying today's classifier. Finalizer separately applies current policy and returns `reintake-required` before reading Reviewable content when a historical declaration is no longer allowed. No Baseline v5 is introduced.

Repository state is accepted only after two consecutive bounded captures agree on the snapshot, tracked/untracked patch, HEAD/ref, and index. Both passes share one finite-positive `--max-capture-seconds` monotonic deadline (90 seconds by default). Every Git child uses the same controlled process-tree execution owner as verification, receives closed stdin, and gets the smaller of the remaining capture time and its finite-positive `--max-git-seconds` limit (30 seconds by default). The limit applies separately to each pre- and post-verification stable-capture lifecycle; `capture_duration_seconds` records their combined observed time and can therefore exceed that per-lifecycle limit. Ordinary untracked files receive streaming SHA-256 fingerprints and bounded, applyable text patches; their task-attributed non-sensitive text also participates in risk analysis. Binary/large files receive type, size, and hash.

Secret-material discovery sends Git shared case-insensitive candidate pathspecs plus literal user-declared roots instead of enumerating every tracked and ignored path. Python reclassifies every candidate with `is_sensitive_material_path()`; a separate bounded candidate ceiling protects the targeted Git queries, while `--max-sensitive-paths` (10,000 by default) counts only the classified material-result union and fails closed. Material includes `.env`, `.envrc`, non-template `.env.<name>` files, credential configuration, private-key/keystore formats, ambiguous `.pem` and `.der`, explicit roots, common key-named forms, and CamelCase names such as `clientSecret.json`, `apiToken.json`, `serviceAccountKey.json`, and `apiKey.json`. `privkey.pem`, `privatekey.pem`, `rsa-key.pem`, `ec-key.pem`, `ecdsa-key.pem`, `ed25519-key.pem`, `encryption-key.pem`, and `decryption-key.pem` are strong names that Reviewable declarations cannot override. `.env.example`, `.env.sample`, `.env.template`, `.env.dist`, and public certificate formats (`.crt`, `.cer`, `.p7b`, `.p7c`) stay patch-readable but raise security risk; DER is an encoding rather than proof of certificate content and therefore stays metadata-only unless explicitly declared reviewable at Intake. `.environment`, `.envelope`, and `.envoy` are ordinary names. Security-domain source such as `src/auth/token.py`, `src/credential_store.ts`, or `internal/secret_manager.go` is likewise handled by `is_security_domain_path()`: it raises risk and verification requirements but stays patch-readable and does not require privacy deletion confirmation. Material content remains unread; symlink targets are represented only by byte length and SHA-256. Any observed material metadata change—including a newly discovered ignored addition relative to the baseline or pre-verification capture—activates quarantine before ordinary content capture, makes every changed endpoint metadata-only, disables extra repository-memory/command discovery, and synthesizes ignored material additions, changes, and deletions into contract scope. The summary reports `sensitive_integrity: metadata-observed` rather than claiming content integrity.

Evidence JSON rejects duplicate keys, non-standard constants, and out-of-range numbers. All verification commands are parsed before the first command runs; Git/status/patch capture and aggregate command output are bounded while read, and timeout, output overflow, or leaked descendants terminate the controlled process tree. Summary revision 5 separates executed commands, capture preservation, sealed structured claim binding, broader declarations, `semantic_coverage`, and top-level `semantic_review`. Its `reviewability_policy` reports actual `policy_provenance` (`intake-sealed` or `self-declared`), `captured_files_provenance: final-capture-observed`, exact paths, policy hash, and final file identity/link metadata; compatibility `source` mirrors the honest policy value. `semantic_coverage: reviewed` produces only the explicit `semantic_review: operator-asserted`; it is not machine proof. Unknown semantic coverage can reach at most `MECHANICALLY_VERIFIED`, and an unsealed semantic assertion is `SEMANTIC_REVIEW_ASSERTED`. Workflow-sealed mechanical evidence plus the assertion yields `REVIEW_EVIDENCE_COMPLETE`, meaning the review evidence chain is complete—not that Rootloom proved the change correct. `evidence_complete` is the stable automation field; `quality_status` is detailed diagnosis. Provenance uses `intake-sealed` and `workflow-sealed`, which do not claim identity. Any otherwise-complete material quarantine is capped at `REVIEW_REQUIRED_WITH_REDACTIONS`, `evidence_complete: false`, and `passed: false`. Strict mode uses quality exit codes by default, so only `REVIEW_EVIDENCE_COMPLETE` returns zero; `--strict-bundle-only` is the explicit non-blocking alternative. No Summary revision 6 or new quality state is introduced. Pure verification requires `--allow-no-change`; gate errors still take priority over `NO_CHANGE`. Protected deletions include secret material, migration, and database artifacts and require exact `--confirm-dangerous-delete` authorization.

Personal Core reports `isolation: process-group-only`; it is not a sandbox for untrusted commands. Evidence and bundle paths must remain outside both the repository worktree and its resolved Git common directory, including for linked worktrees. A reused Rootloom-owned output invalidates its old summary before the new run, so an early refusal cannot leave a stale authoritative result. Verification argv and output are retained in the local bundle, so never place credentials directly in commands or print them. Non-sensitive ignored files, Git administrative files, external state, and a secret copied to an ordinary path without an observable sensitive-source change are outside capture guarantees. Rootloom is not a content-aware secret scanner; broader secret detection belongs in a separate trusted local scanner whose report is redacted before it enters Rootloom evidence.

## Experimental Project Memory

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

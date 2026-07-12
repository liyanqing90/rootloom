# Rootloom 1.2.7 protected verification entrypoints

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security / defect repair
- Risk: Tier 2 (Governed)

## Goal and observable success

Close the verification-entrypoint confidentiality and lifecycle gaps found in the 1.2.6 review. No ignored or sensitive-untracked verification path may be content-read or hashed; failed commands must not leave process-group children; explicit bindings must name a real command and an existing repository-internal regular file; pytest selectors must remain mutable test inputs; and each verification command must be bracketed by entrypoint and repository-state checks.

Success requires focused regression tests for every reported path plus `make validate`, `make check`, and `make compatibility-smoke`.

## Non-goals

- Full verification dependency-closure discovery.
- OS/container isolation for verification commands.
- Human-review acceptance state machine.
- Whole-repository fingerprint performance redesign.
- Setup crash consistency or new platform CI.

## Baseline evidence

- Rootloom 1.2.6 `run_pipeline.py` calls `file_fingerprint()` from `_entrypoint_fingerprint()` without consulting `capture_repo_state()` protected-path classification.
- `run_managed()` checks surviving process groups only when the parent returns zero.
- `--bind-verification-path` is stored under a synthetic `operator-bound` group and permits missing paths.
- Generic token scanning treats a missing pytest positional test path as a missing immutable entrypoint.
- `run_verification()` validates repository state only after the whole batch.
- Baseline worktree is clean at `41ec9567`.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| 1.2.6 has a protected-content fingerprint bypass | fact | local source review | 2026-07-12 | `plugins/rootloom/skills/high-assurance-coding-change/scripts/run_pipeline.py` | current checkout; no protected payload read |
| Reported findings describe reproducible ownership gaps | fact | supplied review report | 2026-07-12 | attachment `753db992-8131-4dcc-b95f-22e428de0d18/pasted-text.txt` | untrusted report checked against source |

## Governed defect diagnosis

- Observed failure: verification entrypoint discovery can read/hash paths that repository-state capture classifies as metadata-only; several adjacent lifecycle and binding gates are incomplete.
- Competing hypotheses: documentation-only mismatch was rejected because the direct `file_fingerprint()` calls are executable; capture-only protection was rejected because entrypoint discovery is a separate content reader.
- Ownership path: strict Runner verification-entrypoint discovery, managed-process lifecycle, and verification batch orchestration.
- Violated invariant: every repository content reader must obey one shared protected-path classification before opening or hashing a path.
- Root cause: entrypoint fingerprinting was added as an isolated subsystem instead of consuming repository-state classification and per-command execution boundaries.
- Root-cause alignment: PASS

## Constraints and invariants

- Protected paths fail closed as verification harnesses; metadata-only fingerprinting is not sufficient to trust executable content.
- Missing common tool configuration candidates remain baseline-bound, but explicit scripts and operator bindings must exist.
- Preserve the existing CLI where unambiguous; a bare binding remains accepted only when exactly one user verification command exists.
- No shell evaluation, network use, new dependency, or external mutation.

## Impact map

- Producers: CLI arguments, verification command parser, repository-state capture.
- Consumers: entrypoint metadata, Writer gate, repair loop, deterministic verification records, docs and repository validator.
- Persisted data: Runner JSON artifacts only; schema-compatible additions are allowed.
- Public contracts: `--bind-verification-path` syntax and Runner metadata.
- Generated artifacts: none.
- External systems: none in this implementation turn.

## Design and decisions

- Ownership: `run_pipeline.py` owns classification-aware entrypoint fingerprints and per-command verification fencing.
- Interfaces: entrypoint discovery receives a captured repository state; validation receives a current state; explicit bindings normalize to `verification-command-id -> path`.
- Dependency direction: repository classification feeds every entrypoint content read, never the reverse.
- Compatibility window: path-only binding remains valid for one user command; multiple commands require `verify-N:path`.
- Alternatives rejected: metadata-only protected harness fingerprints cannot establish executable integrity; allowing missing explicit harnesses creates decorative controls.

## Implementation sequence

1. Add shared protected-path rejection and component-aware symlink fingerprinting.
2. Narrow command parsing, normalize command-scoped explicit bindings, and validate real regular files.
3. Make managed-process cleanup return-code independent and record leftover cleanup.
4. Fence every verification command with state and entrypoint validation.
5. Add negative regressions, update bilingual public docs/contracts, and run the complete verification matrix.

## Rollout, failure, and rollback

- Dry-run/preview: focused unit tests exercise protected paths without reading their contents.
- Mixed-version behavior: new Runner artifacts add explicit binding maps and leftover-process evidence; old artifacts remain readable JSON.
- Failure detection: PipelineError exit 9, focused tests, repository validator, compatibility smoke.
- Rollback or compensation: revert the scoped 1.2.7 local commit before publication if verification fails.
- Irreversible point: publication is excluded until separately authorized.

## Verification

- Original failure path: bundled Runner tests that patch `file_fingerprint` and fail on protected path access.
- Owning-boundary invariant: `python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py`.
- Adjacent negative/alternate path: process-group, pytest selector, scoped binding, parent-symlink, and per-command mutation regressions.
- Focused tests: bundled Runner test module.
- Contract/migration tests: `make validate`.
- Type/lint/build/package: `make check`.
- UI/browser evidence: not applicable.
- Security/dependency checks: `git diff --check`; no dependency change.
- Post-action verification: `make compatibility-smoke`.

## Risks

- Risk: path classification mismatch after Writer changes.
  - Mitigation: recapture state before each fingerprint validation and before/after each command.
  - Residual risk: full transitive harness dependency closure remains unbound.
- Risk: CLI compatibility for existing bare bindings.
  - Mitigation: infer the sole user verification command; fail with an actionable message only when ambiguous.
  - Residual risk: a stability dependency proves immutability, not semantic use by the command.

## Decision log

- 2026-07-12 — Treat the report as a governed security repair; fix the unified ownership boundary before expanding entrypoint adapters.
- 2026-07-12 — Keep publication outside this turn because the current request did not explicitly authorize external mutation.
- 2026-07-12 — Implemented Runner 2.9 / plugin 1.2.7 with shared protected classification, command-scoped real-file bindings, pytest selector classification, full path-component symlink binding, return-code-independent process cleanup, and per-command verification fences.
- 2026-07-12 — Verification passed: 44 focused Runner tests, 41 repository tests, `make validate`, `make check`, `make compatibility-smoke` on `codex-cli 0.144.0-alpha.4`, and `git diff --check`. Root-cause alignment: PASS.
- 2026-07-12 — User explicitly authorized commit and GitHub publication with “完成后发布”. Publication target is `liyanqing90/rootloom` `main`, annotated tag `v1.2.7`, and a non-draft GitHub Release; no force-push is authorized or required.
- 2026-07-12 — Published code commit `35278c4cf98a83d19f2a1c1b6c2cdeeabf573d87`. Its tree `23075c3627b00bc0fc28060d81673ceafb9c9fc6` exactly matches the locally verified release tree. GitHub CI passed at `https://github.com/liyanqing90/rootloom/actions/runs/29183662034`.
- 2026-07-12 — Created annotated tag object `54dcdad2c7ea82f853b65d6cae0a52ac7857370a` for `v1.2.7` and published `https://github.com/liyanqing90/rootloom/releases/tag/v1.2.7` as a non-draft, non-prerelease Release.

## Durable decision records

- None; this restores an existing confidentiality and verification invariant rather than introducing a durable architecture choice.

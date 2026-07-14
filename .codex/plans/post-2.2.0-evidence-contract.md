# Post-2.2.0 Evidence Contract Hardening

## Status

- State: published as 2.2.1; external facts recorded in `docs/releases/2.2.1.md`
- Owner: Codex
- Last updated: 2026-07-14
- Task type: architecture / public contract / release record
- Risk: Tier 2 (Governed)

## Goal and observable success

Address the Rootloom Personal Core 2.2.0 review findings and publish them as Rootloom Personal Core 2.2.1 by making strict-review evidence provenance explicit, binding baseline/contract/finalizer inputs with run identity and hashes, clarifying claim binding versus semantic coverage, adding automation-safe exit policies, versioning the summary schema, documenting process isolation limits, and recording publication facts.

Success is proven by focused contract tests, repository validation, and full `make check`.

## Non-goals

- Do not mutate the existing `v2.2.0` tag or GitHub Release.
- Do not add enterprise approval, audit, strict-runner, or recovery machinery to Personal Core.
- Do not claim semantic proof beyond machine-checkable bindings and recorded operator review level.
- Do not mutate the existing 2.2.0 release artifacts; publish the fixed build as a new `v2.2.1` release.

## Baseline evidence

- Review attachment: `/Users/tangyuan/.codex/attachments/35bdc502-74b2-4558-9874-90797097be5e/pasted-text.txt`.
- Pre-change baseline artifact: `/tmp/rootloom-2.2.1-prechange-baseline.json`.
- Repository state before implementation: `main` at `7018c317e59a6e44081e07c1d68d277c469f0cfb`, clean worktree.
- Analyzer result: Tier 2 due to public/persisted summary, baseline, and change-contract semantics.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| 2.2.0 release exists and tag points at `7018c317...` | fact | local git + GitHub release verification from previous task | 2026-07-14 | `v2.2.0`, PR #1, release URL | public metadata |
| Current strict evidence can be internally consistent without proving operator sealing | fact from review plus source inspection | local checkout | 2026-07-14 | `finalize_change.py`, `baseline.py`, `change_contract.py` | no secrets |

## Governed defect diagnosis

- Observed failure: strict review summaries do not distinguish self-declared evidence from operator-sealed evidence, and `UNVERIFIED` advisory mode exits 0 without an explicit automation policy.
- Competing hypotheses: this is either only documentation ambiguity, or a contract/schema gap. Source inspection confirms the summary lacks provenance/hash/exit-policy fields, so it is a contract gap.
- Ownership path: `plugins/rootloom/skills/engineering-change/scripts/runner/baseline.py`, `change_contract.py`, `finalize_change.py`, `contracts.py`, tests and docs.
- Violated invariant: Personal Core review output must state what the machine actually proved and avoid implying stronger evidence than exists.
- Root cause: evidence identity, provenance, claim binding, and process-exit semantics were not first-class summary contract fields.
- Root-cause alignment: PASS.

## Constraints and invariants

- Preserve low-friction advisory mode by default.
- Preserve existing summary compatibility fields where practical.
- New fields must be bounded, local, deterministic, standard-library-only, and network-free.
- Strict mode may become stricter only when the new contract fields are absent or inconsistent.
- Documentation must avoid claiming Personal Core is a sandbox for untrusted commands.

## Impact map

- Producers: analyzer baseline writer, change-contract loader, finalizer summary writer.
- Consumers: tests, humans, CI wrappers reading summary/exit code, future Rootloom agents.
- Persisted data: baseline JSON, change-contract JSON, summary JSON, release publication record.
- Public contracts: `finalize_change.py` CLI and `rootloom-engineering-summary-v1` fields.
- Generated artifacts: review bundle files under outside-repo output directories.
- External systems: GitHub branch, pull request, merge, annotated tag, and public GitHub Release for `v2.2.1`.

## Design and decisions

- Add additive schema fields rather than remove `passed` or change bundle filenames.
- Keep `format: rootloom-engineering-summary-v1` with `schema_revision: 2` for compatibility.
- Rename machine completeness internally to `claim_binding` while preserving `verification_coverage` as a compatibility alias.
- Add `semantic_coverage` as `unknown`, `partial`, or `reviewed`; the machine defaults to `unknown` unless explicitly declared.
- Add `--exit-policy bundle|quality` and `--require-verified` as a stable CI alias for quality exit behavior.
- Add baseline v2 run metadata and contract run binding while accepting v1 baselines/contracts as self-declared compatibility input unless strict verification requires v2 binding.

## Implementation sequence

1. Extend baseline v2 metadata and shared hash helpers.
2. Extend change-contract loading to validate optional run/hash binding and structured claim bindings.
3. Extend finalizer CLI and summary contract fields.
4. Add focused tests for provenance, hash chain, exit policy, claim binding, process convergence, and release record.
5. Update docs/decision guidance and validation if needed.

## Rollout, failure, and rollback

- Dry-run/preview: local tests and finalizer fixtures.
- Mixed-version behavior: old baselines/contracts remain readable for advisory mode; strict operator-sealed verification requires v2 binding.
- Failure detection: focused tests and `make check`.
- Rollback or compensation: revert local commits before external publication.
- Irreversible point: external push/tag/release. The user explicitly authorized publication with “发布最新版” on 2026-07-14.

## Verification

- Original failure path: focused finalizer tests for self-declared versus operator-sealed evidence and advisory `UNVERIFIED` exit behavior.
- Owning-boundary invariant: tests around baseline/contract hash/run binding and summary schema revision.
- Adjacent negative/alternate path: tests for old evidence compatibility, quality exit policy on `NO_CHANGE`, and process convergence fields.
- Focused tests: `python3 -m unittest tests.test_engineering_change -v`.
- Contract/migration tests: `make validate`.
- Type/lint/build/package: `make check`.
- UI/browser evidence: not applicable.
- Security/dependency checks: no dependency changes.
- Post-action verification: CI checks, merged commit/tag identity, GitHub Release metadata, marketplace-visible repository state, and publication record.

## Risks

- Risk: over-tightening strict mode could break existing local workflows.
  - Mitigation: preserve advisory compatibility and document `--exit-policy`.
  - Residual risk: consumers that assumed `passed` meant command success must migrate to explicit fields.

## Decision log

- 2026-07-14 — Treat post-2.2.0 findings as public contract hardening, not external publication; do not mutate existing release artifacts.
- 2026-07-14 — User authorized publishing the fixed latest version; release as 2.2.1 rather than mutating `v2.2.0`.
- 2026-07-14 — PR #2 merged, `v2.2.1` published, and release metadata recorded in `docs/releases/2.2.1.md`.

## Durable decision records

- Existing: `docs/decisions/2026-07-14-personal-intelligence-contract.md`.
- Update if implementation changes durable evidence contract semantics.

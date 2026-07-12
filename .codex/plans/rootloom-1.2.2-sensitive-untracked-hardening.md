# Rootloom 1.2.2 sensitive-untracked hardening

## Status

- State: release authorized; publication in progress
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security and compatibility
- Risk: Tier 2 (Governed)

## Goal and observable success

Ensure every known or explicitly configured sensitive visible-untracked path is classified before repository-state fingerprinting, is never opened for content hashing, never contains `sha256` in redacted artifacts, and never enters an untracked patch or Reviewer Delta. Reconcile the published 1.2.1 governance record and prepare a release-ready 1.2.2 patch without publishing it absent fresh authorization.

## Baseline and root cause

- 1.2.1 classifies ignored paths before hashing, but computes `file_fingerprint()` for `tracked_paths | untracked_paths` before identifying sensitive visible-untracked paths.
- Later Delta classification correctly removes the raw content from patches, but reuses the already content-derived state entry in `redacted_untracked_metadata`.
- Existing tests assert marker absence, not absence of the read/hash operation or `sha256` field.
- Violated invariant: ignored and sensitive visible-untracked paths must remain metadata-only from their first state producer through every downstream consumer.
- Root cause: sensitivity classification is owned by the late Delta consumer instead of the repository-state producer where content access is decided.
- ROOT_CAUSE_ALIGNMENT: PASS.

## Evidence provenance

| Claim | Kind | Source/environment | Observed | Reference | Freshness/redaction |
| --- | --- | --- | --- | --- | --- |
| Sensitive visible-untracked content is hashed in 1.2.1 | fact | local source inspection / released `v1.2.1` | 2026-07-12 | `run_pipeline.py:capture_repo_state` | current released source; no secret payload retained |
| Redacted metadata can contain a content-derived SHA-256 | fact | local data-flow inspection | 2026-07-12 | `capture_repo_state` → `metadata_manifest` | current released source |
| Existing regression does not reject `file_fingerprint(.env.local)` | fact | local test inspection | 2026-07-12 | `test_sensitive_visible_untracked_content_is_redacted` | current released tests |

## Constraints and non-goals

- Tracked files remain repository deliverables and retain content fingerprints.
- Ordinary visible-untracked deliverables retain content fingerprints and complete patches.
- Built-in matching is explicitly “known secret-like paths,” not universal secret detection.
- Add exact-path and `directory/**` custom redaction rules plus an opt-in all-untracked-dotfiles mode; do not invent shell glob semantics.
- Model roles still have read access to the repository. Artifact/prompt redaction is not OS-level deny-read isolation.
- Full incremental tracked hashing, crash-consistent Setup recovery, platform matrix expansion, and authenticated model smoke belong to 1.3.

## Impact map and compatibility

- Producers: `capture_repo_state`, sensitive-path matcher, CLI option parsing.
- Consumers: change detection, Delta manifests, baseline metadata, Reviewer prompt, tests, docs.
- Persisted/private format: additive state key `sensitive_untracked_paths`; redacted artifact shape changes from a content fingerprint to metadata-only, matching the already documented contract.
- CLI: additive repeatable `--sensitive-path` and boolean `--redact-untracked-dotfiles` options.
- Mixed version: 1.2.1 artifacts remain readable; 1.2.2 emits safer redacted metadata without `sha256`.

## Implementation and verification

1. Classify sensitive untracked paths before constructing content paths.
2. Store sensitive-path identity in state and derive Delta manifests from classified state instead of re-enumerating/re-hashing.
3. Expand known sensitive filenames/directories and add explicit caller controls.
4. Require behavioral verification items to reference at least one user-supplied command, not only `verify-0` whitespace checking.
5. Add no-read/no-hash and metadata-shape regressions plus ordinary-file negative coverage.
6. Update version/changelog/security boundary docs.
7. Run `make check`, `make compatibility-smoke`, `make smoke`, and `git diff --check`.

### Observed local results

- `make check` — PASS: repository validation, 41 suite tests, and 21 strict-runner tests.
- `make compatibility-smoke` — PASS on `codex-cli 0.144.0-alpha.4`; command policy, rollback, and config restoration matched the supported baseline.
- `make smoke` — PASS in an isolated Codex home, including marketplace discovery, setup/rollback, SessionStart execution, and model acknowledgement.
- Strict-runner dry-run with `--sensitive-path 'private/**'` and `--redact-untracked-dotfiles` — PASS; the untracked `.codex` plan appeared only as `file-metadata` without `sha256`.
- `git diff --check` — PASS.

## Rollout, rollback, and authorization

- Local implementation and tests are reversible.
- Roll back before publication by reverting the focused 1.2.2 commit; after publication use a forward patch.
- GitHub `main` push, annotated `v1.2.2` tag, and GitHub Release were explicitly authorized by the user in the Codex task on 2026-07-12. Post-publication branch, tag, Release, and CI evidence must be appended after verification.

## Residual risks

- Unknown sensitive filenames may evade built-in heuristics unless configured.
- Read-capable model stages can still open repository files; users need secret-free worktrees or OS/container isolation for access control.
- Full tracked-content hashing remains proportional to repository bytes per state gate until the planned 1.3 incremental redesign.

## Decision log

- 2026-07-12 — Treat pre-classification sensitive hashing as P0 and target 1.2.2.
- 2026-07-12 — Keep the patch focused; defer crash recovery and full incremental hashing to 1.3.
- 2026-07-12 — Add explicit redaction controls using existing exact/recursive path grammar rather than implicit globbing.

# Rootloom 1.2.3 protected-path gates

## Status

- State: published
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security and execution safety
- Risk: Tier 2 (Governed)

## Goal and observable success

Prevent automated acceptance when the strict Runner's sole writer creates or modifies ignored or sensitive visible-untracked paths that are intentionally hidden from content review. Permit only exact, operator-declared deletion of an already existing protected path, preserve metadata-only capture, and terminate with a machine-visible human-review-required result rather than automatic PASS. Recheck repository topology after every writer and immediately before final acceptance. This post-write gate does not provide OS-level prevention or rollback.

## Baseline, diagnosis, and root-cause alignment

- 1.2.2 protects ignored/sensitive content from artifacts and prompts but treats those paths as ordinary allowed-path changes when the change contract permits them.
- A writer can therefore modify a metadata-only path whose content the reviewer is explicitly told not to inspect.
- `--redact-untracked-dotfiles` can classify deliverable dot-directory files such as `.github/workflows/...` as metadata-only, increasing the consequence of silent acceptance.
- Topology is checked at startup, then disabled for every state snapshot, so a nested repository created during the writer stage lacks an explicit post-write topology gate.
- Violated invariant: every accepted writer change must be content-reviewable, or it must be a narrowly authorized non-content operation that cannot receive automated acceptance.
- Root cause: confidentiality classification influences serialization but is not consumed by the repository-contract acceptance gate; the topology optimization also removed lifecycle-boundary revalidation instead of only redundant read-stage scans.
- ROOT_CAUSE_ALIGNMENT: PASS.

## Evidence provenance

| Claim | Kind | Source/environment | Observed | Reference | Freshness/redaction |
| --- | --- | --- | --- | --- | --- |
| Protected changes can pass when allowed_paths includes them | fact | local source inspection / `main` 2d439ed | 2026-07-12 | `enforce_repository_contract` | current source; no protected payload read |
| Reviewer receives metadata but is instructed not to read content | fact | local prompt/data-flow inspection | 2026-07-12 | `capture_delta`, review prompt | current source |
| Topology checks are disabled after startup | fact | local call-site inspection | 2026-07-12 | `run_pipeline_locked` state captures | current source |

## Contracts and design

- Protected set: the union of baseline/current ignored paths and baseline/current sensitive visible-untracked paths.
- Default: any protected path creation, modification, or deletion fails before Delta capture.
- Exception: repeatable `--allow-protected-path-delete <exact-path>`; directory rules and globs are forbidden.
- Exception validity: the path must be protected in the baseline, must be missing in current state, must be inside the diagnosis `allowed_paths`, and every declared exception must be used exactly.
- A successful Reviewer verdict with protected deletion writes `HUMAN_REVIEW_REQUIRED` and exits nonzero; it never returns automated PASS.
- Topology: full check at startup, after each implementation/repair writer, and after final review before acceptance. Read-only stage snapshots keep topology traversal disabled.
- Verification wording: call non-built-in commands “user-supplied verification commands,” not “behavior commands,” because exit success does not prove semantic adequacy.

## Compatibility and impact

- CLI change is additive; default behavior becomes stricter only for changes that were never content-reviewable.
- Existing ordinary tracked/untracked changes are unaffected.
- Existing Runner consumers must treat the new nonzero human-review-required exit as a governed stop, not a generic implementation failure.
- Private result JSON gains `protected_deletions`; normal PASS keeps an empty list.
- No migration or persisted production data is involved.

## Implementation and verification

1. Add exact protected-deletion option parsing and semantic validation.
2. Enforce protected changes before Delta capture and annotate accepted deletions.
3. Convert final PASS with protected deletion into `HUMAN_REVIEW_REQUIRED` and stable nonzero exit.
4. Re-enable topology checks in post-writer and post-review snapshots.
5. Add regression tests for ignored/sensitive modification failure, protected creation failure, exact deletion, invalid/unused exceptions, human-review result policy, and post-writer topology detection.
6. Update version, changelog, runner docs, architecture, and maturity boundaries.
7. Run `make check`, `make compatibility-smoke`, `make smoke`, strict Runner CLI dry-run, and `git diff --check`.

### Observed local results

- `make check` — PASS: repository validation, 41 suite tests, and 25 strict-runner tests.
- `make compatibility-smoke` — PASS on `codex-cli 0.144.0-alpha.4`; command policy, rollback, and existing config restoration matched the supported baseline.
- `make smoke` — PASS in an isolated Codex home, including plugin discovery, setup/rollback, SessionStart execution, and model acknowledgement.
- Strict Runner dry-run with `--sensitive-path 'private/**'` and `--allow-protected-path-delete '.env.local'` — PASS; Runner version 2.5 metadata recorded the exact deletion authorization and verification command IDs.
- `git diff --check` — PASS.

## Rollout, rollback, authorization, and residual risk

- Local changes are reversible. The user explicitly authorized publishing `main`, an annotated `v1.2.3` tag, and the GitHub Release in the Codex task on 2026-07-12; verified publication evidence is recorded below.
- Before publication, revert the focused patch if compatibility fails; after publication, use a forward patch and never rewrite the tag.
- The post-write gate can reject acceptance but cannot prevent or restore a protected mutation; failure may require operator filesystem recovery.
- Human review can confirm only the deletion path and intent, not the former protected content because the Runner deliberately did not read or back it up.
- Other processes can mutate the repository between checkpoints; the repository lock coordinates Rootloom runners, not arbitrary external writers.
- Full incremental hashing, setup crash recovery, platform matrix expansion, authenticated model smoke, and semantic test-artifact binding remain 1.3 work.

### Publication record

- Release commit: `fe1ee944e1b34ce43041d71c3e0515b66d46dbea`.
- Annotated tag: `v1.2.3`, dereferenced to the release commit.
- Release: <https://github.com/liyanqing90/rootloom/releases/tag/v1.2.3>, published as a final release rather than a draft or prerelease.
- Release CI: <https://github.com/liyanqing90/rootloom/actions/runs/29179292848>, conclusion `success` for the release commit.
- Publication evidence is appended on `main` in a documentation-only follow-up; the immutable release tag remains on the tested code commit.

## Decision log

- 2026-07-12 — Reject all protected writes by default; do not let confidentiality redaction create an acceptance blind spot.
- 2026-07-12 — Support deletion only through explicit exact-path authorization and require human acceptance afterward.
- 2026-07-12 — Restore topology checks at writer and final-review boundaries rather than every read-only snapshot.

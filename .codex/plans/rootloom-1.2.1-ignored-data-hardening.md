# Rootloom 1.2.1 ignored-data hardening

## Status

- State: published
- Owner: Codex
- Last updated: 2026-07-12
- Task type: security, compatibility, and release
- Risk: Tier 2 (Governed)

## Goal and observable success

Prevent ignored or secret-like untracked file contents from being read into strict-runner Delta artifacts or review prompts, bound ignored-path enumeration, and make the runner's platform and governance limits explicit. Success requires fail-before/pass-after regression tests, full repository checks, offline compatibility smoke, and a release-ready 1.2.1 diff.

## Non-goals

- Claim that model-generated evidence is factually true.
- Make native Codex subagent role/model attestation deterministic.
- Implement a native-Windows process/locking backend for the strict runner in this patch.
- Add authenticated model calls to public CI, which has no release credentials.

## Baseline evidence

- `capture_repo_state()` records ignored files with metadata only.
- `capture_delta()` calls `untracked_manifest(repo, introduced_paths)` with `include_ignored=True`, then `untracked_patch()` executes `git diff --no-index --binary /dev/null <path>` for every manifest entry.
- `enforce_repository_contract()` captures Delta before rejecting paths outside the approved contract.
- The runner imports `fcntl` and uses POSIX process-group and lock semantics unconditionally.
- Ignored-path enumeration has no count budget and is repeated at every repository-state gate.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Ignored content can enter artifacts and the reviewer prompt | fact | local source inspection / Rootloom 1.2.0 | 2026-07-12 | `run_pipeline.py:842-999`, `run_pipeline.py:1613-1637` | current released source; no ignored content retained |
| Scope rejection occurs after Delta capture | fact | local source inspection | 2026-07-12 | `run_pipeline.py:972-998` | current released source |
| Strict runner is POSIX-only | fact | local source inspection | 2026-07-12 | top-level `fcntl`, `/dev/null`, `os.killpg`, POSIX flock | current released source |
| Ignored enumeration is unbounded | fact | local source inspection | 2026-07-12 | `capture_repo_state()` Git ignored listing | current released source |

## Governed defect diagnosis

- Observed failure: a file intentionally excluded by `.gitignore` can be metadata-only in state capture but later become a full binary patch in artifacts and the reviewer prompt.
- Competing hypotheses: documentation-only mismatch; metadata helper misuse; or ordering/content-boundary defect.
- Ownership path: state capture classifies paths; Delta capture serializes content; repository-contract enforcement owns scope order; review prompt consumes Delta.
- Violated invariant: ignored and sensitive paths must remain metadata-only through every downstream consumer, and scope must be approved before content capture.
- Root cause: content classification is discarded between state capture and Delta capture; `untracked_manifest()` defaults to re-enumerating ignored files, while contract enforcement serializes before authorizing scope.
- Root-cause alignment: PASS

## Constraints and invariants

- Ignored paths must never be passed to content hashing, `open`/`read_bytes`, or `git diff --no-index` by Delta capture.
- Secret-like visible untracked paths must also remain metadata-only.
- Scope/index/Git-control gates must run before any untracked content patch is generated.
- Ignored enumeration must fail closed at a configurable positive path budget.
- Tracked and ordinary visible-untracked deliverables retain complete content patches.
- Existing 2.2 artifacts are private and pre-release; 1.2.1 may add fields while retaining compatibility aliases where practical.
- The strict runner is supported only on Linux, macOS, and WSL until a Windows backend is implemented and tested.

## Impact map

- Producers: `capture_repo_state`, Delta capture, deterministic verification records.
- Consumers: artifact readers, review prompt, final result JSON, tests, public documentation.
- Persisted data: private runner artifacts only.
- Public contracts: runner CLI, artifact schema, platform requirements, capability descriptions.
- Generated artifacts: Delta patches/manifests and verification JSON.
- External systems: GitHub publication completed after explicit user authorization.

## Design and decisions

- Ownership: preserve ignored classification in repository state and derive ignored metadata directly from that state.
- Interfaces: visible untracked paths may produce patches; ignored and sensitive untracked paths produce metadata/redaction records only.
- Dependency direction: contract gate → classified Delta capture → prompt compaction.
- Compatibility window: keep `untracked` as a visible-only alias while adding explicit `visible_untracked`, `ignored_metadata`, and `redacted_untracked_metadata` fields.
- Alternatives rejected: trusting `.gitignore` naming alone, because visible `.env` or credential files can still exist; hashing ignored content, because it recreates the disclosure and performance risk.

## Implementation sequence

1. [complete] Add an ignored-secret Delta regression and an out-of-scope pre-capture test.
2. [complete] Split visible patch capture from ignored/sensitive metadata capture and reorder scope enforcement.
3. [complete] Add streaming ignored-path enumeration with a configurable fail-closed budget.
4. [complete] Bind verification-map items to declared command IDs and executed records.
5. [complete] Update compatibility/platform/governance documentation and version metadata for 1.2.1.
6. [complete locally] Run full local, installed-lifecycle, and compatibility verification. Publication remains outside the authorized scope.

## Rollout, failure, and rollback

- Dry-run/preview: tests use temporary repositories and private artifact directories.
- Mixed-version behavior: 1.2.1 retains visible `untracked` summary compatibility; new metadata fields are additive.
- Failure detection: focused security tests, full test suite, repository validator, compatibility smoke.
- Rollback or compensation: revert the 1.2.1 hardening commit before publication; after publication use a forward patch release rather than rewriting the tag.
- Irreversible point: completed GitHub tag/Release publication; future corrections use forward patch releases.

## Verification

- Original failure path: ignored secret file changes, Delta captured, secret absent from every artifact and compact prompt.
- Owning-boundary invariant: monkeypatch content fingerprint and `git diff --no-index` paths; neither may receive ignored/sensitive paths.
- Adjacent negative/alternate path: ordinary visible untracked file still produces a complete patch; out-of-scope visible file fails before patch capture.
- Focused tests: runner test module.
- Contract/migration tests: repository validator and compatibility smoke.
- Type/lint/build/package: `make check`, `git diff --check`.
- UI/browser evidence: not applicable.
- Security/dependency checks: secret-like repository scan and artifact assertions.
- Post-action verification: `main`, dereferenced `v1.2.1`, and Release all resolved to `97ff1c26c9ffb07df70080efcd01f9bc48f8a25c`; GitHub CI run `29177611054` passed.

### Observed local results

- `make check` — PASS: repository validation, 41 suite tests, and 19 strict-runner tests.
- `make compatibility-smoke` — PASS on `codex-cli 0.144.0-alpha.4`; commit allow, push prompt, reset forbidden, rollback clean, pre-existing config restored.
- `make smoke` — PASS in an isolated Codex home; marketplace install/discovery, engineering/full setup, live SessionStart model smoke, and rollback completed.
- `git diff --check` — PASS.

### Publication record

- Authorization: the user explicitly authorized commit, push, tag, and GitHub Release publication in the Codex task on 2026-07-12.
- Tag: `v1.2.1` (annotated), dereferenced to `97ff1c26c9ffb07df70080efcd01f9bc48f8a25c`.
- Release: <https://github.com/liyanqing90/rootloom/releases/tag/v1.2.1>.
- CI: <https://github.com/liyanqing90/rootloom/actions/runs/29177611054>, conclusion `success`.

## Risks

- Risk: metadata-only ignored tracking can miss adversarial same-size timestamp-restored edits.
  - Mitigation: ignored paths are never deliverable content and remain prohibited implementation output.
  - Residual risk: metadata is a mutation signal, not cryptographic attestation.
- Risk: strict path budget rejects very large repositories.
  - Mitigation: expose an explicit CLI override and fail with the observed count/budget.
  - Residual risk: increasing the budget trades startup cost for coverage.
- Risk: reviewer can independently open ignored paths from its read-only repository sandbox.
  - Mitigation: explicitly prohibit reading ignored/redacted paths and omit their contents from the supplied Delta.
  - Residual risk: model instruction is not an OS-level deny-read boundary.

## Decision log

- 2026-07-12 — Treat ignored-content capture as P0 and target 1.2.1.
- 2026-07-12 — Declare POSIX/WSL support instead of shipping an untested Windows process backend.
- 2026-07-12 — Keep public CI credential-free; describe it as integration-shape compatibility, not authenticated model compatibility.

## Durable decision records

- None; this patch restores already documented confidentiality and boundedness invariants.

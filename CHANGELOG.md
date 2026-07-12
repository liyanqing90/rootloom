# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.8] - 2026-07-12

### Security

- Preserve every baseline ignored or sensitive-untracked path as metadata-only for the complete high-assurance run. Changes to `.gitignore`, `.git/info/exclude`, or current sensitivity classification can no longer make protected content readable or patchable in later snapshots.
- Reject attempts to declassify an existing baseline-protected path even when its metadata did not otherwise change.
- Poll managed process groups directly during cleanup and escalate from SIGTERM to SIGKILL when descendants remain, including children that ignore SIGTERM after the direct parent exits.

### Changed

- Repository state now records the effective monotonic `metadata_only_paths` boundary, and standalone contract enforcement derives that boundary from its baseline automatically.
- The strict high-assurance runner is now version 2.10.

### Tests

- Added regressions for protected-path declassification through `.gitignore` and `.git/info/exclude`, pre-delta content-read prevention, SIGTERM-ignoring descendant cleanup, and direct timed-out processes that ignore SIGTERM.

## [1.2.7] - 2026-07-12

### Security

- Route every verification-entrypoint content fingerprint through the repository state's ignored and sensitive-untracked classification. Protected harnesses and protected symlink targets now fail before content reads or hashes.
- Validate every verification command immediately before execution and recheck repository state immediately after it, preventing one verification command from mutating a later command's harness before that later command runs.
- Inspect and record symlinks in every entrypoint path component, not only a final symlink.
- Clean up surviving process-group children after both successful and failed commands. Failed commands retain their original exit code and record that leftover children were terminated.

### Changed

- `--bind-verification-path` is now a command-scoped stability dependency. Use `verify-N:path` when multiple user verification commands are configured; the path-only form remains accepted for one user command.
- Operator-bound harnesses and directly executed repository scripts must resolve to existing repository-internal regular files. Missing paths, directories, and protected paths fail closed.
- Pytest positional paths are treated as test selectors, including missing regression-test paths that the Writer is expected to create.

### Tests

- Added regression coverage for ignored and sensitive harness read prevention, protected symlink targets, invalid and ambiguous explicit bindings, missing pytest selectors, parent-directory symlinks, failed-command child cleanup, and verification-batch mutation.

## [1.2.6] - 2026-07-12

### Security

- Include missing common verification entrypoint candidates in the baseline, so writer-created `GNUmakefile`, `makefile`, `pytest.ini`, and related files are treated as verification entrypoint drift.
- Expand verification entrypoint discovery for `./path`, `python -m pytest`, `uv run pytest`, `poetry run pytest`, `make -f`, `pytest -c`, `npm --prefix`, and explicit repeatable `--bind-verification-path` harnesses.
- Bind repository-internal symlink entrypoints to their resolved chain and final target content, not only the symlink target string.
- Fail closed when a successfully returned managed command leaves a live process group; leftover children are terminated.

### Changed

- Directory selectors such as `pytest tests/unit` are no longer treated as verification entrypoints, reducing false positives from broad directory fingerprints.

### Tests

- Added regression coverage for missing candidate creation, wrapper command discovery, explicit harness binding, symlink target mutation, directory selector exclusion, and successful-stage leftover child cleanup.

## [1.2.5] - 2026-07-12

### Security

- Bind detected verification entrypoints across the write stage. Explicit repository-relative verification path tokens, `make` files, JavaScript package manifests, and pytest configuration files are fingerprinted before the writer and must remain unchanged before deterministic verification runs.
- Re-run allowed-path and verification-command symlink checks after every writer or repair writer, before verification executes.
- Reject protected deletion mode when `--allow-dirty` is enabled or repair cycles are configured; deletion-only runs now require a clean baseline and `--max-repair-cycles 0`.

### Changed

- Clarify that verification command path detection covers explicit/common entrypoints and is not a generic shell or CLI semantic parser.

### Tests

- Added regression coverage for writer-created verification symlink replacement, writer-modified Makefile/package/pytest harness files, and protected deletion runtime option rejection.

## [1.2.4] - 2026-07-12

### Security

- Tightened `--allow-protected-path-delete` into a deletion-only run contract. If any protected deletion is authorized, the net repository change must be exactly the approved protected deletion set; ordinary code edits, visible untracked creations, renames, or moves must happen in a separate run.
- Added pre-writer protected deletion validation. Authorized deletion paths must exist in the baseline, be classified as protected, be non-directory exact targets, and be included in the diagnosis `allowed_paths` before the implementation stage can run.
- Reject allowed-path and repository-relative verification command entries that cross an existing symlink outside the repository.
- Recheck unsupported repository topology immediately after deterministic verification, in addition to startup, writer, and final review checkpoints.

### Tests

- Added regression coverage for protected `.env` rename into an ordinary allowed path, invalid deletion authorization preflight, out-of-repository symlink boundaries, and the Runner 2.6 contract.

## [1.2.3] - 2026-07-12

### Security

- Reject automated acceptance after detecting writer creation, modification, or deletion of ignored and sensitive visible-untracked paths, before Delta capture and even when the diagnosis `allowed_paths` includes them. This post-write gate does not claim OS-level prevention or rollback.
- Add a narrow repeatable `--allow-protected-path-delete <exact-path>` exception. It accepts only deletion of an existing baseline protected path, rejects globs/directories and unused authorizations, never reads the former content, and cannot receive automated PASS.
- Successful verification and review of an authorized protected deletion now produce `HUMAN_REVIEW_REQUIRED` with a stable nonzero exit and explicit `protected_deletions` result data.

### Changed

- Recheck unsupported gitlinks, submodules, and nested repositories after every implementation/repair writer and again after final review before acceptance, while keeping redundant topology scans disabled for read-only stage snapshots.
- Rename “user-supplied behavior command” to the accurate “user-supplied verification command”; command execution linkage still does not prove test semantics.

### Tests

- Added protected ignored/sensitive modification and creation rejection, capture-before-failure, exact/unused deletion authorization, human-review outcome, and post-start topology checkpoint coverage.

## [1.2.2] - 2026-07-12

### Security

- Classify known and caller-configured sensitive visible-untracked paths before repository-state fingerprinting, so their contents are never opened or hashed and their redacted metadata never contains `sha256`.
- Expanded known secret-like coverage for npm, PyPI, netrc, Git credential, Docker, Kubernetes, auth, and service-account files.
- Added repeatable exact/recursive `--sensitive-path` rules and opt-in `--redact-untracked-dotfiles` protection for repository-specific cases.

### Changed

- Delta and baseline untracked manifests now derive from the already classified repository state instead of re-enumerating and re-fingerprinting files.
- Repository-topology traversal runs once at strict-runner startup rather than at every stage snapshot; full incremental tracked-file fingerprinting remains planned work.
- A GO diagnosis must map at least one verification requirement to a user-supplied command instead of relying exclusively on the built-in `git diff --check` command.
- Reconciled the published 1.2.1 ExecPlan with its actual tag, Release, authorization, and successful CI result.

### Tests

- Added fail-on-read sensitive-file regression coverage, metadata-shape assertions that reject content hashes, known/custom/dotfile matcher coverage, ordinary-untracked negative coverage, and behavior-command mapping enforcement.

## [1.2.1] - 2026-07-12

### Security

- Prevented ignored files and sensitive visible-untracked paths such as `.env*`, private keys, credentials, secrets, and tokens from entering content hashes, Git patches, runner artifacts, or reviewer Delta prompts. These paths are represented only by path, type, and filesystem metadata.
- Moved the allowed-path and Git-state gates ahead of Delta capture, so rejected out-of-contract changes are not read into content-bearing artifacts first.

### Added

- Added a fail-closed ignored-path enumeration budget, configurable with `--max-ignored-paths` and defaulting to 50,000 paths.
- Linked each diagnosis verification requirement to stable machine command IDs and require every mapped command to have an observed successful result.
- Added explicit strict-runner platform gating for Linux, macOS, and WSL; native Windows is not supported by this runner.

### Changed

- Clarified that native role/model routing is installed but not attested on the currently verified spawn surface, the cumulative child budget is behavioral rather than preventive, Rules are argv-prefix defense in depth, and compatibility smoke tests integration shape without live model calls.
- Added regression coverage for ignored-content non-disclosure, scope-before-capture, sensitive untracked redaction, ignored-path budgets, platform gates, and verification-command coverage.

## [1.2.0] - 2026-07-12

### Added

- Added `$record-engineering-decision` and a concise repository-owned decision template for durable architecture, contract, dependency, security, data, and operational choices.
- Added evidence-provenance and invariant-derived verification contracts across ordinary, governed, review, and high-assurance workflows.
- Added bilingual maturity and guarantee boundaries that distinguish deterministic process mechanics from factual or outcome correctness.
- Added a non-blocking scheduled compatibility probe against the latest Codex CLI while retaining the pinned required baseline.

### Changed

- The strict runner now requires every observed fact and reproduction to reference stable provenance IDs, plus a three-part verification map before a GO diagnosis.
- The strict runner content-hashes deliverable tracked/untracked files while using metadata fingerprints for ignored cache/build files.
- Setup now serializes operations with a cross-process lock, prepares recovery state before mutation, compensates apply and rollback state-commit failures, and restores original file modes.
- Project guidance seeding now excludes symlinked/out-of-repository evidence and protects writes with a Git-common-dir lock plus an exact pre-write snapshot check.
- Pinned and latest Codex compatibility jobs now exercise the full offline plugin lifecycle rather than only command-policy parsing.
- Security response windows are documented as single-maintainer, best-effort targets rather than service-level guarantees.

## [1.1.0] - 2026-07-12

### Added

- Unified task intake around Tier 0 Direct, Tier 1 Scoped, and Tier 2 Governed work without adding another always-on routing Skill.
- Added a Software 3.0 completeness gate, progressive context rules, tier-aware user-facing task packets, and explicit root-cause-alignment review.
- Added deterministic repository validation for the shared tier vocabulary and false-fix prevention contracts.

### Changed

- Behavioral defects now default to Tier 1 or higher, while trivial mechanical work remains bureaucracy-free.
- Ordinary, high-risk, review, and high-assurance Skills now distinguish evidence-backed root-cause fixes from transparent mitigations.

## [1.0.1] - 2026-07-11

### Changed

- Replaced the diagram-like plugin icon with a minimal woven `R` monogram that remains legible at small sizes.
- Simplified the light and dark wordmarks and documented the separation between the compact icon and extended brand narrative.

## [1.0.0] - 2026-07-11

### Added

- Five selectable capability levels: `skills-only`, `guidance`, `engineering`, `delegated`, and `full`.
- A polished, installable global `AGENTS.md`, deterministic project-guidance seeding, and semantic guidance refinement.
- Plan/apply/status/rollback setup with dependency closure, atomic writes, conflict refusal, backups, hash-aware rollback, and semantic config preservation.
- Ordinary coding, review-only, high-risk, and opt-in high-assurance workflow Skills.
- Four model-routed custom Agent templates, a quality-first profile, and tested command Rules that distinguish local commits from remote publication and destructive operations.
- Independently gated `SessionStart` and advisory `SubagentStart` Hooks, disabled by default until setup applies the corresponding capability.
- A deterministic high-assurance `codex exec` runner with one writer, exact scope gates, structured outputs, real verification, independent review, and a bounded repair cycle.
- Bilingual documentation, architecture and capability visuals, tests, CI, security policy, contribution guidance, and release governance.

[Unreleased]: https://github.com/liyanqing90/rootloom/compare/v1.2.8...HEAD
[1.2.8]: https://github.com/liyanqing90/rootloom/compare/v1.2.7...v1.2.8
[1.2.7]: https://github.com/liyanqing90/rootloom/compare/v1.2.6...v1.2.7
[1.2.6]: https://github.com/liyanqing90/rootloom/compare/v1.2.5...v1.2.6
[1.2.5]: https://github.com/liyanqing90/rootloom/compare/v1.2.4...v1.2.5
[1.2.4]: https://github.com/liyanqing90/rootloom/compare/v1.2.3...v1.2.4
[1.2.3]: https://github.com/liyanqing90/rootloom/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/liyanqing90/rootloom/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/liyanqing90/rootloom/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/liyanqing90/rootloom/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/liyanqing90/rootloom/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/liyanqing90/rootloom/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/liyanqing90/rootloom/releases/tag/v1.0.0

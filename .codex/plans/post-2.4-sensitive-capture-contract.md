# Repair and publish Rootloom Personal Core 3.0.0

## Status

- State: finalizing publication record
- Owner: Codex
- Last updated: 2026-07-15
- Task type: privacy, public CLI/JSON contract, resource-governance defect repair, and release
- Risk: Tier 2 (Governed)

## Goal and observable success

Correct every remaining issue identified in the Rootloom Personal Core 2.4.0 final audit, then publish the result as 3.0.0 without weakening redaction or moving the existing tag:

- ordinary security-domain source such as `src/auth/token.py`, `src/token_service.py`, `src/credential_store.ts`, and `internal/secret_manager.go` remains patch-readable and raises the advisory risk floor instead of activating Sensitive Quarantine;
- actual secret material, including `.env*`, private keys/certificates/keystores, explicit sensitive roots, credential configuration, and CamelCase names such as `clientSecret.json`, `apiToken.json`, and `serviceAccountKey.json`, remains metadata-only and activates quarantine when changed;
- one stable repository capture has a 90-second default monotonic deadline shared by both capture passes, while each Git child remains independently capped at 30 seconds by default;
- summary revision 5 adds `evidence_complete`, `capture_limits.max_capture_seconds`, and measured capture duration, and replaces identity-suggesting provenance values with `intake-sealed` / `workflow-sealed`;
- new intakes use `rootloom-change-baseline-v3` with `intake-sealed`; legacy baseline v2 remains readable and sealable, with its historical `operator-sealed` wire value normalized in new summaries;
- the public SemVer policy explicitly classifies additive fields as Minor, compatible semantic corrections as Patch, and field/enum/exit-contract removal or incompatible reinterpretation as Major.

Completion requires focused regressions, the repository contract gate, the full test suite, compatibility smoke, documentation parity, a fresh challenge pass, passing release-PR and merged-main CI, an annotated `v3.0.0` tag, a public GitHub Release, a factual publication record, and a drift-free local upgrade.

## Non-goals

- Moving, deleting, or retagging `v2.4.0` or rewriting historical baseline v2/summary revision-4 artifacts.
- Weakening `REVIEW_REQUIRED_WITH_REDACTIONS`, returning success for redacted evidence, reading secret content, or restoring `VERIFIED_CHANGE` as an authoritative alias.
- Adding identity, signatures, approvals, immutable audit storage, a sandbox, or Enterprise Assurance machinery.

## Baseline evidence

- `v2.4.0` points to `e434654`; current `main`/`origin/main` is the descendant `3b88deb`, containing only post-release records beyond the release commit.
- The worktree has one unrelated untracked user asset, `assets/rootloom-xiaohei-loom.png`; it must remain untouched and outside task scope.
- `plugins/rootloom/lib/rootloom_paths.py::is_sensitive_path` currently treats any dot/underscore/hyphen-delimited `credential`, `secret`, or `token` path word as secret material.
- `runner/state.py` uses that same classifier for targeted discovery, metadata-only capture, quarantine, tracked-patch exclusion, and rename endpoints; `is_protected_deletion_path` also delegates to it.
- `runner/intelligence.py` separately repeats authentication/security path-word sets and inherits the same lack of CamelCase splitting from `path_words`.
- `runner/state.py::stable_repository_capture` runs two complete captures and passes the unchanged `max_git_seconds` value to every Git child; it has no aggregate monotonic deadline.
- `finalize_change.py` emits summary revision 4 and records `max_git_seconds`, patch bytes, and sensitive-path count, but not an aggregate capture limit or duration.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Release/main relationship and dirty-tree constraint | fact | local Git repository on macOS volume | 2026-07-15 | `git log --oneline --decorate -12`; `git status --short --branch` | current; user asset content not read |
| Classifier ownership collision | fact | local source | 2026-07-15 | `plugins/rootloom/lib/rootloom_paths.py`; `runner/state.py`; `runner/intelligence.py` | current; no sensitive content |
| Missing aggregate capture deadline | fact | local source | 2026-07-15 | `runner/state.py::stable_repository_capture`; CLI parsers | current |
| 2.4.0 release/CI evidence | reported fact, not independently re-run at intake | user-supplied final audit | 2026-07-15 | current task statement and `docs/releases/2.4.0.md` | release evidence; no raw CI payload |

## Governed defect diagnosis

- Observed failure: security-domain source is redacted as though it contained credentials, while CamelCase secret configuration can be discarded by Python reclassification; capture time is bounded per child rather than per stable capture.
- Competing hypotheses: (1) remove the redaction status cap; (2) keep one classifier and add more exclusions; (3) split privacy material from security-domain risk and give capture a shared deadline. Option (1) recreates a false pass. Option (2) keeps incompatible responsibilities coupled and remains brittle. Option (3) repairs the owning boundaries while preserving fail-closed privacy behavior.
- Ownership path: material/privacy policy in `plugins/rootloom/lib/rootloom_paths.py`; capture enforcement in `runner/state.py`; risk use in `runner/intelligence.py`; CLI/summary plumbing in analyzer, intake, finalizer, docs, tests, and validator.
- Violated invariant: only paths likely to contain secret material may suppress reviewable content; security-relevant source must remain reviewable while raising risk; a declared capture ceiling must bound the aggregate stable capture rather than reset for every subprocess.
- Root cause: one legacy path predicate accumulated privacy, deletion, discovery, and business-risk responsibilities, and the later redaction cap exposed its false-positive cost; Git timeouts were introduced at the child owner without an aggregate capture owner.
- Root-cause alignment: PASS.

## Constraints and invariants

- Standard-library-only, deterministic, local, network-free, cross-platform behavior.
- Secret contents and symlink targets remain unread/unserialized; ambiguous privacy cases fail closed.
- User-declared sensitive roots remain recursive and case-insensitive at the path boundary.
- The targeted Git query may overmatch candidates, but Python material reclassification is authoritative and candidate/result limits remain separate.
- One stable capture owns one monotonic deadline; each Git timeout is the smaller of the remaining capture time and `max_git_seconds`.
- Revision 5 retains existing field names, quality statuses, quality exits, and artifact names; its documented breaking change is limited to provenance enum values and the new default baseline format.
- Public behavior and safety changes update English and Chinese README plus canonical architecture and contribution guidance.

## Impact map

- Producers: `plugins/rootloom/lib/rootloom_paths.py`; `runner/{state,intelligence}.py`; `analyze_change.py`; `begin_review.py`; `finalize_change.py`.
- Consumers: advisory/strict CLI users, summary JSON consumers, setup target validation, deletion guards, repository validator, tests, release/compatibility automation, and documentation readers.
- Persisted data: `rootloom-engineering-summary-v1` revision 5 and new `rootloom-change-baseline-v3`; legacy baseline v2 remains accepted. Contract/manifest/seal schemas remain unchanged.
- Public contracts: additive `--max-capture-seconds` and capability/timing fields; incompatible provenance enum correction; new baseline producer format; documented SemVer classification.
- Generated artifacts: existing `summary.json`; no new required artifact.
- External systems: GitHub repository, Actions, annotated tag/Release, marketplace/plugin cache, and the installed Personal preset. The user explicitly authorized all publication operations in this task.

## Design and decisions

- `rootloom_paths.py` owns two explicit predicates: material paths control discovery/redaction/quarantine/deletion privacy; security-domain paths control advisory risk only.
- Identifier tokenization preserves path-segment matching and adds CamelCase/acronym boundaries before lowercasing.
- Material classification uses exact secret/config names, material suffixes, explicit secret roots/directories, and strong config-name combinations such as client-secret, API/access token, credential environment, or private/service-account/API/access key. Security schemas, policies, managers, and stores remain reviewable even when their non-code configuration filenames contain a single domain term.
- Targeted Git pathspecs remain deliberately broader than the material classifier so CamelCase candidates are found without whole-tree enumeration.
- `CaptureDeadline` owns monotonic time. Nested Git calls consume the remaining budget; Python loops check the same deadline at bounded points. The deadline failure is distinct from a per-Git timeout.
- CLI producers expose the same finite-positive default. Finalizer records the limit and total measured time spent in its two stable captures; each stable capture receives its own declared lifecycle budget.
- `evidence_complete` is a stable capability boolean equal to the existing `passed` condition. `quality_status` remains the detailed display/diagnostic enum.
- New intakes write baseline v3 with `intake-sealed`. Readers and sealers accept legacy v2 with its historical token; revision-5 summaries normalize any valid sealed intake to identity-neutral provenance values.
- Compatibility window: historical revision-4 summaries remain immutable; baseline-v2 artifacts remain readable/sealable; exact provenance consumers branch on `schema_revision`. New consumers should prefer `evidence_complete` over display enum coupling.
- Alternatives rejected: redaction-cap rollback; source-extension allowlists inside the old single predicate; blanket exclusion of auth/security directories; one timeout reset per subprocess; revision-4 `operator-sealed` rename; a misleading `VERIFIED_CHANGE` alias.

## Implementation sequence

1. Add fail-before classifier/risk/capture-deadline regressions and confirm the old behavior.
2. Split shared path policy and route capture plus intelligence to their owning classifiers.
3. Add the monotonic aggregate deadline, CLI plumbing, duration measurement, and additive summary capability fields.
4. Synchronize version surfaces, validator, Skill/README/architecture/contribution/changelog documentation, and an accepted durable decision record.
5. Run focused and full verification, compatibility smoke, strict governed finalization, diff audit, and strongest counterexample challenge.
6. Commit intended files only, push `codex/release-3.0.0`, open a ready PR, require all checks, merge, and require merged-main checks.
7. Create and push annotated `v3.0.0`, publish a public non-prerelease GitHub Release, record publication facts, rerun final CI, and upgrade/verify the local plugin and preset.

## Rollout, failure, and rollback

- Dry-run/preview: temporary-repository unit tests exercise exact source/material examples, ignored CamelCase material, quarantine, per-child versus aggregate timeout, invalid budgets, and summary fields.
- Mixed-version behavior: old artifacts remain readable; revision-4 consumers keep reading historical bundles, while revision-5 consumers branch for new provenance values. CLI callers that omit the new flag receive the 90-second default.
- Failure detection: nonzero CLI exit with aggregate-deadline text, secret-free patch, high-risk signal for security source, and `REVIEW_REQUIRED_WITH_REDACTIONS` for actual material.
- Rollback or compensation: before the tag, use corrective commits or leave the PR unmerged. After publication, never move/delete `v3.0.0` for an ordinary defect; publish a newer patch. Existing evidence is never migrated in place.
- Irreversible point: pushing annotated tag `v3.0.0`, explicitly covered by the user's Full publication authorization.

## Verification

- Original failure path: focused tests for the four supplied source examples and three CamelCase material examples.
- Owning-boundary invariant: classifier unit tests plus temporary-repository capture/finalizer tests prove readable source, material quarantine, and shared deadline exhaustion.
- Adjacent negative/alternate path: docs/tests with auth names stay low-risk as before; `.env*`, explicit roots, certificate/key suffixes, security-source renames/deletions, non-finite budgets, and per-Git timeout behavior.
- Focused tests: `python3 -B -m unittest tests.test_engineering_change -v`.
- Contract/migration tests: `make check`; `make compatibility-smoke`.
- Type/lint/build/package: `make validate`; `git diff --check`.
- UI/browser evidence: not applicable.
- Security/dependency checks: inspect that Capture imports only the material classifier, secret bytes never enter patch/summary, and no dependency changed.
- Post-action verification: inspect emitted summary; run a fresh analogous-consumer/counterexample pass; verify PR/main/final Actions, tag peel, public Release, and installed version/drift.

### Executed evidence

- Fail-before probe on the 2.4.0 implementation reproduced all four supplied security-source false positives and all three supplied CamelCase false negatives.
- Focused regressions now cover strong material names, security-domain code and configuration counterexamples, shared preflight/two-pass deadline use, finite-positive validation at all three CLI entry points, key-material risk, baseline-v2 normalization, and revision-5 summary fields.
- `make check` passed on macOS: 164 tests passed and one non-UTF-8 filesystem case was skipped because this volume rejects that filename encoding.
- `make compatibility-smoke` passed with `codex-cli 0.144.2`; it reported no plugin-install side effects or managed leftovers after rollback.
- `make validate` and `git diff --check` passed.
- Fresh challenge review found and corrected three post-implementation gaps before publication: Finalizer preflight now consumes the same capture deadline as its stable passes; security material such as API/Service Account keys always reaches a high-risk signal; and domain descriptors such as token schemas/policies or secret managers remain reviewable instead of being treated as material.
- A clean temporary-clone strict replay returned summary revision 5, `REVIEW_EVIDENCE_COMPLETE`, `evidence_complete: true`, `passed: true`, `change_partition: exact`, complete claim binding, and a valid hash chain for the exact 27-path release patch; measured capture time was 0.325201 seconds.
- Release PR run `29390214510` passed all seven Linux 3.11–3.14, macOS, Windows, and Codex CLI jobs. PR #7 merged as `61c1d8202350442721644345678e1525461c7d08`; merged-main run `29390437387` independently passed the same seven jobs.
- Annotated tag object `72091416819a5b16436f2be0b7862dc965856f49` peels to the passing merge commit. Public non-draft, non-prerelease Release `RE_kwDOTVQo6M4VHOPs` was published at 2026-07-15T05:07:33Z.
- Local `rootloom@rootloom` and the managed personal preset upgraded from 2.4.0 to 3.0.0; setup reports no drift or pending upgrade. Installed Rules allow representative routine/high-risk argv and forbid catastrophic root deletion.
- Pending release evidence: publication-record CI and its final factual record.

## Risks

- Risk: a secret material filename outside the explicit/config-like rules is no longer redacted.
  - Mitigation: retain broad targeted Git candidates, explicit user roots, exact/suffix rules, CamelCase tokenization, and fail-closed tests for common credential forms.
  - Residual risk: path-only inference can never identify an arbitrarily named secret copied to an ordinary source-looking path.
- Risk: broad material rules recreate source false positives.
  - Mitigation: distinguish source suffixes from config/material suffixes and test supplied source examples directly.
  - Residual risk: a config-like fixture named as a secret remains conservatively redacted unless the operator reorganizes or accepts metadata-only review.
- Risk: deadline measurement differs across slow filesystems and platforms.
  - Mitigation: assert bounded behavior and field shape rather than exact elapsed values; use monotonic time and existing process-tree cleanup.
  - Residual risk: one non-interruptible filesystem metadata syscall can outlive the deadline before Rootloom regains control.

## Decision log

- 2026-07-15 — Treat the supplied 2.4.0 final audit as the accepted requirement set; preserve the redaction cap and repair the underlying classifier.
- 2026-07-15 — User granted Full authorization for repair, review, and all publication operations in this repository/task.
- 2026-07-15 — Publish 3.0.0 because replacing public provenance enums and the produced baseline format is intentionally incompatible; keep `v2.4.0` fixed in place.
- 2026-07-15 — Apply `max_capture_seconds` per stable capture lifecycle and report aggregate finalizer capture time across the before/after lifecycles.
- 2026-07-15 — Extend each Finalizer lifecycle deadline across its sensitive preflight and both stable passes; document that the summary duration is the combined before/after time.
- 2026-07-15 — Material config names require exact or strong credential/key context and reject security-domain descriptor suffixes; broad Git pathspecs remain candidate-only so schemas, policies, managers, and providers stay reviewable.

## Durable decision records

- Sensitive material and capture bounds: `docs/decisions/2026-07-15-sensitive-material-and-capture-bounds.md`.

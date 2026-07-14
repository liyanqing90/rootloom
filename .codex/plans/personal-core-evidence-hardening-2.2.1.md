# Harden Personal Core governed evidence

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-14
- Task type: security and public CLI/format defect repair
- Risk: Tier 2 (Governed)

## Goal and observable success

Repair all eleven findings in the Rootloom Personal Core 2.2.1 review so that an operator-sealed `VERIFIED_CHANGE` requires a sealed contract, stable repository base, complete structured claims, an explicit semantic-review assertion, preserved sensitive metadata, and successful strict-quality exit semantics. Focused regressions, repository validation, the full test suite, and a fresh counterexample review must pass.

After the first completion pass, independently challenge capture coherence, privacy quarantine, command/process transitions, scope attribution, and artifact publication. Close every serious counterexample and rerun the same broad evidence gates before returning the plan to complete.

The final code review then reproduced two additional release-blocking boundaries: an ignored sensitive path added after baseline could be discovered without activating quarantine before ordinary content reads, and a linked worktree could place evidence or bundle output inside its external Git common directory. Repair both at their owning boundaries, add fail-before regressions for every public entry point, and commit the complete scoped work without the unrelated illustration asset.

## Non-goals

- Do not reintroduce Enterprise Assurance approval, audit-runner, or recovery-journal machinery.
- Do not make the opt-in engineering-change workflow mandatory for ordinary Personal Core tasks.
- Do not read or persist sensitive file contents by default.
- Do not publish, tag, release, or mutate GitHub state in this task without separate authorization.

## Baseline evidence

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_engineering_change` passes 43 tests with 1 skip at `main` commit `09711c3`.
- The supplied 2.2.1 report identifies eleven data-flow/state-machine defects across contract sealing, strict exit semantics, metadata-only capture, sensitive directory classification, scope globs, semantic status, baseline identity, no-change priority, evidence schemas, intake creation, and symlink handling.
- The worktree contains unrelated untracked `assets/rootloom-xiaohei-loom.png`; it must remain untouched and outside task scope.
- The advisory analyzer reports minimum Tier 2 because state-machine and behavioral code are in scope. Baseline: `/tmp/rootloom-2.2.1-deep-review-baseline.json`.
- Post-review reproduction: a newly ignored `.env` plus an ordinary untracked file containing the same synthetic value produced `sensitive_change_quarantine: false`, `content_read: true`, and retained that value in the patch.
- Post-review reproduction: `begin_review.py` accepted a linked-worktree output below the external common directory's `refs/heads/` namespace and created a directory there.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Existing focused suite passes | fact | local macOS checkout | 2026-07-14 | `python3 -m unittest tests.test_engineering_change` | current; no sensitive content |
| Eleven governed-evidence defects are reproducible from source data flow | fact | local `main` plus supplied review | 2026-07-14 | attachment and named source paths | current; sensitive examples synthetic |
| Risk floor is Tier 2 | fact | local deterministic analyzer | 2026-07-14 | `/tmp/rootloom-2.2.1-deep-review-baseline.json` | current; advisory |

## Governed defect diagnosis

- Observed failure: internally consistent but unsealed or semantically unknown evidence can reach `VERIFIED_CHANGE`; strict mode can return zero; sensitive and scope changes can evade intended gates.
- Competing hypotheses: isolated test gaps versus incompatible ownership contracts. Source tracing rejects an isolated-test explanation because the public lifecycle and finalizer state machine explicitly encode the unsafe outcomes.
- Ownership path: `begin_review.py` → contract/seal loader → repository capture → finalizer gates/status/exit → public documentation.
- Violated invariant: `VERIFIED_CHANGE` must mean the pre-change base, immutable contract, captured repository state, structured verification claims, and operator semantic review are all bound and preserved.
- Root cause: mutable draft and seal state are conflated; several validators compare optional declarations rather than computed evidence; metadata/path/glob models are weaker than their documented semantics; status ordering and strict exit policy are inconsistent.
- Post-review root cause: baseline-aware quarantine compared only already-known sensitive records while `repository_snapshot()` treated only Git-status-sensitive endpoints as drift; ignored additions are discoverable but absent from Git status. Repository containment checks compared only the worktree even though `repository_identity()` already records the separate Git common directory.
- Root-cause alignment: PASS.

## Constraints and invariants

- Standard library only, local and network-free.
- Preserve v1 baseline/contract readability as self-declared compatibility input, but never upgrade legacy evidence to operator-sealed without the new seal.
- Keep advisory mode non-blocking by default; change strict mode only.
- Sensitive content remains metadata-only by default and summaries must say so explicitly.
- All file creation and reads must reject symlink redirection at the lexical path boundary.

## Impact map

- Producers: `begin_review.py`, new `seal_contract.py`, `runner/baseline.py`, `runner/state.py`.
- Consumers: `finalize_change.py`, `runner/change_contract.py`, CI/user scripts invoking strict mode.
- Persisted data: outside-repository baseline, draft contract, sealed contract, contract seal, review manifest, finalizer summary.
- Public contracts: `begin_review.py`, `seal_contract.py`, `finalize_change.py` CLI and JSON evidence/status fields.
- Generated artifacts: review intake files and final review bundles.
- External systems: none.

## Design and decisions

- Ownership: intake creation owns a draft-only transaction; sealing owns immutable final contract and seal creation; finalizer owns evidence validation and quality status.
- Interfaces: `begin_review` requires at least one `--path` unless `--allow-all-paths`; `seal_contract --review-dir` validates and seals; strict defaults to quality exit, with explicit `--strict-bundle-only` for non-blocking bundle generation.
- Compatibility window: advisory and legacy self-declared inputs remain readable; only v2 review manifests plus a valid contract seal can be operator-sealed.
- Alternatives rejected: editing `review.json` after drafting (repeats the broken lifecycle); hashing sensitive contents by default (violates metadata-only privacy); retaining slash-insensitive `fnmatch` (contradicts repository glob semantics).

## Implementation sequence

1. Add strict shared schema/path helpers, segment-aware globs, recursive sensitive classification, and stronger metadata.
2. Split intake into transactional draft creation and explicit immutable contract sealing.
3. Bind finalization to seal, repository HEAD/index, structured sealed claims, semantic review, corrected gate priority, and strict quality exit.
4. Update bilingual public documentation, architecture/maturity text, validator contracts, and the durable decision record.
5. Add fail-before counterexamples and positive lifecycle tests, then run focused and full validation.
6. Run a second-pass state-machine challenge independent of the supplied findings; harden mixed-time capture, sensitive replacement/ancestor handling, ignored-sensitive scope, command preflight, platform process fallback, and atomic intake publication.
7. Make repository capture compare a reference sensitive-metadata set before ordinary content reads, including newly discovered ignored additions; use the pre-capture set again after verification.
8. Centralize repository-storage containment across the worktree and Git common directory, then apply it to analyzer baselines, review intake/sealing, finalizer evidence, and bundle output.

## Rollout, failure, and rollback

- Dry-run/preview: all behavior is exercised in temporary Git repositories and outside-repository review directories.
- Mixed-version behavior: old contracts remain advisory/self-declared; new operator-sealed status requires the new lifecycle.
- Failure detection: nonzero strict exit, `FAILED`/non-verified quality status, seal/hash/schema errors, or regression failures.
- Rollback or compensation: revert the focused source/docs/tests commit; evidence files live outside repositories and require no migration.
- Irreversible point: none.

## Verification

- Original failure path: new regressions for mutable/missing contract hashes, strict partial coverage, equal-length sensitive rewrites, nested sensitive files, slash-crossing globs, semantically unknown evidence, base movement, invalid schemas/timestamps, intake partial failure, and symlink output.
- Owning-boundary invariant: focused unit tests for each producer/consumer plus a complete begin → edit draft → seal → strict finalize lifecycle.
- Adjacent negative/alternate path: advisory self-declared compatibility, explicit strict bundle-only, exact path-boundary matches, and clean no-change behavior.
- Focused tests: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_engineering_change`.
- Contract/migration tests: temporary-repository CLI lifecycle tests in the focused suite.
- Type/lint/build/package: `make validate`, `make test`, and `make check`.
- Security/dependency checks: repository validator plus searches for direct `fnmatch` scope use and legacy mutable-seal instructions.
- Post-action verification: fresh diff review and strongest counterexample audit.

### Executed evidence

- `PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest tests.test_engineering_change` — 64 tests, 1 skipped, passed.
- `make test` — 113 tests, 1 skipped, passed.
- `make compatibility-smoke` — passed; no plugin-install side effects or managed rollback leftovers.
- `make check` — repository validation plus 113 tests passed.
- `git diff --check` — passed.
- Fresh counterexample review found and fixed three additional gaps: legacy v1 evidence could claim operator provenance, dirty-baseline overlap/removal could be under-attributed, and schema-valid manifest byte drift was not seal-bound. Lexical parent traversal and analyzer baseline-output symlink handling were also tightened.

### Second-pass executed evidence

- `PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest tests.test_engineering_change` — 90 tests, 1 skipped, passed after the second-pass implementation.
- New fail-before counterexamples cover mixed-time repository state, sensitive replacement with an existing placeholder, sensitive exact-name directory descendants, hashed symlink targets, ignored-sensitive scope attribution, untracked high-risk code, all-command parse-before-execute, Windows Job Object fallback, no-replace intake publication, repository-symlink containment, strict JSON number bounds, and applyable empty/CR-only untracked patches.
- `make test` — 139 tests, 1 skipped, passed after the main second-pass implementation.
- `make compatibility-smoke` — passed; no plugin-install side effects or managed rollback leftovers.
- `make check` — repository validation plus 141 tests passed, with 1 skip because the current macOS filesystem rejects the non-UTF-8 filename fixture; the behavior remains covered on supporting systems and CI.
- `make validate`, `git diff --check`, and Python bytecode compilation of the changed modules — passed.
- The final independent challenge found and fixed two more lifecycle gaps: a failed reuse could leave an old authoritative `summary.json`, and Makefile target discovery reopened an unbounded symlink-following read. Output reuse now invalidates the old summary before accepted execution, while command discovery uses a bounded regular-file descriptor with no-follow and stat-drift checks.
- A fresh deterministic analyzer run over the complete worktree still reports minimum Tier 2 for broad blast radius and public-contract changes, matching this governed workflow; it reports no new semantic finding and explicitly remains advisory.
- No serious counterexample remains after the fresh state-machine, privacy, scope, publication, and process review. The remaining assurance limits below are explicit product boundaries rather than unresolved defects.

### Post-review boundary repair evidence

- The exact newly ignored sensitive-addition reproduction now activates quarantine before ordinary content reads; the synthetic value is absent from `diff.patch`, and the simultaneously added ordinary file is metadata-only. The same invariant holds when verification creates the ignored sensitive path.
- An unchanged ignored sensitive reference remains metadata-only without activating quarantine, proving the adjacent negative path.
- Analyzer baseline output, review intake, contract sealing, finalizer evidence input, and bundle output all reject a linked worktree's resolved Git common directory without creating artifacts there.
- Focused privacy, linked-worktree, symlink-parent, output-redirection, evidence-containment, intake, and sealing regressions passed with `ResourceWarning` promoted to errors.
- `make validate` passed; `make test` and the final `make check` each passed all 144 tests with one platform-conditional non-UTF-8 filename skip on the current macOS filesystem.
- `make compatibility-smoke` passed with no plugin-install side effects or managed rollback leftovers.
- `git diff --check` passed, and the unrelated `assets/rootloom-xiaohei-loom.png` remains untracked and excluded from the scoped commit.

## Risks

- Risk: stricter evidence schemas reject previously accepted malformed inputs.
  - Mitigation: preserve legacy inputs as self-declared where safe and document the compatibility boundary.
  - Residual risk: undocumented consumers relying on malformed strict evidence must update.
- Risk: filesystem metadata cannot prove sensitive content integrity against an attacker who can restore all observable metadata.
  - Mitigation: report `sensitive_integrity: metadata-observed` and avoid stronger claims.
  - Residual risk: metadata-only capture is detection, not cryptographic content integrity.
- Risk: an operator semantic-review assertion is not machine proof.
  - Mitigation: record its provenance explicitly and require it in addition to mechanical evidence.
  - Residual risk: a dishonest or mistaken assertion can still overstate review quality.
- Risk: this local evidence workflow is not a sandbox or adversarial audit system.
  - Mitigation: revalidate repository, Git, evidence, and output identity across verification; quarantine sensitive changes before content capture; document trusted-verifier assumptions.
  - Residual risk: external state, detached descendants, ignored non-sensitive files, `.git` administrative files, and copy-only secret movement without observable source metadata change remain outside the captured model.

## Decision log

- 2026-07-14 — Classify as Tier 2 because public evidence schemas, CLI exit behavior, privacy boundaries, and state-machine transitions change.
- 2026-07-14 — Preserve Personal Core's opt-in/advisory default while strengthening only explicit governed evidence.
- 2026-07-14 — Use canonical JSON without `contract_sha256` as the semantic contract hash and additionally bind the sealed file's raw-byte SHA-256.
- 2026-07-14 — Bind raw review-manifest bytes in the contract seal and refuse legacy/self-declared baselines in the sealing command; v1 remains readable only as self-declared compatibility evidence.
- 2026-07-14 — Treat changed dirty baselines conservatively: all current overlap enters scope, and disappearance of pre-existing dirty paths fails closed.
- 2026-07-14 — Require two identical bounded captures and post-verification evidence/Git revalidation rather than trusting individually valid but mixed-time observations.
- 2026-07-14 — Treat any sensitive metadata drift as a pre-content quarantine signal; synthesize ignored sensitive changes into scope and hash, rather than persist, symlink targets.
- 2026-07-14 — Use atomic no-replace intake publication and parse every verification command before executing the first one.
- 2026-07-14 — Invalidate prior summaries before any accepted output reuse and apply the same bounded no-follow repository-read contract to Makefile target discovery.
- 2026-07-14 — Treat the Git common directory as repository-owned storage for every evidence/output path check, including linked worktrees.
- 2026-07-14 — Bind quarantine to reference-versus-current sensitive metadata before content capture so ignored additions cannot enter ordinary patches.

## Durable decision records

- Update `docs/decisions/2026-07-14-personal-intelligence-contract.md` to reflect the accepted stricter governed-evidence semantics.

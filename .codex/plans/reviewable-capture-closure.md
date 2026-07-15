# Close the reviewable-path capture and privacy boundary

## Status

- State: complete
- Owner: Codex
- Last updated: 2026-07-15
- Task type: security defect and public CLI/evidence contract correction
- Risk: Tier 2 (Governed)

## Goal and observable success

Close every finding in the Rootloom Personal Core 3.1.0 audit and the post-review Git-index suppression counterexample without changing the default baseline-v3 workflow or silently changing the persisted baseline-v4 schema. An Intake that declares `--reviewable-path` must either name a Git-capturable, single-link regular file using the repository's actual spelling or fail before publication. Tracked declarations marked `assume-unchanged` or `skip-worktree` are not capturable because Git Status and Diff suppress their worktree changes, so Intake and every stable capture must reject them. DER material and common private-key PEM names must stay content-unread unless the path is an eligible ambiguous public artifact. Final summaries must disclose the exact Intake-sealed reviewability exception and policy hash.

Success is proven by fail-before/pass-after regression tests for ignored files, DER material, hardlinks, private-key names, case canonicalization, and summary disclosure; compatibility tests for baseline v2/v3/v4 and default v3 emission; `make validate`, `make test`, and `make check`; and a fresh counterexample review.

## Non-goals

- Do not add independent ignored-file content capture or a new baseline format in this patch.
- Do not inspect file contents to decide whether a reviewability exception is safe.
- Do not add a Finalizer reviewability flag or permit post-Intake policy mutation.
- Do not publish, tag, push, deploy, or alter the unrelated untracked image.

## Baseline evidence

- `repository_changes()` derives ordinary capture from `git status --porcelain=v1 -z --untracked-files=all`, which excludes ignored files.
- `discover_sensitive_paths()` sees ignored candidates, but `reviewable_paths` removes declared exceptions from the sensitive result; `repository_snapshot()` fingerprints only the status-derived `untracked` list.
- `.der` is currently in `PUBLIC_CERTIFICATE_SUFFIXES`, although DER can encode private keys.
- `validate_reviewable_paths()` rejects symlinks and non-regular files but does not reject `st_nlink != 1`.
- The strong-name policy misses `key.pem`, `server-key.pem`, `client-key.pem`, `host-key.pem`, `ssh-key.pem`, and `identity-key.pem`.
- Summary revision 5 carries the baseline hash and format but omits the reviewable path set and sensitive-policy hash.
- `git ls-files --cached` includes `assume-unchanged` and `skip-worktree` entries even though Git Status/Diff omit their worktree changes; a temporary-repository reproduction returned an empty Rootloom Snapshot/Patch for modified `public.pem` while stable capture accepted it.
- The worktree started at `1114e06` with one unrelated untracked file, `assets/rootloom-xiaohei-loom.png`; it must remain untouched.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Ignored reviewable content is absent from ordinary and sensitive capture | fact | local `main` source on macOS | 2026-07-15 | `runner/state.py::repository_snapshot` | current; no file content read |
| DER is an encoding that may carry private keys | supplied authoritative evidence | OpenSSL/RFC links in the user audit | 2026-07-15 | attached audit | source links only |
| Hardlink count is unchecked | fact | local `main` source | 2026-07-15 | `rootloom_paths.py::validate_reviewable_paths` | current |
| Summary omits reviewability policy | fact | local `main` source | 2026-07-15 | `finalize_change.py` | current |
| Index-suppressed tracked reviewable content is absent from ordinary capture | fact | local temporary Git repository on macOS | 2026-07-15 | `git ls-files -v`; `stable_repository_capture()` reproduction | synthetic path/content only |

## Governed defect diagnosis

- Observed failure: an ignored or index-suppressed declared file can change without entering Baseline, Scope, risk, or patch evidence; DER private material can remain readable by default; hardlink aliases and common private-key names can pass the declaration boundary; final evidence does not disclose the exception.
- Competing hypotheses: the seal/hash chain is bypassed, Git discovery is incomplete, or classification/validation is too weak. Baseline-v4 hash validation is intact; the missing task evidence is caused by the split between ignored-sensitive discovery and status-derived ordinary capture. The remaining findings reproduce at the shared path-policy and Summary owners.
- Ownership path: `rootloom_paths.py` owns material and filesystem eligibility policy; `runner/state.py` owns Git-capture eligibility and stable checks; `begin_review.py` owns canonical Intake declarations; `finalize_change.py` owns self-contained Summary evidence.
- Violated invariant: every reviewability exception must be sealed before implementation, remain capturable by the evidence path, never override a recognizable private key, and be disclosed to bundle consumers.
- Root cause: reviewability was threaded through classification but not gated against every Git suppression mechanism. The first correction rejected ignored paths but treated `ls-files --cached` membership as proof of capturability; index flags can preserve that membership while suppressing Status/Diff. Suffix/name and file-identity constraints were also incomplete, and Summary exposed only indirect hashes.
- Root-cause alignment: PASS.

## Constraints and invariants

- Keep default Intake output byte-contract compatible with baseline v3 and retain v2/v3/v4 read/seal support.
- Keep baseline v4 fields and snapshot schema unchanged; this patch rejects ignored reviewable files instead of pretending to capture them.
- Canonicalize declarations to the one actual Git-visible repository spelling; reject case-fold ambiguity.
- Reject tracked reviewable paths whose `git ls-files -v` tag is lowercase (`assume-unchanged`) or `S`/`s` (`skip-worktree`) at Intake and every stable capture.
- A reviewable target must have link count one at Intake and whenever capture may read it; deletion remains permitted after Intake.
- Explicit sensitive roots and strong material always win.
- All new Git queries share existing byte/path/time bounds and the aggregate capture deadline.
- Summary disclosure is an additive public field and therefore makes the aggregate release impact Minor even though the ignored-path/classifier corrections are individually Patch-compatible.

## Impact map

- Producers: `rootloom_paths.py`, `begin_review.py`, `runner/state.py`.
- Consumers: baseline producer/reader, Finalizer, risk intelligence, repository validator, unit/compatibility tests, English/Chinese docs.
- Persisted data: baseline v4 remains unchanged; Summary revision 5 gains one additive `reviewability_policy` object.
- Public contracts: `begin_review.py --reviewable-path` validation and Summary JSON.
- Generated artifacts: `summary.json`; no migration or rewrite of historical bundles.
- External systems: none in this task.

## Design and decisions

- Ownership: Git visibility and actual path spelling are resolved by bounded `git ls-files`; file type/link count remain shared filesystem policy.
- Interfaces: ignored existing targets fail with `reviewable path is ignored and cannot be captured reliably`; ambiguous case-fold matches fail; valid alternate casing is saved using Git's actual spelling.
- Dependency direction: Intake and stable capture consume one state helper; Finalizer consumes only baseline-sealed paths and cannot invent exceptions.
- Compatibility window: valid old v4 baselines remain finalizable; a pre-fix declaration that was never captured because it was ignored fails closed, including after deletion, unless its sealed Snapshot contains the ordinary per-path fingerprint. New v4 production has stricter Intake eligibility but no field change. Summary consumers must ignore or may consume the additive field under revision 5.
- Alternatives rejected: independent ignored capture requires a new schema plus trustworthy before/after patch semantics; mutating v4 snapshot fields would break strict 3.1.0 readers; content sniffing could expose secrets.

## Implementation sequence

1. Add focused regression tests for the six audit findings and observe the failures.
2. Correct DER/private-key classification and single-link filesystem validation.
3. Add bounded Git visibility/case canonicalization at Intake and every stable capture.
4. Add self-contained Summary policy disclosure and focused contract assertions.
5. Update English/Chinese public docs, the accepted security decision, changelog, and repository validation.
6. Add a fail-before regression for `assume-unchanged` and `skip-worktree`, implement bounded index-state rejection at the shared Git visibility owner, and prove Intake plus capture-time rechecks.
7. Run focused and full verification, then challenge analogous suffix/name/ignore/case/index-state paths and audit the final diff.

## Rollout, failure, and rollback

- Dry-run/preview: all behavior is exercised in temporary Git repositories.
- Mixed-version behavior: existing baselines remain readable; newly created invalid/ignored declarations fail earlier and cannot produce a bundle.
- Failure detection: exact CLI errors, classifier assertions, baseline format/hash checks, Summary field assertions, repository validation, and full tests.
- Rollback or compensation: revert the local scoped changes; no persisted or remote state is mutated.
- Irreversible point: none.

## Verification

- Original failure path: focused ignored-reviewable end-to-end test must fail before implementation and prove Intake rejection after.
- Owning-boundary invariant: classifier and validation tests for DER, strong PEM names, hardlinks, actual spelling, and Summary policy/hash.
- Adjacent negative/alternate path: `.crt/.cer/.p7b/.p7c`, `public.pem`, `certificate.pem`, tracked/untracked visible files, deletion, default v3, and legacy v2/v3/v4 remain valid.
- Focused tests: targeted `python3 -m unittest` cases in `tests.test_engineering_change`.
- Contract/migration tests: `python3 -m unittest tests.test_engineering_change` and `make validate`.
- Type/lint/build/package: `make check`.
- UI/browser evidence: not applicable.
- Security/dependency checks: no dependency change; fresh source/counterexample review.
- Post-action verification: `git diff --check`, scoped status, unchanged unrelated image, no external action.

### Executed evidence

- Fail-before: six focused regressions failed on the original implementation for ignored Intake, DER classification, hardlinks, common key names, actual path spelling, and Summary disclosure.
- Pass-after: the same focused regressions and the additional capture-time/legacy-safeguard cases passed after the scoped changes.
- `make check`: passed; repository validation passed and 181 tests completed successfully with 2 environment-dependent skips (case-distinct paths and non-UTF-8 filenames on the current macOS filesystem).
- `make compatibility-smoke`: passed against Codex CLI 0.144.2 with no failed commands, install side effects, or rollback leftovers.
- `git diff --check`: passed.
- Fresh counterexample review: PASS; ignored-after-Intake, Hardlink replacement, case-fold ambiguity, missing-without-fingerprint, default-v3, public-certificate, and disabled-policy paths remain fail-closed or compatible as designed.
- Post-review counterexample: PASS after a three-assertion fail-before reproduction. Bounded NUL-safe Index-state checks now reject both `assume-unchanged` and `skip-worktree` at Intake and after Intake during stable capture; focused regressions and the full local gates pass.
- Workspace/remote state: the unrelated `assets/rootloom-xiaohei-loom.png` remains untouched; no commit, tag, push, release, deploy, or external mutation was performed.

## Risks

- Risk: a Git-visible path becomes ignored after Intake and disappears from capture.
  - Mitigation: revalidate visibility inside each stable capture pass before patch production.
  - Residual risk: filesystem/Git state can race after the final bounded capture, the same local non-adversarial boundary as the existing worktree capture.
- Risk: stricter PEM names reject a legitimate public artifact.
  - Mitigation: restrict the new contexts to ambiguous suffixes and retain explicit public names without key context.
  - Residual risk: path-only policy cannot prove content; uncommon private-key names remain operator-declared sensitive territory.
- Risk: additive Summary fields surprise strict consumers.
  - Mitigation: retain format and revision and document that consumers branch by known fields while ignoring additive ones.
  - Residual risk: consumers that incorrectly reject additive fields may require an update.

## Decision log

- 2026-07-15 — Use the audit's Option A for the capture correction: reject ignored reviewable targets and preserve baseline-v4 wire compatibility.
- 2026-07-15 — Classify the aggregate future release as Minor because `reviewability_policy` is an additive observable Summary field under `CONTRIBUTING.md`.
- 2026-07-15 — Treat `.der` as ambiguous material because its encoding does not establish certificate/public-key semantics.
- 2026-07-15 — Normalize a declaration to Git's actual spelling before sealing and fail closed on case-fold ambiguity.
- 2026-07-15 — Enforce single-link regular files at both Intake and stable capture; disclose captured identity metadata in the final policy evidence without changing Baseline v4.
- 2026-07-15 — Permit a missing pre-fix untracked declaration only when the sealed baseline contains its ordinary readable fingerprint; this keeps legitimate deletion compatible without reviving the ignored-file gap.
- 2026-07-15 — Reopen the closure after a verified index-suppression counterexample; reject `assume-unchanged` and `skip-worktree` rather than changing baseline v4 or trusting final-only metadata.

## Durable decision records

- Updated: `docs/decisions/2026-07-15-sensitive-material-and-capture-bounds.md`.

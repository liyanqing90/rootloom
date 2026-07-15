# Separate secret material from security code and bound stable capture

- Status: accepted
- Date: 2026-07-15
- Owners: Rootloom maintainers
- Scope: shared path policy, sealed reviewability exceptions, Strict Review capture, summary provenance, and public version governance
- Supersedes: none
- Superseded by: none

## Context

Rootloom 2.4.0 correctly made redacted evidence review-blocking, but its shared `is_sensitive_path()` predicate treated both likely secret material and source code about credentials, tokens, or secrets as content that must not be read. That made ordinary authentication changes metadata-only while CamelCase credential configuration could be missed by Python reclassification. Capture also bounded each Git child independently without one deadline across both consistency passes. Finally, revision-4 summary provenance used `operator-sealed`, although the local workflow binds intake and hashes without proving an operator identity.

These are ownership and naming defects. Reversing the redaction cap would restore an incorrect pass; expanding the old predicate with exclusions would keep privacy and business-risk decisions coupled; retaining identity-suggesting provenance would continue to overstate the evidence.

The 3.0.0 release audit then exposed a narrower policy defect at the same owner. Prefix-matching every `.env*` name hid environment templates and unrelated `.environment`/`.envelope`/`.envoy` files. Treating public certificate containers and `certs` directories as material hid reviewable trust artifacts. Ambiguous formats such as `.pem` still require a deliberate escape hatch, but allowing Finalizer to invent that exception after Intake would break the sealed policy chain.

The 3.1.0 audit found that the new exception was sealed but not fully capturable. Git status omits ignored files, sensitive discovery deliberately removes a declared reviewable path from quarantine, and ordinary fingerprinting only visits status-derived untracked files. An ignored reviewable file could therefore change outside Baseline, Scope, risk, and Patch evidence. The audit also found that DER had been mistaken for a certificate type, even though OpenSSL processes private keys in DER and documents a PEM-to-DER private-key conversion, while RFC 5958 recommends DER for asymmetric private-key packages. Reviewable targets also lacked a hardlink boundary, common key-named PEM forms remained overridable, repository casing was not canonicalized, and Summary did not disclose the exception. A post-fix counterexample found the same evidence omission for tracked files marked `assume-unchanged` or `skip-worktree`: `ls-files --cached` still returned them while Status, Diff, Rootloom Snapshot, and Patch omitted their worktree changes.

## Evidence

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Four ordinary security-source examples were classified as sensitive material | fact | local 2.4.0 source on macOS | 2026-07-15 | `plugins/rootloom/lib/rootloom_paths.py`; fail-before classifier probe | current; paths only |
| Three CamelCase secret-config examples were discarded by Python reclassification | fact | local 2.4.0 source on macOS | 2026-07-15 | `rootloom_paths.py::path_words`; fail-before classifier probe | current; synthetic names only |
| Stable capture reset the full Git timeout for every child in both passes | fact | local 2.4.0 source | 2026-07-15 | `runner/state.py::stable_repository_capture` | current |
| Provenance binds local workflow artifacts but not identity, signatures, accounts, or devices | fact | local source and accepted product boundary | 2026-07-15 | `begin_review.py`; `seal_contract.py`; `docs/architecture.md` | current; no sensitive payload |
| Exact public enum/provenance changes are incompatible for consumers that compare values | inference grounded in consumer behavior | summary JSON contract and 2.4.0 audit | 2026-07-15 | `finalize_change.py`; `CONTRIBUTING.md` | current |
| Environment templates, unrelated `.env*` names, and public certificate formats were all classified as material | fact | local 3.0.0 source and fail-before matrix | 2026-07-15 | `rootloom_paths.py`; `tests/test_engineering_change.py` | current; synthetic paths only |
| A reviewability exception did not exist in sealed Intake policy | fact | local 3.0.0 baseline/intake/finalizer source | 2026-07-15 | `begin_review.py`; `runner/baseline.py`; `finalize_change.py` | current |
| Ignored reviewable files were absent from both ordinary fingerprints and sensitive metadata | fact | local 3.1.0 source and fail-before end-to-end test | 2026-07-15 | `runner/state.py`; `tests/test_engineering_change.py` | current; synthetic public material only |
| DER can encode private keys and is not a certificate-specific container | fact | OpenSSL 3.5 documentation and IETF RFC 5958 | 2026-07-15 | [OpenSSL `pkey`](https://docs.openssl.org/3.5/man1/openssl-pkey/); [RFC 5958](https://www.rfc-editor.org/rfc/rfc5958.html) | authoritative public sources |
| Link count, actual repository spelling, and final policy disclosure were absent | fact | local 3.1.0 source and fail-before tests | 2026-07-15 | `rootloom_paths.py`; `begin_review.py`; `finalize_change.py` | current; metadata only |
| Index-suppressed tracked files remained listed but absent from change evidence | fact | local temporary Git repositories on macOS | 2026-07-15 | `git ls-files -v`; `git status`; `git diff`; `stable_repository_capture()` | synthetic path/content only |

## Decision

`plugins/rootloom/lib/rootloom_paths.py` owns two distinct classifications:

- `is_sensitive_material_path()` is the only built-in privacy predicate. It controls targeted discovery, content suppression, metadata-only capture, quarantine, and secret-material deletion protection. It recognizes explicit roots, `.env`, `.envrc`, non-template `.env.<name>`, credential/config material, private-key and keystore formats, ambiguous `.pem` and `.der`, common key-named PEM/DER forms, and CamelCase material names. A security term, environment template, or certificate-specific public container alone is not sufficient.
- `is_security_domain_path()` is an advisory risk predicate. It recognizes authentication, authorization, permission, credential, secret, token, crypto, OAuth/OIDC/JWT, material paths, environment templates, public certificate formats, and sealed reviewability exceptions. It never causes content redaction.

Path tokenization splits dot/underscore/hyphen and CamelCase/acronym boundaries before comparison. Git pathspecs deliberately overmatch material candidates; the Python material predicate remains authoritative after candidate collection, with separate candidate and classified-result ceilings.

`.env.example`, `.env.sample`, `.env.template`, and `.env.dist` remain patch-readable security configuration. `.environment`, `.envelope`, and `.envoy` are ordinary. Certificate-specific `.crt`, `.cer`, `.p7b`, and `.p7c` files remain patch-readable security-domain artifacts; `.key`, `.p12`, `.pfx`, `.jks`, `.keystore`, and `.ppk` remain strong material. `.pem` and `.der` remain material by default because either encoding can contain public or private material. Ambiguous `key`, `client + key`, `server + key`, `host + key`, `ssh + key`, and `identity + key` names are strong and non-overridable, while public/trust names without a key signal remain eligible for explicit reviewability.

`begin_review.py --reviewable-path FILE` is the only sealed reviewability declaration and the only negative policy exception when a built-in material rule applies. A bounded case-insensitive literal Git listing resolves each declaration to one actual repository spelling. A separate bounded, NUL-safe `git ls-files -v` query rejects lowercase `assume-unchanged` tags and `S`/`s` `skip-worktree` tags rather than treating Index membership as proof that Status and Diff can observe changes. Intake then accepts only an existing Git-visible, Index-unsuppressed, single-link regular non-symlink file, including an already-reviewable environment template or certificate-specific public artifact. Ignored paths are rejected because baseline v4 has no independent ignored-reviewable capture contract; globs, case-fold ambiguity/duplicates, hardlinks, directories, missing paths, explicit sensitive overlap, and strong suffixes/names/directories also fail closed. Stable capture repeats visibility, Index-state, spelling, type, and link checks before accepting evidence. When consuming pre-fix v4 evidence, a missing untracked declaration is allowed only if its sealed snapshot contains the ordinary per-path fingerprint; this prevents a deleted, never-captured ignored file from disappearing again. The exact set is stored in `rootloom-change-baseline-v4`, included in `sensitive_policy_sha256`, transitively bound by the manifest/contract baseline hash, and always treated as security-domain risk. Finalizer has no equivalent option and cannot add declarations after Intake. Explicit sensitive policy wins even outside strict mode.

One `CaptureDeadline` owns a finite-positive monotonic budget for each stable capture lifecycle. The same instance spans sensitive preflight plus both consistency passes; each Git child receives the smaller of the configured per-command ceiling and remaining aggregate time. Bounded Python loops checkpoint the same deadline. Analyzer, intake, and finalizer expose `--max-capture-seconds` with a 90-second default. Finalizer applies that limit separately before and after verification; revision-5 `capture_duration_seconds` reports the combined observed time of those two lifecycles.

Default new intakes continue to use `rootloom-change-baseline-v3` with `intake-sealed`; only an Intake with a non-empty reviewable exception set emits baseline v4. Readers and sealers accept baseline v2 with its historical `operator-sealed` wire value, v3, and v4. The capture correction rejects unsupported ignored declarations instead of adding fields to the already published v4 schema. Summary revision 5 normalizes valid baseline provenance to `intake-sealed` and sealed contract/claim provenance to `workflow-sealed`; neither term claims identity. Its additive `reviewability_policy` object exposes whether the exception is enabled, exact paths, Intake source, sensitive-policy hash, and final captured device/file identity plus link metadata. `semantic_review: operator-asserted` remains an explicit semantic assertion, not an identity proof. `evidence_complete` is the stable automation capability; `quality_status` remains detailed diagnostic state.

Public contract releases follow impact rather than schema numbering: compatible correction is Patch, additive optional capability is Minor, and removed/replaced fields or enums, changed exits, incompatible reinterpretation, or mandatory incompatible formats are Major. A schema revision under the same `format` must still be assessed against real consumers. Published tags remain immutable.

## Alternatives considered

- Remove the redaction result cap — rejected because metadata-only evidence cannot support a complete review.
- Add source exclusions to one shared sensitive predicate — rejected because privacy and security-risk ownership would remain coupled and regress again as path forms expand.
- Treat every `secrets`/`credentials` directory as material regardless of file type — rejected because source modules such as `src/secrets/manager.py` must remain reviewable; explicit roots remain available for ambiguous repositories.
- Keep resetting `max_git_seconds` for each child — rejected because the declared resource boundary would still multiply with capture steps.
- Emit `operator-sealed` as a compatibility alias in revision 5 — rejected because an authoritative alias would preserve the identity overclaim. Historical summaries remain unchanged, while legacy baseline v2 stays readable by format.
- Publish the incompatible provenance/baseline change as 2.5.0 — rejected because that would repeat the release-governance defect identified in 2.4.0.
- Treat every certificate file or directory as material — rejected because public trust anchors and certificate chains are intended to be reviewed; private-key and keystore formats retain the privacy boundary.
- Allow `--reviewable-path` in Finalizer — rejected because a post-change exception would not be part of the sealed Intake policy.
- Let strong or explicitly sensitive paths be declared reviewable — rejected because that would create a direct privacy bypass. Exact non-strong files may be declared even when already reviewable so the supplied `.env.example` and public-certificate forms can be explicitly pinned without weakening current privacy policy.
- Make baseline v4 the mandatory default — rejected because callers that do not use the additive capability should retain the existing v3 wire contract.
- Continue treating `.der` as a public certificate format — rejected because DER is an encoding used by private-key formats and therefore cannot establish public content from the suffix alone.
- Add ignored-reviewable fingerprints and patches to baseline v4 — rejected for the capture correction because doing so would silently change a published strict schema without a trustworthy before/after patch contract. A future independent-capture design requires a new versioned format.
- Accept hardlinks because Personal Core is not an adversarial sandbox — rejected because link count is cheap, cross-platform file metadata and the alias can expose out-of-repository private material through an otherwise exact path.
- Clear `assume-unchanged` or `skip-worktree` automatically — rejected because Intake must not mutate user Index state, and clearing a flag would not bind a durable review decision. Unsafe declarations fail closed instead.

## Consequences

- Positive: security source, environment templates, and certificate-specific public artifacts remain fully reviewable while receiving high-risk verification guidance; DER and common private-key names stay private by default; exact reviewability pins and ambiguous downgrades are inspectable, capturable, sealed, and disclosed; ignored and Index-suppressed paths fail closed; stable capture has an aggregate bound; provenance names match actual evidence; version choices become predictable.
- Negative: path-only secret inference remains conservative and imperfect; some config-like fixtures with secret names are metadata-only; operators can deliberately expose the content of eligible ambiguous `.pem`/`.der` files after accepting the explicit local-policy risk; ignored public material cannot use the exception until a separately versioned capture contract exists; v4 adds compatibility code for consumers adopting the option.
- Operational: the original provenance/capture decision shipped in 3.0.0 and the additive reviewability refinement shipped in 3.1.0. Personal Core 3.2 closes the capture/privacy boundary while preserving historical tags/artifacts, keeping v3 as the default, and retaining baseline v2/v3/v4 schemas as unsafe declarations fail closed. The validation/classification repairs are Patch-compatible, but 3.2 is Minor because `reviewability_policy` is an additive observable Summary field. Cross-platform PR/main CI plus local contract/compatibility gates remain required before any future tag.

## Verification

- Focused regressions cover the supplied security-source and CamelCase material examples, the environment/public-certificate/DER matrices, exact reviewable Intake and v4 policy hashing, ignored/Index-suppressed/Hardlink/strong-name/Glob/directory/missing/Symlink/case-ambiguity/duplicate rejection, post-Intake Index-state rechecks, actual repository spelling, Finalizer-only consumption, Summary policy disclosure, material directory descendants, deletion behavior, risk signals, remaining Git timeout, one deadline across both passes, invalid budgets, baseline-v2/v3/v4 compatibility, and revision-5 summary fields/provenance.
- `make check`, `make compatibility-smoke`, `git diff --check`, and strict governed finalization are release gates.
- The release PR, merged `main`, tag peel, public Release metadata, publication record, and local installed-version/drift checks provide post-action evidence.

## Revisit when

- a common secret-material family cannot be identified without content inspection;
- source/config suffix classification produces repeated false positives or negatives;
- capture needs a resumable budget across verification or other paused phases;
- baseline v2/v3 compatibility has an explicit, versioned removal gate;
- ignored reviewable files gain a separately versioned before/after fingerprint and patch contract;
- Rootloom adopts real identity, signature, device, or immutable-audit guarantees.

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

## Decision

`plugins/rootloom/lib/rootloom_paths.py` owns two distinct classifications:

- `is_sensitive_material_path()` is the only built-in privacy predicate. It controls targeted discovery, content suppression, metadata-only capture, quarantine, and secret-material deletion protection. It recognizes explicit roots, `.env`, `.envrc`, non-template `.env.<name>`, credential/config material, private-key and keystore formats, ambiguous `.pem`, and CamelCase material names. A security term, environment template, or public certificate container alone is not sufficient.
- `is_security_domain_path()` is an advisory risk predicate. It recognizes authentication, authorization, permission, credential, secret, token, crypto, OAuth/OIDC/JWT, material paths, environment templates, public certificate formats, and sealed reviewability exceptions. It never causes content redaction.

Path tokenization splits dot/underscore/hyphen and CamelCase/acronym boundaries before comparison. Git pathspecs deliberately overmatch material candidates; the Python material predicate remains authoritative after candidate collection, with separate candidate and classified-result ceilings.

`.env.example`, `.env.sample`, `.env.template`, and `.env.dist` remain patch-readable security configuration. `.environment`, `.envelope`, and `.envoy` are ordinary. Public `.crt`, `.cer`, `.der`, `.p7b`, and `.p7c` files remain patch-readable security-domain artifacts; `.key`, `.p12`, `.pfx`, `.jks`, `.keystore`, and `.ppk` remain strong material. `.pem` remains material by default because it can contain either public or private material.

`begin_review.py --reviewable-path FILE` is the only sealed reviewability declaration and the only negative policy exception when a built-in material rule applies. It accepts an exact existing regular non-symlink file, including an already-reviewable environment template or public certificate, and rejects globs, case-insensitive duplicates, directories, missing paths, explicit sensitive overlap, and strong suffixes/names/directories. The exact set is stored in `rootloom-change-baseline-v4`, included in `sensitive_policy_sha256`, transitively bound by the manifest/contract baseline hash, and always treated as security-domain risk. Finalizer has no equivalent option and cannot add declarations after Intake. Explicit sensitive policy wins even outside strict mode.

One `CaptureDeadline` owns a finite-positive monotonic budget for each stable capture lifecycle. The same instance spans sensitive preflight plus both consistency passes; each Git child receives the smaller of the configured per-command ceiling and remaining aggregate time. Bounded Python loops checkpoint the same deadline. Analyzer, intake, and finalizer expose `--max-capture-seconds` with a 90-second default. Finalizer applies that limit separately before and after verification; revision-5 `capture_duration_seconds` reports the combined observed time of those two lifecycles.

Default new intakes continue to use `rootloom-change-baseline-v3` with `intake-sealed`; only an Intake with a non-empty reviewable exception set emits baseline v4. Readers and sealers accept baseline v2 with its historical `operator-sealed` wire value, v3, and v4. Summary revision 5 normalizes valid baseline provenance to `intake-sealed` and sealed contract/claim provenance to `workflow-sealed`; neither term claims identity. `semantic_review: operator-asserted` remains an explicit semantic assertion, not an identity proof. `evidence_complete` is the stable automation capability; `quality_status` remains detailed diagnostic state.

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

## Consequences

- Positive: security source, environment templates, and public certificates remain fully reviewable while receiving high-risk verification guidance; common CamelCase and strong secret material remains private; exact reviewability pins and ambiguous downgrades are inspectable and sealed; stable capture has an aggregate bound; provenance names match actual evidence; version choices become predictable.
- Negative: path-only secret inference remains conservative and imperfect; some config-like fixtures with secret names are metadata-only; operators can deliberately expose the content of an ambiguous `.pem` after accepting the explicit local-policy risk; v4 adds compatibility code for consumers adopting the option.
- Operational: the original provenance/capture decision shipped in 3.0.0. The additive reviewability refinement is prepared as 3.1.0; preserve all historical tags/artifacts, keep v3 as the default, accept baseline v2/v3/v4, and require cross-platform PR/main CI plus local contract/compatibility gates before tagging.

## Verification

- Focused regressions cover the supplied security-source and CamelCase material examples, the environment/public-certificate matrices, exact reviewable Intake and v4 policy hashing, strong-secret/Glob/directory/missing/Symlink/duplicate rejection, Finalizer-only consumption, material directory descendants, deletion behavior, risk signals, remaining Git timeout, one deadline across both passes, invalid budgets, baseline-v2/v3 compatibility, and revision-5 summary fields/provenance.
- `make check`, `make compatibility-smoke`, `git diff --check`, and strict governed finalization are release gates.
- The release PR, merged `main`, tag peel, public Release metadata, publication record, and local installed-version/drift checks provide post-action evidence.

## Revisit when

- a common secret-material family cannot be identified without content inspection;
- source/config suffix classification produces repeated false positives or negatives;
- capture needs a resumable budget across verification or other paused phases;
- baseline v2/v3 compatibility has an explicit, versioned removal gate;
- Rootloom adopts real identity, signature, device, or immutable-audit guarantees.

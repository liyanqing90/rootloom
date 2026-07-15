# Separate secret material from security code and bound stable capture

- Status: accepted
- Date: 2026-07-15
- Owners: Rootloom maintainers
- Scope: shared path policy, Strict Review capture, summary provenance, and public version governance
- Supersedes: none
- Superseded by: none

## Context

Rootloom 2.4.0 correctly made redacted evidence review-blocking, but its shared `is_sensitive_path()` predicate treated both likely secret material and source code about credentials, tokens, or secrets as content that must not be read. That made ordinary authentication changes metadata-only while CamelCase credential configuration could be missed by Python reclassification. Capture also bounded each Git child independently without one deadline across both consistency passes. Finally, revision-4 summary provenance used `operator-sealed`, although the local workflow binds intake and hashes without proving an operator identity.

These are ownership and naming defects. Reversing the redaction cap would restore an incorrect pass; expanding the old predicate with exclusions would keep privacy and business-risk decisions coupled; retaining identity-suggesting provenance would continue to overstate the evidence.

## Evidence

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| Four ordinary security-source examples were classified as sensitive material | fact | local 2.4.0 source on macOS | 2026-07-15 | `plugins/rootloom/lib/rootloom_paths.py`; fail-before classifier probe | current; paths only |
| Three CamelCase secret-config examples were discarded by Python reclassification | fact | local 2.4.0 source on macOS | 2026-07-15 | `rootloom_paths.py::path_words`; fail-before classifier probe | current; synthetic names only |
| Stable capture reset the full Git timeout for every child in both passes | fact | local 2.4.0 source | 2026-07-15 | `runner/state.py::stable_repository_capture` | current |
| Provenance binds local workflow artifacts but not identity, signatures, accounts, or devices | fact | local source and accepted product boundary | 2026-07-15 | `begin_review.py`; `seal_contract.py`; `docs/architecture.md` | current; no sensitive payload |
| Exact public enum/provenance changes are incompatible for consumers that compare values | inference grounded in consumer behavior | summary JSON contract and 2.4.0 audit | 2026-07-15 | `finalize_change.py`; `CONTRIBUTING.md` | current |

## Decision

`plugins/rootloom/lib/rootloom_paths.py` owns two distinct classifications:

- `is_sensitive_material_path()` is the only built-in privacy predicate. It controls targeted discovery, content suppression, metadata-only capture, quarantine, and secret-material deletion protection. It recognizes explicit roots, `.env*`, credential/config material, private keys, certificates, keystores, and CamelCase material names. A security term in a source-code filename is not sufficient.
- `is_security_domain_path()` is an advisory risk predicate. It recognizes authentication, authorization, permission, credential, secret, token, crypto, OAuth/OIDC/JWT, and material paths. It never causes content redaction.

Path tokenization splits dot/underscore/hyphen and CamelCase/acronym boundaries before comparison. Git pathspecs deliberately overmatch material candidates; the Python material predicate remains authoritative after candidate collection, with separate candidate and classified-result ceilings.

One `CaptureDeadline` owns a finite-positive monotonic budget for each stable capture lifecycle. The same instance spans sensitive preflight plus both consistency passes; each Git child receives the smaller of the configured per-command ceiling and remaining aggregate time. Bounded Python loops checkpoint the same deadline. Analyzer, intake, and finalizer expose `--max-capture-seconds` with a 90-second default. Finalizer applies that limit separately before and after verification; revision-5 `capture_duration_seconds` reports the combined observed time of those two lifecycles.

New intakes use `rootloom-change-baseline-v3` with `intake-sealed`. Readers and sealers continue to accept baseline v2 with its historical `operator-sealed` wire value. Summary revision 5 normalizes valid baseline provenance to `intake-sealed` and sealed contract/claim provenance to `workflow-sealed`; neither term claims identity. `semantic_review: operator-asserted` remains an explicit semantic assertion, not an identity proof. `evidence_complete` is the stable automation capability; `quality_status` remains detailed diagnostic state.

Public contract releases follow impact rather than schema numbering: compatible correction is Patch, additive optional capability is Minor, and removed/replaced fields or enums, changed exits, incompatible reinterpretation, or mandatory incompatible formats are Major. A schema revision under the same `format` must still be assessed against real consumers. Published tags remain immutable.

## Alternatives considered

- Remove the redaction result cap — rejected because metadata-only evidence cannot support a complete review.
- Add source exclusions to one shared sensitive predicate — rejected because privacy and security-risk ownership would remain coupled and regress again as path forms expand.
- Treat every `secrets`/`credentials` directory as material regardless of file type — rejected because source modules such as `src/secrets/manager.py` must remain reviewable; explicit roots remain available for ambiguous repositories.
- Keep resetting `max_git_seconds` for each child — rejected because the declared resource boundary would still multiply with capture steps.
- Emit `operator-sealed` as a compatibility alias in revision 5 — rejected because an authoritative alias would preserve the identity overclaim. Historical summaries remain unchanged, while legacy baseline v2 stays readable by format.
- Publish the incompatible provenance/baseline change as 2.5.0 — rejected because that would repeat the release-governance defect identified in 2.4.0.

## Consequences

- Positive: security-domain source remains fully reviewable while receiving high-risk verification guidance; common CamelCase secret material remains private; stable capture has an aggregate bound; provenance names match actual evidence; version choices become predictable.
- Negative: path-only secret inference remains conservative and imperfect; some config-like fixtures with secret names are metadata-only; revision-5 exact provenance consumers must update; a new baseline format adds compatibility code.
- Operational: release as 3.0.0, preserve all historical tags/artifacts, accept baseline v2 and v3 during the compatibility window, and require cross-platform PR/main CI plus local contract/compatibility gates before tagging.

## Verification

- Focused regressions cover the supplied security-source and CamelCase material examples, material directory descendants, deletion behavior, risk signals, remaining Git timeout, one deadline across both passes, invalid budgets, baseline-v2 compatibility, and revision-5 summary fields/provenance.
- `make check`, `make compatibility-smoke`, `git diff --check`, and strict governed finalization are release gates.
- The release PR, merged `main`, tag peel, public Release metadata, publication record, and local installed-version/drift checks provide post-action evidence.

## Revisit when

- a common secret-material family cannot be identified without content inspection;
- source/config suffix classification produces repeated false positives or negatives;
- capture needs a resumable budget across verification or other paused phases;
- baseline v2 compatibility has an explicit, versioned removal gate;
- Rootloom adopts real identity, signature, device, or immutable-audit guarantees.

# Reviewable sensitive-material policy

## Status

- State: complete — local 3.1.0 candidate; external publication requires renewed authorization
- Owner: Codex
- Last updated: 2026-07-15
- Task type: security and public CLI/schema contract
- Risk: Tier 2 (Governed)

## Goal and observable success

Make Rootloom distinguish actual secret material from reviewable security artifacts without weakening quarantine. Environment templates and public certificates remain visible in review patches and raise security risk; unrelated `.env*` names remain ordinary. A user may declare one exact, existing regular file reviewable only at `begin_review`, with that declaration sealed into Intake and the sensitive-policy hash. Already-reviewable templates and public certificates may be pinned; ambiguous material may be downgraded. Private keys, keystores, explicit sensitive paths, directories, globs, missing paths, and symlinks remain non-overridable.

Success is proven by fail-before/pass-after classifier, capture, baseline, seal, finalizer, analyzer, and compatibility tests; `make validate`, `make test`, and `make check`; and a fresh source/contract challenge review.

## Non-goals

- Do not inspect file contents to decide whether a path is secret.
- Do not add a `--reviewable-path` option to Finalizer or permit post-Intake policy changes.
- Do not weaken redaction caps, command authorization, evidence sealing, or existing strong-secret rules.
- Do not redesign Summary revision 5, add identity/signatures, or revive enterprise approval machinery.
- Do not publish, tag, push, or create a GitHub release without renewed task-scoped release authorization.

## Baseline evidence

- `plugins/rootloom/lib/rootloom_paths.py` uses `part.startswith(".env")`, `**/.env*`, public-certificate suffixes, and `certs`/`certificates` material directories.
- A local classifier probe on 2026-07-15 returned `material=True` for `.env.example`, `.env.sample`, `.env.template`, `.env.dist`, `.environment`, `.envelope`, `.envoy`, and public `.crt/.cer/.der/.p7b/.p7c` files.
- Baseline v3 seals `sensitive_paths` and a policy hash but has no reviewable exceptions. Finalizer accepts only baseline-declared sensitive additions and has no sealed way to carry a reviewable exception.
- The working tree started at `7de74a4` with one unrelated untracked user file, `assets/rootloom-xiaohei-loom.png`; it must remain untouched and untracked.

### Evidence provenance

| Claim | Kind | Source and environment | Observed | Reference | Freshness / redaction |
| --- | --- | --- | --- | --- | --- |
| `.env*` prefix overmatches templates and ordinary names | fact | local `main` source and Python probe | 2026-07-15 | `plugins/rootloom/lib/rootloom_paths.py` | current commit; paths only |
| public certificate containers are quarantined | fact | local `main` source and Python probe | 2026-07-15 | `plugins/rootloom/lib/rootloom_paths.py` | current commit; paths only |
| review policy is baseline-sealed | fact | local `main` source | 2026-07-15 | `runner/baseline.py`, `begin_review.py`, `seal_contract.py`, `finalize_change.py` | current commit |
| release audit requires three fixes | supplied evidence | user attachment | 2026-07-15 | `pasted-text.txt` attachment | user-provided audit; no secrets copied |

## Governed defect diagnosis

- Observed failure: benign templates/public certificates trigger whole-change quarantine, unrelated dotfiles beginning with `.env` are falsely sensitive, and ambiguous one-off files have no seal-bound reviewability escape hatch.
- Competing hypotheses: Git discovery alone overmatches; suffix rules alone overmatch; or the shared classifier owns the defect. Direct calls to `is_sensitive_material_path()` reproduce every false positive, while Git pathspecs add unnecessary candidates, so both classifier policy and discovery breadth require correction.
- Ownership path: `plugins/rootloom/lib/rootloom_paths.py` owns classification/discovery policy; baseline and strict-review scripts own immutable policy transport.
- Violated invariant: privacy redaction must classify secret material, while security-domain artifacts must remain reviewable and still raise risk.
- Root cause: broad `.env` prefix, certificate suffix, and certificate-directory material rules conflate naming association with secret-bearing likelihood; sealed Intake lacks an exact negative exception.
- Root-cause alignment: PASS.

## Constraints and invariants

- Default existing strict reviews remain baseline v3 and preserve its field/schema compatibility.
- Baseline v4 is opt-in only when at least one `--reviewable-path` is declared; v2 and v3 remain readable and sealable.
- Reviewable paths are canonical, case-fold unique, repository-relative exact files that exist as regular non-symlink files at Intake.
- Explicit sensitive roots and strong-secret forms always win and cannot overlap a reviewable declaration.
- The reviewable set is included in the sensitive-policy hash and transitively sealed by the manifest/contract baseline hash.
- Capture never reads sensitive material contents merely to classify policy.
- Security-domain analysis includes environment templates, public certificates, and every sealed reviewable override.

## Impact map

- Producers: `rootloom_paths.py`, `begin_review.py`, `baseline.py`.
- Consumers: capture/state, seal/recovery, Finalizer, risk intelligence, tests, repository validator, user documentation.
- Persisted data: opt-in Baseline format v4 and sealed review bundle files.
- Public contracts: `begin_review.py --reviewable-path`, baseline schema, sensitive-policy hash semantics, package version.
- Generated artifacts: review bundles under repository-owned evidence paths.
- External systems: GitHub release only after a separate authorization gate.

## Design and decisions

- Ownership: shared path policy defines material/domain/override eligibility; strict-review baseline owns the sealed exception set.
- Interfaces: repeatable `--reviewable-path FILE` is accepted only by `begin_review`; invalid, duplicate, overlapping, or strong-secret paths fail closed before baseline creation.
- Dependency direction: capture and analyzer consume the shared policy; they do not grow local classifier copies.
- Compatibility window: v3 remains the default schema; v4 is emitted only for the new option. Readers accept v2/v3/v4. No old enum/field is removed.
- Alternatives rejected: changing every baseline to v4 creates gratuitous incompatibility; a Finalizer option permits policy mutation after sealing; content sniffing risks secret exposure; treating all certificates as material hides public artifacts; allowing strong-secret overrides creates an unsafe footgun.

## Implementation sequence

1. Add regression tests that demonstrate current false positives and absent sealed override behavior.
2. Refine shared env/certificate material and security-domain rules plus targeted Git discovery.
3. Add exact reviewable-path validation and opt-in baseline v4, then thread the sealed set through capture, risk analysis, and Finalizer.
4. Update English/Chinese public documentation, ADR, changelog/version, and repository validation.
5. Run focused and full verification, inspect the final diff and public schemas, and challenge bypass/compatibility cases.
6. Prepare a local release candidate; stop before any external publication gate.

## Rollout, failure, and rollback

- Dry-run/preview: run classifier probes and focused tests entirely in temporary repositories before packaging.
- Mixed-version behavior: unchanged calls emit v3; only consumers invoking the new option receive v4 and therefore require the new reader.
- Failure detection: strict JSON/schema errors, policy-hash mismatch, unexpected quarantine status, risk-floor assertions, repository validation, and cross-platform CI after publication.
- Rollback or compensation: revert the local change before release; after a future release, preserve v4 reading support even if the CLI feature is deprecated.
- Irreversible point: creating/pushing a tag or GitHub release; requires renewed explicit authorization.

## Verification

- Original failure path: focused tests for the `.env` matrix and public-certificate matrix must fail before implementation and pass after.
- Owning-boundary invariant: tests for exact override validation, policy hash, v4 schema, sealing, and Finalizer-only consumption.
- Adjacent negative/alternate path: private keys/keystores/explicit-sensitive overlap reject overrides; `.environment/.envelope/.envoy` stay ordinary; legacy v2/v3 remain accepted.
- Focused tests: `python3 -m unittest` with the new `tests.test_engineering_change` cases.
- Contract/migration tests: full `python3 -m unittest tests.test_engineering_change` and `make validate`.
- Type/lint/build/package: `make check`.
- UI/browser evidence: not applicable.
- Security/dependency checks: source challenge review plus `make test`.
- Post-action verification: clean scoped diff, package/version consistency, no change to the unrelated image, and no external tag/release.

Executed evidence as of 2026-07-15:

- Fail-before: eight focused tests produced 26 expected assertions covering every original false positive and the absent CLI/schema path.
- Pass-after: focused classifier/Intake/Finalizer matrices pass, including policy-hash tamper, strong-secret refusal, and post-Intake symlink replacement.
- `make check`: 174 tests passed with one environment-specific non-UTF-8 filesystem skip; repository validation passed.
- `make compatibility-smoke`: passed with Codex CLI 0.144.2, no install side effects, no managed rollback leftovers, and expected command-rule decisions.
- `git diff --check`: passed.
- Final source/contract challenge: default calls still emit field-identical baseline v3; `.env.example`, public `.crt`, and public `.pem` declarations emit sealed v4 and remain high risk; strong/CamelCase secret names, explicit Sensitive roots, type replacement, and rename non-transfer all fail closed or quarantine as designed.
- Self-review correction: the first implementation accepted only ambiguous built-in material. The supplied CLI examples also require already-reviewable templates and public certificates to be pinnable, so the final contract accepts any exact non-strong/non-explicit regular file while preserving every privacy hard stop.

## Risks

- Risk: a reviewable override suppresses quarantine for a real secret.
  - Mitigation: exact existing regular file only, sealed at Intake, strong/explicit secret rejection, prominent warning, and retained high security risk.
  - Residual risk: the operator can deliberately downgrade an ambiguous filename; this is explicit local policy, not machine proof of safe content.
- Risk: discovery misses a newly narrowed env form.
  - Mitigation: `.env`, `.envrc`, `.env.<environment>` coverage plus classifier recheck and matrix tests.
  - Residual risk: uncommon secret names still require `--sensitive-path`; this is an accepted name-based boundary.
- Risk: schema consumers reject v4.
  - Mitigation: opt-in emission only; default remains v3; document the compatibility requirement.
  - Residual risk: callers adopting the new option must upgrade their consumer.

## Decision log

- 2026-07-15 — Keep baseline v3 as the default and introduce v4 only for sealed reviewable exceptions, minimizing public-contract blast radius.
- 2026-07-15 — Public certificates and environment templates are security-domain evidence, not secret material by default.
- 2026-07-15 — Strong secrets and explicit sensitive declarations are non-overridable; Finalizer has no policy-mutation flag.
- 2026-07-15 — A sealed reviewable path may be deleted but must remain a regular file while present; a later Symlink/directory replacement fails before patch capture.
- 2026-07-15 — Strong secret naming overrides an otherwise public certificate suffix; public trust artifacts remain reviewable only when the path does not independently signal secret/key material.
- 2026-07-15 — Exact non-strong paths may be explicitly pinned even when already reviewable, matching the supplied `.env.example` and public-certificate CLI examples; every declaration still emits v4 and raises security risk.

## Durable decision records

- Updated accepted record: `docs/decisions/2026-07-15-sensitive-material-and-capture-bounds.md`.

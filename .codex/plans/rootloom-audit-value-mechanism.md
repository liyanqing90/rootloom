# Rootloom audit-depth and mechanism-value correction

## Status

- State: complete locally; release remains unauthorized
- Owner: Codex
- Last updated: 2026-07-12
- Risk: Tier 2 (workflow and acceptance contract)

## Goal

Make Rootloom discover and falsify rather than merely confirm a supplied issue, while reducing ceremony and configuration. Success means ordinary review/high-risk workflows require an adjacent analog search, a strongest counterexample, and a mechanism-value decision; the Strict Runner consumes existing hypotheses/rejected-alternatives/residual-risk data and refuses PASS without a compact challenge record. No new stage, agent, dependency, or external action.

## Baseline and ponytail audit

- `run_pipeline.py` is 4,228 lines; adding another stage or audit subsystem would increase the dominant monolith.
- `hypotheses`, `rejected_alternatives`, and `residual_risks` already exist but are weakly or not semantically gated.
- Review PASS currently requires only no hard finding plus non-empty compliance/test prose.
- Seven provenance fields are required even for stable local source facts.
- Four new state-budget flags expose implementation detail that can be two operator decisions.

Ranked simplification findings:

1. `shrink:` consume existing hypothesis/alternative/risk fields instead of adding another audit stage.
2. `delete:` remove universal runtime provenance ceremony for repository-local facts; keep it conditional for material runtime/external evidence.
3. `shrink:` merge visible/status/control/stage-output knobs into path-count and state-byte budgets.
4. `yagni:` reject a new deep-audit Skill; strengthen default workflows so users do not need to remember a special mode.

## Invariants

- A review of a supplied finding must search at least one analogous sibling path and attempt to disprove the proposed completion.
- A new mechanism is accepted only when it names the failure it prevents, owning boundary, executable enforcement, proof, and operator decision changed; otherwise delete or document it.
- No-material-finding outcomes require inspected surfaces and verification gaps, not generic assurance.
- Added audit structure must remain smaller than a new stage/agent and must reuse existing model calls.

## Implementation

1. Tighten operating review/coding/high-risk Skills with discovery yield, falsification, and mechanism-value gates.
2. Make local provenance compact; semantically gate multiple hypotheses, rejected alternatives, and residual risks.
3. Add one compact Review `challenge` object: strongest counterexample, adjacent analog checked, and complexity/value judgment.
4. Merge four state-budget flags into `--max-state-paths` and `--max-state-bytes`.
5. Update prompts, tests, validator, bilingual docs, and run full verification.

## Verification

- Source-before: PASS had no challenge contract; reproduced evidence allowed one unchecked hypothesis; GO did not consume rejected alternatives; four state controls exposed producer details.
- Pass-after: semantic tests reject missing challenge, a single reproduced hypothesis, missing contradiction evidence, unknown contradiction provenance, and empty rejected alternatives; a concrete challenged PASS succeeds.
- `PYTHONWARNINGS=error::ResourceWarning make check` — PASS: validator, 43 repository tests, 82 focused Runner tests.
- `make compatibility-smoke` — PASS on local `codex-cli 0.144.0-alpha.4`; prior config restored and no managed leftovers.
- Python compile, Ruby workflow-YAML parse, standalone validator, and `git diff --check` — PASS.

## Fresh challenge findings

- The first semantic implementation checked contradiction references only on the final hypothesis because validation sat outside the loop. The gate now validates every hypothesis, with a regression for a fabricated earlier reference.
- The analogous repository-topology and Git-control-tree paths still used `os.walk()` or `sorted(rglob())`, so enumeration could materialize before the claimed budget fired. Recursive allowed-path validation had the same class. All three now traverse incrementally and fail at the shared path/byte limits.
- The same analog scan found full NUL splitting, unbounded task/role reads, pre-budget path bytes, human-review directory materialization, and path-based Artifact append verification. These now use incremental parsing/reads, bounded input, fail-closed entry counts, and one no-follow regular-file descriptor for append/rollback/verification.
- The challenge record can still be fabricated by a model. Documentation states that executable reproduction and owner-boundary tests remain stronger; no extra reviewer or score was added.

## Outcome

- Existing Evidence, Diagnosis, and Review calls now carry discovery/falsification/value work; stage count, agent count, dependencies, and external actions are unchanged.
- Four public state/output knobs became two operator decisions.
- `repository` provenance no longer requires synthetic runtime metadata; `runtime_external` records machine-require stronger attribution, so simplification does not weaken external evidence.
- Runner contract advanced from 2.15 to 2.16 under Unreleased; the installable plugin manifest remains 1.2.11.

## Non-goals

- More agents, model calls, dependencies, dashboards, scores, or checklist fields.
- Claiming the model cannot fabricate a challenge; executable reproduction and deterministic tests remain stronger evidence.
- Commit, push, tag, or release.

## ROOT_CAUSE_ALIGNMENT

PASS — the owning defect is the acceptance contract and default workflow, not a lack of additional runtime controls.

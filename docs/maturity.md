# Maturity, guarantees, and compatibility

Rootloom Personal Core 2.2 is an early-stage, single-maintainer product. Its goal is to make Codex engineering behavior more deliberate and inspectable without imposing deep-review cost on installation or routine work; the repository does not yet contain controlled evidence that it reduces defects or review time.

Release `v2.0.0` passed the repository's Linux Python 3.11–3.14, macOS, Windows, and pinned Codex CLI contract matrix. That proves the checked mechanics on those environments, not model-level engineering quality.

## What is executable

- deterministic, bounded, network-free project-guidance scanning;
- fail-closed Hook enablement from managed local policy;
- explicit install/upgrade/status/rollback behavior for the personal setup targets, with installed-hash drift refusal;
- ordinary local lock serialization and per-file atomic replacement;
- drift-refusing backup restoration;
- all-command preflight parsing followed by no-shell execution, streaming output ceilings, and descendant-process cleanup;
- out-of-repository, ownership-marked review bundles with bounded status, patch, fingerprints, command count, and aggregate log;
- opt-in atomic no-replace pre-change baselines plus explicit draft-to-sealed strict Tier 1/2 contracts;
- two-pass stable repository capture, strict evidence JSON, segment-aware scope globs, and unchanged HEAD/ref/index binding;
- ordinary untracked content fingerprints, applyable bounded text patches, and tracked/untracked risk signals, with recursive metadata-observed sensitive capture and sensitive-change quarantine;
- exact dangerous-path deletion confirmation;
- explainable static risk floors over task, path, tracked/non-sensitive-untracked diff, operation, and active-memory signals;
- risk-specific verification recommendations kept separate from executed test evidence;
- bounded, relevant, stale-aware project-memory context plus locked explicit updates and one shared strict reader contract;
- repository validation, unit tests, and an offline Codex compatibility smoke.

## What remains semantic

Rootloom does not mechanically prove:

- that collected evidence is complete or true;
- that the diagnosed root cause is correct;
- that the change contract captures every consumer;
- that chosen tests are sufficient;
- that a final review missed no defect;
- that static risk classification captures every semantic effect;
- that a suggested verification command is safe, sufficient, or has run;
- that project memory is current or correct.

Skills guide these decisions; current repository and runtime evidence must verify them.

## Personal safety boundary

The personal artifact bundle is mutable and local. Verification commands are trusted operator input, not sandboxed workloads; argv and output are retained verbatim and must not carry credentials. Capture does not cover non-sensitive ignored files, Git administrative files, external state, detached managers, or a secret copied to an ordinary path without an observable change at its sensitive source. The setup lock is cooperative and ordinary. Setup is atomic per file but not across the complete target set. Backup/rollback is designed for normal local mistakes, not power-loss recovery, hostile same-user races, signed approval, immutable audit, regulated retention, or multi-operator environments.

Those assurance mechanisms remain on `codex/enterprise-assurance`; they are not implied by Personal Core.

## Compatibility

Normal CI validates Python 3.11–3.14 on Linux and portable contracts on macOS/Windows. The pinned Codex compatibility job proves marketplace/plugin installation has no global-policy or review-gate side effects, then separately exercises the optional personal setup round trip and command Rules. A separate live smoke is manual because it requires a logged-in Codex session and a real model turn.

Personal Core 2.0 intentionally breaks the 1.2.19 high-assurance Skill, strict Runner CLI, custom-agent/profile setup, Human Review formats, protected-deletion approval, and recovery-journal contracts. Migrate by rolling back with 1.2.19 first.

Personal Core 2.1 keeps `rootloom-project-memory-v1` envelopes and legacy entries readable. New ID, evidence, status, path, and expiry fields are additive. The existing `rootloom-engineering-summary-v1` fields remain; `risk_assessment` and `verification_plan` are additive, and old `--risk low|medium|high` calls still work. A supplied risk can no longer lower the static detected floor.

Personal Core 2.2 retains the summary format name while revision 3 tightens explicit governed evidence. Advisory finalization remains non-blocking by default. Strict review uses a draft → seal lifecycle, stable two-pass capture, strict JSON, post-verification evidence/base revalidation, reference-aware sensitive-change quarantine, worktree plus Git-common-directory containment, unchanged HEAD/ref/index, and structured sealed claims. It defaults to quality exit codes; `--strict-bundle-only` preserves an explicit non-blocking strict bundle. `semantic_coverage: reviewed` is an operator assertion, not machine proof. Unknown semantics can reach at most `MECHANICALLY_VERIFIED`, and only sealed mechanical evidence plus that assertion yields `VERIFIED_CHANGE`/`passed: true`. Pure verification requires `--allow-no-change`, but invalid evidence and process/capture failures take priority over `NO_CHANGE`.

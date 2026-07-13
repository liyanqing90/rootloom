# Maturity, guarantees, and compatibility

Rootloom Personal Core 2.1 is an early-stage, single-maintainer product. Its goal is to make Codex engineering behavior more deliberate and inspectable; the repository does not yet contain controlled evidence that it reduces defects or review time.

Release `v2.0.0` passed the repository's Linux Python 3.11–3.14, macOS, Windows, and pinned Codex CLI contract matrix. That proves the checked mechanics on those environments, not model-level engineering quality.

## What is executable

- deterministic, bounded, network-free project-guidance scanning;
- fail-closed Hook enablement from managed local policy;
- plan/apply/status/rollback behavior for the personal setup targets;
- ordinary local lock serialization and per-file atomic replacement;
- drift-refusing backup restoration;
- no-shell verification command execution with bounded output;
- out-of-repository review bundles with bounded patch, command count, and aggregate log;
- exact dangerous-path deletion confirmation;
- explainable static risk floors over task, path, tracked diff, operation, and active-memory signals;
- risk-specific verification recommendations kept separate from executed test evidence;
- bounded, relevant, stale-aware project-memory context plus schema-checked explicit updates;
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

The personal artifact bundle is mutable and local. The setup lock is cooperative and ordinary. Setup is atomic per file but not across the complete target set. Backup/rollback is designed for normal local mistakes, not power-loss recovery, hostile same-user races, signed approval, immutable audit, regulated retention, or multi-operator environments.

Those assurance mechanisms remain on `codex/enterprise-assurance`; they are not implied by Personal Core.

## Compatibility

Normal CI validates Python 3.11–3.14 on Linux and portable contracts on macOS/Windows. The pinned Codex compatibility job exercises marketplace installation, plugin discovery, the personal setup round trip, and command Rules. A separate live smoke is manual because it requires a logged-in Codex session and a real model turn.

Personal Core 2.0 intentionally breaks the 1.2.19 high-assurance Skill, strict Runner CLI, custom-agent/profile setup, Human Review formats, protected-deletion approval, and recovery-journal contracts. Migrate by rolling back with 1.2.19 first.

Personal Core 2.1 keeps `rootloom-project-memory-v1` envelopes and legacy entries readable. New ID, evidence, status, path, and expiry fields are additive. The existing `rootloom-engineering-summary-v1` fields remain; `risk_assessment` and `verification_plan` are additive, and old `--risk low|medium|high` calls still work. A supplied risk can no longer lower the static detected floor.

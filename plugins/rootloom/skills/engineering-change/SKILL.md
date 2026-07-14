---
name: engineering-change
description: Run an opt-in deep, single-agent engineering review with risk analysis, bounded capture, verification claims, and a machine summary. Use when the user explicitly requests this Skill, a machine review bundle, or strict evidence for a high-risk/release change. Do not invoke automatically for routine repository work merely because Rootloom is installed.
---

# Engineering change

Run one focused engineering loop. Stay single-agent unless the user explicitly asks for delegation.

This Skill is opt-in. Plugin installation and ordinary Tier 0/1 implementation do not trigger it, and they do not require its analyzer, baseline, contract, or finalizer. Use repository evidence and proportional tests directly unless the user, repository guidance, or a high-risk/release workflow calls for the deeper bundle.

Default sequence: Evidence → Diagnosis → Change Contract → Implementation → Verification → Final Review Summary.

## 1. Route the task

For an advisory assessment, run the deterministic scanner without creating a baseline:

```bash
python3 <skill-dir>/scripts/analyze_change.py \
  --repo /absolute/path/to/repository \
  --task 'Describe the requested behavior' \
  --path src/anticipated-owner.py
```

For strict governed evidence, run it before editing and add the external baseline:

```bash
python3 <skill-dir>/scripts/analyze_change.py \
  --repo /absolute/path/to/repository \
  --task 'Describe the requested behavior' \
  --path src/anticipated-owner.py \
  --write-baseline /absolute/path/outside-repo/baseline.json
```

The external baseline is mandatory only when the finalizer will run with `--strict` for Tier 1/2. It captures bounded tracked/untracked state plus metadata-only ignored, secret-like, symlink, and directory state. Use repeatable `--sensitive-path` for additional metadata-only paths. Never recreate a missing intake baseline after implementation and present it as pre-change evidence.

Inspect every reported signal. The scanner combines task text, paths and operations, bounded tracked diff signals, repository commands, and relevant active project memory. It reports a minimum Tier and verification plan; it cannot prove semantic risk. Raise the tier further when current evidence or unknown consumers require it.

Then classify the request:

- **Tier 0 Direct** — mechanical, local, reversible, and directly verifiable;
- **Tier 1 Scoped** — behavioral change or defect with a bounded ownership path;
- **Tier 2 Governed** — public or persisted contracts, schemas, migrations, security, infrastructure, destructive effects, or materially uncertain blast radius.

Use `operating-coding-change` for Tier 0/1 discipline and `operating-high-risk-change` for Tier 2. Do not use this Skill to bypass an approval gate.

## 2. Load project intelligence

Read the closest `AGENTS.md`. When `.project-memory/` exists, use `project_memory.py context` with the task query and in-scope paths so only relevant active risks, failures, and decisions enter the task. Treat stale matches as history and all memory as leads; repository evidence is truth. Never create or update memory silently.

## 3. Establish evidence and diagnosis

Inspect the observable path and its owning boundary before editing. For a defect, record:

- the trigger and observed failure;
- at least two plausible causes when the root cause is uncertain;
- evidence that rejects the strongest alternative;
- the violated invariant and evidence-backed root cause;
- `ROOT_CAUSE_ALIGNMENT: PASS` before implementation.

For a feature or mechanical change, use `ROOT_CAUSE_ALIGNMENT: NOT_APPLICABLE` and state the intended invariant instead.

## 4. Form the change contract

Tier 0 may keep an internal contract. Advisory finalization may omit a machine contract. Strict Tier 1/2 finalization must provide `rootloom-change-contract-v1` and name:

- allowed files or module boundary;
- forbidden or explicitly excluded scope;
- public/persisted compatibility expectations;
- required verification for the original path, owning invariant, and an adjacent path;
- rollback and remaining risk.

Minimal machine contract:

```json
{
  "format": "rootloom-change-contract-v1",
  "allowed_paths": ["src/auth/**", "tests/auth/**"],
  "forbidden_paths": ["src/billing/**"],
  "root_cause_alignment": "PASS",
  "verification_commands": {
    "verify-primary": "python3 -m unittest tests.test_auth.AuthTests.test_login",
    "verify-invariant": "python3 -m unittest tests.test_auth.TokenTests",
    "verify-adjacent": "python3 -m unittest tests.test_auth.AuthTests.test_expired"
  },
  "verification_claims": {
    "primary": ["verify-primary"],
    "invariant": ["verify-invariant"],
    "adjacent": ["verify-adjacent"]
  }
}
```

The contract never authorizes commands by itself. Every mapped command must still be passed through `--verify` or directly declared with `--verify-claim CLAIM:COMMAND`.

## 5. Implement once, in scope

Use existing architecture and dependencies. Preserve unrelated user changes. Fix the invariant at its owner, not a downstream symptom. Do not add a wrapper, flag, record, or approval step unless it changes a concrete decision.

Before deleting a secret-like file, `.env`, migration, or database artifact, stop and obtain confirmation for the exact path. Ordinary source-file deletion still requires careful diff review but not a separate state machine.

## 6. Verify intelligently

Choose checks from the changed behavior, not only from convenient commands. Map each material change to:

- the original or primary behavior;
- the owning-boundary invariant;
- an adjacent negative or alternate path;
- the smallest focused test, then broader checks proportional to blast radius.

Run repository-owned commands and observe their exit status. Classify failures as introduced, pre-existing, environmental, or unverified.

Use the analyzer's `verification_plan.required_behaviors` as a checklist, not evidence. Its `suggested_commands` are repository-derived suggestions and are never executed automatically. Record only commands actually run under `tests`.

For a non-blocking machine-readable local summary, run:

```bash
python3 <skill-dir>/scripts/finalize_change.py \
  --repo /absolute/path/to/repository \
  --output /absolute/path/to/run \
  --task 'Describe the requested behavior' \
  --verify 'python3 -m unittest tests.test_example' \
  --remaining-risk 'Describe only a material remaining risk'
```

Advisory mode exits successfully when the explicit commands pass and capture remains stable, even if no baseline/contract proves complete coverage. It reports `quality_status: UNVERIFIED` and keeps compatibility `passed: false`; exit zero means the bundle operation succeeded, not that engineering sufficiency was proven.

For release or other explicitly governed work, add:

```text
--strict \
--baseline /absolute/path/outside-repo/baseline.json \
--change-contract /absolute/path/to/change-contract.json
```

The output directory must be outside the repository and must be absent, empty, or already carry Rootloom's ownership marker. The helper recomputes the assessment, does not run a shell, and writes ordinary `diff.patch`, `test.log`, and `summary.json` files. Ordinary untracked files receive streaming SHA-256 fingerprints and bounded text patches; binary/large files receive type, size, and hash; sensitive files remain metadata-only. Status, patch, fingerprints, command output, and memory reads all fail closed at configured bounds.

Verification commands run in a controlled process tree. Output is consumed incrementally and the tree is terminated on timeout, output overflow, or leaked descendants. The summary records observed/retained bytes, process convergence, `commands_passed`, `capture_preserved`, `verification_coverage`, and authoritative `quality_status`. `passed` remains for compatibility but becomes true only for `VERIFIED_CHANGE`; it cannot turn an unrelated passing command into verified engineering evidence. Pure verification requires `--allow-no-change` and reports `NO_CHANGE`.

`--risk low|medium|high` remains optional and can raise but never lower the detected floor. `--strict` requires the intake baseline and change contract for Tier 1/2 and returns nonzero when governed evidence is incomplete. Advisory mode never upgrades incomplete evidence to verified quality. Protected deletions still require every exact path to be repeated with `--confirm-dangerous-delete` after user confirmation.

## 7. Challenge and summarize

Inspect the actual diff, one analogous path, and the strongest plausible counterexample. Remove complexity that does not earn its keep.

Finish with:

```json
{
  "changed_files": [],
  "risk": "low | medium | high",
  "risk_assessment": {"minimum_tier": 0, "signals": []},
  "tests": [],
  "verification_plan": {"status": "suggested-not-executed"},
  "commands_passed": true,
  "capture_preserved": true,
  "verification_coverage": "complete",
  "quality_status": "VERIFIED_CHANGE",
  "remaining_risks": []
}
```

Report the observable outcome first, then exact verification and only material remaining risk.

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

For intake-sealed governed evidence, create a review directory before editing:

```bash
python3 <skill-dir>/scripts/begin_review.py \
  --repo /absolute/path/to/repository \
  --task 'Describe the requested behavior' \
  --output /absolute/path/outside-repo/run \
  --path src/anticipated-owner.py
```

`begin_review.py` requires at least one `--path`; use `--allow-all-paths` only when whole-repository scope is intentional. It normally requires a clean worktree/index, while `--allow-dirty-baseline` explicitly records pre-existing changes. If the aggregate tracked patch later changes, finalization conservatively scopes still-dirty tracked endpoints because the baseline cannot prove their per-path attribution; exact unchanged untracked fingerprints remain pre-existing and outside task scope, risk analysis, and `diff.patch`, while changed fingerprints remain conservatively attributed and a pre-existing dirty path that disappears fails closed. Intake creation uses a temporary-directory transaction followed by the platform's atomic no-replace rename, so capture/write failure leaves no final run and a concurrently created destination is never overwritten.

The intake contains `baseline.json`, editable `change-contract.draft.json`, and immutable-input `review.json`. Edit only the draft, replace every exact Rootloom contract placeholder, and then seal it:

```bash
python3 <skill-dir>/scripts/seal_contract.py \
  --review-dir /absolute/path/outside-repo/run
```

Sealing deeply validates and normalizes the draft, then exclusively creates `change-contract.json` and `contract.seal.json`. The seal binds the canonical contract hash, raw sealed-file hash, review-manifest byte hash, baseline hash, run ID, nonce, and task hash. Do not edit the sealed contract or manifest; finalization rejects post-seal drift. If an interruption left an exact final contract without its seal, rerun with `--recover`; recovery validates the current baseline, manifest, draft-derived contract, and existing bytes and never overwrites mismatched evidence.

For an analyzer-only baseline, run it before editing and add the external baseline:

```bash
python3 <skill-dir>/scripts/analyze_change.py \
  --repo /absolute/path/to/repository \
  --task 'Describe the requested behavior' \
  --path src/anticipated-owner.py \
  --write-baseline /absolute/path/outside-repo/baseline.json
```

The external baseline is mandatory only when the finalizer will run with `--strict` for Tier 1/2. New baselines use `rootloom-change-baseline-v3` with canonical `run_id`, nonce, timestamps and hashes plus repository/Git identity; v3 names the local intake fact `intake-sealed`. Legacy v1/v2 baselines remain readable, and valid sealed v2 intakes remain sealable. A baseline is accepted only after two consecutive bounded captures agree; strict finalization binds current HEAD, symbolic HEAD ref, and index to it and rechecks the base after verification. Both passes share one finite-positive `--max-capture-seconds` monotonic deadline (default 90). Every Git child runs through the controlled process-tree owner with closed stdin and receives the smaller of the remaining capture time and finite-positive `--max-git-seconds` (default 30). Baselines capture bounded tracked/untracked state plus metadata-only ignored secret material, symlinks, and directories. `is_sensitive_material_path()` alone controls privacy capture; `is_security_domain_path()` raises risk for security source without suppressing its patch. Targeted discovery has an independent bounded candidate ceiling; positive `--max-sensitive-paths` (default 10,000) limits only the classified material-result union. Never recreate a missing intake baseline after implementation and present it as pre-change evidence.

Inspect every reported signal. The scanner combines task text, paths and operations, bounded tracked and non-sensitive untracked diff signals, repository commands, and relevant active project memory. It reports a minimum Tier and verification plan; it cannot prove semantic risk. Raise the tier further when current evidence or unknown consumers require it.

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
    "primary": [{
      "id": "primary-behavior",
      "command_ids": ["verify-primary"],
      "target": "tests/test_auth.py::AuthTests.test_login",
      "expected_evidence": "valid login creates a session",
      "evidence_kind": "regression-test"
    }],
    "invariant": [{
      "id": "owning-invariant",
      "command_ids": ["verify-invariant"],
      "target": "tests/test_auth.py::TokenTests",
      "expected_evidence": "token invariants hold",
      "evidence_kind": "unit-test"
    }],
    "adjacent": [{
      "id": "adjacent-path",
      "command_ids": ["verify-adjacent"],
      "target": "tests/test_auth.py::AuthTests.test_expired",
      "expected_evidence": "expired login remains rejected",
      "evidence_kind": "regression-test"
    }]
  },
  "baseline_sha256": "<sha256 of baseline.json>",
  "task_sha256": "<baseline task_sha256>",
  "run_id": "<baseline run_id>",
  "nonce": "<baseline nonce>"
}
```

This is the editable draft shape; `seal_contract.py` adds `contract_sha256` to the immutable final contract. The hash basis is canonical JSON without that field, and `contract.seal.json` additionally binds the final file bytes.

The contract never authorizes commands by itself. Every mapped command must still be passed through `--verify`. Simple string claims and temporary `--verify-claim` values remain diagnostic declarations and cannot complete strict evidence. Only structured claims originating in the sealed contract qualify for strict claim completeness. A structured target check is still mechanical evidence, not proof that the test is semantically sufficient.

## 5. Implement once, in scope

Use existing architecture and dependencies. Preserve unrelated user changes. Fix the invariant at its owner, not a downstream symptom. Do not add a wrapper, flag, record, or approval step unless it changes a concrete decision.

Before deleting secret material, `.env`, a migration, or a database artifact, stop and obtain confirmation for the exact path. Security-domain source deletion raises risk and still requires careful diff review, but it does not invoke the privacy confirmation solely because its name contains token, credential, or secret.

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

Advisory mode exits successfully when the explicit commands pass and capture remains stable, even if no baseline/contract proves complete coverage. It reports `quality_status: UNVERIFIED` and keeps compatibility `passed: false`; default `--exit-policy bundle` means exit zero can mean "bundle generated", not "engineering sufficiency proven". Use `--exit-policy quality` or `--require-verified` in CI.

For release or other explicitly governed work, add:

```text
--strict \
--baseline /absolute/path/outside-repo/baseline.json \
--change-contract /absolute/path/outside-repo/change-contract.json \
--semantic-coverage reviewed
```

Strict mode defaults to quality exit semantics: only `REVIEW_EVIDENCE_COMPLETE` returns zero. Use explicit `--strict-bundle-only` when a non-blocking strict bundle is intentionally required. Evidence and output paths must be outside both the repository worktree and its resolved Git common directory, including for linked worktrees; output must also be absent, empty, or already carry Rootloom's ownership marker. A reused owned output invalidates its previous summary before the new run can exit early. Lexical path and parent checks reject symlink redirection before resolution. The helper recomputes the assessment, does not run a shell, and writes ordinary `diff.patch`, `test.log`, and `summary.json` files.

Ordinary untracked files receive streaming SHA-256 fingerprints and bounded applyable text patches; only task-attributed non-material text participates in risk analysis and the final patch. Binary/large files receive type, size, and hash. Secret-material discovery asks Git only for shared case-insensitive candidate pathspecs and literal declared roots, then reclassifies every returned path with `is_sensitive_material_path()`; deliberately overmatching candidates and classified results use separate bounded ceilings. Material includes `.env*`, credential configuration, private keys, certificates, keystores, explicit roots, and common CamelCase names. Security-domain source stays content-readable and raises high-risk verification signals instead. Material files remain content-unread and metadata-only, including device/inode or platform equivalents, link count, size, mode, modification time, and change time; symlink targets are represented only by byte length and SHA-256. Any material metadata change before or during verification, including a newly discovered ignored addition relative to the reference capture, quarantines every changed endpoint before ordinary content capture, disables additional repository-memory/command discovery, and places ignored material additions, changes, and deletions into scope. An otherwise-complete redacted review is capped at `REVIEW_REQUIRED_WITH_REDACTIONS` with `evidence_complete: false` and `passed: false`. The summary reports `sensitive_integrity: metadata-observed`; this detects ordinary same-size rewrites but is not cryptographic content integrity. Status, patch, fingerprints, command output, and memory reads all fail closed at configured bounds.

Evidence JSON rejects duplicate keys, non-standard constants, and out-of-range numbers. Every verification command is parsed before the first command executes. Evidence files, seals, the Git base, and the output target are revalidated after command execution; trust-input drift forces `FAILED`.

Verification commands run in a controlled process tree. Output is consumed incrementally and the tree is terminated on timeout, output overflow, or leaked descendants. Personal Core reports `isolation: process-group-only`; it is not a sandbox for untrusted commands and cannot govern detached service managers, containers, privileged background processes, non-sensitive ignored files, Git administrative state, or external state. Command argv and output are retained verbatim in the local bundle, so never place credentials in verification commands or print them. A secret copied to an ordinary path without an observable sensitive-source change is outside the path-classifier guarantee. The summary records observed/retained bytes, `process_convergence`, `commands_passed`, `capture_preserved`, structured `claim_binding`, broader `declared_claim_binding`, `semantic_coverage`, evidence provenance, hash chain, and authoritative `quality_status`.

`semantic_coverage: reviewed` is an explicit operator assertion, reported separately as `semantic_review: operator-asserted`, not machine proof. `unknown` can reach at most `MECHANICALLY_VERIFIED`; an unsealed assertion is `SEMANTIC_REVIEW_ASSERTED`; workflow-sealed mechanical evidence plus the assertion yields `REVIEW_EVIDENCE_COMPLETE`. That state means the evidence chain is complete, not that correctness was proven. `evidence_complete` and `passed` remain true only for `REVIEW_EVIDENCE_COMPLETE`; prefer `evidence_complete` for stable automation and treat the detailed status as diagnosis. Summary provenance uses `intake-sealed` / `workflow-sealed`, not an identity claim. Pure verification requires `--allow-no-change` and reports `NO_CHANGE` only after more severe gate/process errors have been excluded.

`--risk low|medium|high` remains optional and can raise but never lower the detected floor. `--strict` requires the intake baseline and change contract for Tier 1/2, refuses inconsistent seals/hash chains or moved HEAD/ref/index, and uses quality exit codes by default. Advisory mode never upgrades incomplete evidence to verified quality. Protected deletions still require every exact path to be repeated with `--confirm-dangerous-delete` after user confirmation.

## 7. Challenge and summarize

Inspect the actual diff, one analogous path, and the strongest plausible counterexample. Remove complexity that does not earn its keep.

Finish with:

```json
{
  "schema_revision": 5,
  "changed_files": [],
  "risk": "low | medium | high",
  "risk_assessment": {"minimum_tier": 0, "signals": []},
  "tests": [],
  "verification_plan": {"status": "suggested-not-executed"},
  "commands_passed": true,
  "capture_preserved": true,
  "claim_binding": "complete",
  "verification_coverage": "complete",
  "semantic_coverage": "reviewed",
  "semantic_review": "operator-asserted",
  "evidence_provenance": {
    "baseline": "intake-sealed",
    "change_contract": "workflow-sealed",
    "verification_claims": "workflow-sealed",
    "semantic_review": "operator-asserted"
  },
  "capture_limits": {"max_capture_seconds": 90, "max_git_seconds": 30},
  "capture_duration_seconds": 2.41,
  "quality_status": "REVIEW_EVIDENCE_COMPLETE",
  "evidence_complete": true,
  "passed": true,
  "remaining_risks": []
}
```

Report the observable outcome first, then exact verification and only material remaining risk.

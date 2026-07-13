# Maturity, guarantees, and compatibility

Rootloom is an early-stage, single-maintainer project. Its repository structure, tests, and release gates can demonstrate how the shipped mechanisms behave; they do not yet demonstrate broad adoption, team-scale outcomes, fewer production defects, or a measured reduction in rework. Independent usage reports and longitudinal quality data are not established evidence today.

## What “reliable” means here

“Reliable Codex engineering” is the design goal. A concrete claim is valid only at the boundary where Rootloom has executable proof:

| Claim | Current evidence | Not guaranteed |
| --- | --- | --- |
| Setup compensates caught failures and recovers recorded interrupted apply/rollback operations | shared no-follow/reparse-aware single-link lock opener, Manifest-bound recovery journal, versioned historical target schemas, fault-injected state-commit compensation, simulated abrupt apply/rollback interruption followed by `recover`, hashes, mode-preserving rollback tests | crash consistency under an actual `SIGKILL`, host/power failure, storage corruption, or parent-directory durability below atomic file replacement |
| Project seeding is bounded | deterministic local scanner, repository-contained non-symlink evidence, shared hardened Git-common-dir writer lock, snapshot recheck, and regression tests | semantic completeness or perfectly current architecture knowledge |
| Command policy is intentional | pinned and latest-CLI offline lifecycle smoke for direct-argv commit, push, and destructive reset | shell-wrapped equivalents, every administrator/platform policy composition, or future CLI semantics |
| High-assurance execution is deterministic | fixed stage order, linked provenance IDs, metadata-only secret/ignored capture shared by entrypoint readers, pre-capture scope gates, mapped command results, per-command repository fences, bounded command-output tails, minimal verification environment names, detected and command-scoped verification-entrypoint fingerprints, and bounded repair cycles | factual truth of model evidence, output-secret redaction, hidden CLI path parsing, proof that a command uses every bound dependency, full dependency-closure binding, semantic adequacy of selected commands, correct root cause, business correctness, or production safety |
| Review is independent by role | separate read-only reviewer configuration | human-independent correctness or elimination of shared model bias |

JSON Schema validates required shape. Semantic gates validate selected cross-stage consistency. Neither proves that a model's statement is true, and process discipline does not prove the conclusion true. Repository source, reproducible behavior, attributable runtime evidence, tests, reviewers, CI, and production controls remain necessary.

Runner artifact redaction is also narrower than file-access isolation. Ignored and known/configured sensitive untracked paths are not content-hashed or supplied in Delta prompts, but read-capable model stages can still open them from the repository. Use secret-free worktrees, external secret storage, or OS/container mount policy when deny-read behavior is required. Built-in sensitive-name matching is deliberately finite; repository-specific names require explicit rules or opt-in untracked-dotfile redaction.

Redaction follows paths, not byte provenance. Copying protected bytes into an ordinary allowed path can make the copy eligible for content hashing and Delta capture. Delta generation is streamed and complete-or-fail under explicit tracked/ordinary-untracked byte budgets; internal capture disables repository diff/textconv execution, verifies complete writes and batch rollback, and loads only fixed prompt excerpts, but this is not content-lineage DLP. Process cleanup likewise governs only the original POSIX process group: a descendant can create a new session and survive. Direct-parent completion starts the hard local drain deadline immediately for both managed commands and Runner-owned Artifact capture; a detected drain cutoff now forces effective exit 125 and blocks automated acceptance. The escaped process may still act after failure or avoid detection by closing inherited output, so hostile commands require container, cgroup, or equivalent job isolation.

Managed stdout/stderr retention is bounded per command; verification also has retained-output and actual serialized-NDJSON batch budgets, a command-count ceiling, and a model-facing summary ceiling. Escape bytes are counted before rejected records are materialized, and minimum record space is checked before command execution. Model-stage outcomes have structured sidecars, and exceptional exits clean the original process group even after the direct parent exits. Deterministic verification no longer inherits the complete host environment by default. Explicit `--verify-env` opt-in passes a value to the command while recording only its name. These controls reduce memory denial-of-service, repeated-write amplification, and accidental credential propagation; they do not redact a secret that a command obtains from an allowed variable, HOME, a file, a subprocess, or the network and then prints within the retained tail.

Visible path sets, `git status`, index/control-ref data, Delta/log records, and model `-o` JSON now have producer-specific limits, and stable content hashes can be reused inside one locked run. These controls are not a single filesystem quota: Codex may briefly write beyond the stage-output limit before post-command rejection, metadata manifests still scale up to the path ceiling, and hostile same-inode metadata restoration is outside the cache threat model. Very large or hostile workloads still need an isolated worktree and external filesystem/job quotas.

Detected metadata-only path changes are ineligible for automated acceptance by default. The gate runs after the writer and is not OS-level write prevention or rollback, so the operator may need to recover a protected filesystem change after failure. An operator may authorize deletion of one exact baseline path, but the authorization is preflighted before the writer, requires a clean baseline with no repair cycle, and forces a deletion-only run; ordinary edits, renames, moves, or visible file creations must be done separately. The Runner then exits with `HUMAN_REVIEW_REQUIRED`; it cannot claim automated PASS because neither the model nor the artifact proves the former protected content. Protected verification harnesses are rejected before fingerprinting. Topology and per-command state checkpoints reduce writer-created or verification-created nested-repository and batch-mutation TOCTOU risk, and detected/command-scoped verification-entrypoint fingerprints reduce writer-created harness redirection, but arbitrary external processes, hidden command indirection, semantic non-use of a bound dependency, and unbound harness dependency files can still mutate or redirect behavior outside those checkpoints.

`HUMAN_REVIEW_REQUIRED` now has a v4 accept/reject command bound to the exact final validated worktree/index/Git-control commitment, exact-missing protected targets and parent boundaries, canonical run-directory identity, the complete final metadata-only floor, bounded private Artifact hashes, and reviewer/local identity. Initial Binding carries the validated floor before reads and refuses commitment drift instead of adopting it. Result is read through stable no-follow descriptors before the append, after it, and after the repeated commitment; a copied run, Result mutation, repository drift, or protected-path declassification refuses or compensates the decision. Per-file/aggregate Artifact bytes are enforced from observed descriptor reads, with count, binding time, and Result size separately bounded. Terminal and Summary share a 1 MiB producer/consumer limit, are preflighted before either file exists, and stay pinned through final exact-byte-count/SHA-256 validation; reviewer/local-account identities are capped at 4096 UTF-8 bytes. The verifier validates the exact persisted Binding schema and all internal commitments before recapture, fixes malformed evidence at `INVALID`/9, and reserves `STALE`/12 for structurally valid current-state drift; bounded stderr adds a reason while stdout remains machine-stable. Schema, binding recomputation, pair I/O, decision transaction, and verification classification now have separate modules. The hardened cooperative lock and repeated checks cannot stop arbitrary same-UID writers or replacement of the locked pathname with a new inode. Human Review v4 is therefore frozen as attributable final review for trusted personal or small-team environments, not hostile local approval or cryptographically signed/WORM organizational evidence; stronger governance belongs to immutable snapshots, independent workers or UIDs, external signers, remote immutable Artifact stores, and WORM audit systems.

The optional isolation launcher must live outside the repository and Artifact root and is identity-checked through a stable no-follow descriptor at configuration and immediately before every spawn. That proves path identity at those checks, not launcher semantics, kernel policy, or freedom from the final path-to-`exec` race. Hostile commands still require an immutable container/cgroup worker or equivalent externally attested execution platform.

## Adoption fit and learning cost

Use the smallest capability that pays for itself:

- `skills-only` or `guidance` for individuals who mainly want reusable workflows or project context;
- `engineering` as the normal single-agent default;
- `delegated` only when controlled role separation is worth its token and coordination cost;
- `full` only when fixed stages and stronger local gates justify the setup and operational overhead.

The five presets, four role files, Rules, Hooks, and runner are intentionally inspectable, but they impose learning and maintenance cost. Rootloom is not automatically better than a concise `AGENTS.md` plus CI for a small, low-risk repository.

The challenge contract improves default search behavior but cannot prove that a model genuinely explored or falsified a claim. A filled counterexample or analog field can still be shallow or fabricated. Fail-before/pass-after reproduction, owner-boundary tests, raw runtime evidence, and independent source inspection remain stronger than structured prose. The mechanism therefore reuses existing stages and fields instead of pretending that another reviewer or longer checklist creates assurance.

## Platform scope

Rootloom is Codex-specific by design. Skills, Hooks, Rules, profiles, and custom-agent configuration follow Codex interfaces and may need maintenance as those interfaces change. Portable project truth should live in source, tests, schemas, ordinary documentation, and decision records—not only in Codex configuration.

The strict high-assurance runner supports Linux, macOS, and WSL and rejects native Windows. The v1.2.17 CI matrix runs full Linux checks on Python 3.11–3.14, macOS Strict Runner tests, portable setup/guidance/hook and hardened-cooperative-lock tests on macOS and Windows, and the pinned Codex CLI compatibility smoke; exact POSIX permission-mode assertions remain Linux/macOS-only because Windows exposes ACL/read-only semantics rather than `fchmod`. Release run `29234377961` passed all eight jobs against exact tagged commit `4b749632ca042a73546defd1e3ff0ddf2bdfe82c`. Native custom-role/model routing is still not attested on the currently verified spawn surface, so the sequential runner is the supported route when model assignment must be evidenced.

The compatibility policy has two tracks:

1. a pinned Codex CLI version is the required, reproducible contract in normal CI;
2. a scheduled latest-version probe detects upstream drift early and is informational until reviewed and adopted.

Both tracks run an offline lifecycle smoke: local marketplace registration, plugin installation/discovery, full setup and status, setup validation, high-assurance profile parsing, commit/push/reset Rules decisions, complete rollback, and preservation of pre-existing config. This tests Linux integration shape without credentials or model calls; it does not prove model aliases are callable, future interactive Hook semantics, native custom-role routing, model behavior, or Windows/macOS compatibility.

Model IDs and configuration keys are centralized in managed assets and validated structurally, but the credential-free probe cannot detect a removed or renamed model alias. Release adoption therefore requires an authenticated/manual model-routing check outside public CI when those assets change. No upper-layer tool can eliminate upstream change risk.

Codex command Rules are argv-prefix policy, not a parser for nested shell programs. A direct `git push` can match a Rootloom rule while `bash -c 'git push'` is evaluated under the broader `bash` policy. Rules and the advisory child-budget Hook are defense-in-depth signals, not preventive security boundaries: the Hook cannot cancel the already-started over-budget child.

## External evidence and MCP

Rootloom does not ship a universal evidence MCP server. Runtime truth varies by organization and may live in logs, traces, metrics, issue systems, deployment records, or user reports. Connect only the narrow, authorized source a role needs, and preserve a compact provenance record: environment, observation time/window, stable reference, freshness/redaction, and fact-versus-inference status.

The strict runner disables external tools and network access. Collect authorized external evidence before a run and pass only bounded, sanitized material. Provenance improves auditability; it does not turn incomplete evidence into truth.

## Governance

The current bus factor is one. Security response times are targets rather than service-level guarantees. The initial releases were produced in a short single-author window without external code review, so passing local/CI tests is evidence of implemented contracts, not long-term operational reliability. Releases should remain small, reversible, tested against the pinned baseline, and explicit about unsupported or unverified surfaces. Broader reliability claims should be added only with public methodology and reproducible data.

After the Human Review v4 content-integrity closeout, investment should favor broader evidence and operational leverage: first-class container/cgroup integration, large-repository benchmarks, incremental path snapshots, verification dependency-closure binding, authenticated model-routing smoke tests, Artifact retention and cleanup policy, an external Human Review signer, and third-party usage/escaped-defect data. Further local same-UID TOCTOU patches require a new demonstrated invariant rather than extending v4 by default.

## Outcome evidence protocol

Rootloom does not collect telemetry from user repositories. To evaluate whether it improves outcomes, use an opt-in, privacy-reviewed study with a representative task set and a declared baseline. Hold task, repository revision, model, reasoning effort, tool access, and acceptance checks constant; distinguish synthetic benchmarks from real maintenance work; publish exclusions and failures rather than selecting only successful examples.

Track at least:

- first-pass acceptance against executable criteria;
- repair cycles and total model/tool work per accepted task;
- reviewer time and severity-ranked findings;
- root-cause-alignment failures or mitigations incorrectly presented as fixes;
- regressions or escaped defects within a declared observation window.

Report sample size, uncertainty, environment, raw or reproducibly derived aggregates, and limitations. Do not turn a process-conformance rate into a product-quality claim.

## Reference quality

OpenAI documentation and observed Codex behavior govern platform contracts. The GEB article is acknowledged as informal design inspiration for hierarchical context and feedback loops; it is not an official or peer-reviewed specification.

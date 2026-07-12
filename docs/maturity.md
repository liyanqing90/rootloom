# Maturity, guarantees, and compatibility

Rootloom is an early-stage, single-maintainer project. Its repository structure, tests, and release gates can demonstrate how the shipped mechanisms behave; they do not yet demonstrate broad adoption, team-scale outcomes, fewer production defects, or a measured reduction in rework. Independent usage reports and longitudinal quality data are not established evidence today.

## What “reliable” means here

“Reliable Codex engineering” is the design goal. A concrete claim is valid only at the boundary where Rootloom has executable proof:

| Claim | Current evidence | Not guaranteed |
| --- | --- | --- |
| Setup is transactional | cross-process lock, prepared recovery manifest, fault-injected state-commit compensation, hashes, mode-preserving rollback tests | failures outside the managed Codex home or simultaneous mutation by software that ignores the lock |
| Project seeding is bounded | deterministic local scanner, repository-contained non-symlink evidence, Git-common-dir writer lock, snapshot recheck, and regression tests | semantic completeness or perfectly current architecture knowledge |
| Command policy is intentional | pinned and latest-CLI offline lifecycle smoke for direct-argv commit, push, and destructive reset | shell-wrapped equivalents, every administrator/platform policy composition, or future CLI semantics |
| High-assurance execution is deterministic | fixed stage order, linked provenance IDs, metadata-only secret/ignored capture, pre-capture scope gates, mapped command results, and bounded repair cycles | factual truth of model evidence, semantic adequacy of selected commands, correct root cause, business correctness, or production safety |
| Review is independent by role | separate read-only reviewer configuration | human-independent correctness or elimination of shared model bias |

JSON Schema validates required shape. Semantic gates validate selected cross-stage consistency. Neither proves that a model's statement is true, and process discipline does not prove the conclusion true. Repository source, reproducible behavior, attributable runtime evidence, tests, reviewers, CI, and production controls remain necessary.

## Adoption fit and learning cost

Use the smallest capability that pays for itself:

- `skills-only` or `guidance` for individuals who mainly want reusable workflows or project context;
- `engineering` as the normal single-agent default;
- `delegated` only when controlled role separation is worth its token and coordination cost;
- `full` only when fixed stages and stronger local gates justify the setup and operational overhead.

The five presets, four role files, Rules, Hooks, and runner are intentionally inspectable, but they impose learning and maintenance cost. Rootloom is not automatically better than a concise `AGENTS.md` plus CI for a small, low-risk repository.

## Platform scope

Rootloom is Codex-specific by design. Skills, Hooks, Rules, profiles, and custom-agent configuration follow Codex interfaces and may need maintenance as those interfaces change. Portable project truth should live in source, tests, schemas, ordinary documentation, and decision records—not only in Codex configuration.

The strict high-assurance runner supports Linux, macOS, and WSL and rejects native Windows. Setup and project-seeding code include Windows locking branches, but the current public CI matrix is Linux-only; Windows and macOS installation behavior is not certified. Native custom-role/model routing is also not attested on the currently verified spawn surface, so the sequential runner is the supported route when model assignment must be evidenced.

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

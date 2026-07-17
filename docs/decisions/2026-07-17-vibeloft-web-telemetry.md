# Adopt the official VibeLoft runtime for website telemetry

Status: accepted

Date: 2026-07-17

## Context

Rootloom's public GitHub Pages site needs lightweight deployment telemetry without adding a package manager, a second JavaScript bootstrap path, a direct database dependency, or host-owned fingerprinting logic. The site is one static `index.html` document with hash navigation and no SPA router. GitHub Pages serves it from the registered production origin `https://liyanqing90.github.io/rootloom/`.

The integration changes the website's external dependency and privacy boundary. The browser credential is a revocable product-level write credential intended for the public script tag, but it must not be copied into documentation, tests, logs, or alternate collectors.

## Evidence

| Observation | Kind | Source | Date | Notes |
| --- | --- | --- | --- | --- |
| The production site has one HTML entry and no SPA router | verified fact | `index.html`, `site/main.js` | 2026-07-17 | hash anchors remain in one rendered document |
| GitHub Pages serves the registered HTTPS origin without a Content Security Policy header | verified fact | production response headers from `https://liyanqing90.github.io/rootloom/` | 2026-07-17 | HSTS is enabled; CSP changes are not applicable |
| Runtime v0.3.0 derives page URLs from the current HTTPS location, removes query/hash data, honors GPC/DNT, uses omitted fetch credentials, owns retry/backoff, and listens to History API navigation | verified fact | `https://vibeloft.ai/telemetry/v1.js` | 2026-07-17 | upstream runtime inspected directly; no credential included in this record |
| The runtime endpoint validator accepts only the VibeLoft AWS API, with an HTTP exception limited to localhost development endpoints | verified fact | official runtime source | 2026-07-17 | Rootloom does not configure an endpoint override |

## Decision

`index.html` is the only initialization boundary. It loads the official deferred VibeLoft runtime exactly once with the assigned product ID and browser auth attribute. Rootloom will not install a telemetry package, wrap the runtime, emit manual page views, forge page URLs, configure an alternate endpoint, or access Supabase from the browser.

The official runtime owns its random first-party device ID, coarse environment digest, GPC/DNT handling, History API coverage, retry/backoff, and failure isolation. Rootloom host code does not read or extend those signals. Local HTTP development loads cannot become valid production events because the runtime rejects non-HTTPS product page URLs. Other HTTPS preview origins retain their real origin and depend on VibeLoft's registered-origin enforcement; Rootloom never substitutes the production URL.

There is currently no CSP in source or in the GitHub Pages response, so no directive changes are made. If a CSP is introduced later, its minimum telemetry allowances are `https://vibeloft.ai` in `script-src` and `https://api.vibeloft.ai` in `connect-src`; no other directive may be weakened for this integration.

## Alternatives rejected

- Install an npm telemetry package — rejected because the site has no package runtime and the official global script is the required integration boundary.
- Add a local telemetry wrapper or manual SPA page-view calls — rejected because it would create duplicate initialization and compete with the official runtime's navigation and privacy behavior.
- Post directly to Supabase or another collector — rejected because it would expose a broader data boundary and bypass VibeLoft's registered product and origin contract.
- Proxy events through Rootloom infrastructure — rejected because Rootloom has no website backend and does not need to own telemetry payloads.

## Consequences

- Positive: every rendered production document has one observable, testable telemetry initialization.
- Positive: host code gains no tracking implementation, database credential, alternate endpoint, or extra fingerprinting surface.
- Positive: telemetry failure remains isolated from the website because the deferred runtime catches initialization and delivery failures.
- Negative: the website now depends on a third-party script at runtime; an upstream change can alter collection behavior without a Rootloom commit.
- Negative: visitors who do not enable GPC or DNT may send page URL, a random device ID, and the documented coarse environment digest to VibeLoft.
- Operational: repository validation pins the integration location, product identity, credential digest, single occurrence, and absence of local collectors. `make telemetry-check` inspects the current official runtime without emitting an event.

## Verification and revisit triggers

Run `make validate`, `make test`, `make telemetry-check`, the Pages production workflow, a live browser load, and VibeLoft Deployment Verification. Revisit this decision if VibeLoft changes the script host, endpoint, privacy signals, payload schema, origin enforcement, device identity, or environment digest; if Rootloom adds another HTML entry or a real SPA router; or if a CSP is introduced.

Rollback is a Git revert that removes the script tag and validation contract, followed by the normal Pages deployment. Disable the VibeLoft product credential if the browser write boundary must be revoked immediately.

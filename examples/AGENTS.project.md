<!-- Illustrative output. Real commands and invariants must come from the repository. -->
<!-- rootloom:managed-start version=1 fingerprint=example scope=. -->
# Project guidance for Example Commerce API

## Scope and sources of truth

- Project purpose: Process checkout and order state transitions for the example storefront. (from `README.md`).
- Detected sources of truth: `README.md`, `pyproject.toml`, `Makefile`, `docs/architecture.md`, `.github/workflows/ci.yml`.

## Repository map

- `src/` — application source.
- `tests/` — unit and integration tests.
- `migrations/` — database migrations.
- `docs/` — canonical project documentation.

## Canonical commands

- `make test` — detected from `Makefile target test`.
- `make lint` — detected from `Makefile target lint`.
- `make check` — detected from `Makefile target check`.

## Verification contract

- Run the smallest detected command set that proves the changed behavior, then expand with blast radius.
- If a required command cannot run, report the exact gap and do not convert it into a passing claim.
- Keep generated guidance factual: project-only invariants belong below the managed block and must cite real paths.
<!-- rootloom:managed-end -->

<!-- Add durable project-only rules below this line. The seeder preserves content outside the managed block. -->

## Project-specific invariants

- `src/orders/state.py` owns legal order transitions; callers must use it instead of writing status fields directly, and `tests/orders/test_state.py` is the behavioral contract.
- `migrations/` is append-only after release; schema compatibility and rollback requirements are defined in `docs/migrations.md`.
- Files under `src/generated/` are owned by `make generate`; never edit them by hand.
- Payment-provider retries must preserve the idempotency contract documented in `docs/payments.md` and covered by `tests/payments/test_idempotency.py`.

.PHONY: check test validate smoke compatibility-smoke

check: validate test

validate:
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_repo.py

test:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v

smoke:
	PYTHONDONTWRITEBYTECODE=1 python3 tests/live_smoke.py

compatibility-smoke:
	PYTHONDONTWRITEBYTECODE=1 python3 tests/compatibility_smoke.py

.PHONY: check test validate smoke

check: validate test

validate:
	PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_repo.py

test:
	PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
	PYTHONDONTWRITEBYTECODE=1 python3 plugins/rootloom/skills/high-assurance-coding-change/scripts/test_run_pipeline.py

smoke:
	PYTHONDONTWRITEBYTECODE=1 python3 tests/live_smoke.py

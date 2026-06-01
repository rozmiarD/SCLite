.PHONY: dev validate test public-validation strict-schema security-regression public-truth

PYTHON ?= $(shell if [ -x .venv/bin/python ]; then printf '%s' .venv/bin/python; elif command -v python >/dev/null 2>&1; then printf '%s' python; else printf '%s' python3; fi)

dev: validate

validate:
	PYTHON=$(PYTHON) scripts/dev_gate.sh

test:
	$(PYTHON) -m pytest -q

public-validation:
	PYTHON=$(PYTHON) scripts/public_validation_gate.sh

strict-schema:
	PYTHON=$(PYTHON) scripts/strict_schema_gate.sh

security-regression:
	PYTHON=$(PYTHON) scripts/security_regression_gate.sh

public-truth:
	$(PYTHON) scripts/validate_public_truth.py

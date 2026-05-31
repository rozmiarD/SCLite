.PHONY: dev validate test public-validation strict-schema security-regression public-truth

dev: validate

validate:
	scripts/dev_gate.sh

test:
	python -m pytest -q

public-validation:
	scripts/public_validation_gate.sh

strict-schema:
	scripts/strict_schema_gate.sh

security-regression:
	scripts/security_regression_gate.sh

public-truth:
	python scripts/validate_public_truth.py

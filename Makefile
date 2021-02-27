MODULE = qemu


ci: clean lint test


.PHONY: clean
clean:
	find $(MODULE) tests -name '__pycache__' -exec rm -rf {} +
	find $(MODULE) tests -name '*.pyc' -exec rm -f {} +
	find $(MODULE) tests -name '*.pyo' -exec rm -f {} +
	find $(MODULE) tests -name '*~' -exec rm -f {} +
	find $(MODULE) tests -name '._*' -exec rm -f {} +
	find $(MODULE) tests -name '.coverage*' -exec rm -f {} +
	rm -rf .tox *.egg dist build .coverage MANIFEST || true


.PHONY: lint
lint:
	flake8


.PHONY: test
test:
	pytest -vv -s


.PHONY: coverage
coverage:
	pytest --no-cov-on-fail --cov=$(MODULE) --cov-report=html --cov-report=term -vv -s tests/


# The default make target is ci
.DEFAULT_GOAL := ci

.PHONY: install lint format test

install:
	pip install -e .[dev]

lint:
	ruff check .

format:
	ruff format .

test:
	pytest

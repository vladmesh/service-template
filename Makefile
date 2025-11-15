.PHONY: install lint format typecheck test up

install:
	pip install -e .[dev]

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy apps tests

test:
	pytest

up:
	uvicorn apps.backend.main:create_app --factory --reload --host 0.0.0.0 --port 8000

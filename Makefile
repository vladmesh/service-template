.PHONY: install lint format typecheck test up

POETRY ?= poetry
BACKEND_DIR := apps/backend

install:
	cd $(BACKEND_DIR) && $(POETRY) install --with dev

lint:
	cd $(BACKEND_DIR) && $(POETRY) run bash -c 'cd ../.. && ruff check .'

format:
	cd $(BACKEND_DIR) && $(POETRY) run bash -c 'cd ../.. && ruff format .'

typecheck:
	cd $(BACKEND_DIR) && $(POETRY) run bash -c 'cd ../.. && mypy apps tests'

test:
	cd $(BACKEND_DIR) && $(POETRY) run bash -c 'cd ../.. && PYTHONPATH=. pytest'

up:
	cd $(BACKEND_DIR) && $(POETRY) run bash -c 'cd ../.. && PYTHONPATH=. uvicorn apps.backend.main:create_app --factory --reload --host 0.0.0.0 --port 8000'

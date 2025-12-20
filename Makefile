# Framework Development Makefile
# This Makefile is for developing the service-template framework itself.
# For product development commands, see the generated project's Makefile.

.PHONY: lint format test test-copier test-all help sync-framework

DOCKER_COMPOSE ?= docker compose
COMPOSE_FRAMEWORK := -f infra/compose.framework.yml
COMPOSE_ENV := COMPOSE_PROJECT_NAME=framework-tooling
PYTHON_TOOLING := $(COMPOSE_ENV) $(DOCKER_COMPOSE) $(COMPOSE_FRAMEWORK) run --build --rm tooling python

# Default target
help:
	@echo "Framework Development Commands:"
	@echo "  make lint          - Run linters on framework code"
	@echo "  make format        - Format framework code"
	@echo "  make test          - Run framework unit tests"
	@echo "  make test-copier   - Run copier template tests"
	@echo "  make test-all      - Run all tests"
	@echo "  make sync-framework - Sync framework/ to template/.framework/"

lint:
	$(COMPOSE_ENV) $(DOCKER_COMPOSE) $(COMPOSE_FRAMEWORK) run --build --rm tooling sh -c "ruff check framework/ tests/"

format:
	$(COMPOSE_ENV) $(DOCKER_COMPOSE) $(COMPOSE_FRAMEWORK) run --build --rm tooling sh -c "ruff format framework/ tests/ && ruff check --fix framework/ tests/"

test:
	$(COMPOSE_ENV) $(DOCKER_COMPOSE) $(COMPOSE_FRAMEWORK) run --build --rm tooling pytest -q --cov=framework --cov-report=term-missing tests/unit tests/tooling

test-copier:
	$(COMPOSE_ENV) $(DOCKER_COMPOSE) $(COMPOSE_FRAMEWORK) run --build --rm tooling pytest -v tests/copier/

test-all: test test-copier

sync-framework:
	@echo "Syncing framework/ to template/.framework/..."
	@rsync -av --delete framework/ template/.framework/
	@echo "Done."

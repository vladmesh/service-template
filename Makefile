# Framework Development Makefile
# This Makefile is for developing the service-template framework itself.
# For product development commands, see the generated project's Makefile.

.PHONY: lint format test test-copier test-all help sync-framework sync-framework-preview check-sync

DOCKER_COMPOSE ?= docker compose
EXEC_MODE ?= docker
COMPOSE_FRAMEWORK := -f infra/compose.framework.yml
COMPOSE_ENV := COMPOSE_PROJECT_NAME=framework-tooling HOST_UID=$$(id -u) HOST_GID=$$(id -g) DOCKER_GID=$$(getent group docker | cut -d: -f3)

ifeq ($(EXEC_MODE),native)
RUN_TOOLING := uv run
PYTHON_TOOLING := uv run python
else
RUN_TOOLING := $(COMPOSE_ENV) $(DOCKER_COMPOSE) $(COMPOSE_FRAMEWORK) run --build --rm tooling
PYTHON_TOOLING := $(RUN_TOOLING) python
endif

# Default target
help:
	@echo "Framework Development Commands:"
	@echo "  make lint                  - Run linters on framework code"
	@echo "  make format                - Format framework code"
	@echo "  make test                  - Run framework unit tests"
	@echo "  make test-copier           - Run copier template tests"
	@echo "  make test-all              - Run all tests"
	@echo "  make sync-framework        - Sync framework/ to template/.framework/"
	@echo "  make sync-framework-preview - Preview sync changes (dry-run)"
	@echo "  make check-sync            - Check if framework/ and template/.framework/ are in sync"

lint:
	$(RUN_TOOLING) sh -c "ruff check --no-cache framework/ tests/"

lint-template:
	$(RUN_TOOLING) sh -c "cd template && ruff check ."

format:
	$(RUN_TOOLING) sh -c "ruff format framework/ tests/ && ruff check --no-cache --fix framework/ tests/"

test:
	$(RUN_TOOLING) pytest -q --cov=framework --cov-report=term-missing tests/unit tests/tooling

test-copier:
	$(RUN_TOOLING) pytest -v tests/copier/

test-all: test test-copier

sync-framework:
	@./scripts/sync-framework-to-template.sh

sync-framework-preview:
	@./scripts/sync-framework-to-template.sh --dry-run

check-sync:
	@./scripts/check-framework-sync.sh

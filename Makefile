.PHONY: lint format typecheck tests dev-start dev-stop prod-start prod-stop makemigrations log services-validate

DOCKER_COMPOSE ?= docker compose
COMPOSE_BASE := -f infra/compose.base.yml
COMPOSE_DEV := $(COMPOSE_BASE) -f infra/compose.dev.yml
COMPOSE_PROD := $(COMPOSE_BASE) -f infra/compose.prod.yml
COMPOSE_TEST_UNIT := -f infra/compose.tests.unit.yml
COMPOSE_TEST_INTEGRATION := -f infra/compose.tests.integration.yml
COMPOSE_ENV_UNIT := COMPOSE_PROJECT_NAME=tests-unit
COMPOSE_ENV_TOOLING := COMPOSE_PROJECT_NAME=tooling
COMPOSE_ENV_INTEGRATION := COMPOSE_PROJECT_NAME=tests-integration

ifeq ($(word 1,$(MAKECMDGOALS)),log)
LOG_SERVICE := $(word 2,$(MAKECMDGOALS))
ifneq ($(LOG_SERVICE),)
$(eval $(LOG_SERVICE):;@:)
endif
endif

ifeq ($(word 1,$(MAKECMDGOALS)),tests)
TEST_TARGET := $(word 2,$(MAKECMDGOALS))
ifneq ($(TEST_TARGET),)
$(eval $(TEST_TARGET):;@:)
endif
endif

lint:
	$(COMPOSE_ENV_TOOLING) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tooling ruff check .

format:
	$(COMPOSE_ENV_TOOLING) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tooling ruff format --exclude 'apps/**/migrations' --exclude '.venv' .
	$(COMPOSE_ENV_TOOLING) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tooling ruff check --fix --exclude 'apps/**/migrations' --exclude '.venv' .

typecheck:
	$(COMPOSE_ENV_TOOLING) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tooling mypy apps tests

tests:
	@run_integration_tests() { \
		$(COMPOSE_ENV_INTEGRATION) $(DOCKER_COMPOSE) $(COMPOSE_TEST_INTEGRATION) up --build --abort-on-container-exit --exit-code-from integration-tests integration-tests; \
		status=$$?; \
		$(COMPOSE_ENV_INTEGRATION) $(DOCKER_COMPOSE) $(COMPOSE_TEST_INTEGRATION) down --volumes --remove-orphans; \
		return $$status; \
	}; \
	target="$(if $(suite),$(suite),$(if $(service),$(service),$(TEST_TARGET)))"; \
	case "$$target" in \
		""|"all") \
			set -e; \
			$(COMPOSE_ENV_UNIT) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm backend-tests-unit; \
			$(COMPOSE_ENV_UNIT) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tg-bot-tests-unit; \
			run_integration_tests; \
			;; \
		"backend") \
			$(COMPOSE_ENV_UNIT) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm backend-tests-unit; \
			;; \
		"tg_bot") \
			$(COMPOSE_ENV_UNIT) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tg-bot-tests-unit; \
			;; \
		"integration") \
			run_integration_tests; \
			;; \
		"frontend") \
			echo "Frontend tests are not configured yet. Skipping."; \
			;; \
		*) \
			echo "Unknown test suite: $$target"; \
			echo "Valid options: backend, tg_bot, integration, frontend, all"; \
			exit 1; \
			;; \
	esac

makemigrations:
	@if [ -z "$(name)" ]; then \
		echo "Usage: make makemigrations name=\"<description>\""; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) $(COMPOSE_DEV) run --rm backend alembic -c apps/backend/migrations/alembic.ini revision --autogenerate -m "$(name)"

log:
	@service="$(if $(service),$(service),$(LOG_SERVICE))"; \
	if [ -z "$$service" ]; then \
		echo "Usage: make log <service_name>"; \
		echo "       make log service=\"<service_name>\""; \
		exit 1; \
	fi; \
	$(DOCKER_COMPOSE) $(COMPOSE_DEV) logs -f $$service

dev-start:
	$(DOCKER_COMPOSE) $(COMPOSE_DEV) up -d --build

dev-stop:
	$(DOCKER_COMPOSE) $(COMPOSE_DEV) down --remove-orphans

prod-start:
	$(DOCKER_COMPOSE) $(COMPOSE_PROD) up -d --remove-orphans

prod-stop:
	$(DOCKER_COMPOSE) $(COMPOSE_PROD) down --remove-orphans

services-validate:
	$(COMPOSE_ENV_TOOLING) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tooling python scripts/services_registry.py validate

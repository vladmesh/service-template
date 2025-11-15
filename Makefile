.PHONY: lint format typecheck test-backend test-backend-unit test-backend-integration dev-start dev-stop prod-start prod-stop makemigrations

DOCKER_COMPOSE ?= docker compose
COMPOSE_BASE := -f infra/compose.base.yml
COMPOSE_DEV := $(COMPOSE_BASE) -f infra/compose.dev.yml
COMPOSE_PROD := $(COMPOSE_BASE) -f infra/compose.prod.yml
COMPOSE_TEST := -f infra/compose.test.yml

lint:
	COMPOSE_PROFILES=unit $(DOCKER_COMPOSE) $(COMPOSE_TEST) run --rm backend-unit ruff check .

format:
	COMPOSE_PROFILES=unit $(DOCKER_COMPOSE) $(COMPOSE_TEST) run --rm backend-unit ruff format .

typecheck:
	COMPOSE_PROFILES=unit $(DOCKER_COMPOSE) $(COMPOSE_TEST) run --rm backend-unit mypy apps tests

test-backend: test-backend-unit

test-backend-unit:
	COMPOSE_PROFILES=unit $(DOCKER_COMPOSE) $(COMPOSE_TEST) run --rm backend-unit

test-backend-integration:
	COMPOSE_PROFILES=integration $(DOCKER_COMPOSE) $(COMPOSE_TEST) run --rm backend-integration

makemigrations:
	@if [ -z "$(name)" ]; then \
		echo "Usage: make makemigrations name=\"<description>\""; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) $(COMPOSE_DEV) run --rm backend alembic -c apps/backend/migrations/alembic.ini revision --autogenerate -m "$(name)"

dev-start:
	$(DOCKER_COMPOSE) $(COMPOSE_DEV) up -d --build

dev-stop:
	$(DOCKER_COMPOSE) $(COMPOSE_DEV) down --remove-orphans

prod-start:
	$(DOCKER_COMPOSE) $(COMPOSE_PROD) up -d --remove-orphans

prod-stop:
	$(DOCKER_COMPOSE) $(COMPOSE_PROD) down --remove-orphans

.PHONY: lint format typecheck tests dev-start dev-stop prod-start prod-stop makemigrations log sync-services tooling-tests

DOCKER_COMPOSE ?= docker compose
COMPOSE_BASE := -f infra/compose.base.yml
COMPOSE_DEV := $(COMPOSE_BASE) -f infra/compose.dev.yml
COMPOSE_PROD := $(COMPOSE_BASE) -f infra/compose.prod.yml
COMPOSE_TEST_UNIT := -f infra/compose.tests.unit.yml
COMPOSE_TEST_INTEGRATION := -f infra/compose.tests.integration.yml
COMPOSE_ENV_UNIT := COMPOSE_PROJECT_NAME=tests-unit
COMPOSE_ENV_TOOLING := COMPOSE_PROJECT_NAME=tooling
COMPOSE_ENV_INTEGRATION := COMPOSE_PROJECT_NAME=tests-integration
PYTHON_TOOLING := $(COMPOSE_ENV_TOOLING) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tooling python

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

ifeq ($(word 1,$(MAKECMDGOALS)),sync-services)
SYNC_MODE := $(word 2,$(MAKECMDGOALS))
ifneq ($(SYNC_MODE),)
$(eval $(SYNC_MODE):;@:)
endif
endif

lint:
	$(COMPOSE_ENV_TOOLING) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tooling ruff check .

format:
	$(COMPOSE_ENV_TOOLING) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tooling ruff format --exclude 'services/**/migrations' --exclude '.venv' .
	$(COMPOSE_ENV_TOOLING) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tooling ruff check --fix --exclude 'services/**/migrations' --exclude '.venv' .

typecheck:
	$(COMPOSE_ENV_TOOLING) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tooling mypy services tests

tests:
	@set -eu; \
	target="$(if $(suite),$(suite),$(if $(service),$(service),$(TEST_TARGET)))"; \
	tmp_file="$$(mktemp)"; \
	trap 'rm -f "$$tmp_file"' EXIT; \
		if [ -z "$$target" ] || [ "$$target" = "all" ]; then \
			$(PYTHON_TOOLING) -m scripts.service_info tests > "$$tmp_file"; \
		else \
				$(PYTHON_TOOLING) -m scripts.service_info tests --suite "$$target" > "$$tmp_file"; \
		fi; \
	grep -E '^[[:alnum:]_]+ ' "$$tmp_file" > "$$tmp_file.filtered"; \
	mv "$$tmp_file.filtered" "$$tmp_file"; \
	while read -r suite compose_project compose_file compose_service mode; do \
		[ -z "$$suite" ] && continue; \
		echo ">> Running $$suite tests ($(basename $$compose_file))"; \
		if [ "$$mode" = "up" ]; then \
			COMPOSE_PROJECT_NAME=$$compose_project $(DOCKER_COMPOSE) -f $$compose_file up --build --abort-on-container-exit --exit-code-from $$compose_service $$compose_service; \
			status=$$?; \
			COMPOSE_PROJECT_NAME=$$compose_project $(DOCKER_COMPOSE) -f $$compose_file down --volumes --remove-orphans; \
			if [ $$status -ne 0 ]; then exit $$status; fi; \
		else \
			COMPOSE_PROJECT_NAME=$$compose_project $(DOCKER_COMPOSE) -f $$compose_file run --build --rm $$compose_service; \
		fi; \
	done < "$$tmp_file"

makemigrations:
	@if [ -z "$(name)" ]; then \
		echo "Usage: make makemigrations name=\"<description>\""; \
		exit 1; \
	fi
	$(DOCKER_COMPOSE) $(COMPOSE_DEV) run --rm backend alembic -c services/backend/migrations/alembic.ini revision --autogenerate -m "$(name)"

log:
	@service="$(if $(service),$(service),$(LOG_SERVICE))"; \
	if [ -z "$$service" ]; then \
		echo "Usage: make log <service_name>"; \
		echo "       make log service=\"<service_name>\""; \
		exit 1; \
	fi; \
	tmp_file="$$(mktemp)"; \
	trap 'rm -f "$$tmp_file"' EXIT; \
		$(PYTHON_TOOLING) -m scripts.service_info logs --service $$service > "$$tmp_file"; \
	target_line="$$(grep -E '^[[:alnum:]_]+ ' "$$tmp_file" | head -n 1)"; \
	if [ -z "$$target_line" ]; then \
		exit 1; \
	fi; \
	set -- $$target_line; \
	compose_service="$$2"; \
	echo ">> Streaming logs for $$service (compose service: $$compose_service)"; \
	$(DOCKER_COMPOSE) $(COMPOSE_DEV) logs -f $$compose_service

dev-start:
	$(DOCKER_COMPOSE) $(COMPOSE_DEV) up -d --build

dev-stop:
	$(DOCKER_COMPOSE) $(COMPOSE_DEV) down --remove-orphans

prod-start:
	$(DOCKER_COMPOSE) $(COMPOSE_PROD) up -d --remove-orphans

prod-stop:
	$(DOCKER_COMPOSE) $(COMPOSE_PROD) down --remove-orphans

sync-services:
	@mode="$(if $(mode),$(mode),$(if $(SYNC_MODE),$(SYNC_MODE),check))"; \
	case "$$mode" in \
		create) cmd="create" ;; \
		check|"") cmd="check" ;; \
		*) echo "Unknown sync mode: $$mode (expected 'check' or 'create')" >&2; exit 1 ;; \
	esac; \
	$(COMPOSE_ENV_TOOLING) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tooling python -m scripts.sync_services $$cmd

tooling-tests:
	$(COMPOSE_ENV_TOOLING) $(DOCKER_COMPOSE) $(COMPOSE_TEST_UNIT) run --build --rm tooling pytest -q tests/tooling

# План: отказ от tooling-контейнера

> **Основание**: [brainstorm-tooling-removal.md](brainstorm-tooling-removal.md) — все решения приняты
> **Связан с**: [simplification-plan.md](simplification-plan.md) — пункт 4
> **Scope**: два репозитория — `service-template` и `codegen_orchestrator`

---

## Зачем

Агенты (основные пользователи фреймворка) живут в Docker. Tooling-контейнер заставляет их делать docker-in-docker для `make lint` и `make test`. Это медленно, хрупко, усложняет отладку.

Заменяем Docker-based tooling на per-project venv-ы через uv. Линтеры и юнит-тесты работают плоско. Docker остаётся только для интеграционных тестов (postgres, redis) и production-деплоя.

---

## Итерация 1: Poetry → uv (service-template)

**Цель**: заменить Poetry на uv во всех шаблонных файлах. После этой итерации всё работает как раньше — через Docker — но с uv вместо Poetry.

### Файлы

| Файл | Действие |
|------|----------|
| `template/shared/pyproject.toml` | `[tool.poetry]` → `[project]` (PEP 621), `poetry-core` → `hatchling` |
| `template/services/backend/pyproject.toml` | `[tool.poetry]` → `[project]` + `[dependency-groups]` + `[tool.uv.sources]` |
| `template/services/tg_bot/pyproject.toml` | Аналогично |
| `template/services/notifications_worker/pyproject.toml` | Аналогично |
| `template/services/backend/poetry.lock` | Удалить |
| `template/services/tg_bot/poetry.lock` | Удалить |
| `template/services/notifications_worker/poetry.lock` | Удалить |
| `template/services/backend/Dockerfile` | `pip install poetry` → `COPY --from=ghcr.io/astral-sh/uv:latest`, `poetry install` → `uv pip install --system` |
| `template/services/tg_bot/Dockerfile` | Аналогично |
| `template/services/notifications_worker/Dockerfile` | Аналогично |
| `template/tooling/Dockerfile` | Убрать `poetry` из `pip install` (пока не удаляем сам файл) |
| `template/Makefile.jinja` | `poetry run pytest` → `pytest` (2 строки) |
| `template/services/tg_bot/AGENTS.md.jinja` | Упоминание Poetry → uv |
| `template/services/backend/AGENTS.md` | Упоминание Poetry → uv |

### Тестирование

```bash
# 1. Генерация проекта — оба режима
copier copy --data 'modules=tg_bot' --defaults template/ /tmp/test-standalone
copier copy --data 'modules=backend,tg_bot' --defaults template/ /tmp/test-fullstack

# 2. Docker build работает для каждого сервиса
cd /tmp/test-fullstack
docker build -f services/backend/Dockerfile .
docker build -f services/tg_bot/Dockerfile .

# 3. Существующий CI-путь работает (make lint, make tests через Docker)
make lint
make tests
```

**Критерий закрытия**: Docker build и существующий CI проходят с uv вместо Poetry. Никаких изменений в поведении — только пакетный менеджер.

---

## Итерация 2: Venv-инфраструктура (service-template)

**Цель**: добавить `make setup`, переписать Makefile на venv-ы, удалить tooling-контейнер и EXEC_MODE. Сразу сюда же можно добавить настройку гитхуков, чтобы запретить пользователю пушить код, не прошедший линтинг и юнит-тесты.

### Файлы

| Файл | Действие |
|------|----------|
| `template/.framework/pyproject.toml` | **Создать.** Объявить framework как пакет с deps: pydantic, PyYAML, jinja2, datamodel-codegen |
| `template/Makefile.jinja` | **Переписать.** Удалить EXEC_MODE, `RUN_TOOLING`, `COMPOSE_TEST_UNIT`, `COMPOSE_ENV_TOOLING`. Добавить `setup`. Все таргеты через `.venv/bin/` и `services/*/.venv/bin/` |
| `template/tooling/Dockerfile` | **Удалить** |
| `template/infra/compose.tests.unit.yml.jinja` | **Удалить** |
| `template/.github/workflows/ci.yml.jinja` | Добавить `astral-sh/setup-uv@v4` + `make setup`. Убрать cleanup для tests-unit compose project |
| `template/.gitignore` (или `.jinja`) | Добавить `.venv/`, `services/*/.venv/` в игнор |

### Новый `make setup` (схема)

```makefile
setup:
	uv venv
	uv pip install -e .framework/ ruff xenon
	@for svc in services/*/; do \
		[ -f "$$svc/pyproject.toml" ] || continue; \
		echo ">> Setting up $$svc"; \
		cd "$$svc" && uv venv && uv pip install -e ".[dev]" -e ../../shared && cd ../..; \
	done
```

### Новые таргеты (схема)

```makefile
lint:
	.venv/bin/ruff check .
	.venv/bin/xenon --max-absolute B --max-modules A --max-average A --exclude '.framework/*,tests/*' .
	.venv/bin/python -m framework.enforce_spec_compliance
	.venv/bin/python -c "from framework.spec.loader import validate_specs_cli; ..."
	.venv/bin/python -c "from framework.lint.controller_sync import lint_controllers_cli; ..."

format:
	.venv/bin/ruff format --exclude 'services/**/migrations' --exclude '.venv' --exclude '*/.venv' .
	.venv/bin/ruff check --fix --exclude 'services/**/migrations' --exclude '.venv' --exclude '*/.venv' .

test:
	@for svc in services/*/; do \
		[ -d "$$svc/tests" ] || continue; \
		echo ">> Testing $$(basename $$svc)"; \
		"$$svc/.venv/bin/pytest" "$$svc/tests/unit" -q; \
	done

tooling-tests:
	.venv/bin/pytest tests/tooling tests/unit -q --cov=framework --cov-report=term-missing --cov-fail-under=70

generate-from-spec:   # backend only
	.venv/bin/python -m framework.generate

typecheck:
	@for svc in services/*/; do \
		[ -f "$$svc/.venv/bin/mypy" ] || continue; \
		echo ">> Typechecking $$(basename $$svc)"; \
		cd "$$svc" && .venv/bin/mypy . && cd ../..; \
	done
```

### Тестирование

```bash
# 1. Standalone bot
copier copy --data 'modules=tg_bot' --defaults template/ /tmp/test-standalone
cd /tmp/test-standalone
make setup           # создаёт .venv/ и services/tg_bot/.venv/
make lint            # ruff + xenon + graceful spec checks
make test            # pytest в services/tg_bot/.venv/
make format          # ruff format

# 2. Full-stack
copier copy --data 'modules=backend,tg_bot' --defaults template/ /tmp/test-fullstack
cd /tmp/test-fullstack
make setup
make generate-from-spec   # генерация из specs
make lint                 # ruff + xenon + spec checks + compliance + controller sync
make test                 # pytest для backend и tg_bot
make typecheck            # mypy per-service

# 3. CI workflow валидна
# Проверить что ci.yml.jinja рендерится корректно и содержит setup-uv + make setup

# 4. Docker build сервисов по-прежнему работает (production path не сломан)
docker build -f services/backend/Dockerfile .
```

**Критерий закрытия**: `make setup && make lint && make test` работает нативно в обоих режимах (standalone, full-stack). Tooling-контейнер удалён. CI workflow использует `setup-uv`.

---

## Итерация 3: Документация (service-template)

**Цель**: обновить всю документацию генерируемых проектов.

### Файлы

| Файл | Что менять |
|------|-----------|
| `template/docs/ARCHITECTURE.md` (или `.jinja`) | Убрать "Tooling Container" секцию. Описать venv-архитектуру |
| `template/CONTRIBUTING.md.jinja` | Заменить Docker-инструкции на `make setup`. Описать workflow |
| `template/services/backend/AGENTS.md` | Убрать "через docker-compose", добавить "через make setup / make test" |
| `template/services/tg_bot/AGENTS.md.jinja` | Аналогично |
| `template/CLAUDE.md` (если есть) | Прописать `make setup` как первую команду после clone |

### Тестирование

```bash
# 1. Сгенерировать проект, прочитать доки — они должны соответствовать реальности
copier copy --data 'modules=backend,tg_bot' --defaults template/ /tmp/test-docs
# Проверить что в сгенерированных доках нет упоминаний:
grep -r "tooling" /tmp/test-docs/docs/ /tmp/test-docs/CONTRIBUTING.md  # не должно быть
grep -r "poetry" /tmp/test-docs/                                        # не должно быть
grep -r "EXEC_MODE" /tmp/test-docs/                                     # не должно быть
```

**Критерий закрытия**: в сгенерированном проекте нет упоминаний tooling-контейнера, Poetry, EXEC_MODE. Документация описывает актуальный workflow с `make setup`.

---

## Итерация 4: Orchestrator (codegen_orchestrator)

**Цель**: облегчить образ агента, добавить uv cache volume.

### Файлы

| Файл | Действие |
|------|----------|
| `services/worker-manager/images/worker-base-common/Dockerfile` | Убрать pip install: ruff, xenon, pytest, pytest-cov, mypy, PyYAML, jinja2, copier. Добавить `COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv` |
| `services/worker-manager/src/worker_manager.py` (или аналог) | Добавить `"uv-cache"` volume mount + `UV_CACHE_DIR` env var при создании контейнера |
| `docker-compose.yml` | Если нужно — добавить named volume `uv-cache` |

### Тестирование

```bash
# 1. Билд worker-base образов
docker build -f services/worker-manager/images/worker-base-common/Dockerfile .
docker build -f services/worker-manager/images/worker-base-claude/Dockerfile .

# 2. Проверить что uv доступен в контейнере
docker run --rm worker-base-common uv --version

# 3. Проверить что убранные инструменты НЕ доступны глобально
docker run --rm worker-base-common ruff --version    # должен упасть
docker run --rm worker-base-common pytest --version   # должен упасть

# 4. E2E: полный цикл
# scaffolder создаёт проект → developer agent клонирует → make setup (из uv cache) → make lint → make test → push
# Первый прогон: ~20-35 сек (скачивание)
# Второй прогон (другой worker, тот же cache volume): ~3-5 сек
```

**Критерий закрытия**: worker-base образ легче. Агент может `make setup && make lint && make test` без предустановленных Python-пакетов. uv cache шарится между воркерами.

---

## Сводка изменений по репозиториям

### service-template (итерации 1-3)

| Действие | Файлы |
|----------|-------|
| **Удалить** | `template/tooling/Dockerfile`, `template/infra/compose.tests.unit.yml.jinja`, `template/services/*/poetry.lock` (3 шт) |
| **Создать** | `template/.framework/pyproject.toml` |
| **Переписать** | `template/Makefile.jinja`, `template/.github/workflows/ci.yml.jinja` |
| **Мигрировать** | `template/shared/pyproject.toml`, `template/services/*/pyproject.toml` (3 шт), `template/services/*/Dockerfile` (3 шт) |
| **Обновить** | Документация: ARCHITECTURE.md, CONTRIBUTING.md, AGENTS.md (2 шт), CLAUDE.md |

### codegen_orchestrator (итерация 4)

| Действие | Файлы |
|----------|-------|
| **Переписать** | `services/worker-manager/images/worker-base-common/Dockerfile` |
| **Обновить** | `services/worker-manager/src/` — volume mount + env var |

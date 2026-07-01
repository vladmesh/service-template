# Backlog

Открытая работа сверху, закрытое — в архиве внизу (одной строкой, детали в git по коммиту).
Открытые пункты сверены с кодом 2026-07-01.

## Открытые задачи

### Add Predefined Module to Existing Project

**Status**: TODO

Команда `make add-module name=tg_bot` — добавить предопределённый модуль (tg_bot/notifications/frontend)
в уже сгенерированный проект. Сейчас `copier update` обновляет инфру, но не добавляет модули,
исключённые при генерации (их директории удаляются `_tasks` в `copier.yml`). Обходной путь —
регенерить проект целиком, теряя правки. Нужно: валидировать модуль, тянуть его из template-репо,
обновить `services.yml` + `.copier-answers.yml`, прогнать `make setup`. Вопросы: version mismatch
проект/шаблон, авто-регенерация compose.

### Eager import chains cause fragility

**Status**: OPEN · LOW · *E2E todo_api with-PO, 2026-03-05*

`services/backend/src/__init__.py` и `api/__init__.py` делают eager-импорты (app, router). Любой битый
импорт в цепочке (routers→controllers→repositories→schemas) роняет всё приложение на import-time;
alembic `env.py` тоже задет. Фикс: lazy-импорты или чтобы alembic импортировал модели напрямую,
минуя app-инициализацию.

### Auto-update `__init__.py` re-exports after generation

**Status**: OPEN · LOW · *E2E todo_api Level C, 2026-03-04*

После добавления моделей `schemas/__init__.py`, `models/__init__.py`, `repositories/__init__.py`
надо править руками — генератор их не трогает. Фикс: генерить эти `__init__.py` или отказаться от
re-export в пользу прямых импортов.

### Audit Scaffold Templates

**Status**: TODO · LOW

Ревью шаблонов в `.framework/framework/templates/scaffold/services/` — свериться с актуальными
практиками основных сервисов.

### Вынести маппинг типов в конфиг

**Status**: PARTIALLY DONE · LOW

Маппинг централизован в Python (`framework/spec/types.py`, `TypeRenderer`: Python / JsonSchema /
TypeScript через `fold_type_spec()`). Осталось: вынести таблицы в YAML/TOML, чтобы новый язык
добавлялся конфигом, а не классом. Низкий приоритет — Python-реализация чистая.

## Идеи (future, LOW)

Пул архитектурных идей, не запланированы:

- **Spec-Only Module Storage** — хранить в шаблоне только спеки+скаффолды, весь бизнес-код генерить
  при `copier copy`. Плюс: ноль дрейфа код↔спека, экономия токенов. Минусы: контроллеры/ORM тяжело
  специфицировать генерически, нет reference-имплементации для отладки. Путь: гибрид → спеки+минимум
  скаффолда → чистый spec-only после зрелости генераторов.
- **Celery Worker Support** — тип сервиса `celery-worker` в `services.yml`, преднастроенный
  Redis/RabbitMQ, авто-скаффолд `celery_app` + декораторы задач.
- **High-Level Architecture Spec** — централизованный «граф связности» (`architecture.yaml`):
  `access`/`exposes`/`consumes` по сервисам → генерить типизированные клиенты внутренних сервисов
  и network policies в compose.
- **Auto-fuzzing / Contract Testing** — `schemathesis` в CI: читает `openapi.json`, фаззит
  запущенный сервис, ловит 500 и краевые случаи без ручных тестов.
- **Spec-First Observability** — авто-встраивание OpenTelemetry-трейсов/метрик в генерируемый код
  (обёртки роутеров). Zero-config observability из спеки.
- **CLI Wrappers** — обернуть `make`/скрипты в отдельный CLI (`my-framework init/sync/update`),
  PyPI или бинарь.
- **Context Packer** — `make context service=backend` собирает токен-оптимизированный контекст для
  агента (спека + AGENTS.md + сигнатуры импортов + текущие linter-ошибки).
- **Unified Handlers: Transactional Outbox** — сейчас события публикуются сразу после DB-записи;
  рассмотреть outbox против dual-write проблемы.
- **Rust-миграция** (см. `docs/rust-migration-analysis.md`): PoC backend на Axum+SeaORM+utoipa;
  PoC tg-бота на teloxide; оценить Tera как замену Jinja2 для codegen; тип сервиса `rust-axum` в
  `services.yml` (микс Python+Rust в одном проекте).

## Не делаем (вне скоупа шаблона)

- **compose.dev.yml ports (5432/6379) конфликтуют с worker-контейнерами orchestrator'а** — оставлено
  сознательно: порты нужны для локальной разработки без orchestrator'а. Фикс на стороне
  orchestrator'а (inject override `ports: []`), не шаблона. См. `codegen_orchestrator` задача #53.
- **Auto-generate routers from specs** — `RouterGenerator` сознательно удалён (simplification Phase 2,
  коммит `e924857`): роутеры пишутся руками намеренно, как editable-файлы. Идея противоречит текущему
  направлению фреймворка.

## Закрытые пункты (архив)

<details>
<summary>Развернуть</summary>

Детали — в git по указанному коммиту.

**Spec / codegen**
- Spec-First Async Messaging (Queues) — Redis Streams + FastStream, `EventsGenerator`/`EventAdapterGenerator` из `events.yaml`.
- Enum Types in Model Fields — `EnumType` в `framework/spec/types.py`, генерится как `Literal`/`Enum` (`1e3aab7`).
- Unified Handlers: Error Handling Strategy — `publish_on_error_channel` в генераторе событий (`9371ceb`).
- YAML-спеки language-agnostic — shorthand `list[string]` парсится `TypeSpec`.
- Codegen: косметические баги (schema defaults, indentation в protocols, trailing whitespace в lifespan).
- Codegen: param types (`UUID` вместо `uuid`) + optional schemas (`nullable` только при `default None`).
- Нет list-операции в reference User домене — добавлен `list_users` (spec→repo→controller→router→test).
- Copier tests переписаны — 68 быстрых + 5 медленных (`44a17d8`).

**AGENTS.md / DX**
- tg_bot AGENTS.md: `API_BASE_URL` → `BACKEND_API_URL`.
- Примеры роутеров и list-эндпоинтов в AGENTS.md.
- Пояснение про `shared/shared/` структуру.

**Compose / deploy**
- Host venv shebang несовместим с контейнером — PATH на image-venv + anonymous volume.
- Backend readiness check в integration compose — healthcheck + `service_healthy`.
- `compose.base.yml`: `${VAR:?}` → `${VAR}` (валидация в Settings при старте).
- `deploy.yml`: post-deploy health check (crash больше не проходит как green).
- Убрать `.env.prod` — единый `.env` на проде + fail-fast на пустой decode.
- `compose.dev.yml`: PATH с per-service `.venv/bin`.
- Generated-код не попадал в Docker-образ → backend crash loop (`.gitignore` + CI regen).

**CI / Makefile**
- E2E CI job для unified handlers (`test_e2e_dual_transport_pipeline`).
- `deptry` в CI — ловит runtime-импорты, оставленные в dev-deps.
- tg_bot crash loop: relative import в entrypoint → абсолютный + smoke-test + entrypoint-lint (`6fa6472`).
- `makemigrations` не грузил `.env` → `-include .env` + `export`.
- Нет `make migrate` таргета — добавлен.
- `make setup` не идемпотентен → `uv venv || uv venv --clear` (`b605d3c`).
- Xenon excludes покрывают `services/*/tests/*` (`b605d3c`).
- Jinja whitespace в TASK/CONTRIBUTING/ARCHITECTURE шаблонах.
- Cache mounts (`--mount=type=cache`) в Dockerfile.

**Backend scaffold**
- Broken import в scaffolded user repository (`..schemas` → `shared.generated.schemas`).
- `ORMBase` форсил `updated_at` → `CreatedAtMixin` (`b0afb10`).

**Logging / analytics**
- structlog + FastAPI request middleware + error logging (JSON-логи в stdout).
- Telegram bot update middleware (аналог для входящих update'ов).

**Ранее закрытое**
- Remove poetry lock — миграция на uv.
- `make init` → покрыто `make setup`.
- `ruff check --fix` в post-gen → `make setup`.
- `ruff format --extend-exclude` → `ruff.toml`.
- Copier `_tasks` генерация schemas → `make setup`.
- FutureWarning от datamodel-code-generator → `formatters=[...]`.
- E2E issues iterations 4-5 (`5c9128f`).
- `.dockerignore` (root + template).
- Frontend Dockerfile `npm ci`.
- Tooling Removal: миграция на uv (native `.venv`).
- Event Channel Naming (snake_case → dot-notation в `EventsGenerator`).

</details>

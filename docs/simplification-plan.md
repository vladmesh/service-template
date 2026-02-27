# Service Template Simplification

> **Задача**: Backlog #1 в codegen_orchestrator — Service Template Simplification & Refactoring
> **Брейншторм**: `codegen_orchestrator/docs/brainstorms/service-template-and-dev-environment.md`
> **Cross-project**: основная работа здесь (service-template), интеграция — в оркестраторе (scaffolder)

---

## Проблема

Фреймворк перегружен: 9 кодогенераторов, обязательный PostgreSQL,
тесная связка tg_bot → backend. Простой Telegram-бот невозможен без полного бэкенда,
а его разработка затягивается на десятки минут из-за лишней инфраструктуры.

---

## ~~Текущее состояние связки backend ↔ tg_bot~~ DONE

**Сделано.** Backend теперь опциональный модуль. Убрали хардкод `backend module is required` из `copier.yml`, заменили на `at least one module must be selected`.

Все три зависимости tg_bot → backend стали условными через Jinja-шаблоны:
- Compose `depends_on: backend` — только при `'backend' in modules`
- `manifest.yaml` → `.jinja` — `consumes: []` без backend (ClientsGenerator не генерирует BackendClient)
- `main.py` → `.jinja` — без backend нет импортов httpx/BackendClient/UserCreate, нет `_sync_user_with_backend()`, `/start` отвечает простым приветствием
- Тесты, документация (AGENTS.md, README.md) — аналогично обёрнуты

Теперь работают три режима: `modules="tg_bot"` (standalone бот), `modules="backend,tg_bot"` (полный стек), `modules="backend"` (только API).

---

## Генераторы — анализ и решения (из 9 → 5)

### Убрать

| Генератор | LOC генератора | LOC шаблона | Типичный output | Решение |
|-----------|---------------|-------------|-----------------|---------|
| **RegistryGenerator** | 102 | 79 | ~54 строки | **Убрать первым.** Генерирует 4-5 вызовов `include_router()`, обёрнутые в 54 строки импортов и реэкспортов. 10 строк реальной логики. |
| **RoutersGenerator** | 117 | 97 | 70-111 строк | **Убрать.** Механическая транскрипция spec → FastAPI декораторы. ~20 строк на операцию, чистый бойлерплейт. Агент напишет роутер с контекстом (middleware, security) за 500 токенов. |
| **ClientsGenerator** | 203 | 232 | ~204 строки | **Убрать генератор, вынести retry-базу в shared.** 86% output-а (175 строк) — одинаковая инфраструктура (retry, backoff, lifecycle), копируется в каждый клиент. Бизнес-методы — 14% (29 строк на 2 операции). Межсервисный REST — антипаттерн в event-driven архитектуре; единственный потребитель — tg_bot → backend, и тот опционален. Базовый `ServiceClient` с retry ляжет в `shared/` как утилита (~60 строк), клиенты при необходимости пишутся руками за 15 строк. |
| **sync_services** | 262 | — | Dockerfiles, compose-блоки | **Убрать.** Перегенерирует Dockerfiles и compose при каждом `copier update`, затирая ручные правки. Одноразовый scaffold при создании — ок, дальше файлы должны быть пользовательскими. |

### Оставить

| Генератор | LOC генератора | LOC шаблона | Типичный output | Почему оставляем |
|-----------|---------------|-------------|-----------------|-----------------|
| **SchemasGenerator** | 51 | — (datamodel-codegen) | ~84 строки | Контракт между сервисами. Single source of truth: `models.yaml` → Pydantic-модели с валидацией. Без него — drift между сервисами гарантирован. Генерация бесплатная и мгновенная. |
| **EventsGenerator** | 59 | 24 | ~34 строки | Pub/sub контракт. Все сервисы гарантированно используют одинаковые channel names и типы. Дёшево, предотвращает рассинхрон. |
| **EventAdapterGenerator** | 114 | 83 | ~49 строк | Самый интеллектуальный генератор. Session lifecycle (get_session → controller → commit/rollback) — паттерн, который легко написать неправильно. 12-16 строк на хендлер, каждая строка важна. |
| **ControllersGenerator** | 85 | 34 | 30-40 строк | Стартовые стабы с `NotImplementedError` и правильными сигнатурами. Генерит только если файл не существует — не перезаписывает. Показывает агенту «вот что реализовать». |
| **ProtocolsGenerator** | 91 | 43 | ~61 строка | Изначально не был в плане на удаление. `typing.Protocol` для контроллеров — интерфейс для DI. Без него IDE не покажет ошибки типов. Дёшевый и важный. |

### Ключевые выводы из обсуждения

**Архитектура коммуникаций:**
- REST = внешний API (фронтенд, мобилка, бот как клиент)
- Events = внутренняя коммуникация между сервисами (pub/sub через Redis Streams)
- Межсервисный REST — антипаттерн; единственный случай (tg_bot → backend) опционален и может быть заменён на events

**Принцип отбора генераторов:**
- Генерировать код через агентов дорого (токены). Генераторы, которые делают это быстро и бесплатно — оставляем.
- Генераторы, которые производят мало кода или редко используются — убираем.
- Оставляем то, что обеспечивает **контракты** (schemas, events, protocols) и **сложные паттерны** (session lifecycle в event adapters).
- Убираем то, что производит **механический бойлерплейт** (routers, registry) или **дублирует инфраструктуру** в каждый файл (clients).

**ServiceClient в shared:**
- Retry с exponential backoff, разделение 4xx/5xx, context manager для httpx — полезная утилита.
- Не генератор, а обычный базовый класс в `shared/shared/http_client.py` (~60 строк).
- Если кому-то нужен HTTP-клиент к другому сервису — наследуется от `ServiceClient` и пишет 15 строк методов.

**Итого по LOC:**
- Удаляем: 684 LOC генераторов + 408 LOC шаблонов = **1092 строки**
- Добавляем: ~60 LOC `ServiceClient` в shared
- Оставляем: 400 LOC генераторов + 184 LOC шаблонов (контракты и паттерны)

---

### Инфраструктурный оверхед

- **PostgreSQL + Alembic как обязательный** — для многих ботов хватит Redis или in-memory state
- **Tooling-контейнер** — отдельный Docker-образ для линтеров/тестов. Заменяется на `uv run pytest`
- **Spec-формат как обязательный слой** — для простого бота с 3 хендлерами описывать их в YAML → генератор → контроллер — три шага вместо одного

---

## Приоритеты реализации

| # | Что делать | Импакт | Сложность |
|---|------------|--------|-----------|
| ~~1~~ | ~~Сделать backend опциональным в copier.yml (standalone tg_bot)~~ **DONE** | Высокий | Средняя |
| ~~2~~ | ~~Убрать RoutersGenerator, ClientsGenerator, RegistryGenerator, sync_services; добавить ServiceClient в shared~~ **DONE** | Высокий — упрощает шаблон вдвое (−1092 строк) | Низкая — удалить + обновить pipeline |
| ~~3~~ | ~~Сделать specs опциональными (подробности ниже)~~ **DONE** | Средний — упрощает простые проекты | Средняя |
| 4 | Убрать tooling-контейнер, перейти на `uv run` — [брейншторм](brainstorm-tooling-removal.md), [план](plan-tooling-removal.md) | Средний — ускоряет dev-цикл | Низкая |

---

## ~~Пункт 3: Specs опциональны~~ DONE

### Проблема

Specs (models.yaml, events.yaml, domain YAML) — это контракты между сервисами. Для standalone tg_bot без backend контрактов нет, но фреймворк требует их наличия: `load_specs()` падает без models.yaml, `make lint` включает spec-валидацию, CI проверяет generated files. Standalone бот не может даже определить `class FSMState(BaseModel)` — enforce_spec_compliance запрещает.

### Принцип

- **Specs = контракты между сервисами.** Один сервис → нет контрактов → specs не нужны.
- **Инфраструктура генерации (`.framework/`) — всегда присутствует.** Хочешь добавить backend → `copier update`, specs появляются, генерация включается.
- **Качество кода enforce'ится всегда**, но scope проверок адаптируется к наличию specs.

### Что сделано

**3.1. Copier: cleanup для standalone** ✅

Вместо Jinja-условий в самих файлах specs — добавлены `_tasks` в `copier.yml` для post-copy удаления:
```yaml
- "{% if 'backend' not in modules %}rm -rf shared/spec shared/shared/generated shared/shared/http_client.py{% endif %}"
- "{% if 'backend' not in modules %}rm -rf services/*/spec{% endif %}"
```

> **Отклонение от плана**: план предлагал обернуть spec-файлы в `{% if %}`, но post-copy cleanup через `_tasks` проще и надёжнее — не нужно трогать каждый YAML/Python файл в `shared/spec/`. Также удаляется `http_client.py` (не было в плане) и `services/*/spec/manifest.yaml` (не было в плане, но нужно для чистого standalone).

**3.2. tg_bot main.py.jinja: standalone = plain PTB бот** ✅

> **Отклонение от плана**: план упоминал aiogram, но шаблон использует python-telegram-bot (PTB). Это не баг плана — просто неточность в тексте. Реализация корректна.

В standalone режиме (`'backend' not in modules`):
- Нет импортов `shared.generated.events`, `shared.generated.schemas`, `httpx`, `ServiceClient`
- Нет event bus, broker lifecycle (post_init/post_shutdown)
- Нет `BackendClient`, `_sync_user_with_backend()`
- `/start` отвечает простым приветствием, без синхронизации с backend
- Тесты (test_command_handler.py.jinja) аналогично — standalone вариант без mock broker

**3.3. framework/spec/loader.py: graceful при отсутствии specs** ✅

Реализовано по плану. `load_specs()` возвращает пустой `AllSpecs` если `models.yaml` не существует. `validate_specs_cli()` возвращает `(True, "No specs found. Skipping validation.")`.

**3.4. framework/generate.py: no-op при пустых specs** ✅

Реализовано по плану. Плюс добавлен warning при отсутствии `datamodel-code-generator` в native mode: "schemas.py may be stale. Run `make generate-from-spec` in Docker to regenerate."

**3.5. enforce_spec_compliance: B+C** ✅

Реализовано по плану:
- **C — conditional**: skip если нет `shared/spec/models.yaml`
- **B — сужение scope**: BaseModel check только в `controllers/`
- APIRouter message обновлён

**3.6. Makefile.jinja и CI: conditional spec targets** ✅

Spec-only targets обёрнуты в `{% if 'backend' in modules %}`: `validate-specs`, `lint-specs`, `generate-from-spec`, `lint-controllers`, `openapi`, `typescript`, `makemigrations`.

CI шаги "Generate from spec" и "Check generated files are up to date" — обёрнуты.

> **Отклонение от плана**: план предлагал `{% if %}...{% else %}...{% endif %}` для `lint:` target с разными командами в standalone vs full-stack. В реализации обнаружился баг: `{% else -%}` в Jinja стирает `\n\t`, а tab — обязательный префикс рецепта в Makefile. Вместо этого **lint использует одну универсальную команду** в обоих режимах. Это работает т.к. `validate_specs_cli()` и `lint_controllers_cli()` graceful — в standalone печатают "No specs found" и выходят с 0.

**3.7. Документация** ✅

- `ARCHITECTURE.md.jinja`: Spec-First Flow, shared/ directory, Unified Handlers — обёрнуты в `{% if 'backend' in modules %}`
- `CONTRIBUTING.md.jinja`: spec-зависимые разделы обёрнуты

**3.8. Косметика: Jinja whitespace** ✅

> **Не было в плане** — обнаружено при тестировании. `{% endif -%}` стирает ВСЕ whitespace (включая пробелы и табы), что ломает:
> - Python-отступы в `main.py` (`if update.message:` оказывался на column 0)
> - YAML-отступы в `ci.yml` (`- name: Run linters` терял 6 пробелов)
> - Makefile recipe tab в `lint:` target
>
> Решение: `{% endif -%}` безопасен только на column 0 (import blocks, markdown). Для остального — `{% endif %}` + управление количеством blank lines в шаблоне (каждый `{% endif %}` добавляет 1 `\n`).

### Результат

**`modules=tg_bot`:**
```
project/
├── .framework/              ← генераторы готовы к работе
├── shared/shared/           ← без http_client.py, без generated/
├── services/tg_bot/         ← plain PTB бот, свободен в BaseModel
│   └── (без spec/)
├── Makefile                 ← lint = ruff + xenon + graceful spec checks
└── .github/workflows/ci.yml ← без spec generation
```

**`modules=backend,tg_bot`:**
```
project/
├── .framework/
├── shared/
│   ├── spec/models.yaml, events.yaml
│   └── shared/generated/schemas.py, events.py
│   └── shared/http_client.py
├── services/backend/        ← spec-driven, BaseModel enforce в controllers/
├── services/tg_bot/         ← event-driven, uses shared schemas
├── Makefile                 ← lint = ruff + xenon + spec checks
└── .github/workflows/ci.yml ← с spec generation + drift check
```

---

## Связь с другими задачами

- **Backlog #2 (Agent Hierarchy)** в оркестраторе — пересечение по pipeline (Architect node, Scaffolder-как-нода). Упрощение шаблона делается независимо; интеграция с новым pipeline — второй этап.
- **Backlog #4 (CI Pipeline Redesign)** — шаблон генерирует ci.yml для проектов. Слабое пересечение, не блокирует.
- Прямых блокеров нет, можно приступать.

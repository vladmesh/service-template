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
| 3 | Сделать specs опциональными (подробности ниже) | Средний — упрощает простые проекты | Средняя |
| 4 | Убрать tooling-контейнер, перейти на `uv run` | Средний — ускоряет dev-цикл | Низкая |

---

## Пункт 3: Specs опциональны

### Проблема

Specs (models.yaml, events.yaml, domain YAML) — это контракты между сервисами. Для standalone tg_bot без backend контрактов нет, но фреймворк требует их наличия: `load_specs()` падает без models.yaml, `make lint` включает spec-валидацию, CI проверяет generated files. Standalone бот не может даже определить `class FSMState(BaseModel)` — enforce_spec_compliance запрещает.

### Принцип

- **Specs = контракты между сервисами.** Один сервис → нет контрактов → specs не нужны.
- **Инфраструктура генерации (`.framework/`) — всегда присутствует.** Хочешь добавить backend → `copier update`, specs появляются, генерация включается.
- **Качество кода enforce'ится всегда**, но scope проверок адаптируется к наличию specs.

### Что менять

**3.1. Copier: не копировать specs для tg_bot-only**

`shared/spec/models.yaml` и `shared/spec/events.yaml` — обернуть в `{% if 'backend' in modules %}`. При `modules=tg_bot` директория `shared/spec/` пустая или отсутствует.

`shared/shared/generated/` (schemas.py, events.py) — аналогично conditional. Без specs нечего генерировать.

Добавление backend: `copier update --data 'modules=backend,tg_bot'` — specs появляются, Makefile и CI перегенерируются.

**3.2. tg_bot main.py.jinja: standalone = plain aiogram бот**

В standalone режиме (`'backend' not in modules`):
- Не импортировать `shared.generated.events`, `shared.generated.schemas`
- Не использовать event bus (некому подписываться)
- Простой aiogram бот с хендлерами напрямую

**3.3. framework/spec/loader.py: graceful при отсутствии specs**

`load_specs()` — если `models.yaml` не существует, возвращать пустой `AllSpecs` вместо `SpecValidationError`. Это defensive coding: фреймворк не должен падать от отсутствия файла, он должен корректно обрабатывать пустое состояние.

**3.4. framework/generate.py: no-op при пустых specs**

Если `load_specs()` вернул пустые specs (нет моделей) — вывести "No specs found. Skipping generation." и выйти. Генераторы не запускаются.

**3.5. enforce_spec_compliance: B+C**

Комбинация двух изменений:

**C — conditional**: если `shared/spec/models.yaml` не существует → skip целиком, exit 0. Нет specs — нечего enforce'ить, сервис свободен писать свои модели.

**B — сужение scope**: если specs существуют, проверять BaseModel **только в `controllers/`**. Контроллеры реализуют протоколы из spec → должны использовать сгенерированные схемы. В остальных местах (`utils/`, `handlers/`, `models/`) — пиши что хочешь.

APIRouter check — оставить как организационное правило (роутеры в `routers/`, не разбросаны). Обновить сообщение: ~~"forbidden"~~ → "APIRouter should be defined in app/api/routers/, not here." (без намёка на генерацию, просто правило организации).

**3.6. Makefile.jinja и CI: conditional spec targets**

Обернуть в `{% if 'backend' in modules %}`:
- `make validate-specs`, `make lint-specs`, `make lint-controllers`, `make generate-from-spec`
- CI шаги: "Generate from spec", "Check generated files are up to date"

`make lint` — ruff и xenon работают всегда; spec-зависимые проверки включаются только при наличии backend.

### Результат

**`modules=tg_bot`:**
```
project/
├── .framework/              ← генераторы готовы к работе
├── shared/shared/
│   └── http_client.py       ← ServiceClient (если понадобится)
├── services/tg_bot/         ← plain aiogram бот, свободен в BaseModel
├── Makefile                 ← lint = ruff + xenon (без spec checks)
└── .github/workflows/ci.yml ← без spec generation
```

**`modules=backend,tg_bot`:**
```
project/
├── .framework/
├── shared/
│   ├── spec/models.yaml, events.yaml
│   └── shared/generated/schemas.py, events.py
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

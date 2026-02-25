# Service Template Simplification

> **Задача**: Backlog #1 в codegen_orchestrator — Service Template Simplification & Refactoring
> **Брейншторм**: `codegen_orchestrator/docs/brainstorms/service-template-and-dev-environment.md`
> **Cross-project**: основная работа здесь (service-template), интеграция — в оркестраторе (scaffolder)

---

## Проблема

Фреймворк перегружен: 8 кодогенераторов, обязательный PostgreSQL,
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

## Что убрать

### Генераторы (из 8 → 3-4)

| Генератор | Решение | Причина |
|-----------|---------|---------|
| **RoutersGenerator** | Убрать | Агент напишет роутер напрямую лучше и быстрее, видит контекст |
| **ClientsGenerator** | Убрать | При 2-3 сервисах клиент пишется за минуту. При standalone tg_bot не нужен |
| **RegistryGenerator** | Убрать | Механика на 10 строк, обёрнутая в генератор с Jinja-шаблоном и spec-парсингом |
| **sync_services** | Убрать | Перегенерирует все Dockerfiles/compose при каждом `copier update`. Достаточно одноразовой генерации |
| SchemasGenerator | Оставить | Контракт между сервисами (models.yaml → shared Pydantic-схемы) |
| EventsGenerator | Оставить | Pub/sub контракты между сервисами |
| EventAdapterGenerator | Оставить | Wiring подписок + handler stubs с типами |
| ControllersGenerator | Оставить | Стабы с типами — показывают агенту "вот что нужно реализовать" |

### Инфраструктурный оверхед

- **PostgreSQL + Alembic как обязательный** — для многих ботов хватит Redis или in-memory state
- **Tooling-контейнер** — отдельный Docker-образ для линтеров/тестов. Заменяется на `uv run pytest`
- **Spec-формат как обязательный слой** — для простого бота с 3 хендлерами описывать их в YAML → генератор → контроллер — три шага вместо одного

---

## Что оставить

- **SchemasGenerator** (models.yaml → shared Pydantic-схемы) — контракты между сервисами
- **EventsGenerator + EventAdapterGenerator** — pub/sub контракты
- **ControllersGenerator** — стабы с типами
- **Scaffold структуры** (папки, pyproject, Dockerfile, compose-блок) — одноразовая генерация

---

## Приоритеты реализации

| # | Что делать | Импакт | Сложность |
|---|------------|--------|-----------|
| ~~1~~ | ~~Сделать backend опциональным в copier.yml (standalone tg_bot)~~ **DONE** | Высокий | Средняя |
| 2 | Убрать RoutersGenerator, ClientsGenerator, RegistryGenerator, sync_services | Высокий — упрощает шаблон вдвое | Низкая — удалить + обновить pipeline |
| 3 | Сделать specs опциональными (не требовать YAML для простых сервисов) | Средний — упрощает простые проекты | Средняя — ветка "с генерацией / без" |
| 4 | Убрать tooling-контейнер, перейти на `uv run` | Средний — ускоряет dev-цикл | Низкая |

---

## Связь с другими задачами

- **Backlog #2 (Agent Hierarchy)** в оркестраторе — пересечение по pipeline (Architect node, Scaffolder-как-нода). Упрощение шаблона делается независимо; интеграция с новым pipeline — второй этап.
- **Backlog #4 (CI Pipeline Redesign)** — шаблон генерирует ci.yml для проектов. Слабое пересечение, не блокирует.
- Прямых блокеров нет, можно приступать.

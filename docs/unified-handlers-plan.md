# Unified Handlers Implementation Plan

> **Status**: DRAFT — требует обсуждения перед реализацией
> 
> **Цель**: Унифицировать описание REST и Event-driven операций в одной спеке, сохраняя раздельную реализацию под капотом.

## Содержание

1. [Контекст и мотивация](#1-контекст-и-мотивация)
2. [Ключевые принципы](#2-ключевые-принципы)
3. [Фазы реализации](#3-фазы-реализации)
4. [Открытые вопросы](#4-открытые-вопросы)
5. [Критерии успеха](#5-критерии-успеха)

---

## 1. Контекст и мотивация

### Текущее состояние

Сейчас в проекте существует **два раздельных мира**:

| Аспект | REST | Events |
|--------|------|--------|
| Спецификация | `services/<svc>/spec/<domain>.yaml` с `rest:` секцией | `shared/spec/events.yaml` (глобально) + `events:` в domain spec |
| Генераторы | `RoutersGenerator` → FastAPI routers | `EventsGenerator` → shared publishers, `EventHandlersGenerator` → per-service handlers |
| Регистрация | Ручная в `app/api/router.py` | Ручная в `main.py` или `handlers.py` |
| DI | FastAPI `Depends()` | Своя система или без DI |
| Контроллер | `ControllerProtocol` (generated) | `EventsHandlerProtocol` (generated, частично) |

### Проблемы

1. **Дублирование концепций**: Два разных Protocol'а, два способа регистрации
2. **Event-driven недоразвит**: REST полностью spec-first, Events — частично
3. **Нет единого языка**: Разработчик должен знать два формата
4. **Мотивация к events низкая**: REST проще использовать → events игнорируются

### Цель

**Одна спека → один Controller → несколько Adapters (REST, Events)**

```yaml
operations:
  get_user:       # Query — только REST
    rest: {method: GET, path: "/{user_id}"}
    
  create_user:    # Command — REST + event publication
    rest: {method: POST, status: 201}
    events: {publish_on_success: user.created}
    
  process_import: # Background — только events
    events: {subscribe: user.import.requested}
```

---

## 2. Ключевые принципы

### 2.1. Типы операций

| Тип | Транспорт | Поведение |
|-----|-----------|-----------|
| **Query** | REST only | Синхронный read, без side effects |
| **Command** | REST + Events | REST возвращает результат, event публикуется асинхронно |
| **Background** | Events only | Нет HTTP endpoint, только subscribe/publish |

### 2.2. Один Controller — много Adapters

```
┌─────────────────────────────────────────────────┐
│            UsersController (бизнес-логика)      │
│  ┌──────────────────────────────────────────┐   │
│  │ get_user(user_id) → UserRead             │   │
│  │ create_user(payload) → UserRead          │   │
│  │ process_import(batch) → ImportResult     │   │
│  └──────────────────────────────────────────┘   │
└───────────────────────────────────────────────────┘
                    ▲                 ▲
                    │                 │
        ┌───────────┴───────┐   ┌─────┴─────────────┐
        │   REST Adapter    │   │   Events Adapter  │
        │   (generated)     │   │   (generated)     │
        └───────────────────┘   └───────────────────┘
```

### 2.3. Events — не замена, а дополнение

- **Query операции (GET) остаются синхронными** — фронтенд получает данные сразу
- **Events нужны для**: side effects, уведомления, pipelines, decoupling
- **Не пропускаем всё через Redis** — это overkill для простых reads

---

## 3. Фазы реализации

### Фаза 0: Подготовка и инвентаризация
**Оценка: 1-2 часа**

- [x] Документировать текущее состояние генераторов
- [x] Составить список всех мест, где events обрабатываются вручную
- [x] Определить breaking changes для существующих спек
- [x] Создать feature branch

**Проверка**: Документ с текущим состоянием готов, checklist пройден.

---

### Фаза 1: Расширение OperationSpec
**Оценка: 2-3 часа**

#### 1.1. Расширить `EventsConfig` в `framework/spec/operations.py`

Текущий формат:
```python
class EventsConfig(BaseModel):
    subscribe: str | None = None
    publish_on_success: str | None = None
```

Новый формат:
```python
class EventsConfig(BaseModel):
    subscribe: str | None = None           # Канал для подписки
    publish_on_success: str | None = None  # Канал для публикации после успеха
    publish_on_error: str | None = None    # (опционально) Канал для ошибок
    message_model: str | None = None       # Override модели сообщения (если != input/output)
```

#### 1.2. Добавить валидацию

- Если есть `events.subscribe` — должен быть `input` (что получаем)
- Если есть `events.publish_on_success` — должен быть `output` (что публикуем)
- Модель события должна существовать в `models.yaml`

#### 1.3. Тестирование

- [x] Unit тесты для новых полей EventsConfig
- [x] Тесты валидации (невалидные комбинации)
- [x] Тесты парсинга YAML → OperationSpec

**Проверка**: ✅ `make test-unit` проходит, 14 новых тестов покрывают изменения.

---

### Фаза 2: Унификация Protocol генерации
**Оценка: 2-3 часа**

#### 2.1. Объединить `ProtocolsGenerator` и `EventHandlersGenerator`

Сейчас:
- `ProtocolsGenerator` → `protocols.py` (для REST)
- `EventHandlersGenerator` → `event_handlers.py` (отдельный Protocol)

После:
- Один `ProtocolsGenerator` → `protocols.py` с **всеми** операциями
- Protocol включает методы для REST И Events операций

```python
# protocols.py (generated)
class UsersControllerProtocol(Protocol):
    # REST operations
    async def get_user(self, session: AsyncSession, user_id: int) -> UserRead: ...
    async def create_user(self, session: AsyncSession, payload: UserCreate) -> UserRead: ...
    
    # Events operations
    async def process_import(self, session: AsyncSession, batch: UserImportBatch) -> ImportResult: ...
```

#### 2.2. Обновить `OperationContextBuilder`

- `build_for_protocol()` должен включать ВСЕ операции (REST + Events + оба)
- Добавить флаг `is_event_only`, `is_rest_only`, `is_dual`

#### 2.3. Тестирование

- [x] Unit тесты: Protocol включает все типы операций
- [x] Unit тесты: Сигнатуры методов корректны для каждого типа

**Проверка**: ✅ `make test-unit` проходит, 4 новых теста для transport flags.

---

### Фаза 3: Event Adapter генерация
**Оценка: 3-4 часа**

#### 3.1. Создать/обновить `EventAdapterGenerator`

Генерирует `services/<svc>/src/generated/event_adapter.py`:

```python
# event_adapter.py (generated)
from faststream.redis import RedisRouter
from shared.generated.schemas import UserImportBatch, ImportResult
from .protocols import UsersControllerProtocol

router = RedisRouter()

def register_event_handlers(
    get_controller: Callable[[], UsersControllerProtocol],
    get_session: Callable[[], AsyncSession],
) -> None:
    """Register all event handlers for this service."""
    
    @router.subscriber("user.import.requested")
    async def handle_process_import(event: UserImportBatch) -> None:
        async with get_session() as session:
            controller = get_controller()
            result = await controller.process_import(session, event)
            await publish_user_import_completed(result)
```

#### 3.2. Шаблон `event_adapter.py.j2`

- Создать новый Jinja2 шаблон
- Использовать тот же `OperationContextBuilder.build_for_events()`

#### 3.3. Обработка `publish_on_success`

Если операция имеет `events.publish_on_success`:
- После успешного выполнения контроллера
- Опубликовать результат в указанный канал

#### 3.4. Интеграция с FastAPI (для dual-transport)

Для операций с `rest:` + `events.publish_on_success`:
```python
# В REST adapter после вызова контроллера:
result = await controller.create_user(session, payload)
await publish_user_created(result)  # ← добавляется автоматически
return result
```

#### 3.5. Тестирование

- [x] Unit тесты: генерация event_adapter.py
- [x] Unit тесты: корректные subscriber декораторы
- [x] Unit тесты: publish_on_success добавлен в event adapter
- [x] Integration with REST (publish_on_success in RoutersGenerator)

**Проверка**: ✅ `make test-unit` проходит, все тесты для EventAdapterGenerator и RoutersGenerator проходят.

---

### Фаза 4: Session Management для Events
**Оценка: 2-3 часа**

> [!NOTE]
> **Решение принято**: Опция A — session factory передаётся при регистрации.

#### Реализовано:

1. **Правильная типизация**: `Callable[[], AbstractAsyncContextManager[AsyncSession]]`
2. **Явный commit/rollback**:
   ```python
   async with get_session() as session:
       try:
           result = await controller.process(session, payload=event)
           await session.commit()
           await broker.publish(result, "success.channel")
       except Exception as e:
           await session.rollback()
           await broker.publish({"error": str(e)}, "error.channel")
           raise
   ```

#### Тестирование

- [x] Unit тест: session.commit() вызывается после успеха
- [x] Unit тест: session.rollback() вызывается при ошибке
- [x] Unit тест: AbstractAsyncContextManager используется в сигнатуре

**Проверка**: ✅ 122 теста проходят, включая новые тесты для session management.

---

### Фаза 5: Auto-Registration
**Оценка: 2-3 часа**

> [!NOTE]
> **Статус**: Реализовано. `RegistryGenerator` генерирует `registry.py`.

#### 5.1. Генерация `registry.py`

```python
# services/<svc>/src/generated/registry.py
from .routers.users import create_router as create_users_router
from .routers.debug import create_router as create_debug_router
from .protocols import UsersControllerProtocol, DebugControllerProtocol

def create_api_router(
    get_db: Callable[[], AsyncSession],
    get_users_controller: Callable[[], UsersControllerProtocol],
    get_debug_controller: Callable[[], DebugControllerProtocol],
) -> APIRouter:
    """Create and configure the API router with all domain routers."""
    router = APIRouter()
    router.include_router(create_users_router(get_db, get_users_controller))
    router.include_router(create_debug_router(get_db, get_debug_controller))
    return router

# Re-export protocols for convenient imports
__all__ = ["create_api_router", "UsersControllerProtocol", "DebugControllerProtocol"]
```

#### 5.2. Упрощение main.py / router.py

До:
```python
# Много импортов, ручная регистрация каждого роутера
from controllers.users import UsersController
from generated.routers.users import create_router
# ... 20 строк boilerplate
```

После:
```python
from generated.registry import create_api_router

api_router = create_api_router(
    get_db=get_async_db,
    get_users_controller=lambda: UsersController(),
    get_debug_controller=lambda: DebugController(),
)
```

#### 5.3. Тестирование

- [x] Unit тесты: генерация registry.py
- [x] Unit тесты: registry включает все domain routers
- [x] Unit тесты: registry экспортирует protocols в __all__
- [x] Unit тесты: registry включает event_adapter если есть subscribe операции

**Проверка**: ✅ 127 тестов проходят, auto-registration готова.

---

### Фаза 6: Legacy Cleanup
**Оценка: 2-3 часа**

#### 6.1. Удалить устаревшие файлы/генераторы

- [x] Удалить `EventHandlersGenerator` (заменён на `EventAdapterGenerator`)
- [x] Удалить `event_handlers.py.j2` (заменён на `event_adapter.py.j2`)
- [x] Обновить `__init__.py` exports

#### 6.2. Миграция существующих сервисов в template

#### 6.2. Миграция существующих сервисов в template
 
- [x] `notifications_worker/src/handlers.py` → генерируемый event_adapter
- [x] `tg_bot` event publishing → через generated publishers
 
#### 6.3. Обновить документацию
 
- [x] `ARCHITECTURE.md` — новая секция про Unified Handlers
- [ ] `AGENTS.md` — обновить инструкции для агентов
- [ ] `backlog.md` — закрыть связанные задачи
 
#### 6.4. Тестирование
 
- [x] Все существующие тесты проходят
- [x] Нет warnings о deprecated imports
- [x] Документация обновлена
 
**Проверка**: ✅ `make lint && make test` проходят, миграция завершена.

---

### Фаза 7: CI/CD Updates
**Оценка: 1-2 часа**

#### 7.1. Обновить CI workflow

- [ ] Добавить шаг проверки event handlers (если есть events в specs)
- [ ] Линтинг сгенерированных event adapters

#### 7.2. Добавить spec validation для events

- [ ] Проверка: модели сообщений существуют
- [ ] Проверка: каналы событий уникальны
- [ ] Проверка: publish_on_success ссылается на валидный канал

#### 7.3. Тестирование

- [ ] CI проходит на feature branch
- [ ] CI генерирует и проверяет event adapters

**Проверка**: GitHub Actions зелёные.

---

### Фаза 8: End-to-End Verification
**Оценка: 2-3 часа**

#### 8.1. Полный сценарий тестирования

1. Создать новый проект через `copier copy`
2. Добавить domain spec с REST + Events операциями
3. Запустить `make generate-from-spec`
4. Имплементировать контроллер
5. Запустить сервисы
6. Вызвать REST endpoint → проверить событие в Redis
7. Опубликовать событие → проверить обработку

#### 8.2. Документировать happy path

- [ ] README с примером dual-transport операции
- [ ] Пример в template services

**Проверка**: Сценарий выполняется без ошибок, документация понятна.

---

## 4. Открытые вопросы

> [!WARNING]
> Эти вопросы требуют обсуждения перед реализацией.

### 4.1. События в одном месте или двух?

**Текущее состояние**:
- `shared/spec/events.yaml` — глобальное определение событий (message types)
- `services/<svc>/spec/<domain>.yaml` — использование событий в операциях

**Вопрос**: Нужно ли объединять? Или оставить разделение (events.yaml = каталог, domain.yaml = использование)?

**Варианты**:
- A) Оставить как есть: events.yaml определяет типы, domain.yaml ссылается
- B) Убрать events.yaml, определять события прямо в domain specs
- C) events.yaml = инфраструктура (broker config), domain = бизнес-события

---

### 4.2. Как обрабатывать ошибки в event handlers?

**Вопрос**: Что делать если event handler падает?

**Варианты**:
- A) Retry с exponential backoff (как в REST clients)
- B) Dead Letter Queue (DLQ)
- C) Publish error event (`events.publish_on_error`)
- D) Просто логировать и терять

---

### 4.3. Транзакционность: Outbox Pattern?

**Вопрос**: Сейчас events публикуются напрямую после DB write. Это ненадёжно (dual write problem). Нужен ли Transactional Outbox?

**Варианты**:
- A) Пока без outbox — простота важнее
- B) Опциональный outbox через конфигурацию
- C) Обязательный outbox для всех events

---

### 4.4. Формат имён каналов

**Текущее**: `user_created`, `command_received`

**Вопрос**: Стандартизировать формат?

**Варианты**:
- A) `<entity>.<action>` → `user.created`, `order.shipped`
- B) `<service>.<entity>.<action>` → `backend.user.created`
- C) Свободный формат (как сейчас)

---

### 4.5. Нужен ли Event Sourcing?

**Вопрос**: Идти ли дальше к полному Event Sourcing (state = replay of events)?

**Текущее понимание**: Нет, это overkill. Events — для интеграции, не для persistence.

---

## 5. Критерии успеха

### Must Have (MVP)

- [ ] Одна спека описывает REST и Events операции
- [ ] Генерируется единый Protocol для контроллера  
- [ ] Генерируется Event Adapter с FastStream handlers
- [ ] Session management работает в event handlers
- [ ] Существующие тесты проходят
- [ ] Документация обновлена

### Nice to Have

- [x] Auto-registration (registry.py)
- [x] Legacy cleanup полностью завершён
- [ ] E2E сценарий задокументирован

### Out of Scope (для этой итерации)

- Transactional Outbox Pattern
- Event Sourcing
- Saga orchestration
- Dead Letter Queues

---

## Приложение: Пример итоговой спеки

```yaml
# services/backend/spec/users.yaml
domain: users
config:
  rest:
    prefix: "/users"
    tags: ["users"]

operations:
  # ═══════════════════════════════════════════════════════════════
  # QUERY — синхронный REST, без events
  # ═══════════════════════════════════════════════════════════════
  get_user:
    output: UserRead
    params:
      - name: user_id
        type: int
    rest:
      method: GET
      path: "/{user_id}"

  list_users:
    output: list[UserRead]
    params:
      - name: limit
        type: int
        source: query
        default: 20
    rest:
      method: GET
      path: ""

  # ═══════════════════════════════════════════════════════════════
  # COMMAND — REST + event publication
  # ═══════════════════════════════════════════════════════════════
  create_user:
    input: UserCreate
    output: UserRead
    rest:
      method: POST
      path: ""
      status: 201
    events:
      publish_on_success: user.created

  delete_user:
    params:
      - name: user_id
        type: int
    rest:
      method: DELETE
      path: "/{user_id}"
      status: 204
    events:
      publish_on_success: user.deleted

  # ═══════════════════════════════════════════════════════════════
  # BACKGROUND — только events, нет REST
  # ═══════════════════════════════════════════════════════════════
  process_user_import:
    input: UserImportBatch
    output: UserImportResult
    events:
      subscribe: user.import.requested
      publish_on_success: user.import.completed
      publish_on_error: user.import.failed
```

---

## Changelog

| Дата | Изменение |
|------|-----------|
| 2025-12-21 | Initial draft created from brainstorming session |

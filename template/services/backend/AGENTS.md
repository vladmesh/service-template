# AGENTS — Backend API

## Location

- Код, тесты и зависимости живут в `services/backend`. Не разносите `Dockerfile`, `src/` или `tests/` по другим каталогам.
- Любые команды запускайте через `make` и docker-compose (см. `CONTRIBUTING.md`). Локальный Python не используем.

## Spec-First Workflow

Backend использует spec-first подход: модели и протоколы генерируются из YAML-спецификаций.

**Расположение спеков:**
- `shared/spec/models.yaml` — общие Pydantic-модели (схемы данных)
- `services/backend/spec/*.yaml` — domain operations (REST endpoints + events)

**Workflow:**
1. Отредактируйте спек (`shared/spec/models.yaml` или `services/backend/spec/<domain>.yaml`)
2. Запустите `make validate-specs` (проверяет YAML до генерации)
3. Запустите `make generate-from-spec`
4. Сгенерированные протоколы появятся в `services/backend/src/generated/protocols.py`
5. Реализуйте методы в `services/backend/src/controllers/<domain>.py`

**Правило:** Никогда не создавайте `BaseModel` или `APIRouter` вручную — они генерируются. Это проверяется линтером (`make lint`).

## Directory Structure

```
services/backend/
├── spec/              # YAML спецификации (Source of Truth)
├── src/
│   ├── app/           # Бизнес-логика: repositories, models, lifespan
│   ├── controllers/   # Реализации протоколов (ваш код)
│   └── generated/     # НЕ РЕДАКТИРОВАТЬ: protocols.py, routers
├── migrations/        # Alembic миграции
└── tests/
```

## Database & Migrations

- Миграции в `services/backend/migrations/versions/`.
- Перед запуском API: `services/backend/scripts/migrate.sh`.
- Создать новую миграцию: `make makemigrations name="describe_change"`.

## Event Publishing

Backend подключается к Redis через lazy broker в lifespan:

```python
from shared.generated.events import get_broker

@asynccontextmanager
async def lifespan(app: FastAPI):
    broker = get_broker()
    await broker.connect()
    yield
    await broker.close()
```

Публикация событий из контроллеров:
```python
from shared.generated.events import publish_user_registered
await publish_user_registered(event)
```

## Key Commands

| Команда | Назначение |
|---------|-----------|
| `make generate-from-spec` | Перегенерировать код из спеков |
| `make validate-specs` | Проверить YAML спеки |
| `make lint-specs` | Проверить соответствие спекам |
| `make lint-controllers` | Проверить синхронизацию контроллеров с протоколами |
| `make makemigrations name="..."` | Создать Alembic миграцию |
| `make openapi` | Экспорт OpenAPI JSON |
| `make tests backend` | Запустить тесты backend |

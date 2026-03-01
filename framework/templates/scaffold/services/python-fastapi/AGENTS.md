# AGENTS — __SERVICE_NAME__ (FastAPI)

## Overview

HTTP API сервис на FastAPI + uvicorn. Expose порт 8000 в Docker Compose.

- Код, тесты и зависимости в `services/__SERVICE_NAME__/`. Не выносите за пределы.
- Запуск через `make dev-start`. Не запускайте uvicorn напрямую на хосте.
- Entrypoint: `src/main.py`.

## Structure

```
services/__SERVICE_NAME__/
├── spec/              # YAML спецификации (если spec-first)
├── src/
│   ├── app/           # Бизнес-логика, repositories, lifespan
│   ├── controllers/   # Реализации протоколов (ваш код)
│   └── generated/     # НЕ РЕДАКТИРОВАТЬ (protocols, routers)
├── migrations/        # Alembic миграции (если есть БД)
└── tests/
```

## Spec-First Workflow

Если проект использует spec-first:
1. Отредактируйте `spec/<domain>.yaml`
2. Запустите `make generate-from-spec`
3. Реализуйте методы в `src/controllers/<domain>.py`

**Правило:** Не создавайте `BaseModel` или `APIRouter` вручную — они генерируются.

## Key Commands

| Команда | Назначение |
|---------|-----------|
| `make tests __SERVICE_NAME__` | Тесты сервиса |
| `make log __SERVICE_NAME__` | Логи контейнера |
| `make generate-from-spec` | Перегенерировать код из спеков |
| `make lint` | Линтинг |
| `make typecheck` | mypy |

## Environment Variables

NEVER use default values. Fail immediately if missing. Document all vars in `.env.example`.

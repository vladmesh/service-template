# AGENTS — __SERVICE_NAME__ (FastStream Worker)

## Overview

Event-driven worker, подписывающийся на Redis Streams через FastStream. Не expose HTTP-порт.

- Код и зависимости в `services/__SERVICE_NAME__/`. Не выносите за пределы.
- Запуск через `make dev-start`. Не запускайте broker напрямую на хосте.
- Entrypoint: `src/main.py`.

## Broker Pattern

```python
import os
from faststream import FastStream
from faststream.redis import RedisBroker

async def main():
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise RuntimeError("REDIS_URL is not set")
    broker = RedisBroker(redis_url)
    # register subscribers via create_event_adapter(broker=broker, ...)
    app = FastStream(broker)
    await app.run()
```

Lifecycle (`connect`/`close`) управляется автоматически через `FastStream(broker).run()`. Не вызывайте `broker.connect()` вручную.

## Spec-First Workflow

Если сервис использует spec-first event adapter:
1. Отредактируйте `spec/<domain>.yaml`
2. Запустите `make generate-from-spec` (перегенерирует `src/generated/`)
3. Реализуйте новые методы в `src/controllers/<domain>.py`

Подписки регистрируются автоматически через `create_event_adapter()`. Не регистрируйте `@broker.subscriber` вручную.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `REDIS_URL` | Yes | Redis connection string |

NEVER use default values. Document all vars in `.env.example`.

## Key Commands

| Команда | Назначение |
|---------|-----------|
| `make tests __SERVICE_NAME__` | Тесты сервиса |
| `make log __SERVICE_NAME__` | Логи контейнера |
| `make generate-from-spec` | Перегенерировать event adapter |
| `make lint` | Линтинг |

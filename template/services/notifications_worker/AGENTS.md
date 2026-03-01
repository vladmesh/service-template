# AGENTS — Notifications Worker

## Overview

Event-driven FastStream worker, подписывающийся на Redis Streams и обрабатывающий события через `NotificationsController`.

- Весь код в `services/notifications_worker`. Не выносите файлы за пределы.
- Запуск и тесты только через `make` + Docker. Не устанавливайте deps на хост.
- Точка входа: `services/notifications_worker/src/main.py`.

## Architecture

Сервис использует spec-first event adapter:

```
spec/notifications.yaml -> src/generated/ (protocols.py, event_adapter.py)
                                    |
                        src/controllers/notifications.py  <- ваш код
```

**Workflow при изменении событий:**
1. Отредактируйте `services/notifications_worker/spec/notifications.yaml`
2. Запустите `make generate-from-spec` (перегенерирует `src/generated/`)
3. Реализуйте новые методы в `src/controllers/notifications.py`

## Event Subscriptions

| Event | Handler |
|-------|---------|
| `user_registered` | `NotificationsController.on_user_registered` |

Подписки регистрируются автоматически через `create_event_adapter()` в `main.py`. Не регистрируйте `@broker.subscriber` вручную.

## Broker Pattern

Этот сервис создаёт `RedisBroker` напрямую (не через `get_broker()`):

```python
redis_url = os.getenv("REDIS_URL")
if not redis_url:
    raise RuntimeError("REDIS_URL is not set")
broker = RedisBroker(redis_url)
create_event_adapter(broker=broker, ...)
app = FastStream(broker)
await app.run()
```

Lifecycle (`connect`/`close`) управляется автоматически через `FastStream(broker).run()`.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `REDIS_URL` | Yes | Redis connection string (e.g., `redis://redis:6379`) |

## Key Commands

| Команда | Назначение |
|---------|-----------|
| `make tests notifications_worker` | Тесты сервиса |
| `make generate-from-spec` | Перегенерировать event adapter |
| `make lint` | Линтинг (включая spec compliance) |
| `make log notifications_worker` | Логи контейнера |

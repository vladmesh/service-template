# AGENTS — Telegram Bot

## Overview

- Весь код и зависимости находятся в `services/tg_bot`. Держите `Dockerfile`, `src/` и `tests/` в этом каталоге.
- Запуск и тесты выполняются через `make` + Docker (`make dev-start`, `make tests tg_bot`). Не устанавливайте deps на хост.
- Скрипт запуска — `services/tg_bot/src/main.py`. Dockerfile использует Poetry и базовый образ `python:3.11-slim`.

## Event Publishing

Бот публикует события напрямую в Redis Streams (не через REST API backend'а):

- **Broker**: FastStream RedisBroker из `shared.generated.events`
- **Events**: `command_received` для команд бота
- **Lifecycle**: Broker подключается при старте приложения (`post_init`) и отключается при shutdown (`post_shutdown`)

```python
from shared.generated.events import broker, publish_command_received
from shared.generated.schemas import CommandReceived

# Publishing
event = CommandReceived(command=cmd, args=args, user_id=telegram_id, timestamp=datetime.now(UTC))
await publish_command_received(event)
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `REDIS_URL` | Yes | Redis connection string (e.g., `redis://redis:6379`) |
| `API_BASE_URL` | Yes | Backend URL for user sync (e.g., `http://backend:8000`) |

## Communication Patterns

1. **User Sync** — HTTP POST to backend `/users` endpoint (создание/проверка пользователя)
2. **Command Events** — Direct publish to Redis Streams (события команд)

## Dependencies

- `python-telegram-bot` — Telegram Bot API
- `httpx` — HTTP client for backend communication
- `shared` — Generated events and schemas from `shared/`

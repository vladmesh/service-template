# AGENTS — Telegram Bot

- Весь код и зависимости находятся в `services/tg_bot`. Держите `Dockerfile`, `src/` и `tests/` в этом каталоге.
- Запуск и тесты выполняются через `make` + Docker (`make dev-start`, `make tests tg_bot`). Не устанавливайте deps на хост.
- Скрипт запуска — `services/tg_bot/src/main.py`. Dockerfile использует Poetry и базовый образ `python:3.11-slim`.
- Описывайте здесь протоколы общения с другими сервисами (webhook/polling, API бэкенда, переменные окружения), чтобы агентам было проще поддерживать бот.

# AGENTS — __SERVICE_NAME__ (Python)

## Overview

Generic Python-сервис без конкретного фреймворка.

- Код и зависимости держите внутри каталога сервиса `services/__SERVICE_NAME__/`.
- Запуск через `make` и Docker. Не устанавливайте deps напрямую на хост.
- Dockerfile на базе `python:3.11-slim`. Адаптируйте CMD под конкретный entrypoint.

## Key Commands

| Команда | Назначение |
|---------|-----------|
| `make tests __SERVICE_NAME__` | Тесты этого сервиса |
| `make log __SERVICE_NAME__` | Логи контейнера |
| `make lint` | Линтинг всего проекта |

## Environment Variables

Все переменные окружения определяются в `.env.example`. Не используйте значения по умолчанию.

## После наполнения

Обновите этот файл: добавьте описание сервиса, env vars, архитектуру, команды запуска.

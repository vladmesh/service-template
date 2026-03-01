# AGENTS — __SERVICE_NAME__ (Node.js)

## Overview

Node.js сервис. Expose порт через Docker Compose (обычно 4321).

- Весь код в `services/__SERVICE_NAME__/`. Не выносите файлы за пределы.
- Запуск через `make dev-start`. Не запускайте node напрямую на хосте.
- Entrypoint и фреймворк определяются в `package.json`.

## Key Commands

| Команда | Назначение |
|---------|-----------|
| `make dev-start` | Запустить dev-окружение |
| `make log __SERVICE_NAME__` | Логи контейнера |
| `make tests __SERVICE_NAME__` | Тесты (если настроены) |

## Environment Variables

Все переменные окружения в `.env.example`. Не используйте значения по умолчанию.

## После наполнения

Обновите этот файл: добавьте описание сервиса, env vars, команды запуска.

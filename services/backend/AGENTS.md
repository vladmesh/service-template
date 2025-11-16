# AGENTS — Backend API

- Код и зависимости живут в `services/backend`. Не разносите Dockerfile, src или tests по другим каталогам.
- Любые команды запускайте через `make` и docker-compose (см. корневой `AGENTS.md`). Локальный Python/Poetry не используем.
- Миграции лежат в `services/backend/migrations`. Перед запуском API нужно выполнить `services/backend/scripts/migrate.sh`.
- Dockerfile собирает образ на базе `python:3.11-slim`, точка входа — `uvicorn services.backend.src.main:app`.
- Добавляйте сюда любые особенности сервиса (API, конфиги, migraции), чтобы другим агентам было проще подключаться.

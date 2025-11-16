# AGENTS PLAYBOOK

Guidelines for automation agents (or humans in "automation mode") working inside this repository.

## Workflow Rules

1. **Drive everything through the `Makefile`.** If a target exists (lint, format, tests, migrations, Compose stacks), call it instead of invoking Docker/Poetry/Python directly.
2. **Never run code on the host.** All tooling is containerized. Keep the local machine limited to Docker + `make`.
3. **Stay within Docker compose projects.** Compose project names are already set in the Makefile; avoid overriding them unless you know what you’re doing.

## Environment Checklist

- Requirements: Docker (with Compose v2), GNU Make, POSIX shell.
- Bootstrap configuration once per clone:

  ```bash
  cp .env.example .env
  git config core.hooksPath .githooks
  ```

- Hooks will run `make format` on commit and `make lint/tests` on pushes to `main`. Leave them enabled so local checks match CI.

## Day-to-Day Commands

- `make dev-start` / `make dev-stop` — bring up/down the development stack defined in `infra/compose.dev.yml`.
- `make lint` — Ruff checks through the tooling container.
- `make format` — Ruff formatter (auto-applied, used by the pre-commit hook).
- `make typecheck` — Mypy for every Python module.
- `make tests` — runs backend + bot unit suites and the shared integration tests. Use `make tests backend|tg_bot|integration` for scoped suites.
- `make makemigrations name="..."` — generates Alembic migrations via Docker (never run Alembic locally).
- `make services-validate` — checks that `services.yml` stays well-formed before automating infra changes.
- `make compose-sync` — регенерирует сервисные блоки `infra/compose.*.yml` из `services.yml` и шаблонов.
- `make add-service` — интерактивный генератор нового сервиса; запускает шаблон, обновляет `services.yml` и синхронизирует Compose.

## Service Specs & Sync (rollout plan)

- Каждый сервис переезжает в директорию `services/<slug>/` со структурой из [`template_service_spec.md`](template_service_spec.md) (`Dockerfile`, `src/`, `tests/`, `AGENTS.md`, README).
- `services.yml` остаётся единственным источником правды и будет содержать только три обязательных поля: `name` (slug = имя каталога), `type` и `description`.
- Допустимые `type` значения: `python` и `default`. Расширения набора должны проходить код-ревью и сопровождаться обновлением шаблонов в `templates/services/<type>`.
- `sync_services` станет новой точкой входа:
  - `make sync-services` (`sync_services check`) — только детектирует расхождения между `services.yml` и артефактами (директории, compose-шаблоны, блоки в `infra/compose.*.yml`). Никаких автофиксов; non-zero exit в CI.
  - `make sync-services create` (`sync_services create-missing`) — создаёт отсутствующие артефакты из шаблонов, не правит существующие файлы.
- Автоматически управляемые артефакты: `services/<slug>/` (шаблонная заготовка), `infra/compose.services/<slug>/base.yml` и `dev.yml`, а также секции между маркерами `# >>> services`/`# <<< services` в `infra/compose.base.yml` и `infra/compose.dev.yml`.
- README и AGENTS внутри сервиса заполняются вручную после генерации (никаких автотекстов) — sync лишь проверяет их наличие.
- До полного ввода `sync_services` допускается `make add-service`, но новые PR уже должны описывать сервис в `services.yml` и ссылаться на этот план миграции.

## Coding Standards

- Python formatting: Ruff formatter (see `make format`).
- Imports + linting: `ruff check`.
- Typing: keep `disallow_untyped_defs` happy. Type all fixtures and request/response objects.
- Database changes: place migrations in `services/backend/migrations`; the backend entrypoint applies them automatically.

## What Not to Do

- Don’t install Poetry/pip deps globally.
- Don’t run `pytest`, `uvicorn`, or random scripts outside Docker.
- Don’t edit `.env` with secrets you’re not willing to commit; use overrides or another env file if needed.

If an action is not exposed via the Makefile yet, add a target before attempting to run it manually. Consistency keeps local loops aligned with CI.

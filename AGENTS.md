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
- `make sync-services [create]` — сверяет `services.yml` с файловой системой (по умолчанию `check`, `create` дописывает отсутствующие каркасы и compose-шаблоны).
- `make tooling-tests` — pytest-набор для `sync_services` и scaffolding-хелперов (в tooling-контейнере).

## Service Specs & Sync (rollout plan)

- Каждый сервис переезжает в директорию `services/<slug>/` и использует базовый шаблон из `templates/services/<type>` (`Dockerfile`, `src/`, `tests/`, `AGENTS.md`, README).
- `services.yml` остаётся единственным источником правды и будет содержать только три обязательных поля: `name` (slug = имя каталога), `type` и `description`.
- Допустимые `type` значения: `python` и `default`. Расширения набора должны проходить код-ревью и сопровождаться обновлением шаблонов в `templates/services/<type>`.
- `sync_services` станет новой точкой входа:
  - `make sync-services` (`sync_services check`) — только детектирует расхождения между `services.yml` и артефактами (директории, compose-шаблоны, блоки в `infra/compose.*.yml`). Никаких автофиксов; non-zero exit в CI.
  - `make sync-services create` (`sync_services create-missing`) — создаёт отсутствующие артефакты из шаблонов, не правит существующие файлы.
- Автоматически управляемые артефакты: `services/<slug>/` (шаблонная заготовка) и секции между маркерами `# >>> services`/`# <<< services` в `infra/compose.base.yml` и `infra/compose.dev.yml`. Отдельных файлов в `infra/compose.services` больше нет.
- Сервис может отключить dev-блок в compose через поле `dev_template: false` в `services.yml`.
- README и AGENTS внутри сервиса заполняются вручную после генерации (никаких автотекстов) — sync лишь проверяет их наличие.
- Новые сервисы создаются только через `services.yml` + `make sync-services create`; интерактивный `add-service` больше не поддерживается.

## Добавление нового сервиса

1. Добавьте запись в `services.yml` (поля `name`, `type`, `description`).
2. Запустите `make sync-services create`, чтобы получить заготовку каталога и compose-шаблонов.
3. В сервисе заполните `README.md`, `AGENTS.md`, `Dockerfile` и минимальный код.
4. Закоммитьте изменения и прогоните `make sync-services`, `make lint`, `make tests` перед PR.

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

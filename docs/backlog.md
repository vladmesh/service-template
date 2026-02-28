# Backlog

## Spec-First API Generation — Future Improvements

### Spec-First Async Messaging (Queues)

**Status**: DONE

**Description**: Support asynchronous messaging via queues.
- **Decision**: We chose **Redis** (Streams) + **FastStream**.
    - **Why**: Fits "Rigidity is Freedom". Single container, strongly typed, spec-first.
- **Goal**: Define topics/events in YAML.
- **Generation**: Auto-generate consumers and producer wrappers using FastStream.
- **Validation**: Ensure messages conform to schemas defined in `models.yaml`.

> **Реализовано:** `EventsGenerator`, `EventAdapterGenerator` генерируют pub/sub код из `events.yaml`. Lazy broker через `get_broker()`. Полностью spec-driven.

### Spec-Only Module Storage (Long-term Vision)

**Status**: IDEA
**Priority**: LOW (Long-term architectural evolution)

**Description**: Store only specs and minimal scaffolds for template modules instead of full implementation code. Generate all business logic on project creation.

**Current State**:
- Template stores complete implementation: controllers, models, repositories, etc.
- Modules (backend, tg_bot, etc.) are selected via Jinja conditions during `copier copy`
- Creates distinction between "built-in batteries" and user-added services

**Proposed State**:
- Template stores only:
  - Domain specs (`services/backend/spec/*.yaml`)
  - Infrastructure scaffolds (`src/core/`, `scripts/`, minimal `pyproject.toml`)
- Delete implementation code: controllers, models, repositories
- On `copier copy`, automatically run `make setup` (which includes `make generate-from-spec`)

**Benefits**:
- ✅ Perfect spec-first implementation (no code drift from specs)
- ✅ Massive token economy win (only specs to read/edit)
- ✅ Zero distinction between built-in and custom services
- ✅ Simpler compose management (no markers needed, full generation)
- ✅ Cleaner framework updates via `copier update`

**Challenges**:
- ❌ Controllers contain business logic hard to specify generically
- ❌ ORM models need DB-specific types, indexes, relationships
- ❌ No reference implementation in template (harder to debug framework)
- ❌ Bootstrap requires generation step (slower initial copy)
- ❌ Generators must handle validation rules, hooks, complex logic

**Prerequisites for Implementation**:
1. Create ORM model generator from extended specs
2. Add validation/constraint rules to operation specs
3. Implement convention-based controller hooks/stubs
4. Enhance scaffolding templates for business logic slots
5. Add reference implementation outside template for framework development

**Recommended Path**:
1. **Short-term**: Current hybrid approach (Jinja templates)
2. **Medium-term**: Keep specs + minimal scaffolds, delete business logic
3. **Long-term**: Pure spec-only after generator maturity (2-3 months)

### Celery Worker Support

**Status**: IDEA

**Description**: Add native support for distributed tasks via Celery.
- **Spec**: Allow defining a service type as `celery-worker` in `services.yml` or `AGENTS.md`.
- **Integration**: Pre-configured Redis/RabbitMQ in docker-compose.
- **Scaffolding**: Generate `celery_app` instance and task decorators automatically.

### High-Level Architecture Spec ("Who talks to whom")

**Status**: IDEA

**Description**: Introduce a centralized "Connectivity Graph" specification.
- **Problem**: Currently, dependencies (DB access, inter-service calls) are implicit in code.
- **Solution**: Explicitly define service relationships in `services.yml` or a new `architecture.yaml`.
    - `access: [database, internet]`
    - `exposes: [rest, rpc]`
    - `consumes: [auth-service.v1.verify_token]`
- **Outcome**: Generate explicit typed clients ("SDKs") for internal services and firewall rules/network policies in Docker Compose.

### Auto-fuzzing and Contract Testing

**Status**: IDEA

**Description**: Integrate contract testing tools like `schemathesis` into the CI pipeline.
- **Mechanism**: The tool reads the generated `openapi.json` and fuzzes the running service with valid and invalid inputs.
- **Goal**: Automatically detect 500 errors and edge case failures without writing manual tests. If the code doesn't handle inputs described in the spec, the build fails.

### Spec-First Observability

**Status**: IDEA

**Description**: Automatically embed OpenTelemetry traces and metrics into generated code.
- **Mechanism**: Wrap generated router endpoints with telemetry decorators.
- **Goal**: Zero-config observability. Defining an endpoint `POST /users` in the spec automatically yields metrics like `http_requests_total{route="/users"}` and traces with propagated Request-IDs.

## Distribution & Usage Evolution

### 1.1 Add Predefined Module to Existing Project

**Status**: TODO

**Description**: Allow adding a predefined module (tg_bot, notifications, frontend) to an existing project that was initially generated without it.

- **Problem**: Copier's `update` command updates infrastructure but cannot add modules that were excluded during initial generation. The `_tasks` in `copier.yml` delete unselected module directories, making them unavailable for later addition.

- **Use Case**: Agent generates project with `modules=backend`, later decides to add `tg_bot`.

- **Current Workaround**: Re-generate project with all desired modules (loses customizations) or manually copy module from template.

- **Proposed Solution**: `make add-module name=tg_bot` command that:
  1. Validates module is in predefined list (backend, tg_bot, notifications, frontend)
  2. Fetches module directory from template repository (via git archive or copier partial)
  3. Updates `services.yml` to include the new module
  4. Runs `make setup` to install deps and regenerate
  5. Updates `.copier-answers.yml` to reflect new module selection

- **Considerations**:
  - How to handle template version mismatch (project on v1.0, template on v2.0)?
  - Should module addition trigger compose regeneration automatically?
  - Integration with `copier update` — should it respect manually added modules?

### 2. CLI Wrappers

**Status**: IDEA

**Description**: Wrap `make` commands and boilerplate scripts into a standalone CLI tool (distributed via PyPI or binary).
- **Why**: Simplify usage for both humans and agents.
- **Commands**:
    - `my-framework init` (wraps `copier copy`)
    - `my-framework sync` (wraps `make setup`)
    - `my-framework update` (wraps `copier update`)

### 4. Context Packer

**Status**: IDEA

**Description**: A tool to optimize context loading for agents.
- **Problem**: Agents waste tokens reading unrelated files.
- **Solution**: A command like `make context service=backend` that aggregates:
    - Relevant Spec (models + paths)
    - `AGENTS.md` for the service
    - Signatures of imported modules
    - Current linter errors
- **Goal**: Provide a single, token-optimized file containing strictly necessary information for the current task.

---

## Template / Copier Issues

### Copier tests (`tests/copier/`) нужно переписать

**Status**: TODO
**Priority**: MEDIUM

**Description**: 55 тестов скипаются с `copier not installed`. Fixture `copier_available` проверяет `shutil.which("copier")`, но при запуске через `.venv/bin/pytest` copier не в PATH. Кроме того, после итераций 2-3 (убрали tooling, перешли на venv, lazy broker) многие тесты устарели и требуют обновления. `make test-copier` определён в корневом Makefile. Copier тесты отключены в `.githooks/pre-push` (закомментированы с TODO).

### Enum Types in Model Fields

**Status**: IDEA

**Description**: Add support for enum types in model field definitions.

**Example**:
```yaml
models:
  Book:
    fields:
      status:
        type: enum
        values: [wishlist, reading, finished]
        default: wishlist
```

**Benefit**: Generated Pydantic models would use `Literal` or `Enum` types instead of plain strings.

---

## Usability Issues (from Testing Feedback)

### Auto-Register Routers

**Status**: TODO

**Description**: After generating a new domain router, the user must manually:
1. Import the controller class
2. Import the generated router factory
3. Create a dependency function for the controller
4. Call `create_router()` and register it with `api_router`

This is repetitive and error-prone.

**Proposed Solution**:
- Generate a `router_registry.py` that auto-discovers all generated routers
- Use a naming convention like `controllers/{domain}.py` → `routers/{domain}.py`
- Main router imports and includes all discovered routers automatically

---

### Add E2E CI Job for Unified Handlers

**Status**: TODO
**Priority**: MEDIUM

**Description**: Add a CI job that:
1. Generates a project via copier with dual-transport operations
2. Runs `make setup && make generate-from-spec`
3. Runs `make lint`
4. Runs `make tests`

This would catch integration issues between generated code and user templates.

---

### Full Router.py Generation (Eliminate Wiring Layer)

**Status**: IDEA
**Priority**: LOW

**Description**: Currently `router.py` is manual (wiring layer). We could generate it fully from specs, making the framework 100% spec-first even for FastAPI services.

---

## Jinja Whitespace в шаблонах документации

**Status**: TODO
**Priority**: LOW

**Description**: Шаблоны `TASK.md.jinja`, `CONTRIBUTING.md.jinja`, `ARCHITECTURE.md.jinja` генерируют лишние пустые строки и некорректные отступы из-за whitespace от Jinja conditional blocks. Подробности — в `docs/e2e-issues-iteration6.md` (issues #1-#4, #9). Все функциональные — никакого влияния на работу проекта, только косметика markdown.

---

## Infrastructure Audit Fixes

### Reduce Docker Build Context with .dockerignore

**Status**: TODO
**Priority**: HIGH

**Description**: Create a `.dockerignore` file in the root to prevent copying unnecessary files (like `.venv`, `__pycache__`, `.git`) into the Docker build context.

### Update Frontend Dockerfile to use npm ci

**Status**: TODO
**Priority**: MEDIUM

**Description**: Replace `npm install` with `npm ci` in `services/frontend/Dockerfile`.

### Add Cache Mounts to Dockerfiles

**Status**: TODO
**Priority**: LOW

**Description**: Use `--mount=type=cache,target=/root/.cache/uv` in Dockerfiles to speed up rebuilds.

> **Примечание**: Было про pip/poetry cache, теперь актуально для uv cache.

### Audit Scaffold Templates

**Status**: TODO
**Priority**: LOW

**Description**: Review templates in `.framework/framework/templates/scaffold/services/` to ensure they use the latest best practices adopted by main services.

## Simplification & Unification Tasks

### Tooling Removal: Migrate to uv and Run Tools Natively

**Status**: DONE

**Description**: Tooling container removed. All tools run natively via per-service `.venv/` and root `.venv/`. See `docs/plan-tooling-removal.md`.

### Unified Handlers: Error Handling Strategy

**Status**: TODO
**Priority**: MEDIUM

**Description**: Formulate a strategy for handling errors in event handlers. Should we use Dead Letter Queues (DLQ), publish an error event (`events.publish_on_error`), or implement retries with exponential backoff?

### Unified Handlers: Transactional Outbox Pattern

**Status**: IDEA
**Priority**: LOW

**Description**: Currently, events are published directly after DB writes. Consider implementing the Transactional Outbox pattern to avoid the dual write problem and ensure reliable event publishing.

### Unified Handlers: Event Channel Naming Convention

**Status**: TODO
**Priority**: LOW

**Description**: Standardize the format for event channel names (e.g., `<entity>.<action>` like `user.created`).

---

## Закрытые пункты (архив)

<details>
<summary>Развернуть</summary>

### Remove poetry lock from Backend Dockerfile — DONE
Migrated to uv. Poetry полностью удалён.

### Add `make init` Command — DONE (покрыто `make setup`)
`make setup` — единая точка входа: создаёт venvs, устанавливает зависимости, генерирует код, настраивает git hooks.

### Add `ruff check --fix` to Copier Post-Generation Tasks — DONE (покрыто `make setup`)
`make format` запускается пользователем вручную после `make setup`. Copier `_tasks` больше не запускают генерацию/lint — всё делает `make setup`.

### Makefile.jinja: `ruff format --extend-exclude` — DONE
Excludes перенесены в `ruff.toml`, CLI-флаги убраны.

### Copier _tasks: генерация schemas — DONE (покрыто `make setup`)
Генерация перенесена из copier `_tasks` в `make setup`. Пользователь обязан запустить `make setup` после `copier copy`.

### FutureWarning от datamodel-code-generator — DONE
Добавлен `formatters=[Formatter.RUFF_FORMAT, Formatter.RUFF_CHECK]`.

### E2E Issues iterations 4-5 — DONE
Все 15 issues из iteration 5 закрыты в коммите `5c9128f`.

</details>

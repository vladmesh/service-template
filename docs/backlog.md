# Backlog

## Spec-First API Generation — Future Improvements

### Readonly Fields Support

**Status**: DONE

**Description**: Уточнить поддержку `readonly` полей в генераторе. Решить, как правильно трактовать `readonly` поля (например, делать их необязательными в create/update схемах, выставлять `Field(..., const=True)` и т.д.) и расширить генератор, чтобы эти правила соблюдались автоматически.

**Current State**: Implemented. Fields marked as `readonly: true` in `models.yaml` are automatically excluded from `Create` and `Update` variants.


### Split Routers by Service

**Status**: DONE

**Description**: Currently, `routers/rest.py` is a monolith containing all endpoints. This will become unmaintainable. We need to split generated routers into `shared/generated/routers/<service_name>/<tag>.py` so each service only imports what it needs.

### Custom Linter for Spec Enforcement

**Status**: DONE

**Description**: We need to ensure that agents (and devs) don't bypass the spec. A custom linter/AST script should run in CI/pre-commit to forbid:
1. Defining `BaseModel` subclasses inside `services/` (except migrations/tests).
2. Instantiating `APIRouter` manually inside `services/` (except the main app composition).

### Spec Validation Before Code Generation

**Status**: DONE

**Description**: Validate YAML specifications before code generation to catch errors early.
- **Implementation**: `framework/spec/loader.py` validates with Pydantic:
  - `models.yaml`: field types, constraints, variant references (exclude/optional)
  - `routers/*.yaml`: HTTP methods, model/variant existence
  - `events.yaml`: message type existence
- **Integration**: Runs as part of `make lint` and available separately via `make validate-specs`.
- **Benefit**: Clear error messages like "Unknown variant 'Patch' for model 'User'" instead of cryptic generation failures.

### Implement Controller Pattern for Generated Routers

**Status**: DONE

**Description**: Protocol-based Controller Pattern for generated routers.

**Implementation**:
- Generated protocols in `services/<service>/src/generated/protocols.py` using `typing.Protocol`
- Router factory pattern: `create_router(get_db, get_controller)` with DI
- Controller stubs generated in `services/<service>/src/controllers/<router>.py` (skipped if exists)
- Controllers implement protocols and contain business logic
- Routers delegate all calls to injected controller

**Pattern**:
```python
# Protocol (generated)
class UsersControllerProtocol(Protocol):
    async def create_user(self, session: AsyncSession, payload: UserCreate) -> UserRead: ...

# Controller (user-implemented)
class UsersController(UsersControllerProtocol):
    async def create_user(self, session: AsyncSession, payload: UserCreate) -> UserRead:
        # Business logic here
        ...

# Router factory (generated)
def create_router(get_db, get_controller) -> APIRouter:
    router = APIRouter(...)
    @router.post(...)
    async def create_user(..., controller = Depends(get_controller)):
        return await controller.create_user(...)
    return router
```

### Remove Caddy from Template

**Status**: DONE
**Priority**: MEDIUM

**Description**: Remove Caddy reverse proxy from generated projects. SSL termination and reverse proxying should be handled by the infrastructure layer (prod_infra), not by individual projects.

**Current State**:
- Removed `template/infra/Caddyfile`
- Removed `caddy` service from all compose templates
- Backend and Frontend now expose ports directly (8000 and 4321)


## Infrastructure & Inter-Service Communication

### Retry Logic for Telegram Bot Backend Communication

**Status**: DONE

**Description**: Exponential backoff retry for transient backend errors.

**Implementation** (`services/tg_bot/src/main.py`):
- `_sync_user_with_backend` now accepts `max_retries` (default: 3) and `initial_delay` (default: 1.0s)
- Retries on `httpx.ConnectError` (backend unavailable) and 5xx status codes
- Exponential backoff: 1s → 2s → 4s
- No retry on 4xx client errors (fail immediately)\n- Logging of retry attempts for debugging\n\n**Tests** (`services/tg_bot/tests/unit/test_command_handler.py`):\n- `test_sync_user_retries_on_5xx` — 5xx triggers retries, succeeds after recovery\n- `test_sync_user_retries_on_connect_error` — ConnectError triggers retries\n- `test_sync_user_no_retry_on_4xx` — 4xx errors do NOT retry\n- `test_sync_user_exhausts_all_retries` — returns None after all retries fail

### Unified Retry Logic in Generated Clients

**Status**: DONE

**Description**: Add configurable retry logic to generated REST clients (from `ClientsGenerator`).

**Implementation**:
- Modified `framework/templates/codegen/client.py.j2` to include `_request_with_retry` method
- Generated clients now accept `max_retries` (default: 3) and `initial_delay` (default: 1.0s)
- Retry behavior:
  - Retries on `httpx.ConnectError` (service unavailable)
  - Retries on 5xx status codes (server errors)
  - No retry on 4xx client errors (fails immediately)
  - Exponential backoff: 1s → 2s → 4s
- Simplified `tg_bot/src/main.py` from ~80 lines to ~35 lines by using built-in client retry
- Tests in `tests/tooling/test_client_generator.py` verify generated code structure

**Usage**:
```python
# Default retry (3 attempts, 1s initial delay)
async with BackendClient() as client:
    user = await client.create_user(payload)

# Custom retry settings
async with BackendClient(max_retries=5, initial_delay=0.5) as client:
    user = await client.get_user(user_id=123)
```

### Spec-First Async Messaging (Queues)

**Status**: IN PROGRESS

**Description**: Support asynchronous messaging via queues.
- **Decision**: We chose **Redis** (Streams) + **FastStream**.
    - **Why**: Fits "Rigidity is Freedom". Single container, strongly typed, spec-first.
- **Goal**: Define topics/events in YAML.
- **Generation**: Auto-generate consumers and producer wrappers using FastStream.
- **Validation**: Ensure messages conform to schemas defined in `models.yaml`.

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
- On `copier copy`, automatically run `make sync-services create` and `make generate-from-spec`

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
1. **Short-term**: Current hybrid approach (Jinja templates + sync markers)
2. **Medium-term**: Keep specs + minimal scaffolds, delete business logic
3. **Long-term**: Pure spec-only after generator maturity (2-3 months)

**Related**: See implementation plan in `.gemini/antigravity/brain/*/implementation_plan.md` for detailed analysis.

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

### Direct Event Publishing for Services

**Status**: DONE

**Description**: Enable services to publish events directly to message broker instead of using REST API intermediaries.

**Implementation**:
- Telegram bot (`tg_bot`) now publishes `command_received` events directly to Redis Streams
- Added `shared` as dependency to tg_bot for access to generated events module
- Broker lifecycle managed via `post_init`/`post_shutdown` hooks in telegram Application
- Backend debug endpoint marked as DEPRECATED (kept for manual testing)
- tg_bot now depends on `redis: service_healthy` in `services.yml`

**Pattern for other services**:
```python
from shared.generated.events import broker, publish_<event_name>
from shared.generated.schemas import <EventModel>

# On startup
await broker.connect()

# Publishing
event = EventModel(...)
await publish_<event_name>(event)

# On shutdown
await broker.close()
```

**Benefits achieved**:
- True decoupling: tg_bot no longer depends on backend for event publishing
- Better performance: Direct Redis operations instead of HTTP round-trips
- Architectural consistency: Events as primary communication pattern

## Quality Assurance & Observability

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

### 1. Updatable Template (Copier)

**Status**: DONE

**Description**: Move from a static repository to a template compatible with `copier` or `cruft`.
- **Why**: To solve the "Upgrade Problem". Users should be able to pull updates from the upstream template (e.g., fixes to Makefile or Dockerfiles) even after they have started developing their services.
- **Goal**: `copier update` should work seamlessly for infrastructure files while respecting user code in `services/`.

**Implementation**:
- `copier.yml` with module selection (backend, tg_bot, notifications, frontend)
- Jinja templates for conditional generation of services, compose files, documentation
- `_skip_if_exists` preserves user code in `services/*/src/app/`, `services/*/src/controllers/`, specs
- `_tasks` clean up unselected modules after copy
- Comprehensive test suite in `tests/copier/` (41 tests covering generation, updates, module exclusion, workflows)
- GitHub workflows templatized with conditional CI matrix based on selected modules
- Template CI workflow (`test-template.yml`) for testing template generation

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
  4. Runs `make sync-services` to update compose files
  5. Updates `.copier-answers.yml` to reflect new module selection

- **Alternative Approach**: Don't delete unselected modules during generation, just exclude them from compose files. Modules remain dormant until explicitly enabled.

- **Considerations**:
  - How to handle template version mismatch (project on v1.0, template on v2.0)?
  - Should module addition trigger compose regeneration automatically?
  - Integration with `copier update` — should it respect manually added modules?

- **Differentiation from Custom Services**:
  - **Predefined modules**: `make add-module` — pulls from template, includes all boilerplate
  - **Custom services**: `make sync-services create` — scaffolds empty service structure

### 2. CLI Wrappers

**Status**: IDEA

**Description**: Wrap `make` commands and boilerplate scripts into a standalone CLI tool (distributed via PyPI or binary).
- **Why**: Simplify usage for both humans and agents.
- **Commands**:
    - `my-framework init` (wraps `copier copy`)
    - `my-framework sync` (wraps `make sync-services`)
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

### Copier Shows "version None"

**Status**: DONE

**Description**: During `copier copy`, the output shows `Copying from template version None` instead of the actual git tag or branch.

**Implementation**: Created git tag `v0.1.0` to enable Copier's automatic version detection. Copier uses git tags sorted by PEP 440 to determine template version. The `vcs_ref` is a CLI argument, not a `copier.yml` setting.

---

## Spec-First Features — Wishlist

### Query Parameters in Domain Specs

**Status**: DONE

**Description**: Add support for query parameters in domain operation specs for filtering and pagination.

**Implementation**:
- Extended `ParamSpec` in `framework/spec/operations.py` with `source: Literal["path", "query"]` and `default` fields
- Updated `OperationContextBuilder` in `framework/generators/context.py` to generate `Query(...)` syntax for query params
- Modified router template (`router.py.j2`) to use `fastapi_source` for parameter FastAPI dependencies
- Modified client template (`client.py.j2`) to separate path and query params, passing query params as `params=` dict
- Added tests in `tests/tooling/test_generators.py` verifying `Query(default=...)` generation

**Example**:
```yaml
list_books:
  output: list[BookRead]
  params:
    - name: status
      type: string
      source: query
      required: false
    - name: limit
      type: int
      source: query
      default: 20
  rest:
    method: GET
    path: ""
```

**Generated Router Code**:
```python
async def list_books(
    status: str = Query(default=None),  # optional query param
    limit: int = Query(default=20),     # query param with default
    session: AsyncSession = Depends(get_db),
    controller: BooksControllerProtocol = Depends(get_controller),
) -> list[BookRead]:
    ...
```

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

### Fix Root-Owned Generated Files

**Status**: DONE
**Priority**: CRITICAL

**Description**: Files generated by `make generate-from-spec` are owned by `root`, causing "Permission Denied" errors when the user tries to edit them in VSCode.

**Root Cause**: The `tooling` container in `compose.tests.unit.yml` runs as root and writes directly to the bind mount.

**Proposed Solution**:
- Add `user: "${HOST_UID:-1000}:${HOST_GID:-1000}"` to `tooling` service in compose files
- Update Makefile to pass `HOST_UID=$(id -u) HOST_GID=$(id -g)` when invoking docker compose

**Workaround**: `sudo chown -R $(id -u):$(id -g) .` after generation

---

### Fix Nullable Field Inheritance in Schema Generation

**Status**: DONE

**Description**: When a field is marked `optional: true` in `models.yaml`, this should propagate to all variants unless overridden.

**Implementation**:
- Added `optional: bool = False` attribute to `FieldSpec` in `framework/spec/models.py`
- `to_json_schema()` now adds `nullable: true` when field has `optional: true`
- `_model_to_schema()` now excludes optional fields from `required` list in all variants
- Added 4 unit tests in `tests/unit/test_spec_models.py`

**Example**:
```yaml
Subscription:
  fields:
    telegram_id:
      type: int
      optional: true  # Makes it `int | None` in ALL variants
  variants:
    Create: {}
    Read: {}  # telegram_id is now nullable here too
```

---


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

### Add `make init` Command

**Status**: TODO

**Description**: New users have to manually run `cp .env.example .env` before any other command. A unified `make init` would improve onboarding.

**Proposed Implementation**:
```makefile
init:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example"; fi
	$(MAKE) sync-services check
```

---

### Document Data Layer Pattern

**Status**: DONE

**Description**: `ARCHITECTURE.md` now includes a comprehensive Data Layer section covering:
- ORM model location (`services/<service>/src/app/models/`)
- Relationship between ORM models and Pydantic schemas (manual mapping)
- Transaction management (`get_async_db()` auto-commit/rollback)
- Migration workflow (`make makemigrations`)
- Repository pattern (recommended but optional)

---

## E2E Testing Issues (Unified Handlers)

### Fix Compose Context for Tooling Service

**Status**: DONE
**Priority**: CRITICAL

**Description**: The `compose.tests.unit.yml.jinja` template has incorrect context and volumes paths for the tooling service. Since compose files are in `infra/`, the context should be `..` not `.`.

**Current (broken)**:
```yaml
tooling:
  build:
    context: .
    dockerfile: tooling/Dockerfile
  volumes:
    - .:/workspace:delegated
```

**Fixed**:
```yaml
tooling:
  build:
    context: ..
    dockerfile: tooling/Dockerfile
  volumes:
    - ..:/workspace:delegated
```

**Impact**: `make generate-from-spec` fails with "tooling/Dockerfile not found".

---

### Router.py Missing get_broker When Using publish_on_success

**Status**: DONE
**Priority**: HIGH

**Description**: When adding `events.publish_on_success` to an operation, the generated `registry.py` requires `get_broker` dependency, but the user's `router.py` doesn't have it.

**Problem**: Breaking change in `create_api_router` signature when any operation gets `publish_on_success`.

**Proposed Solutions**:
1. **Always include get_broker** — even if not used (simple, wasteful)
2. **Update template router.py** — include broker dependency by default
3. **Document migration** — clear instructions on how to add broker to existing projects

---

### Spec Compliance Checker False Positive

**Status**: DONE
**Priority**: MEDIUM

**Description**: The spec compliance checker flags `APIRouter()` in `router.py` as forbidden, even though it's used for health/utility endpoints, not domain logic.

**Solution**: Added whitelist in `enforce_spec_compliance.py` for `router.py` and `health.py` files. Added "Wiring Layer" section to `ARCHITECTURE.md` documenting why these files are manual.

---

### Copier Root-Owned Files in Generated Project

**Status**: DONE
**Priority**: HIGH

**Description**: When generating a project via `copier copy`, some files (especially in `.ruff_cache`) are owned by root, requiring `sudo` to delete or modify.

**Root Cause**: Copier's post-generation tasks (`ruff check --fix`, `ruff format`) run as root inside Docker and create cache files.

**Proposed Solutions**:
1. Add `--no-cache` to ruff commands in `copier.yml` tasks
2. Run `chown` task at the very end of generation
3. Ensure tooling image runs as host user (already has `HOST_UID`/`HOST_GID` support)

**Workaround**: Run `docker run --rm -v "$(pwd):/workspace" alpine chown -R $(id -u):$(id -g) /workspace`

---

### Add E2E CI Job for Unified Handlers

**Status**: TODO
**Priority**: MEDIUM

**Description**: Add a CI job that:
1. Generates a project via copier with dual-transport operations
2. Runs `make generate-from-spec`
3. Runs `make lint`
4. Runs `make tests`

This would catch integration issues between generated code and user templates.

---

### Full Router.py Generation (Eliminate Wiring Layer)

**Status**: IDEA
**Priority**: LOW

**Description**: Currently `router.py` is manual (wiring layer). We could generate it fully from specs, making the framework 100% spec-first even for FastAPI services.

**What would be needed:**
1. Service-level spec (`service.yml`) for config: health endpoints, middleware, DI settings
2. `MainRouterGenerator` — generates `router.py` with controller imports and wiring
3. `HealthGenerator` — generates standard health endpoints
4. Convention-based controller discovery: `controllers/{domain}.py` → `{Domain}Controller`

**Escape hatch:**
```yaml
# service.yml
config:
  custom_wiring: true  # → router.py is not regenerated
```

**Why IDEA (not TODO):**
- This is only needed for FastAPI services (currently just `backend`)
- Current wiring layer is minimal (~30 lines)
- May add complexity for rare edge cases (DI containers, async init)
- Consider implementing when multiple FastAPI services exist

**Related:** Documented current approach in `ARCHITECTURE.md` → "Wiring Layer" section.

---

### Consider `make format` in Copier Tasks

**Status**: IDEA
**Priority**: LOW

**Description**: Templates should produce clean, lint-passing output. Currently we achieve this by carefully crafting templates with correct import ordering and whitespace control.

**Future consideration**: For complex templates with heavy Jinja conditionals, maintaining perfect formatting may become burdensome. Consider adding `make format` to copier post-generation tasks:

```yaml
_tasks:
  # ... module cleanup ...
  - "cp .env.example infra/.env"
  - "make format || true"
  - "chown ..."
```

**Trade-offs**:
- ✅ Guaranteed clean output regardless of template complexity
- ✅ Consistent with dev workflow
- ❌ Slower first-time generation (+30-60s for Docker build)
- ❌ Requires Docker available during `copier copy`

**Current approach**: Templates are manually maintained to produce valid Python. Tests in `tests/copier/test_generated_code_quality.py` verify lint compliance.

---

### Fix Compose Context for Test Services

**Status**: TODO
**Priority**: HIGH

**Description**: The `compose.tests.unit.yml.jinja` template has incorrect `context: .` for test services. Since compose files are in `infra/`, the context `.` resolves to `infra/` instead of project root.

**Current (broken)**:
```yaml
tg-bot-tests-unit:
  build:
    context: .
    dockerfile: services/tg_bot/Dockerfile
```

**Problem**: When running `docker compose -f infra/compose.tests.unit.yml run tg-bot-tests-unit`, Docker looks for `infra/services/tg_bot/Dockerfile` which doesn't exist.

**Proposed Solutions**:

1. **Change context to parent directory**:
```yaml
tg-bot-tests-unit:
  build:
    context: ..
    dockerfile: services/tg_bot/Dockerfile
```

2. **Use --project-directory flag** (in Makefile):
```makefile
tests:
	docker compose -f infra/compose.tests.unit.yml --project-directory . run ...
```

**Note**: The `tooling` service already has `context: ..` (fixed earlier), but test services still have `context: .`.

**Impact**: Docker-based tests fail in coding-worker containers and local development when running from project root.



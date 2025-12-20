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

## Infrastructure & Inter-Service Communication

### Retry Logic for Telegram Bot Backend Communication

**Status**: DONE

**Description**: Exponential backoff retry for transient backend errors.

**Implementation** (`services/tg_bot/src/main.py`):
- `_sync_user_with_backend` now accepts `max_retries` (default: 3) and `initial_delay` (default: 1.0s)
- Retries on `httpx.ConnectError` (backend unavailable) and 5xx status codes
- Exponential backoff: 1s → 2s → 4s
- No retry on 4xx client errors (fail immediately)
- Logging of retry attempts for debugging

**Tests** (`services/tg_bot/tests/unit/test_command_handler.py`):
- `test_sync_user_retries_on_5xx` — 5xx triggers retries, succeeds after recovery
- `test_sync_user_retries_on_connect_error` — ConnectError triggers retries
- `test_sync_user_no_retry_on_4xx` — 4xx errors do NOT retry
- `test_sync_user_exhausts_all_retries` — returns None after all retries fail

### Unified Retry Logic in Generated Clients

**Status**: TODO

**Description**: Add configurable retry logic to generated REST clients (from `ClientsGenerator`).

**Problem**: 
- Current retry implementation is manual in `tg_bot/src/main.py` 
- Each consumer service would need to duplicate this logic
- Violates DRY and "Generation > Context" principle

**Proposed Solution**:
- Add `tenacity` as optional dependency for generated clients
- Configure retry at client init: `BackendClient(max_retries=3, retry_on=[5xx, ConnectError])`
- Smart defaults: retry safe methods (GET), configurable for others
- Alternatively: retry at httpx transport level

**Considerations**:
- POST/PUT with side effects — danger of duplicate actions
- Need to distinguish retryable vs non-retryable errors (5xx vs 4xx)
- Timeout vs connection error handling

### Spec-First Async Messaging (Queues)

**Status**: IN PROGRESS

**Description**: Support asynchronous messaging via queues.
- **Decision**: We chose **Redis** (Streams) + **FastStream**.
    - **Why**: Fits "Rigidity is Freedom". Single container, strongly typed, spec-first.
- **Goal**: Define topics/events in YAML.
- **Generation**: Auto-generate consumers and producer wrappers using FastStream.
- **Validation**: Ensure messages conform to schemas defined in `models.yaml`.

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

**Status**: IDEA

**Description**: Add support for query parameters in domain operation specs for filtering and pagination.

**Example**:
```yaml
list_books:
  output: list[BookRead]
  params:
    - name: status
      type: string
      source: query  # NEW: query vs path
    - name: limit
      type: int
      source: query
      default: 20
  rest:
    method: GET
    path: ""
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


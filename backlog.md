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
- **Implementation**: `framework/validate_specs.py` validates:
  - `models.yaml`: field types, constraints, variant references (exclude/optional)
  - `routers/*.yaml`: HTTP methods, model/variant existence
  - `events.yaml`: message type existence
- **Integration**: Runs as part of `make lint` and available separately via `make validate-specs`.
- **Benefit**: Clear error messages like "Unknown variant 'Patch' for model 'User'" instead of cryptic generation failures.

### Implement Controller Pattern for Generated Routers

**Status**: IN PROGRESS

**Description**: Currently, generated routers contain `raise NotImplementedError`. We need a pattern (e.g., Controller injection or Protocol) to allow implementing logic without editing the generated file, while still satisfying the linter.
- Forbid manual `APIRouter` definitions that don't match spec interfaces.

## Infrastructure & Inter-Service Communication

### Retry Logic for Telegram Bot Backend Communication

**Status**: TODO

**Description**: Add retry logic to Telegram bot's `handle_command` function to handle temporary backend unavailability.
- **Problem**: When backend is reloading (dev mode with `--reload`), it becomes temporarily unavailable, causing command sending to fail.
- **Solution**: Implement exponential backoff retry mechanism in `services/tg_bot/src/main.py` for `handle_command` function.
- **Details**: 
  - Retry on `httpx.ConnectError` and `httpx.HTTPStatusError` (5xx errors)
  - Use exponential backoff (e.g., 1s, 2s, 4s) with max 3 retries
  - Log retry attempts for debugging
  - Only retry transient errors, not client errors (4xx)

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

**Status**: TODO

**Description**: Enable services to publish events directly to message broker instead of using REST API intermediaries.
- **Problem**: Currently, Telegram bot makes REST calls to backend's debug endpoint to publish commands, violating event-driven architecture principles and creating unnecessary dependencies.
- **Solution**: Give all services direct access to Redis broker for publishing events, remove debug REST endpoint as unnecessary intermediary.
- **Details**:
  - Update shared events module to be available to all services
  - Modify Telegram bot to publish `command_received` events directly to Redis Streams
  - Remove debug REST endpoint from backend
  - Update event specifications to define which services can publish which events
  - Ensure proper broker connection lifecycle in all services that publish events
- **Benefits**:
  - True decoupling: Services don't depend on each other through REST
  - Improved reliability: No single point of failure through backend API
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
- Comprehensive test suite in `tests/copier/` (32 tests covering generation, updates, module exclusion)

### 2. CLI Wrappers

**Status**: IDEA

**Description**: Wrap `make` commands and boilerplate scripts into a standalone CLI tool (distributed via PyPI or binary).
- **Why**: Simplify usage for both humans and agents.
- **Commands**:
    - `my-framework init` (wraps `copier copy`)
    - `my-framework sync` (wraps `make sync-services`)
    - `my-framework update` (wraps `copier update`)

### 3. MCP Server for Agents

**Status**: IDEA

**Description**: Build a Model Context Protocol (MCP) server that exposes the framework's capabilities to AI agents.
- **Why**: Agents shouldn't just "edit files"; they should call high-level tools to manage the project lifecycle.
- **Functionality**:
    - `initialize_project(spec)`
    - `add_service(name, type)`
    - `update_infrastructure()`

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

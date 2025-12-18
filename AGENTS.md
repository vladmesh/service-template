# Agents Playbook / Documentation Map

This file serves as the entry point for AI Agents exploring the repository. Use this map to load only the context you need.

## 🗺 Navigation

- **Philosophy & Goals:** `MANIFESTO.md` (Read this first to understand *why*)
- **System Design:** `ARCHITECTURE.md` (Read this to understand *how*)
- **Rules & Standards:** `CONTRIBUTING.md` (Strict rules for coding)
- **Service Registry:** `services.yml` (List of all active services)

## ⚠️ CRITICAL: Environment Variables

**STRICT RULE: NO DEFAULT VALUES FOR ENVIRONMENT VARIABLES**

- **NEVER** use default values in `os.getenv("VAR", "default")` or similar patterns
- If a required environment variable is missing, the application **MUST FAIL IMMEDIATELY** with a clear error
- Use this pattern:
  ```python
  value = os.getenv("REQUIRED_VAR")
  if not value:
      raise RuntimeError("REQUIRED_VAR is not set; please add it to your environment variables")
  ```
- **Rationale:** Default values hide configuration errors and cause silent failures in production
- **Example:** `REDIS_URL`, `API_BASE_URL`, `DATABASE_URL` must all be explicitly configured
- All required environment variables must be documented in `.env.example`

## 📂 Service Modules

Detailed documentation for each service can be found in its respective directory. Only load these if you are working on that specific service.

- **Backend:** `services/backend/AGENTS.md`
- **Telegram Bot:** `services/tg_bot/AGENTS.md`
- **Infrastructure:** `infra/README.md` (if available)

## 🛠 Operational Commands

Agents should interact with the system primarily through `make`.

- **Check State:** `make sync-services check`
- **Scaffold:** `make sync-services create`
- **Verify:** `make lint && make tests`
- **Generate Code:** `make generate-from-spec`
- **Generate OpenAPI:** `make openapi` (Outputs to `services/<service>/docs/openapi.json`)

## 🧠 Critical Project Knowledge

### Shared Module Architecture

The `shared/` directory contains generated code and shared models used by ALL services. Key facts:

1. **Generated Code Location:** `shared/shared/generated/` contains auto-generated:
   - `schemas.py` - Pydantic models from `shared/spec/models.yaml`
   - `events.py` - FastStream publishers/subscribers from `shared/spec/events.yaml`
   - `routers/` - FastAPI routers from `shared/spec/routers/*.yaml`
   - `protocols.py` - Controller interfaces

2. **Volume Mounts for Development:**
   - Services install `shared` as a Python package during Docker build
   - **CRITICAL:** In development, mount `../shared:/app/shared:delegated` in `infra/compose.dev.yml`
   - Without this mount, services use stale code from the build, not live changes
   - Required for BOTH backend and any Python services that import from `shared`

3. **Code Generation Workflow:**
   ```bash
   # 1. Edit specs in shared/spec/
   # 2. Regenerate code
   make generate-from-spec
   # 3. Services automatically pick up changes (if volume mounted)
   ```

### FastStream Event Architecture

**Broker Lifecycle Management:**

1. **Global Broker Instance:** `shared/shared/generated/events.py` exports a singleton `broker` object
2. **Connection Required:** The broker MUST be connected before publishing/subscribing:
   ```python
   # In application lifespan (e.g., services/backend/src/app/lifespan.py)
   from shared.generated.events import broker
   
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       await broker.connect()  # CRITICAL: Connect on startup
       yield
       await broker.close()    # CRITICAL: Close on shutdown
   ```
3. **Publishing Events:** Use generated publisher functions:
   ```python
   from shared.generated.events import publish_command_received
   from shared.generated.schemas import CommandReceived
   
   event = CommandReceived(...)
   await publish_command_received(event)  # Requires broker to be connected
   ```

4. **Subscribing to Events:** Use FastStream decorators in service controllers:
   ```python
   from shared.generated.events import broker
   
   router = broker.router()
   
   @router.subscriber("event_name")
   async def handle_event(msg: EventModel):
       # Handle event
   ```

### Direct Event Publishing Pattern

Services should publish events directly to Redis, NOT through REST API intermediaries.

**Example (Telegram Bot):**
```python
from shared.generated.events import broker, publish_command_received
from shared.generated.schemas import CommandReceived

# For python-telegram-bot, use post_init/post_shutdown hooks:
async def post_init(application: Application) -> None:
    await broker.connect()

async def post_shutdown(application: Application) -> None:
    await broker.close()

# In handler:
event = CommandReceived(command=cmd, args=args, user_id=user_id, timestamp=datetime.now(UTC))
await publish_command_received(event)
```

**Required Setup:**
1. Add `shared` as dependency in service's `pyproject.toml`
2. Add `redis: service_healthy` to `depends_on` in `services.yml`
3. Ensure `REDIS_URL` is available in environment

### Service Creation Pattern

1. **Add to Registry:** Define in `services.yml` with appropriate type:
   - `python-fastapi` - HTTP API with FastAPI/uvicorn (exposes port 8000)
   - `python-faststream` - Event-driven worker with FastStream (no HTTP port)
   - `node` - Node.js service (exposes port 4321)
   - `default` - Generic container placeholder
2. **Optional Compose Options:** Add `depends_on` and `profiles` in `services.yml`:
   ```yaml
   - name: my_service
     type: python-faststream
     description: My event worker
     depends_on:
       redis: service_healthy
     profiles:
       - workers
   ```
3. **Scaffold:** Run `make sync-services create` to generate:
   - Service directory structure
   - Dockerfile (generated from type-specific template)
   - Docker Compose integration (auto-generated blocks in compose files)
4. **Development Setup:** Volume mounts are auto-configured in `infra/compose.dev.yml`

### Common Pitfalls

1. **Missing Broker Connection:** Publishing events without `broker.connect()` → `AssertionError`
2. **Stale Shared Code:** Forgetting volume mount → services use old generated code
3. **Type Mismatches:** Code generator now supports `list[type]` but verify complex types
4. **Timezone Awareness:** Use `datetime.now(UTC)` for Pydantic `AwareDatetime` fields
5. **Dockerfile Validation:** `sync_services.py` validates COPY sources - use proper Poetry patterns

# Plan: Direct Event Publishing for Telegram Bot

**Status**: Ready for Implementation  
**Backlog Item**: "Direct Event Publishing for Services"  
**Estimated Effort**: 4-6 hours

## Problem Statement

Currently, the Telegram bot (`tg_bot`) publishes events through a REST API intermediary:

```
tg_bot → HTTP POST /debug/command → backend → Redis Streams
```

This violates event-driven architecture principles:
- Creates unnecessary coupling between tg_bot and backend
- Single point of failure (backend must be up for events to flow)
- HTTP overhead instead of direct Redis operations
- Architectural inconsistency with MANIFESTO.md principles

## Target Architecture

```
tg_bot → Redis Streams (direct publish)
backend → Redis Streams (subscribe)
```

Each service that needs to publish events will have direct access to the Redis broker.

---

## Implementation Plan

### Phase 1: Prepare tg_bot for Direct Publishing

#### 1.1 Add shared dependency to tg_bot

**File**: `services/tg_bot/pyproject.toml`

Add `shared` as a path dependency:
```toml
[tool.poetry.dependencies]
# ... existing deps
shared = { path = "../../shared", develop = true }
```

**Verification**: `poetry lock` succeeds in tg_bot directory.

#### 1.2 Update tg_bot Dockerfile

**File**: `services/tg_bot/Dockerfile`

The Dockerfile already copies `shared/` into the image. Verify that:
- `COPY shared ./shared` is present (already exists)
- `shared` package is installed during poetry install

No changes expected if template is correct.

#### 1.3 Add REDIS_URL to tg_bot environment

**Files**:
- `.env.example` — add `REDIS_URL=redis://redis:6379`
- `.env.example.jinja` — add templated version
- `infra/compose.base.yml` — ensure tg_bot has access to redis network
- `infra/compose.base.yml.jinja` — update jinja template

**Changes to compose.base.yml** for tg_bot service:
```yaml
tg_bot:
  # ... existing config
  depends_on:
    redis:
      condition: service_healthy
    backend:
      condition: service_started  # keep for user sync
  environment:
    REDIS_URL: redis://redis:6379
```

**Changes to services.yml**:
```yaml
- name: tg_bot
  # ... existing config
  depends_on:
    backend: service_started
    redis: service_healthy  # ADD THIS
```

Run `make sync-services` to regenerate compose files.

---

### Phase 2: Implement Direct Publishing in tg_bot

#### 2.1 Create broker lifecycle management

**New file**: `services/tg_bot/src/broker.py`

```python
"""Broker lifecycle management for tg_bot."""
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from shared.generated.events import broker


@asynccontextmanager
async def broker_lifespan() -> AsyncGenerator[None, None]:
    """Connect and disconnect broker around application lifecycle."""
    await broker.connect()
    try:
        yield
    finally:
        await broker.close()
```

#### 2.2 Refactor main.py to use direct publishing

**File**: `services/tg_bot/src/main.py`

Changes:
1. Remove `DEBUG_ENDPOINT` constant
2. Remove `httpx` import (keep for user sync with backend)
3. Add imports from `shared.generated.events` and `shared.generated.schemas`
4. Modify `handle_command()` to publish directly
5. Integrate broker lifecycle with telegram Application

**Before**:
```python
DEBUG_ENDPOINT: Final[str] = f"{API_BASE_URL}/debug/command"

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... 
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(DEBUG_ENDPOINT, json=payload)
```

**After**:
```python
from shared.generated.events import broker, publish_command_received
from shared.generated.schemas import CommandReceived

async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_user = update.effective_user
    if telegram_user is None:
        return

    command = update.message.text or "/command"
    args = context.args or []

    event = CommandReceived(
        command=command,
        args=args,
        user_id=telegram_user.id,
        timestamp=datetime.now(UTC),
    )

    try:
        await publish_command_received(event)
        await update.message.reply_text("Command published!")
    except Exception:
        LOGGER.exception("Failed to publish command event")
        await update.message.reply_text("Failed to send command.")
```

#### 2.3 Integrate broker with Application lifecycle

**File**: `services/tg_bot/src/main.py`

Use `post_init` and `post_shutdown` hooks:

```python
async def post_init(application: Application) -> None:
    """Connect to Redis broker after application init."""
    await broker.connect()
    LOGGER.info("Connected to Redis broker")


async def post_shutdown(application: Application) -> None:
    """Disconnect from Redis broker on shutdown."""
    await broker.close()
    LOGGER.info("Disconnected from Redis broker")


def build_application() -> Application:
    application = (
        ApplicationBuilder()
        .token(_get_token())
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    # ... handlers
    return application
```

---

### Phase 3: Clean Up Backend

#### 3.1 Remove debug endpoint (OPTIONAL - can keep for testing)

**Decision point**: The debug endpoint may be useful for:
- Manual testing via curl/Postman
- Integration tests that don't have Redis access

**Option A**: Keep debug endpoint (recommended for now)
- No changes to backend
- Add deprecation comment

**Option B**: Remove debug endpoint completely
- Delete `services/backend/spec/debug.yaml`
- Delete `services/backend/src/controllers/debug.py`
- Remove debug router from `services/backend/src/app/api/router.py`
- Delete `services/backend/tests/unit/test_debug.py`
- Run `make generate-from-spec` to clean up generated files

**Recommendation**: Option A — keep endpoint but mark as deprecated. Remove in future iteration.

#### 3.2 Add deprecation notice (if keeping endpoint)

**File**: `services/backend/src/controllers/debug.py`

```python
import warnings

class DebugController(DebugControllerProtocol):
    """
    DEPRECATED: This endpoint exists for testing purposes only.
    Services should publish events directly to Redis.
    """
    # ...
```

---

### Phase 4: Update Tests

#### 4.1 Update tg_bot unit tests

**File**: `services/tg_bot/tests/unit/test_main.py` (new file)

```python
"""Unit tests for tg_bot command handling."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_broker():
    """Mock the broker connection."""
    with patch("services.tg_bot.src.main.broker") as mock:
        mock.connect = AsyncMock()
        mock.close = AsyncMock()
        yield mock


@pytest.fixture
def mock_publish():
    """Mock the publish function."""
    with patch("services.tg_bot.src.main.publish_command_received") as mock:
        mock.return_value = None
        yield mock


@pytest.mark.asyncio
async def test_handle_command_publishes_event(mock_publish, mock_broker):
    """Test that handle_command publishes event to Redis."""
    # ... test implementation
    pass


@pytest.mark.asyncio
async def test_handle_command_handles_publish_failure(mock_publish, mock_broker):
    """Test graceful handling of publish failures."""
    mock_publish.side_effect = Exception("Redis connection failed")
    # ... test implementation
    pass
```

#### 4.2 Add integration test for event flow

**File**: `tests/integration/test_event_flow.py` (new file)

This test requires Redis to be available:

```python
"""Integration tests for event publishing flow."""
import asyncio

import pytest
from redis.asyncio import Redis

from shared.generated.schemas import CommandReceived


@pytest.fixture
async def redis_client():
    """Create Redis client for test verification."""
    client = Redis.from_url("redis://redis:6379")
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_tg_bot_publishes_to_redis(redis_client):
    """
    Verify that tg_bot can publish events directly to Redis.
    
    This test simulates the event publishing and verifies
    the message arrives in Redis Streams.
    """
    # Subscribe to command_received stream
    # Publish test event
    # Verify event received
    pass
```

**Note**: Full integration test may require running tg_bot in test mode or directly testing the publish function.

#### 4.3 Update existing tests

**File**: `services/backend/tests/unit/test_debug.py`

Add comment that this tests the deprecated debug endpoint:

```python
"""
Tests for the debug endpoint.

NOTE: This endpoint is DEPRECATED. Services should publish events directly.
These tests remain to ensure backward compatibility during transition.
"""
```

---

### Phase 5: Update Documentation

#### 5.1 Update backlog.md

**File**: `backlog.md`

Change status of "Direct Event Publishing for Services" from `TODO` to `DONE`:

```markdown
### Direct Event Publishing for Services

**Status**: DONE

**Description**: Enable services to publish events directly to message broker...

**Implementation**: 
- tg_bot now publishes `command_received` events directly to Redis Streams
- Backend debug endpoint marked as deprecated
- All services with event publishing needs should follow this pattern
```

#### 5.2 Update AGENTS.md

**File**: `AGENTS.md`

Add section about event publishing pattern:

```markdown
### Event Publishing Pattern

Services can publish events directly to Redis Streams:

1. Add `shared` as dependency in `pyproject.toml`
2. Import broker and publish functions from `shared.generated.events`
3. Connect broker in service lifecycle (startup/shutdown)
4. Use generated `publish_*` functions

Example:
```python
from shared.generated.events import broker, publish_command_received

# On startup
await broker.connect()

# Publishing
await publish_command_received(event)

# On shutdown
await broker.close()
```
```

#### 5.3 Update tg_bot/AGENTS.md

**File**: `services/tg_bot/AGENTS.md`

Document the new architecture:

```markdown
## Event Publishing

The bot publishes events directly to Redis Streams (not via backend REST API):

- **Broker**: FastStream RedisBroker from `shared.generated.events`
- **Events**: `command_received` for bot commands
- **Lifecycle**: Broker connects on app init, disconnects on shutdown

Required environment variables:
- `REDIS_URL` — Redis connection string (e.g., `redis://redis:6379`)
- `TELEGRAM_BOT_TOKEN` — Bot token from @BotFather
- `API_BASE_URL` — Backend URL (still needed for user sync)
```

---

### Phase 6: Verification & Testing

#### 6.1 Run linters and type checks

```bash
make lint
make typecheck
```

#### 6.2 Run unit tests

```bash
make tests suite=tg_bot
make tests suite=backend
```

#### 6.3 Run integration tests

```bash
make tests suite=integration
```

#### 6.4 Manual verification

1. Start services with tg profile:
   ```bash
   COMPOSE_PROFILES=tg make dev-start
   ```

2. Send `/command test arg1 arg2` to the bot

3. Verify in Redis that event was published:
   ```bash
   docker compose exec redis redis-cli XREAD STREAMS command_received 0
   ```

4. Check backend logs for event consumption (if subscriber is implemented)

---

## Rollback Plan

If issues arise:

1. Revert tg_bot/src/main.py to use HTTP endpoint
2. Remove REDIS_URL from tg_bot environment
3. Keep debug endpoint in backend

The debug endpoint remains as fallback, so rollback is safe.

---

## Future Improvements

After this change is stable:

1. Remove debug endpoint from backend completely
2. Add retry logic with exponential backoff for Redis publishing
3. Add health check for Redis connection in tg_bot
4. Consider adding dead letter queue for failed publishes

---

## Files Changed Summary

| File | Change Type |
|------|-------------|
| `services/tg_bot/pyproject.toml` | Modify |
| `services/tg_bot/src/main.py` | Modify |
| `services/tg_bot/tests/unit/test_main.py` | Create |
| `services.yml` | Modify |
| `.env.example` | Modify |
| `.env.example.jinja` | Modify |
| `infra/compose.base.yml` | Auto-generated |
| `infra/compose.base.yml.jinja` | Modify |
| `tests/integration/test_event_flow.py` | Create |
| `services/backend/src/controllers/debug.py` | Modify (deprecation notice) |
| `services/backend/tests/unit/test_debug.py` | Modify (add note) |
| `backlog.md` | Modify |
| `AGENTS.md` | Modify |
| `services/tg_bot/AGENTS.md` | Modify |

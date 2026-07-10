"""E2E checks for generated REST routers."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
import sys
from types import ModuleType
from typing import Any

import pytest

from framework.generators.protocols import ProtocolsGenerator
from framework.generators.routers import RoutersGenerator
from framework.generators.schemas import SchemasGenerator
from framework.spec.loader import load_specs


def _write_package(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "__init__.py").write_text("", encoding="utf-8")


class FakeAPIRouter:
    def __init__(self, *, prefix: str = "", tags: list[str] | None = None) -> None:
        self.prefix = prefix
        self.tags = tags or []
        self.routes: list[dict[str, Any]] = []

    def _route(self, method: str, path: str, **kwargs: Any) -> Callable[[Any], Any]:
        def decorator(handler: Any) -> Any:
            self.routes.append(
                {
                    "method": method,
                    "path": path,
                    "handler": handler,
                    **kwargs,
                }
            )
            return handler

        return decorator

    def get(self, path: str, **kwargs: Any) -> Callable[[Any], Any]:
        return self._route("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Callable[[Any], Any]:
        return self._route("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Callable[[Any], Any]:
        return self._route("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Callable[[Any], Any]:
        return self._route("DELETE", path, **kwargs)


def _install_router_import_fakes(monkeypatch: pytest.MonkeyPatch) -> None:
    fastapi = ModuleType("fastapi")
    fastapi.APIRouter = FakeAPIRouter
    fastapi.Body = lambda default: default
    fastapi.Depends = lambda dependency: dependency
    fastapi.Path = lambda default: default
    fastapi.Query = lambda default=None: default
    monkeypatch.setitem(sys.modules, "fastapi", fastapi)

    faststream = ModuleType("faststream")
    faststream_redis = ModuleType("faststream.redis")
    faststream_redis.RedisBroker = object
    monkeypatch.setitem(sys.modules, "faststream", faststream)
    monkeypatch.setitem(sys.modules, "faststream.redis", faststream_redis)

    sqlalchemy = ModuleType("sqlalchemy")
    sqlalchemy_ext = ModuleType("sqlalchemy.ext")
    sqlalchemy_asyncio = ModuleType("sqlalchemy.ext.asyncio")
    sqlalchemy_asyncio.AsyncSession = object
    monkeypatch.setitem(sys.modules, "sqlalchemy", sqlalchemy)
    monkeypatch.setitem(sys.modules, "sqlalchemy.ext", sqlalchemy_ext)
    monkeypatch.setitem(sys.modules, "sqlalchemy.ext.asyncio", sqlalchemy_asyncio)


def test_generated_rest_router_publishes_to_subscriber(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A new REST domain works after codegen without a manual router."""
    root = tmp_path / "repo"
    _write_package(root / "shared")
    _write_package(root / "shared" / "shared")
    _write_package(root / "shared" / "shared" / "generated")
    _write_package(root / "services")
    _write_package(root / "services" / "backend")
    _write_package(root / "services" / "backend" / "src")
    _write_package(root / "services" / "backend" / "src" / "generated")
    (root / "shared" / "spec").mkdir(parents=True)
    (root / "services" / "backend" / "spec").mkdir(parents=True)

    (root / "shared" / "spec" / "models.yaml").write_text(
        """
models:
  Widget:
    fields:
      id:
        type: int
        readonly: true
      name:
        type: string
    variants:
      Create: {}
      Read: {}
""",
        encoding="utf-8",
    )
    (root / "services" / "backend" / "spec" / "widgets.yaml").write_text(
        """
domain: widgets
config:
  rest:
    prefix: "/widgets"
    tags: ["widgets"]

operations:
  create_widget:
    input: WidgetCreate
    output: WidgetRead
    rest:
      method: POST
      path: ""
      status: 201
    events:
      publish_on_success: widget_created
""",
        encoding="utf-8",
    )

    specs = load_specs(root)
    SchemasGenerator(specs, root).generate()
    ProtocolsGenerator(specs, root).generate()
    RoutersGenerator(specs, root).generate()

    _install_router_import_fakes(monkeypatch)
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "shared"))
    try:
        from services.backend.src.generated.routers.widgets import create_router
        from shared.generated.schemas import WidgetCreate, WidgetRead

        class FakeController:
            async def create_widget(self, session: object, payload: WidgetCreate) -> WidgetRead:
                return WidgetRead(id=1, name=payload.name)

        class FakeSession:
            def __init__(self) -> None:
                self.commits = 0

            async def commit(self) -> None:
                self.commits += 1

        class FakeBroker:
            def __init__(self) -> None:
                self.subscribers: dict[str, list[Any]] = {}

            def subscriber(self, channel: str):
                def register(handler):
                    self.subscribers.setdefault(channel, []).append(handler)
                    return handler

                return register

            async def publish(self, message: Any, channel: str) -> None:
                for handler in self.subscribers.get(channel, []):
                    await handler(message)

        session = FakeSession()
        broker = FakeBroker()
        received: list[WidgetRead] = []

        @broker.subscriber("widget_created")
        async def handle_widget_created(event: WidgetRead) -> None:
            received.append(event)

        router = create_router(
            get_session=lambda: session,
            get_controller=FakeController,
            get_broker=lambda: broker,
        )
        assert router.prefix == "/widgets"

        post_route = next(route for route in router.routes if route["method"] == "POST")
        response = asyncio.run(
            post_route["handler"](
                payload=WidgetCreate(name="router"),
                session=session,
                controller=FakeController(),
                broker=broker,
            )
        )

        assert response.model_dump() == {"id": 1, "name": "router"}
        assert session.commits == 0
        assert [event.model_dump() for event in received] == [{"id": 1, "name": "router"}]
    finally:
        sys.path.remove(str(root / "shared"))
        sys.path.remove(str(root))

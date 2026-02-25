"""Router for debug."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from services.backend.src.controllers.debug import DebugController
from services.backend.src.core.db import get_async_db
from services.backend.src.generated.protocols import DebugControllerProtocol
from shared.generated.schemas import (
    CommandReceived,
    CommandReceivedCreate,
)

router = APIRouter(
    prefix="/debug",
    tags=["debug"],
)


def get_controller() -> DebugControllerProtocol:
    return DebugController()


@router.post(
    "/command",
    response_model=CommandReceived,
    status_code=202,
)
async def command(
    payload: CommandReceivedCreate = Body(...),  # noqa: B008
    session: AsyncSession = Depends(get_async_db),  # noqa: B008
    controller: DebugControllerProtocol = Depends(get_controller),  # noqa: B008
) -> CommandReceived:
    return await controller.command(
        session=session,
        payload=payload,
    )

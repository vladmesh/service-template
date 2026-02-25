"""Router for users."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from services.backend.src.controllers.users import UsersController
from services.backend.src.core.db import get_async_db
from services.backend.src.generated.protocols import UsersControllerProtocol
from shared.generated.schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
)

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


def get_controller() -> UsersControllerProtocol:
    return UsersController()


@router.post(
    "",
    response_model=UserRead,
    status_code=201,
)
async def create_user(
    payload: UserCreate = Body(...),  # noqa: B008
    session: AsyncSession = Depends(get_async_db),  # noqa: B008
    controller: UsersControllerProtocol = Depends(get_controller),  # noqa: B008
) -> UserRead:
    return await controller.create_user(
        session=session,
        payload=payload,
    )


@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=200,
)
async def get_user(
    user_id: int = Path(...),  # noqa: B008
    session: AsyncSession = Depends(get_async_db),  # noqa: B008
    controller: UsersControllerProtocol = Depends(get_controller),  # noqa: B008
) -> UserRead:
    return await controller.get_user(
        session=session,
        user_id=user_id,
    )


@router.put(
    "/{user_id}",
    response_model=UserRead,
    status_code=200,
)
async def update_user(
    user_id: int = Path(...),  # noqa: B008
    payload: UserUpdate = Body(...),  # noqa: B008
    session: AsyncSession = Depends(get_async_db),  # noqa: B008
    controller: UsersControllerProtocol = Depends(get_controller),  # noqa: B008
) -> UserRead:
    return await controller.update_user(
        session=session,
        user_id=user_id,
        payload=payload,
    )


@router.delete(
    "/{user_id}",
    status_code=204,
)
async def delete_user(
    user_id: int = Path(...),  # noqa: B008
    session: AsyncSession = Depends(get_async_db),  # noqa: B008
    controller: UsersControllerProtocol = Depends(get_controller),  # noqa: B008
) -> None:
    return await controller.delete_user(
        session=session,
        user_id=user_id,
    )

# AUTO-GENERATED FROM shared/spec/rest.yaml – DO NOT EDIT MANUALLY

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from sqlalchemy.orm import Session

from services.backend.src.app.api.deps import get_db

# Import the controller.
# Note: We assume the controller module is named after the router but located in
# services.backend.src.controllers. This might need adjustment if we support multiple services.
from services.backend.src.controllers import users as controller
from shared.generated.schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
)

router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.post(
    "/",
    response_model=UserRead,
    status_code=201,
)
async def create_user(
    session: Annotated[Session, Depends(get_db)],
    payload: Annotated[UserCreate, Body(...)],
) -> UserRead:
    """Handler for create_user"""
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
    session: Annotated[Session, Depends(get_db)],
    user_id: Annotated[int, Path(...)],
) -> UserRead:
    """Handler for get_user"""
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
    session: Annotated[Session, Depends(get_db)],
    user_id: Annotated[int, Path(...)],
    payload: Annotated[UserUpdate, Body(...)],
) -> UserRead:
    """Handler for update_user"""
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
    session: Annotated[Session, Depends(get_db)],
    user_id: Annotated[int, Path(...)],
) -> None:
    """Handler for delete_user"""
    return await controller.delete_user(
        session=session,
        user_id=user_id,
    )

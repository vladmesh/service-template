# AUTO-GENERATED FROM shared/spec/rest.yaml – DO NOT EDIT MANUALLY

from __future__ import annotations

from fastapi import APIRouter

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
    payload: UserCreate,
) -> UserRead:
    """Handler for create_user"""
    # TODO: implement
    raise NotImplementedError


@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=200,
)
async def get_user(
    user_id: int,
) -> UserRead:
    """Handler for get_user"""
    # TODO: implement
    raise NotImplementedError


@router.put(
    "/{user_id}",
    response_model=UserRead,
    status_code=200,
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
) -> UserRead:
    """Handler for update_user"""
    # TODO: implement
    raise NotImplementedError


@router.delete(
    "/{user_id}",
    status_code=204,
)
async def delete_user(
    user_id: int,
) -> None:
    """Handler for delete_user"""
    # TODO: implement
    raise NotImplementedError

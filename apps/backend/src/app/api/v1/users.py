"""User CRUD API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...models import User
from ...repositories import UserRepository
from ...schemas import UserCreate, UserRead, UserUpdate
from ..deps import get_db

router = APIRouter(prefix="/users", tags=["users"])
SessionDep = Annotated[Session, Depends(get_db)]


def _get_repo(session: Session) -> UserRepository:
    return UserRepository(session)


def _get_user_or_404(repo: UserRepository, user_id: int) -> User:
    user = repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _ensure_unique_telegram(
    repo: UserRepository, telegram_id: int, current_id: int | None = None
) -> None:
    existing = repo.get_by_telegram_id(telegram_id)
    if existing is not None and existing.id != current_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Telegram user already exists"
        )


def _to_schema(user: User) -> UserRead:
    return UserRead.from_orm(user)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, session: SessionDep) -> UserRead:
    repo = _get_repo(session)
    _ensure_unique_telegram(repo, payload.telegram_id)
    created = repo.create(payload)
    return _to_schema(created)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, session: SessionDep) -> UserRead:
    repo = _get_repo(session)
    user = _get_user_or_404(repo, user_id)
    return _to_schema(user)


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, session: SessionDep) -> UserRead:
    repo = _get_repo(session)
    user = _get_user_or_404(repo, user_id)
    data = payload.dict(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes supplied")
    if payload.telegram_id is not None:
        _ensure_unique_telegram(repo, payload.telegram_id, current_id=user_id)
    updated = repo.update(user, payload)
    return _to_schema(updated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, session: SessionDep) -> None:
    repo = _get_repo(session)
    user = _get_user_or_404(repo, user_id)
    repo.delete(user)


__all__ = ["router"]

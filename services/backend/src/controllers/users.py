from __future__ import annotations

from datetime import UTC

from fastapi import HTTPException, status
from shared.generated.protocols import UsersControllerProtocol
from shared.generated.schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
)
from sqlalchemy.orm import Session

from services.backend.src.app.models import User
from services.backend.src.app.repositories import UserRepository


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
    # Fix for SQLite returning naive datetimes in tests
    if user.created_at and user.created_at.tzinfo is None:
        user.created_at = user.created_at.replace(tzinfo=UTC)
    if user.updated_at and user.updated_at.tzinfo is None:
        user.updated_at = user.updated_at.replace(tzinfo=UTC)
    return UserRead.model_validate(user, from_attributes=True)


class UsersController(UsersControllerProtocol):
    """
    Implementation of UsersControllerProtocol.
    """

    async def create_user(
        self,
        session: Session,
        payload: UserCreate,
    ) -> UserRead:
        """
        Handler for create_user
        """
        repo = _get_repo(session)
        _ensure_unique_telegram(repo, payload.telegram_id)
        created = repo.create(payload)
        return _to_schema(created)

    async def get_user(
        self,
        session: Session,
        user_id: int,
    ) -> UserRead:
        """
        Handler for get_user
        """
        repo = _get_repo(session)
        user = _get_user_or_404(repo, user_id)
        return _to_schema(user)

    async def update_user(
        self,
        session: Session,
        user_id: int,
        payload: UserUpdate,
    ) -> UserRead:
        """
        Handler for update_user
        """
        repo = _get_repo(session)
        user = _get_user_or_404(repo, user_id)
        data = payload.model_dump(exclude_unset=True)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="No changes supplied"
            )
        if payload.telegram_id is not None:
            _ensure_unique_telegram(repo, payload.telegram_id, current_id=user.id)
        updated = repo.update(user, payload)
        return _to_schema(updated)

    async def delete_user(
        self,
        session: Session,
        user_id: int,
    ) -> None:
        """
        Handler for delete_user
        """
        repo = _get_repo(session)
        user = _get_user_or_404(repo, user_id)
        repo.delete(user)

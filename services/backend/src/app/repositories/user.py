"""User repository helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User
from ..schemas import UserCreate, UserUpdate


class UserRepository:
    """Data access methods for users."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, payload: UserCreate) -> User:
        user = User(**payload.model_dump())
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def update(self, user: User, payload: UserUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(user, field, value)
        self.session.commit()
        self.session.refresh(user)
        return user

    def delete(self, user: User) -> None:
        self.session.delete(user)
        self.session.commit()


__all__ = ["UserRepository"]

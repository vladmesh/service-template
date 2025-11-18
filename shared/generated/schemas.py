# AUTO-GENERATED FROM shared/spec/models.yaml – DO NOT EDIT MANUALLY

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class User(BaseModel):
    """Base model for User."""

    created_at: datetime
    id: int
    is_admin: bool = Field(default=False)
    telegram_id: int = Field(..., ge=0)
    updated_at: datetime

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    """Variant Create for User."""

    is_admin: bool = Field(default=False)
    telegram_id: int = Field(..., ge=0)

    class Config:
        orm_mode = True


class UserRead(User):
    """Variant Read for User."""

    pass


class UserUpdate(BaseModel):
    """Variant Update for User."""

    is_admin: bool | None = None
    telegram_id: int | None = Field(default=None, ge=0)

    class Config:
        orm_mode = True

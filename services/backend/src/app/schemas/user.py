"""Pydantic schemas for user endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Shared fields for user payloads."""

    telegram_id: int = Field(..., ge=0)
    is_admin: bool = False


class UserCreate(UserBase):
    """Schema for creating a user."""


class UserUpdate(BaseModel):
    """Schema for updating existing users."""

    telegram_id: int | None = Field(default=None, ge=0)
    is_admin: bool | None = None


class UserRead(UserBase):
    """Response schema with metadata."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


__all__ = ["UserCreate", "UserUpdate", "UserRead"]

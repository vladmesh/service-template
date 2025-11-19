"""Database engine and session management."""

from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .settings import get_settings

settings = get_settings()
async_engine = create_async_engine(settings.async_database_url, future=True, echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, autoflush=False, autocommit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class ORMBase(Base):
    """Common columns shared by all persisted models."""

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional scope around a series of async operations."""

    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

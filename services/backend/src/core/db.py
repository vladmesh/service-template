"""Database engine and session management."""

from collections.abc import Generator
from datetime import datetime

from sqlalchemy import DateTime, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .settings import get_settings

settings = get_settings()
engine = create_engine(settings.sync_database_url, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


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


def get_db() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

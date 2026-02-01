"""Async SQLAlchemy database setup."""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import DATABASE_PATH


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


def get_database_url() -> str:
    """Get the SQLite database URL, ensuring the data directory exists."""
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path.resolve()}"


engine = create_async_engine(
    get_database_url(),
    echo=False,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """Dependency for getting async database sessions."""
    async with async_session() as session:
        yield session


def get_session():
    """Context manager for getting async database sessions outside of FastAPI routes."""
    return async_session()

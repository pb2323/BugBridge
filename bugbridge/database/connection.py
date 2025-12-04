"""
Database Connection Management

Async SQLAlchemy engine and session factory setup.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

# Load .env file if it exists
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

DATABASE_URL_ENV_VAR = "DATABASE_URL"
DEFAULT_DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/bugbridge"

_engine = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_database_url() -> str:
    """Get database URL from environment variable or use default."""
    return os.getenv(DATABASE_URL_ENV_VAR, DEFAULT_DATABASE_URL)


def get_engine():
    """Create or return existing async engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_database_url(),
            echo=False,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create or return async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """Async dependency for acquiring a database session."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


@asynccontextmanager
async def get_session_context() -> AsyncIterator[Session]:
    """Async context manager for database session usage.

    This wraps the async generator in an `asynccontextmanager` so it can be
    used with `async with get_session_context() as session:` across the codebase.
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


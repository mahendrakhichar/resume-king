"""Async SQLAlchemy engine and session factory for Neon PostgreSQL."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
import asyncpg

# Monkeypatch asyncpg.connect to strip out the 'channel_binding' parameter.
# This prevents TypeErrors when newer SQLAlchemy versions connect to Postgres using older asyncpg versions.
_original_connect = asyncpg.connect

async def _patched_connect(*args, **kwargs):
    kwargs.pop("channel_binding", None)
    return await _original_connect(*args, **kwargs)

asyncpg.connect = _patched_connect

from config.settings import settings


db_url = settings.database_url
if "sslmode=" in db_url:
    db_url = db_url.replace("sslmode=", "ssl=")

engine = create_async_engine(
    db_url,
    echo=settings.app_debug,
    pool_pre_ping=True,      # Essential for Neon scale-to-zero
    pool_recycle=300,         # Recycle stale connections
    pool_size=5,
    max_overflow=10,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables (for development only; use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Dispose of the engine connection pool."""
    await engine.dispose()

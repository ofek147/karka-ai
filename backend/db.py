"""
Database engine + session factory (async SQLAlchemy + asyncpg).
DATABASE_URL is required — set it in Railway environment variables.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from .config import settings


def _build_url(raw: str) -> str:
    """Normalize Railway postgres:// → postgresql+asyncpg://"""
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw.startswith("postgresql://") and "+asyncpg" not in raw:
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw


class Base(DeclarativeBase):
    pass


def get_engine():
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required. Set it in Railway environment variables.")
    return create_async_engine(_build_url(settings.database_url), echo=False)


engine = get_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    async with SessionLocal() as session:
        yield session


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

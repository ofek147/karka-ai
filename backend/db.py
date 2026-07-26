"""
Database engine + session factory (async SQLAlchemy + asyncpg).

Railway provides DATABASE_URL automatically when Postgres addon is added.
Local dev: set DATABASE_URL in .env, or leave empty to use SQLite fallback.
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
    url = _build_url(settings.database_url) if settings.database_url else None
    if not url:
        # SQLite fallback — use /tmp (always writable in containers + local)
        import os
        os.makedirs("/tmp/karka", exist_ok=True)
        url = "sqlite+aiosqlite:////tmp/karka/karka.db"
    return create_async_engine(url, echo=False)


engine = get_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    async with SessionLocal() as session:
        yield session


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

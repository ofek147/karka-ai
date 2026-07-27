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
    """Create all tables on startup + migrate existing tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migrate leads table — add intelligence columns if missing
        migrations = [
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS score INTEGER DEFAULT 0",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_active TIMESTAMPTZ",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS total_questions INTEGER DEFAULT 0",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS total_sessions INTEGER DEFAULT 0",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS source VARCHAR(200)",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS topics JSONB DEFAULT '[]'",
            "ALTER TABLE leads ADD COLUMN IF NOT EXISTS parcels JSONB DEFAULT '[]'",
        ]
        from sqlalchemy import text
        for sql in migrations:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass  # Column already exists or DB doesn't support IF NOT EXISTS

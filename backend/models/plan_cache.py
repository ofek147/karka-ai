"""
SQLAlchemy ORM model for plan PDF cache.

Stores extracted text from mavat plan PDFs so we don't re-download
and re-parse on every report generation. TTL is enforced by the service.
"""

from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


class PlanCache(Base):
    __tablename__ = "plan_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Plan identifier — mavat plan number (e.g. "1013/03/50")
    plan_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # Extracted text from PDF (full or truncated to DB limits)
    pdf_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Source URL that was fetched
    pdf_url: Mapped[str] = mapped_column(String(500), nullable=True)

    # When cached — used for TTL eviction
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )

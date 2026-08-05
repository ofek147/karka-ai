"""
SQLAlchemy ORM model for report job queue.

status flow: pending → processing → done | failed
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


class ReportJob(Base):
    __tablename__ = "report_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Parcel
    gush: Mapped[int] = mapped_column(Integer, nullable=False)
    helka: Mapped[int] = mapped_column(Integer, nullable=False)

    # Contact — at least one required (validated in router)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Queue state
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )  # pending | processing | done | failed

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Error details on failure
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

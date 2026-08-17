"""
SQLAlchemy ORM model for plan PDF cache.

Stores extracted text from mavat plan PDFs so we don't re-download
and re-parse on every report generation. TTL is enforced by the service.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base


class PlanCache(Base):
    __tablename__ = "plan_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Plan identifier — mavat plan number (e.g. "1013/03/50")
    plan_number: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # Extracted text from PDF (full raw text)
    pdf_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Claude summary — free text (legacy, kept for compat)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Claude summary — structured JSON (שלב 1 output: total_units, plan_size_dunam, warnings, positives...)
    summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source URL that was fetched
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # OCR metadata — populated when PDF was scanned (not digital text)
    # ocr_confidence: 0-100 (Tesseract word-level confidence average), None if digital
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # extraction_method: "digital" | "ocr" | "none"
    extraction_method: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # When cached
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )

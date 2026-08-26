"""
plan_cache_service.py — get/set plan PDF text + Claude summary from DB cache.

Cache invalidation: based on upstream receiving_date (last-modified proxy).
If receiving_date is newer than cached_at → cache is stale → re-fetch.
"""

from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.plan_cache import PlanCache


async def get_cached_plan(
    db: AsyncSession,
    plan_number: str,
    last_modified: Optional[datetime.datetime] = None,
) -> Optional[PlanCache]:
    """
    Return cached PlanCache row, or None if:
    - Not in cache
    - last_modified is newer than cached_at (plan changed upstream)
    """
    result = await db.execute(
        select(PlanCache).where(PlanCache.plan_number == plan_number)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None

    if last_modified is not None:
        cached_at = row.cached_at.replace(tzinfo=None)
        lm = last_modified.replace(tzinfo=None)
        if lm > cached_at:
            await db.execute(delete(PlanCache).where(PlanCache.plan_number == plan_number))
            await db.commit()
            return None

    return row


async def get_cached_plan_text(
    db: AsyncSession,
    plan_number: str,
    last_modified: Optional[datetime.datetime] = None,
) -> Optional[str]:
    """Return cached pdf_text only."""
    row = await get_cached_plan(db, plan_number, last_modified)
    return row.pdf_text if row else None


async def get_cached_plan_summary(
    db: AsyncSession,
    plan_number: str,
) -> Optional[str]:
    """
    Return cached Claude summary (free text, legacy field).
    No staleness check — this is a legacy field not used in the main report flow.
    Use get_cached_plan_summary_json (with last_modified) for the active path.
    """
    result = await db.execute(
        select(PlanCache).where(PlanCache.plan_number == plan_number)
    )
    row = result.scalar_one_or_none()
    return row.summary if row else None


async def set_cached_plan_text(
    db: AsyncSession,
    plan_number: str,
    pdf_text: str,
    pdf_url: Optional[str] = None,
    ocr_confidence: Optional[float] = None,
    extraction_method: Optional[str] = None,
) -> None:
    """Insert or replace cached PDF text. Preserves existing summary if present."""
    result = await db.execute(
        select(PlanCache).where(PlanCache.plan_number == plan_number)
    )
    existing = result.scalar_one_or_none()

    now = datetime.datetime.utcnow()
    if existing:
        # Update text + timestamp + OCR metadata, keep summary
        await db.execute(
            update(PlanCache)
            .where(PlanCache.plan_number == plan_number)
            .values(
                pdf_text=pdf_text,
                pdf_url=pdf_url,
                ocr_confidence=ocr_confidence,
                extraction_method=extraction_method,
                cached_at=now,
            )
        )
    else:
        db.add(PlanCache(
            plan_number=plan_number,
            pdf_text=pdf_text,
            pdf_url=pdf_url,
            ocr_confidence=ocr_confidence,
            extraction_method=extraction_method,
            cached_at=now,
        ))
    await db.commit()


async def set_cached_plan_summary(
    db: AsyncSession,
    plan_number: str,
    summary: str,
) -> None:
    """Save Claude summary (free text, legacy) for a plan."""
    await db.execute(
        update(PlanCache)
        .where(PlanCache.plan_number == plan_number)
        .values(summary=summary)
    )
    await db.commit()


async def get_cached_plan_summary_json(
    db: AsyncSession,
    plan_number: str,
    last_modified: Optional[datetime.datetime] = None,
) -> Optional[str]:
    """
    החזר סיכום JSON מובנה (שלב 1) מה-cache.

    אם last_modified מסופק ו-receiving_date ב-iplan חדש יותר מה-cache:
    מחזיר None — ה-summary_json יחשב כ-stale ו-re-extraction יורץ בהמשך ה-flow.
    אם last_modified לא מסופק (None) — מחזיר כל מה שב-cache בלי בדיקה.
    """
    result = await db.execute(
        select(PlanCache).where(PlanCache.plan_number == plan_number)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None

    if last_modified is not None:
        cached_at = row.cached_at.replace(tzinfo=None)
        lm = last_modified.replace(tzinfo=None)
        if lm > cached_at:
            print(f"[plan_cache] summary_json stale for {plan_number} — iplan={lm} > cached={cached_at}, forcing re-extraction")
            return None  # stale — יאלץ re-extraction בהמשך ה-flow

    return row.summary_json


async def set_cached_plan_summary_json(
    db: AsyncSession,
    plan_number: str,
    summary_json: str,
) -> None:
    """שמור סיכום JSON מובנה לתכנית (שלב 1 output)."""
    await db.execute(
        update(PlanCache)
        .where(PlanCache.plan_number == plan_number)
        .values(summary_json=summary_json)
    )
    await db.commit()

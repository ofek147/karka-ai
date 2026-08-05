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
    """Return cached Claude summary only (no invalidation — summary is stable)."""
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
) -> None:
    """Insert or replace cached PDF text. Preserves existing summary if present."""
    result = await db.execute(
        select(PlanCache).where(PlanCache.plan_number == plan_number)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update text + timestamp, keep summary
        await db.execute(
            update(PlanCache)
            .where(PlanCache.plan_number == plan_number)
            .values(
                pdf_text=pdf_text,
                pdf_url=pdf_url,
                cached_at=datetime.datetime.utcnow(),
            )
        )
    else:
        db.add(PlanCache(
            plan_number=plan_number,
            pdf_text=pdf_text,
            pdf_url=pdf_url,
            cached_at=datetime.datetime.utcnow(),
        ))
    await db.commit()


async def set_cached_plan_summary(
    db: AsyncSession,
    plan_number: str,
    summary: str,
) -> None:
    """Save Claude summary for a plan (plan_text must already exist)."""
    await db.execute(
        update(PlanCache)
        .where(PlanCache.plan_number == plan_number)
        .values(summary=summary)
    )
    await db.commit()

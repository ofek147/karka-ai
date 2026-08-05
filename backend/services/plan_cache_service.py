"""
plan_cache_service.py — get/set plan PDF text from DB cache.

TTL: 30 days (plans don't change often; re-fetch if stale).
"""

from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.plan_cache import PlanCache

async def get_cached_plan_text(
    db: AsyncSession,
    plan_number: str,
    last_modified: Optional[datetime.datetime] = None,
) -> Optional[str]:
    """
    Return cached PDF text for a plan, or None if:
    - Not in cache
    - last_modified is provided and newer than cached_at (plan changed upstream)
    """
    result = await db.execute(
        select(PlanCache).where(PlanCache.plan_number == plan_number)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None

    # If caller knows the upstream last-modified date, invalidate if stale
    if last_modified is not None:
        cached_at = row.cached_at.replace(tzinfo=None)
        lm = last_modified.replace(tzinfo=None)
        if lm > cached_at:
            await db.execute(delete(PlanCache).where(PlanCache.plan_number == plan_number))
            await db.commit()
            return None

    return row.pdf_text


async def set_cached_plan_text(
    db: AsyncSession,
    plan_number: str,
    pdf_text: str,
    pdf_url: Optional[str] = None,
) -> None:
    """
    Insert or replace cached PDF text for a plan.
    """
    # Delete existing (upsert via delete+insert — compatible with asyncpg)
    await db.execute(delete(PlanCache).where(PlanCache.plan_number == plan_number))
    db.add(PlanCache(
        plan_number=plan_number,
        pdf_text=pdf_text,
        pdf_url=pdf_url,
        cached_at=datetime.datetime.utcnow(),
    ))
    await db.commit()

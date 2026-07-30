"""
parcel_cache.py — In-memory + Redis cache for parcel data.
Falls back to in-memory if Redis unavailable.
"""
from typing import Optional
from ..models.parcel import ParcelFullData

# In-memory fallback (process-local, cleared on restart)
_mem_cache: dict = {}


async def get_parcel_cached(gush: int, helka: int) -> Optional[ParcelFullData]:
    """Get parcel from cache (Redis → memory → None)."""
    key = f"parcel:{gush}:{helka}"

    # Try Redis first
    try:
        from .redis_cache import get_cached
        data = await get_cached(key)
        if data:
            return ParcelFullData(**data)
    except Exception:
        pass

    # Fallback: memory
    if key in _mem_cache:
        return _mem_cache[key]

    return None


async def set_parcel_cached(gush: int, helka: int, parcel: ParcelFullData) -> None:
    """Store parcel in cache (Redis + memory)."""
    key = f"parcel:{gush}:{helka}"

    try:
        from .redis_cache import set_cached
        await set_cached(key, parcel.model_dump())
    except Exception:
        pass

    _mem_cache[key] = parcel

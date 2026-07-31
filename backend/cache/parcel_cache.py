"""
parcel_cache.py — In-memory cache for parcel data with 24h TTL.
Data refreshes automatically after 24 hours to avoid stale govmap results.
"""
import time
from typing import Optional
from ..models.parcel import ParcelFullData

TTL_SECONDS = 86400  # 24 hours

# { key: (ParcelFullData, expires_at) }
_mem_cache: dict = {}


async def get_parcel_cached(gush: int, helka: int) -> Optional[ParcelFullData]:
    key = f"parcel:{gush}:{helka}"
    entry = _mem_cache.get(key)
    if entry:
        data, expires_at = entry
        if time.time() < expires_at:
            return data
        del _mem_cache[key]  # expired
    return None


async def set_parcel_cached(gush: int, helka: int, parcel: ParcelFullData) -> None:
    key = f"parcel:{gush}:{helka}"
    _mem_cache[key] = (parcel, time.time() + TTL_SECONDS)

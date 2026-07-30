"""
parcel.py — REST endpoints for parcel data (non-chat).
"""
from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..services.parcel_service import get_parcel_data
from ..cache.parcel_cache import get_parcel_cached, set_parcel_cached
from ..models.parcel import ParcelFullData

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/api/parcel", response_model=ParcelFullData)
@limiter.limit("30/minute")
async def get_parcel(request: Request, gush: int, helka: int):
    cached = await get_parcel_cached(gush, helka)
    if cached:
        return cached

    data = await get_parcel_data(gush, helka)
    await set_parcel_cached(gush, helka, data)
    return data

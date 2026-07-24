from fastapi import FastAPI, HTTPException
from .clients.iplan_client import get_plans_by_centroid
from .clients.govmap_client import get_parcel_geometry
from .cache.redis_cache import get_cached, set_cached
from .models.parcel import ParcelFullData
from .config import settings

app = FastAPI(title="karka-ai API", version="0.1.0")


@app.get("/api/parcel", response_model=ParcelFullData)
async def get_parcel(gush: int, helka: int):
    cache_key = f"parcel:{gush}:{helka}"

    cached = await get_cached(cache_key)
    if cached:
        cached["source"] = "cache"
        return ParcelFullData(**cached)

    geometry = await get_parcel_geometry(gush, helka)

    plans = []
    if geometry.centroid_x is not None and geometry.centroid_y is not None:
        plans = await get_plans_by_centroid(geometry.centroid_x, geometry.centroid_y)

    source = "mock" if (settings.mock_mode or not settings.govmap_token) else "live"
    result = ParcelFullData(
        gush=gush,
        helka=helka,
        geometry=geometry,
        plans=plans,
        source=source,
    )

    await set_cached(cache_key, result.model_dump())
    return result


@app.get("/health")
async def health():
    return {"status": "ok", "mock_mode": settings.mock_mode}

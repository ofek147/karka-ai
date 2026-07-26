from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .clients.iplan_client import get_plans_by_centroid
from .clients.govmap_client import get_parcel_geometry
from .cache.redis_cache import get_cached, set_cached
from .models.parcel import ParcelFullData, AskRequest, AskResponse
from .services.claude_service import ask_claude
from .config import settings
from .routers import leads as leads_router
from .routers import chat as chat_router
from .routers import auth as auth_router
from .db import init_db
from .models import lead_model  # noqa: F401 — registers ORM model with Base
from .models import chat_model  # noqa: F401
from .models import auth_model  # noqa: F401

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="karka-ai API", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://karka-ai.co.il",
        "https://www.karka-ai.co.il",
        "https://karka-ai.pages.dev",  # Cloudflare Pages preview
        "https://karka-ai.vercel.app",
        "http://localhost:3000",  # local dev
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(leads_router.router)
app.include_router(chat_router.router)
app.include_router(auth_router.router)


@app.get("/api/parcel", response_model=ParcelFullData)
@limiter.limit("30/minute")
async def get_parcel(request: Request, gush: int, helka: int):
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


@app.post("/api/ask", response_model=AskResponse)
@limiter.limit("10/minute")
async def ask_about_parcel(request: Request, req: AskRequest):
    try:
        cache_key = f"parcel:{req.gush}:{req.helka}"
        cached = await get_cached(cache_key)

        if cached:
            cached["source"] = "cache"
            parcel_data = ParcelFullData(**cached)
        else:
            geometry = await get_parcel_geometry(req.gush, req.helka)
            plans = []
            if geometry.centroid_x and geometry.centroid_y:
                plans = await get_plans_by_centroid(geometry.centroid_x, geometry.centroid_y)
            source = "mock" if (settings.mock_mode or not settings.govmap_token) else "live"
            parcel_data = ParcelFullData(
                gush=req.gush, helka=req.helka,
                geometry=geometry, plans=plans,
                source=source,
            )
            await set_cached(cache_key, parcel_data.model_dump())

        answer = await ask_claude(req.gush, req.helka, parcel_data, req.question)

        return AskResponse(
            gush=req.gush,
            helka=req.helka,
            question=req.question,
            answer=answer,
            source=parcel_data.source,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok", "mock_mode": settings.mock_mode}

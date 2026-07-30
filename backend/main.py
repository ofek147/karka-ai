from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from .config import settings
from .routers import leads as leads_router
from .routers import chat as chat_router
from .routers import auth as auth_router
from .routers import admin as admin_router
from .routers import parcel as parcel_router
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
app.include_router(admin_router.router)
app.include_router(parcel_router.router)


@app.get("/health")
async def health():
    return {"status": "ok", "mock_mode": settings.mock_mode}

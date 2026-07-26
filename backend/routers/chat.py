import re
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import SessionLocal as async_session
from ..models.chat_model import ChatSession, ChatMessage, LeadScore
from ..services.claude_service import chat_claude
from ..clients.iplan_client import get_plans_by_centroid
from ..clients.govmap_client import get_parcel_geometry
from ..models.parcel import ParcelFullData
from ..config import settings

router = APIRouter()

GUSH_HELKA_RE = re.compile(r"גוש\s*[:\-]?\s*(\d+)[,\s]+חלקה\s*[:\-]?\s*(\d+)", re.UNICODE)
BUDGET_RE = re.compile(r"תקציב|מיליון|להשקיע|השקעה", re.UNICODE)
ROI_RE = re.compile(r"תשואה|ROI|רווח|רנטביליות", re.UNICODE)


class MessageItem(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    messages: List[MessageItem]


class ChatResponse(BaseModel):
    answer: str
    session_id: str


async def _update_lead_score(user_id: str, messages: List[MessageItem], db: AsyncSession):
    if not user_id:
        return

    all_text = " ".join(m.content for m in messages)
    score_delta = 0
    signals = {}

    if GUSH_HELKA_RE.search(all_text):
        score_delta += 30
        signals["parcel_query"] = True

    if BUDGET_RE.search(all_text):
        score_delta += 25
        signals["budget_mention"] = True

    if ROI_RE.search(all_text):
        score_delta += 20
        signals["roi_mention"] = True

    if len(messages) > 10:
        score_delta += 15
        signals["deep_engagement"] = True

    # +10 for being registered (user_id exists) — added on first call
    signals["registered"] = True
    score_delta += 10

    result = await db.execute(select(LeadScore).where(LeadScore.user_id == user_id))
    lead = result.scalar_one_or_none()

    if lead:
        new_score = lead.score + score_delta
        new_signals = {**lead.signals, **signals}
        await db.execute(
            update(LeadScore)
            .where(LeadScore.user_id == user_id)
            .values(score=new_score, signals=new_signals)
        )
    else:
        db.add(LeadScore(user_id=user_id, score=score_delta, signals=signals))

    await db.commit()


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: Request, req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages array is empty")

    last_user_msg = next((m for m in reversed(req.messages) if m.role == "user"), None)
    if not last_user_msg:
        raise HTTPException(status_code=400, detail="no user message found")

    # Detect gush/helka in any message
    parcel_context = ""
    all_text = " ".join(m.content for m in req.messages)
    match = GUSH_HELKA_RE.search(all_text)
    if match:
        try:
            gush, helka = int(match.group(1)), int(match.group(2))
            geometry = await get_parcel_geometry(gush, helka)
            plans = []
            if geometry.centroid_x and geometry.centroid_y:
                plans = await get_plans_by_centroid(geometry.centroid_x, geometry.centroid_y)
            source = "mock" if (settings.mock_mode or not settings.govmap_token) else "live"
            parcel_data = ParcelFullData(gush=gush, helka=helka, geometry=geometry, plans=plans, source=source)
            from ..services.claude_service import build_parcel_context
            parcel_context = build_parcel_context(gush, helka, parcel_data)
        except Exception:
            pass  # If parcel fetch fails, continue without it

    try:
        answer = await chat_claude([m.model_dump() for m in req.messages], parcel_context)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Persist session + messages if user is registered
    session_id = req.session_id or str(uuid4())
    async with async_session() as db:
        if req.user_id:
            # Upsert session
            result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
            session = result.scalar_one_or_none()
            if not session:
                # Auto-title from first user message
                title = last_user_msg.content[:40] + ("..." if len(last_user_msg.content) > 40 else "")
                db.add(ChatSession(id=session_id, user_id=req.user_id, title=title))

            # Save only the latest user message + assistant answer (avoid duplicates)
            db.add(ChatMessage(session_id=session_id, role="user", content=last_user_msg.content))
            db.add(ChatMessage(session_id=session_id, role="assistant", content=answer))
            await db.commit()

            # Update lead score
            await _update_lead_score(req.user_id, req.messages, db)

    return ChatResponse(answer=answer, session_id=session_id)


@router.get("/api/sessions/{user_id}")
async def get_sessions(user_id: str):
    async with async_session() as db:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        sessions = result.scalars().all()
        return [{"id": s.id, "title": s.title, "created_at": s.created_at, "updated_at": s.updated_at}
                for s in sessions]


@router.get("/api/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    async with async_session() as db:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        messages = result.scalars().all()
        return [{"role": m.role, "content": m.content, "created_at": m.created_at}
                for m in messages]

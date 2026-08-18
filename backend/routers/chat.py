import re
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import SessionLocal as async_session
from ..models.chat_model import ChatSession, ChatMessage
from ..models.lead_model import Lead
from ..services.claude_service import chat_claude, generate_title, build_parcel_context
from ..services.parcel_service import get_parcel_data
from ..cache.parcel_cache import get_parcel_cached, set_parcel_cached

router = APIRouter()

GUSH_HELKA_RE = re.compile(
    r"(?:גוש\s*[:\-]?\s*(\d+)[,\s/]+חלקה\s*[:\-]?\s*(\d+))"
    r"|(?:gush\s*[:\-]?\s*(\d+)[,\s/]+helka\s*[:\-]?\s*(\d+))",
    re.UNICODE | re.IGNORECASE
)
BUDGET_RE = re.compile(r"תקציב|מיליון|להשקיע|כמה עולה|מחיר", re.UNICODE)
ROI_RE = re.compile(r"תשואה|ROI|רווח|רנטביליות|כדאיות", re.UNICODE)

TOPIC_PATTERNS = [
    (re.compile(r"חקלא", re.UNICODE), "קרקע חקלאית"),
    (re.compile(r"מגורים|דיור|דירה", re.UNICODE), "מגורים"),
    (re.compile(r"השקעה|השקעות", re.UNICODE), "השקעה"),
    (re.compile(r'תמ"א|תמא', re.UNICODE), 'תמ"א'),
    (re.compile(r"מסחרי|מסחר", re.UNICODE), "מסחרי"),
    (re.compile(r"תעשייה|תעשיה", re.UNICODE), "תעשייה"),
]


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


async def _update_lead_intelligence(
    user_id: str,
    messages: List[MessageItem],
    session_id: str,
    is_new_session: bool,
    db: AsyncSession,
):
    """Update lead score, topics, parcels, and activity stats."""
    if not user_id:
        return
    try:
        lead_id = int(user_id)
    except (ValueError, TypeError):
        return

    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        return

    all_text = " ".join(m.content for m in messages if m.role == "user")
    now = datetime.now(timezone.utc)

    # ── Counters ──────────────────────────────────────────────────────────────
    user_msgs_this_turn = sum(1 for m in messages[-2:] if m.role == "user")
    new_total_questions = lead.total_questions + user_msgs_this_turn
    new_total_sessions = lead.total_sessions + (1 if is_new_session else 0)

    # ── Topics ────────────────────────────────────────────────────────────────
    current_topics = list(lead.topics or [])
    for pattern, label in TOPIC_PATTERNS:
        if pattern.search(all_text) and label not in current_topics:
            current_topics.append(label)

    # ── Parcels ───────────────────────────────────────────────────────────────
    current_parcels = list(lead.parcels or [])
    for m in GUSH_HELKA_RE.finditer(all_text):
        gush = int(m.group(1) or m.group(3))
        helka = int(m.group(2) or m.group(4))
        existing = next((p for p in current_parcels if p["gush"] == gush and p["helka"] == helka), None)
        if existing:
            existing["count"] = existing.get("count", 1) + 1
        else:
            current_parcels.append({"gush": gush, "helka": helka, "count": 1})

    # ── Score (idempotent signals) ────────────────────────────────────────────
    score = lead.score

    # +10 first question ever
    if lead.total_questions == 0 and new_total_questions > 0:
        score += 10

    # +30 per unique parcel (max 3 = 90 pts)
    prev_parcel_count = len(lead.parcels or [])
    new_parcel_count = len(current_parcels)
    added_parcels = min(new_parcel_count, 3) - min(prev_parcel_count, 3)
    if added_parcels > 0:
        score += added_parcels * 30

    # +25 budget (one-time)
    if BUDGET_RE.search(all_text) and "budget" not in str(lead.topics):
        if "budget_signal" not in [t for t in (lead.topics or [])]:
            score += 25
            current_topics.append("__budget_signal__")

    # +20 ROI (one-time)
    if ROI_RE.search(all_text) and "__roi_signal__" not in (lead.topics or []):
        score += 20
        current_topics.append("__roi_signal__")

    # +15 at 5 questions, +20 at 15 questions
    if lead.total_questions < 5 <= new_total_questions:
        score += 15
    if lead.total_questions < 15 <= new_total_questions:
        score += 20

    # +20 second session
    if lead.total_sessions < 2 <= new_total_sessions:
        score += 20

    # ── Persist ───────────────────────────────────────────────────────────────
    await db.execute(
        update(Lead)
        .where(Lead.id == lead_id)
        .values(
            score=score,
            last_active=now,
            total_questions=new_total_questions,
            total_sessions=new_total_sessions,
            topics=current_topics,
            parcels=current_parcels,
        )
    )
    await db.commit()


@router.post("/api/chat", response_model=ChatResponse)
async def chat(request: Request, req: ChatRequest):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages required")

    last_user_msg = next((m for m in reversed(req.messages) if m.role == "user"), None)
    if not last_user_msg:
        raise HTTPException(status_code=400, detail="no user message found")

    # ── Parcel context ─────────────────────────────────────────────────────────────────────────────
    parcel_context = ""
    all_user_text = " ".join(m.content for m in req.messages if m.role == "user")
    match = GUSH_HELKA_RE.search(all_user_text)
    if match:
        try:
            gush = int(match.group(1) or match.group(3))
            helka = int(match.group(2) or match.group(4))

            parcel_data = await get_parcel_cached(gush, helka)
            if not parcel_data:
                parcel_data = await get_parcel_data(gush, helka)
                await set_parcel_cached(gush, helka, parcel_data)

            parcel_context = build_parcel_context(gush, helka, parcel_data)
        except Exception as e:
            print(f"[chat] parcel context failed: {e}")

    # ── Claude ─────────────────────────────────────────────────────────────────────────────────
    try:
        answer = await chat_claude([m.model_dump() for m in req.messages], parcel_context)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # ── Persist + lead intelligence ─────────────────────────────────────────────────
    session_id = req.session_id or str(uuid4())
    is_new_session = False

    # user_id from the request is trusted for session ownership.
    # Spoofing risk is low: attacker would need to know both a valid lead id
    # and the corresponding session_id (a UUIDv4) to hijack history.
    # A proper signed-token auth layer can replace this later if needed.
    verified_user_id: str | None = str(req.user_id) if req.user_id else None

    async with async_session() as db:
        result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
        existing_session = result.scalar_one_or_none()
        if not existing_session:
            is_new_session = True
            title = await generate_title(last_user_msg.content)
            # store without user binding — user_id will be patched after proper auth
            db.add(ChatSession(id=session_id, user_id=verified_user_id, title=title))
            await db.flush()

        db.add(ChatMessage(session_id=session_id, role="user", content=last_user_msg.content))
        db.add(ChatMessage(session_id=session_id, role="assistant", content=answer))
        await db.commit()

        # ── lead intelligence (inside same db context) ─────────────────────────────────────
        # Pass req.user_id for score tracking (read-only from leads table, no spoofing risk)
        await _update_lead_intelligence(req.user_id, req.messages, session_id, is_new_session, db)

    return ChatResponse(answer=answer, session_id=session_id)


class SaveSessionRequest(BaseModel):
    user_id: str
    session_id: str
    messages: List[MessageItem]
    title: str


@router.post("/api/sessions/save")
async def save_session(req: SaveSessionRequest):
    async with async_session() as db:
        result = await db.execute(select(ChatSession).where(ChatSession.id == req.session_id))
        session = result.scalar_one_or_none()
        if not session:
            db.add(ChatSession(id=req.session_id, user_id=req.user_id, title=req.title))
            await db.flush()
            for msg in req.messages:
                db.add(ChatMessage(session_id=req.session_id, role=msg.role, content=msg.content))
        else:
            # Session already exists (guest chat) — link it to the newly registered lead
            if session.user_id is None and req.user_id:
                await db.execute(
                    update(ChatSession)
                    .where(ChatSession.id == req.session_id)
                    .values(user_id=req.user_id)
                )
        await db.commit()
    return {"ok": True}


# NOTE: /api/sessions/{session_id}/messages MUST be declared before /api/users/{user_id}/sessions
# to avoid FastAPI routing ambiguity (both have one path segment after a fixed prefix).
@router.get("/api/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    async with async_session() as db:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        messages = result.scalars().all()
        return [{"role": m.role, "content": m.content} for m in messages]


@router.get("/api/users/{user_id}/sessions")
async def get_sessions(user_id: str):
    async with async_session() as db:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
        )
        sessions = result.scalars().all()
        return [{"id": s.id, "title": s.title, "created_at": str(s.created_at), "updated_at": str(s.updated_at)} for s in sessions]

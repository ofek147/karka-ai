"""
Admin router — lead intelligence dashboard.
# TODO: add admin auth before making this public
"""
from fastapi import APIRouter
from sqlalchemy import select
from ..db import SessionLocal as async_session
from ..models.lead_model import Lead
from ..models.chat_model import ChatSession, ChatMessage

router = APIRouter()


@router.get("/api/admin/leads")
async def get_leads():
    async with async_session() as db:
        result = await db.execute(
            select(Lead).order_by(Lead.score.desc())
        )
        leads = result.scalars().all()
        return [
            {
                "id": l.id,
                "name": l.name,
                "email": l.email,
                "phone": l.phone,
                "score": l.score,
                "topics": [t for t in (l.topics or []) if not t.startswith("__")],
                "parcels": l.parcels or [],
                "total_questions": l.total_questions,
                "total_sessions": l.total_sessions,
                "source": l.source,
                "last_active": l.last_active.isoformat() if l.last_active else None,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in leads
        ]


@router.get("/api/admin/leads/{lead_id}/sessions")
async def get_lead_sessions(lead_id: int):
    async with async_session() as db:
        sessions_result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == str(lead_id))
            .order_by(ChatSession.created_at.desc())
        )
        sessions = sessions_result.scalars().all()

        output = []
        for s in sessions:
            msgs_result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == s.id)
                .order_by(ChatMessage.created_at.asc())
            )
            messages = msgs_result.scalars().all()
            output.append({
                "id": s.id,
                "title": s.title,
                "created_at": str(s.created_at),
                "messages": [{"role": m.role, "content": m.content} for m in messages],
            })

        return output

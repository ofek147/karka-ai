"""
Admin router — lead intelligence dashboard.
Protected by ADMIN_TOKEN env var (Authorization: Bearer <token>).
"""
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from sqlalchemy import select, delete
from ..db import SessionLocal as async_session
from ..models.lead_model import Lead
from ..models.chat_model import ChatSession, ChatMessage
from ..config import settings

router = APIRouter()


def _check_auth(authorization: Optional[str]):
    if not settings.admin_token:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN not configured")
    if authorization != f"Bearer {settings.admin_token}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/api/admin/leads")
async def get_leads(authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    async with async_session() as db:
        result = await db.execute(select(Lead).order_by(Lead.score.desc()))
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
async def get_lead_sessions(lead_id: int, authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
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


@router.delete("/api/admin/leads/{lead_id}")
async def delete_lead(lead_id: int, authorization: Optional[str] = Header(default=None)):
    _check_auth(authorization)
    async with async_session() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        await db.execute(delete(Lead).where(Lead.id == lead_id))
        await db.commit()
    return {"ok": True, "deleted": lead_id}

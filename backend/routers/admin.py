"""
Admin router — lead intelligence dashboard.
Auth: magic link to approved ADMIN_EMAIL only.
Unauthorized attempts trigger an alert email to the admin.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, delete

from ..db import SessionLocal as async_session
from ..models.lead_model import Lead
from ..models.chat_model import ChatSession, ChatMessage
from ..config import settings

router = APIRouter()

# In-memory token store: {token: expiry}
# Simple enough for single-instance; replace with Redis for multi-instance
_admin_tokens: dict[str, datetime] = {}

LINK_TTL_MINUTES = 15
SESSION_TTL_HOURS = 24


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _check_session(admin_session: Optional[str]):
    if not admin_session or admin_session not in _admin_tokens:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if datetime.now(timezone.utc) > _admin_tokens[admin_session]:
        del _admin_tokens[admin_session]
        raise HTTPException(status_code=401, detail="Session expired")


async def _send_alert(attempted_email: str):
    """Alert admin about unauthorized access attempt."""
    if not settings.resend_api_key or not settings.admin_email:
        return
    try:
        import httpx
        await httpx.AsyncClient().post(
            "https://api.resend.com/emails",
            json={
                "from": f"karkAi <noreply@karka-ai.co.il>",
                "to": [settings.admin_email],
                "subject": "⚠️ ניסיון כניסה לא מורשה ל-Admin",
                "html": f"""
<div dir="rtl" style="font-family:sans-serif;max-width:480px;margin:auto;padding:24px">
  <h3 style="color:#ef4444">⚠️ ניסיון כניסה לא מורשה</h3>
  <p>מישהו ניסה להיכנס לדשבורד האדמין של karkAi עם המייל:</p>
  <p style="font-size:18px;font-weight:bold;color:#0d1829;background:#f1f5f9;padding:12px;border-radius:8px">{attempted_email}</p>
  <p style="color:#64748b;font-size:13px">זמן: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
</div>""",
            },
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            timeout=10,
        )
    except Exception:
        pass


# ── Endpoints ─────────────────────────────────────────────────────────────────

class MagicRequest(BaseModel):
    email: str


@router.post("/api/admin/auth/request")
async def request_admin_link(req: MagicRequest):
    email = req.email.strip().lower()

    if not settings.admin_email:
        raise HTTPException(status_code=503, detail="ADMIN_EMAIL not configured")

    if email != settings.admin_email.lower():
        # Unauthorized attempt — alert admin silently
        await _send_alert(email)
        return {"ok": True}  # Don't reveal whether email is approved

    # Generate magic link token
    token = secrets.token_urlsafe(32)
    expiry = datetime.now(timezone.utc) + timedelta(minutes=LINK_TTL_MINUTES)
    _admin_tokens[f"link:{token}"] = expiry

    link = f"{settings.frontend_url}/admin?token={token}"

    try:
        import httpx
        await httpx.AsyncClient().post(
            "https://api.resend.com/emails",
            json={
                "from": "karkAi <noreply@karka-ai.co.il>",
                "to": [email],
                "subject": "קישור כניסה לדשבורד karkAi",
                "html": f"""
<div dir="rtl" style="font-family:sans-serif;max-width:480px;margin:auto;padding:24px">
  <h2 style="color:#0d1829">kark<span style="color:#c4a044;font-style:italic">A</span>i Admin</h2>
  <p>לחץ להתחברות לדשבורד:</p>
  <a href="{link}" style="display:inline-block;background:#c4a044;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;margin:16px 0">
    כניסה לאדמין
  </a>
  <p style="color:#64748b;font-size:12px">הקישור בתוקף ל-{LINK_TTL_MINUTES} דקות.</p>
</div>""",
            },
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            timeout=10,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")

    return {"ok": True}


@router.get("/api/admin/auth/verify")
async def verify_admin_token(token: str):
    link_key = f"link:{token}"
    if link_key not in _admin_tokens:
        raise HTTPException(status_code=401, detail="קישור לא תקין או פג תוקף")
    if datetime.now(timezone.utc) > _admin_tokens[link_key]:
        del _admin_tokens[link_key]
        raise HTTPException(status_code=401, detail="קישור פג תוקף")

    # Exchange link token for session token
    del _admin_tokens[link_key]
    session_token = secrets.token_urlsafe(32)
    _admin_tokens[session_token] = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)

    response = JSONResponse({"ok": True, "session": session_token})
    return response


# ── Protected routes ──────────────────────────────────────────────────────────

def _auth(authorization: Optional[str]):
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    _check_session(token)


@router.get("/api/admin/leads")
async def get_leads(authorization: Optional[str] = Header(default=None)):
    _auth(authorization)
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
    _auth(authorization)
    async with async_session() as db:
        sessions_result = await db.execute(
            select(ChatSession).where(ChatSession.user_id == str(lead_id)).order_by(ChatSession.created_at.desc())
        )
        sessions = sessions_result.scalars().all()
        output = []
        for s in sessions:
            msgs_result = await db.execute(
                select(ChatMessage).where(ChatMessage.session_id == s.id).order_by(ChatMessage.created_at.asc())
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
    _auth(authorization)
    async with async_session() as db:
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        await db.execute(delete(Lead).where(Lead.id == lead_id))
        await db.commit()
    return {"ok": True, "deleted": lead_id}

"""
Admin router — lead intelligence dashboard.
Auth: magic link to ADMIN_EMAIL only.
Unauthorized attempts → alert email with IP + location.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, delete

from ..db import SessionLocal as async_session
from ..models.lead_model import Lead
from ..models.chat_model import ChatSession, ChatMessage
from ..config import settings

router = APIRouter()

# In-memory session store {token: expiry}. Fine for single-instance Railway.
_tokens: dict[str, datetime] = {}

LINK_TTL  = timedelta(minutes=15)
SESSION_TTL = timedelta(hours=24)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_session(authorization: Optional[str]):
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token or token not in _tokens:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if datetime.now(timezone.utc) > _tokens[token]:
        del _tokens[token]
        raise HTTPException(status_code=401, detail="Session expired")


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


async def _geolocate(ip: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"http://ip-api.com/json/{ip}?fields=country,regionName,city,isp,status")
            data = r.json()
            if data.get("status") == "success":
                return data
    except Exception:
        pass
    return {}


async def _send_alert(email: str, ip: str, geo: dict):
    if not settings.resend_api_key or not settings.admin_email:
        return
    country  = geo.get("country", "—")
    region   = geo.get("regionName", "")
    city     = geo.get("city", "")
    isp      = geo.get("isp", "—")
    location = ", ".join(filter(None, [city, region, country]))
    now      = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = f"""
<div dir="rtl" style="font-family:sans-serif;max-width:500px;margin:auto;padding:28px">
  <h3 style="color:#ef4444;margin-top:0">⚠️ ניסיון כניסה לא מורשה</h3>
  <table style="border-collapse:collapse;width:100%;font-size:14px">
    <tr><td style="padding:8px 0;color:#64748b;width:90px">מייל</td>
        <td style="padding:8px 0;font-weight:600">{email}</td></tr>
    <tr><td style="padding:8px 0;color:#64748b">IP</td>
        <td style="padding:8px 0;font-family:monospace">{ip}</td></tr>
    <tr><td style="padding:8px 0;color:#64748b">מיקום</td>
        <td style="padding:8px 0">{location or "—"}</td></tr>
    <tr><td style="padding:8px 0;color:#64748b">ISP</td>
        <td style="padding:8px 0">{isp}</td></tr>
    <tr><td style="padding:8px 0;color:#64748b">זמן</td>
        <td style="padding:8px 0">{now}</td></tr>
  </table>
</div>"""

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                "https://api.resend.com/emails",
                json={"from": "karkAi <noreply@karka-ai.co.il>",
                      "to": [settings.admin_email],
                      "subject": "⚠️ ניסיון כניסה לא מורשה ל-Admin",
                      "html": html},
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            )
    except Exception:
        pass


async def _send_magic_link(email: str, token: str):
    link = f"{settings.frontend_url}/admin?token={token}"
    html = f"""
<div dir="rtl" style="font-family:sans-serif;max-width:480px;margin:auto;padding:28px">
  <h2 style="margin-top:0">kark<span style="color:#c4a044;font-style:italic">A</span>i Admin</h2>
  <p>לחץ להתחברות לדשבורד:</p>
  <a href="{link}" style="display:inline-block;background:#c4a044;color:#fff;padding:12px 28px;
     border-radius:8px;text-decoration:none;font-weight:bold;margin:16px 0">
    כניסה לאדמין
  </a>
  <p style="color:#94a3b8;font-size:12px">הקישור בתוקף ל-15 דקות.</p>
</div>"""

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(
            "https://api.resend.com/emails",
            json={"from": "karkAi <noreply@karka-ai.co.il>",
                  "to": [email],
                  "subject": "קישור כניסה לדשבורד karkAi",
                  "html": html},
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        )
        r.raise_for_status()


# ── Auth endpoints ────────────────────────────────────────────────────────────

class MagicRequest(BaseModel):
    email: str


@router.post("/api/admin/auth/request")
async def request_admin_link(req: MagicRequest, request: Request):
    if not settings.admin_email:
        raise HTTPException(status_code=503, detail="ADMIN_EMAIL not configured")

    email = req.email.strip().lower()

    if email != settings.admin_email.lower():
        ip  = _get_ip(request)
        geo = await _geolocate(ip)
        await _send_alert(email, ip, geo)
        return {"ok": True}  # Don't reveal approval status

    token = secrets.token_urlsafe(32)
    _tokens[f"link:{token}"] = datetime.now(timezone.utc) + LINK_TTL

    try:
        await _send_magic_link(email, token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}")

    return {"ok": True}


@router.get("/api/admin/auth/verify")
async def verify_admin_token(token: str):
    key = f"link:{token}"
    if key not in _tokens or datetime.now(timezone.utc) > _tokens[key]:
        _tokens.pop(key, None)
        raise HTTPException(status_code=401, detail="קישור לא תקין או פג תוקף")

    del _tokens[key]
    session = secrets.token_urlsafe(32)
    _tokens[session] = datetime.now(timezone.utc) + SESSION_TTL
    return JSONResponse({"ok": True, "session": session})


# ── Protected routes ──────────────────────────────────────────────────────────

@router.get("/api/admin/leads")
async def get_leads(authorization: Optional[str] = Header(default=None)):
    _require_session(authorization)
    async with async_session() as db:
        result = await db.execute(select(Lead).order_by(Lead.score.desc()))
        return [
            {
                "id": l.id, "name": l.name, "email": l.email, "phone": l.phone,
                "score": l.score,
                "topics": [t for t in (l.topics or []) if not t.startswith("__")],
                "parcels": l.parcels or [],
                "total_questions": l.total_questions,
                "total_sessions": l.total_sessions,
                "source": l.source,
                "last_active": l.last_active.isoformat() if l.last_active else None,
                "created_at":  l.created_at.isoformat()  if l.created_at  else None,
            }
            for l in result.scalars().all()
        ]


@router.get("/api/admin/leads/{lead_id}/sessions")
async def get_lead_sessions(lead_id: int, authorization: Optional[str] = Header(default=None)):
    _require_session(authorization)
    async with async_session() as db:
        s_result = await db.execute(
            select(ChatSession).where(ChatSession.user_id == str(lead_id)).order_by(ChatSession.created_at.desc())
        )
        output = []
        for s in s_result.scalars().all():
            m_result = await db.execute(
                select(ChatMessage).where(ChatMessage.session_id == s.id).order_by(ChatMessage.created_at.asc())
            )
            output.append({
                "id": s.id, "title": s.title, "created_at": str(s.created_at),
                "messages": [{"role": m.role, "content": m.content} for m in m_result.scalars().all()],
            })
        return output


@router.delete("/api/admin/leads/{lead_id}")
async def delete_lead(lead_id: int, authorization: Optional[str] = Header(default=None)):
    _require_session(authorization)
    async with async_session() as db:
        lead = (await db.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        await db.execute(delete(Lead).where(Lead.id == lead_id))
        await db.commit()
    return {"ok": True, "deleted": lead_id}

"""
Auth router — phone OTP + email magic link login for returning users.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete

from ..db import SessionLocal as async_session
from ..models.auth_model import OtpCode
from ..models.lead_model import Lead
from ..services.email_service import send_magic_link

router = APIRouter()

MAGIC_TTL_MINUTES = 30


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_phone(phone: str) -> str:
    """Strip spaces/dashes for loose matching."""
    return phone.replace("-", "").replace(" ", "")


# ─── Request OTP (SMS) ───────────────────────────────────────────────────────

class OtpRequest(BaseModel):
    phone: str


@router.post("/api/auth/request-otp")
async def request_otp(req: OtpRequest):
    phone = _normalize_phone(req.phone)

    async with async_session() as db:
        # Verify phone exists in our leads
        result = await db.execute(select(Lead).where(Lead.phone.contains(phone[-9:])))
        lead = result.scalars().first()
        if not lead:
            # Don't reveal whether phone exists — generic success response
            return {"ok": True}

        # Delete old OTPs for this phone
        await db.execute(delete(OtpCode).where(OtpCode.identifier == phone, OtpCode.kind == "sms"))

        # Generate 4-digit code
        code = "".join(random.choices(string.digits, k=4))
        expires = _now() + timedelta(minutes=OTP_TTL_MINUTES)

        db.add(OtpCode(id=str(uuid4()), identifier=phone, code=code, kind="sms", expires_at=expires))
        await db.commit()

    await send_otp_sms(req.phone, code)
    return {"ok": True}


# ─── Verify OTP ──────────────────────────────────────────────────────────────

class OtpVerify(BaseModel):
    phone: str
    code: str


@router.post("/api/auth/verify-otp")
async def verify_otp(req: OtpVerify):
    phone = _normalize_phone(req.phone)

    async with async_session() as db:
        result = await db.execute(
            select(OtpCode).where(
                OtpCode.identifier == phone,
                OtpCode.code == req.code,
                OtpCode.kind == "sms",
                OtpCode.used == False,  # noqa: E712
                OtpCode.expires_at > _now(),
            )
        )
        otp = result.scalar_one_or_none()
        if not otp:
            raise HTTPException(status_code=400, detail="קוד שגוי או פג תוקף")

        otp.used = True
        await db.commit()

        # Find lead
        lead_result = await db.execute(select(Lead).where(Lead.phone.contains(phone[-9:])))
        lead = lead_result.scalars().first()
        if not lead:
            raise HTTPException(status_code=404, detail="משתמש לא נמצא")

        return {"user": {"id": str(lead.id), "name": lead.name, "phone": lead.phone, "email": lead.email}}


# ─── Request Magic Link (Email) ───────────────────────────────────────────────

class MagicRequest(BaseModel):
    email: str


@router.post("/api/auth/request-magic")
async def request_magic(req: MagicRequest):
    email = req.email.strip().lower()

    async with async_session() as db:
        result = await db.execute(select(Lead).where(Lead.email == email))
        lead = result.scalars().first()
        if not lead:
            return {"ok": False, "reason": "not_registered"}

        # Delete old magic links for this email
        await db.execute(delete(OtpCode).where(OtpCode.identifier == email, OtpCode.kind == "email"))

        token = str(uuid4())
        expires = _now() + timedelta(minutes=MAGIC_TTL_MINUTES)

        db.add(OtpCode(id=str(uuid4()), identifier=email, code=token, kind="email", expires_at=expires))
        await db.commit()

    await send_magic_link(email, token)
    return {"ok": True}


# ─── Verify Magic Link ────────────────────────────────────────────────────────

@router.get("/api/auth/verify-magic")
async def verify_magic(token: str):
    async with async_session() as db:
        result = await db.execute(
            select(OtpCode).where(
                OtpCode.code == token,
                OtpCode.kind == "email",
                OtpCode.used == False,  # noqa: E712
                OtpCode.expires_at > _now(),
            )
        )
        otp = result.scalar_one_or_none()
        if not otp:
            raise HTTPException(status_code=400, detail="קישור לא תקין או פג תוקף")

        otp.used = True
        await db.commit()

        lead_result = await db.execute(select(Lead).where(Lead.email == otp.identifier))
        lead = lead_result.scalars().first()
        if not lead:
            raise HTTPException(status_code=404, detail="משתמש לא נמצא")

        return {"user": {"id": str(lead.id), "name": lead.name, "phone": lead.phone, "email": lead.email}}

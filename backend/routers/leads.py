from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator, EmailStr
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from ..db import get_db
from ..models.lead_model import Lead
from ..models.chat_model import ChatSession

router = APIRouter()

ISRAELI_PHONE_RE = re.compile(r'^(\+972|972|0)([23489]|5[02-9]|7[0-9])[0-9]{7}$')


class LeadIn(BaseModel):
    name: str
    phone: str
    email: EmailStr
    source: Optional[str] = None
    guest_session_id: Optional[str] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError('שם חייב להכיל לפחות 2 תווים')
        return v

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip().replace('-', '').replace(' ', '')
        if not ISRAELI_PHONE_RE.match(v):
            raise ValueError('מספר טלפון לא תקין — נא להכניס מספר ישראלי')
        return v


@router.post("/api/register")
async def register(lead: LeadIn, db: AsyncSession = Depends(get_db)):
    # בדיקת כפילות
    existing = await db.execute(
        select(Lead).where(Lead.email == str(lead.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail='כבר קיים חשבון עם האימייל הזה')

    new_lead = Lead(
        name=lead.name,
        phone=lead.phone,
        email=str(lead.email),
        source=lead.source,
    )
    db.add(new_lead)
    await db.commit()
    await db.refresh(new_lead)

    # Link guest session to new lead
    if lead.guest_session_id:
        await db.execute(
            update(ChatSession)
            .where(ChatSession.id == lead.guest_session_id)
            .values(user_id=str(new_lead.id))
        )
        await db.commit()

    return {"status": "ok", "id": new_lead.id, "name": new_lead.name, "email": str(lead.email)}

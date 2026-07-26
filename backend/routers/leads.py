from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator, EmailStr
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import get_db
from ..models.lead_model import Lead

router = APIRouter()

ISRAELI_PHONE_RE = re.compile(r'^(\+972|972|0)([23489]|5[02-9]|7[0-9])[0-9]{7}$')


class LeadIn(BaseModel):
    name: str
    phone: str
    email: EmailStr

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

    new_lead = Lead(name=lead.name, phone=lead.phone, email=str(lead.email))
    db.add(new_lead)
    await db.commit()
    await db.refresh(new_lead)
    return {"status": "ok", "id": new_lead.id, "name": new_lead.name, "email": str(lead.email)}

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from ..db import get_db
from ..models.lead_model import Lead

router = APIRouter()


class LeadIn(BaseModel):
    name: str
    phone: str
    email: str


@router.post("/api/register")
async def register(lead: LeadIn, db: AsyncSession = Depends(get_db)):
    new_lead = Lead(name=lead.name, phone=lead.phone, email=lead.email)
    db.add(new_lead)
    await db.commit()
    return {"status": "ok", "message": "נרשמת בהצלחה!"}

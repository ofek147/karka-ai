from fastapi import APIRouter
from pydantic import BaseModel
import csv
import os
from datetime import datetime

router = APIRouter()
LEADS_FILE = "data/leads.csv"


class LeadIn(BaseModel):
    name: str
    phone: str
    email: str


@router.post("/api/register")
async def register(lead: LeadIn):
    os.makedirs("data", exist_ok=True)
    file_exists = os.path.exists(LEADS_FILE)
    with open(LEADS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "name", "phone", "email"])
        writer.writerow([datetime.now().isoformat(), lead.name, lead.phone, lead.email])
    return {"status": "ok", "message": "נרשמת בהצלחה!"}

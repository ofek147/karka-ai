"""
report router — POST /api/report/request → queues a report job

Request:
    {
        "gush": 6672,
        "helka": 50,
        "email": "user@example.com",   # at least one of email/phone required
        "phone": "0501234567",          # optional
        "name": "ישראל ישראלי"          # optional
    }

Response:
    {"status": "queued", "job_id": 42, "message": "..."}

The report is generated asynchronously by the background worker and sent via email.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator, EmailStr
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models.report_job import ReportJob

router = APIRouter(prefix="/api", tags=["report"])


class ReportRequest(BaseModel):
    gush: int
    helka: int
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    name: Optional[str] = None

    @field_validator("gush", "helka")
    @classmethod
    def positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("חייב להיות מספר חיובי")
        return v

    def model_post_init(self, __context) -> None:
        if not self.email and not self.phone:
            raise ValueError("נדרש לפחות מייל או טלפון")


@router.post("/report/request")
async def request_report(req: ReportRequest, db: AsyncSession = Depends(get_db)):
    """
    Queue a report generation job.
    Returns immediately — the worker processes it in the background and emails the result.
    """
    job = ReportJob(
        gush=req.gush,
        helka=req.helka,
        email=str(req.email) if req.email else None,
        phone=req.phone,
        name=req.name,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    contact = str(req.email) if req.email else req.phone
    return {
        "status": "queued",
        "job_id": job.id,
        "message": f"הדוח בהכנה ויישלח ל-{contact} בקרוב",
    }


@router.get("/report/status/{job_id}")
async def report_status(job_id: int, db: AsyncSession = Depends(get_db)):
    """Check the status of a queued report job."""
    result = await db.execute(select(ReportJob).where(ReportJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "gush": job.gush,
        "helka": job.helka,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_msg": job.error_msg,
    }

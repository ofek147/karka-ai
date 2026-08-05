"""
report router — POST /api/report → returns PDF file

Request:
    {"gush": 6672, "helka": 50}

Response:
    application/pdf  (Content-Disposition: attachment; filename=report-{gush}-{helka}.pdf)
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..services.report_service import generate_report_html
from ..services.pdf_service import html_to_pdf

router = APIRouter(prefix="/api", tags=["report"])


class ReportRequest(BaseModel):
    """Request body for PDF report generation."""
    gush: int
    helka: int


@router.post("/report")
async def generate_report(req: ReportRequest, db: AsyncSession = Depends(get_db)) -> Response:
    """
    Generate a PDF report for a specific parcel (גוש + חלקה).

    Fetches live data from govmap + iplan, generates AI analysis via Claude,
    renders Jinja2 HTML template, and converts to PDF via WeasyPrint.

    Returns the PDF binary directly as an attachment.
    """
    try:
        html = await generate_report_html(req.gush, req.helka, db=db)
        pdf_bytes = await html_to_pdf(html)
        filename = f"report-{req.gush}-{req.helka}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

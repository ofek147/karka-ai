"""
mavat_client.py — downloads a plan PDF from a direct URL and extracts text.

pl_url from iplan API is a direct PDF link — no JavaScript navigation needed.
We download with httpx and extract text with PyMuPDF (fitz).

Returns: raw text string (full, no truncation — caller decides what to do with it).
"""

from __future__ import annotations

import os
from typing import Optional

import fitz  # PyMuPDF
import httpx

# Max characters to store — prevents DB bloat on extremely large PDFs (>500 pages)
# Set to None to disable. Current: no limit (per product decision).
MAX_CHARS: Optional[int] = None

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
}


def _extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """Extract all text from PDF bytes using PyMuPDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts: list[str] = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            parts.append(text)
    doc.close()
    full = "\n".join(parts)
    return full[:MAX_CHARS] if MAX_CHARS else full


async def fetch_plan_pdf_text_from_url(pdf_url: str) -> Optional[str]:
    """
    Download PDF from a direct URL and extract text.

    Args:
        pdf_url: Direct URL to a PDF file (e.g. from iplan pl_url field).

    Returns:
        Extracted text string, or None on error / empty PDF.
    """
    try:
        async with httpx.AsyncClient(
            timeout=60,
            follow_redirects=True,
            verify=False,  # iplan uses older TLS — same as iplan_client
        ) as client:
            r = await client.get(pdf_url, headers=_HEADERS)
            r.raise_for_status()
            pdf_bytes = r.content

        text = _extract_text_from_bytes(pdf_bytes)
        if not text.strip():
            print(f"[mavat_client] PDF has no extractable text: {pdf_url}")
            return None

        print(f"[mavat_client] Extracted {len(text):,} chars from {pdf_url}")
        return text

    except Exception as e:
        print(f"[mavat_client] Error fetching {pdf_url}: {e}")
        return None

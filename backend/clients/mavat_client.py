"""
mavat_client.py — fetches plan PDF from mavat.iplan.gov.il and extracts text.

Flow:
  1. Playwright (headless Chromium) navigates to the mavat plan page
  2. Intercepts the PDF download URL from the network response
  3. Downloads the PDF bytes via httpx
  4. Extracts text with PyMuPDF (fitz)

Returns: raw text string (may be large — caller should truncate if needed).

Environment:
  PLAYWRIGHT_BROWSER_PATH — optional override for Chromium binary path.
  MAVAT_TIMEOUT_MS        — page navigation timeout in ms (default: 30000).
"""

from __future__ import annotations

import asyncio
import os
import re
from typing import Optional

import fitz  # PyMuPDF
import httpx
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

MAVAT_BASE = "https://mavat.iplan.gov.il/SV4/1?PL_ID={plan_id}"
MAVAT_TIMEOUT = int(os.getenv("MAVAT_TIMEOUT_MS", "30000"))

# Patterns that indicate a PDF download URL in mavat network traffic
_PDF_URL_PATTERNS = [
    re.compile(r"mavat.*\.pdf", re.IGNORECASE),
    re.compile(r"/blob/.*pdf", re.IGNORECASE),
    re.compile(r"GeneratePDF", re.IGNORECASE),
    re.compile(r"PL_ID=\d+.*pdf", re.IGNORECASE),
]

# Max characters to store (prevents DB bloat on very large PDFs)
MAX_CHARS = 200_000


def _extract_text_from_bytes(pdf_bytes: bytes) -> str:
    """Extract all text from PDF bytes using PyMuPDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts: list[str] = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            parts.append(text)
    doc.close()
    return "\n".join(parts)[:MAX_CHARS]


async def _download_pdf(url: str) -> bytes:
    """Download PDF from URL."""
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.content


async def fetch_plan_pdf_text(plan_id: str) -> Optional[str]:
    """
    Navigate to a mavat plan page, intercept the PDF URL, download and extract text.

    Args:
        plan_id: mavat internal plan ID (PL_ID parameter).

    Returns:
        Extracted text string, or None if PDF not found / error.
    """
    pdf_url: Optional[str] = None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                accept_downloads=True,
                locale="he-IL",
            )
            page = await context.new_page()

            # Intercept network responses to find PDF URL
            intercepted: list[str] = []

            async def on_response(response):
                url = response.url
                ct = response.headers.get("content-type", "")
                if "pdf" in ct.lower() or any(p.search(url) for p in _PDF_URL_PATTERNS):
                    intercepted.append(url)

            page.on("response", on_response)

            try:
                await page.goto(
                    MAVAT_BASE.format(plan_id=plan_id),
                    timeout=MAVAT_TIMEOUT,
                    wait_until="networkidle",
                )
            except PWTimeout:
                # Page may still have useful network responses
                pass

            # Try clicking "download PDF" button if visible
            try:
                pdf_btn = page.locator("button:has-text('PDF'), a:has-text('PDF'), [title*='PDF']")
                if await pdf_btn.count() > 0:
                    async with page.expect_response(
                        lambda r: "pdf" in r.headers.get("content-type", "").lower(),
                        timeout=15000,
                    ) as resp_info:
                        await pdf_btn.first.click()
                    intercepted.append((await resp_info.value).url)
            except Exception:
                pass

            await browser.close()

            if intercepted:
                pdf_url = intercepted[-1]

    except Exception as e:
        print(f"[mavat_client] Playwright error for plan_id={plan_id}: {e}")
        return None

    if not pdf_url:
        print(f"[mavat_client] No PDF URL found for plan_id={plan_id}")
        return None

    try:
        pdf_bytes = await _download_pdf(pdf_url)
        text = _extract_text_from_bytes(pdf_bytes)
        print(f"[mavat_client] Extracted {len(text):,} chars from plan_id={plan_id}")
        return text if text.strip() else None
    except Exception as e:
        print(f"[mavat_client] PDF download/extract error for plan_id={plan_id}: {e}")
        return None


async def fetch_plan_pdf_text_from_url(pdf_url: str) -> Optional[str]:
    """
    Direct download + extract from a known PDF URL (no Playwright needed).
    Use this when the plan URL is already known from iplan API.
    """
    try:
        pdf_bytes = await _download_pdf(pdf_url)
        text = _extract_text_from_bytes(pdf_bytes)
        print(f"[mavat_client] Extracted {len(text):,} chars from URL")
        return text if text.strip() else None
    except Exception as e:
        print(f"[mavat_client] Direct PDF error for {pdf_url}: {e}")
        return None

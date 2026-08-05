"""
mavat_client.py — extracts PDF text from a mavat plan page.

mavat.iplan.gov.il is a full SPA — direct HTTP gives only HTML shell.
We use Playwright (headless Chromium) to:
  1. Navigate to the plan page
  2. Wait for the network to settle
  3. Intercept any PDF response OR find a PDF link in the DOM
  4. Download the PDF bytes via httpx
  5. Extract text with PyMuPDF (fitz)

The Playwright image (mcr.microsoft.com/playwright/python:v1.47.0-jammy)
ships with Chromium pre-installed — no extra install step needed.
"""

from __future__ import annotations

import os
import re
from typing import Optional

import fitz  # PyMuPDF
import httpx
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

MAVAT_TIMEOUT = int(os.getenv("MAVAT_TIMEOUT_MS", "25000"))

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

# Patterns that identify a PDF network response from mavat
_PDF_CT_RE = re.compile(r"pdf", re.IGNORECASE)
_PDF_URL_RE = re.compile(r"\.pdf($|\?)", re.IGNORECASE)


def _extract_text(pdf_bytes: bytes) -> str:
    """Extract all text from PDF bytes using PyMuPDF."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts = [page.get_text("text") for page in doc if page.get_text("text").strip()]
    doc.close()
    return "\n".join(parts)


async def _download_pdf(url: str) -> Optional[bytes]:
    """Download PDF bytes from a direct URL."""
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True, verify=False) as client:
            r = await client.get(url, headers=_HEADERS)
            r.raise_for_status()
            if b"%PDF" in r.content[:10]:
                return r.content
    except Exception as e:
        print(f"[mavat_client] download error {url}: {e}")
    return None


async def fetch_plan_pdf_text_from_url(plan_url: str) -> Optional[str]:
    """
    Navigate to a mavat plan page, find and download the plan PDF, extract text.

    Args:
        plan_url: mavat plan page URL (e.g. https://mavat.iplan.gov.il/SV4/1/{id}/310)

    Returns:
        Full extracted text, or None if PDF not found / unreadable.
    """
    pdf_url: Optional[str] = None
    pdf_bytes: Optional[bytes] = None

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()

            intercepted_pdfs: list[str] = []

            # Intercept PDF responses from the network
            async def on_response(response):
                ct = response.headers.get("content-type", "")
                url = response.url
                if _PDF_CT_RE.search(ct) or _PDF_URL_RE.search(url):
                    intercepted_pdfs.append(url)

            page.on("response", on_response)

            # Navigate and wait for network to settle
            try:
                await page.goto(plan_url, timeout=MAVAT_TIMEOUT, wait_until="networkidle")
            except PWTimeout:
                pass  # Still try to extract what we got

            # Strategy 1: intercepted PDF from network traffic
            if intercepted_pdfs:
                pdf_url = intercepted_pdfs[-1]

            # Strategy 2: find PDF link in DOM
            if not pdf_url:
                try:
                    links = await page.eval_on_selector_all(
                        "a[href*='.pdf'], a[href*='pdf'], a[href*='PDF']",
                        "els => els.map(e => e.href)"
                    )
                    if links:
                        pdf_url = links[0]
                except Exception:
                    pass

            # Strategy 3: look for download button and click it
            if not pdf_url:
                try:
                    btn = page.locator(
                        "button:has-text('הורד'), a:has-text('הורד'), "
                        "button:has-text('PDF'), a:has-text('PDF'), "
                        "[title*='הורד'], [title*='PDF']"
                    )
                    if await btn.count() > 0:
                        async with page.expect_response(
                            lambda r: _PDF_CT_RE.search(r.headers.get("content-type", "")),
                            timeout=10000,
                        ) as resp_info:
                            await btn.first.click()
                        pdf_url = (await resp_info.value).url
                        intercepted_pdfs.append(pdf_url)
                except Exception:
                    pass

            await browser.close()

    except Exception as e:
        print(f"[mavat_client] Playwright error for {plan_url}: {e}")
        return None

    if not pdf_url:
        print(f"[mavat_client] No PDF found for {plan_url}")
        return None

    pdf_bytes = await _download_pdf(pdf_url)
    if not pdf_bytes:
        return None

    text = _extract_text(pdf_bytes)
    if not text.strip():
        print(f"[mavat_client] PDF has no extractable text: {pdf_url}")
        return None

    print(f"[mavat_client] Extracted {len(text):,} chars from {plan_url}")
    return text

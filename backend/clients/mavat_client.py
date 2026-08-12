"""
mavat_client.py — extracts PDF text from a mavat plan page.

mavat.iplan.gov.il is a full SPA with session-bound download tokens.
Direct HTTP / network interception does NOT work — tokens are one-time and session-bound.

Working approach (confirmed 2026-08-12):
  1. Playwright navigates to the plan page
  2. Wait for Angular to fully render (~12s)
  3. Use accept_downloads=True + expect_download context manager
  4. Click the "הוראות התכנית" button (a.sv4-docs)
  5. Copy downloaded PDF before closing browser
  6. Extract text with PyMuPDF (fitz)

Note: only plans with active "הוראות" button (no gray-disabled class) yield a PDF.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import Optional

import fitz  # PyMuPDF
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

MAVAT_TIMEOUT = int(os.getenv("MAVAT_TIMEOUT_MS", "30000"))
MAVAT_LOAD_WAIT = int(os.getenv("MAVAT_LOAD_WAIT_S", "12"))  # seconds for Angular to render


def _extract_text(pdf_path: str) -> str:
    """Extract all text from a PDF file using PyMuPDF."""
    doc = fitz.open(pdf_path)
    parts = [page.get_text("text") for page in doc if page.get_text("text").strip()]
    doc.close()
    return "\n".join(parts)


async def fetch_plan_pdf_text_from_url(plan_url: str) -> Optional[str]:
    """
    Navigate to a mavat plan page, download the plan PDF via the
    'הוראות התכנית' button, and extract text.

    Args:
        plan_url: mavat plan page URL (e.g. https://mavat.iplan.gov.il/SV4/1/{id}/310)

    Returns:
        Full extracted text, or None if PDF not available / unreadable.
    """
    import asyncio as _asyncio

    tmp_path: Optional[str] = None

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                accept_downloads=True,
                ignore_https_errors=True,
            )
            page = await context.new_page()

            # Navigate and wait for Angular to render
            try:
                await page.goto(plan_url, timeout=MAVAT_TIMEOUT, wait_until="domcontentloaded")
            except PWTimeout:
                pass  # Still try to interact with whatever loaded

            await _asyncio.sleep(MAVAT_LOAD_WAIT)

            # Check if "הוראות התכנית" button exists and is active (not gray-disabled)
            docs_btn = await page.query_selector("a.sv4-docs")
            if not docs_btn:
                print(f"[mavat_client] No הוראות button found for {plan_url}")
                await browser.close()
                return None

            btn_class = await docs_btn.get_attribute("class") or ""
            if "gray-disabled" in btn_class:
                print(f"[mavat_client] הוראות button is disabled for {plan_url}")
                await browser.close()
                return None

            # Download PDF via button click
            try:
                async with page.expect_download(timeout=MAVAT_TIMEOUT) as download_info:
                    await docs_btn.click(force=True)
                download = await download_info.value

                # Copy to temp file before browser closes (Playwright cleans up on close)
                tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
                os.close(tmp_fd)
                src = await download.path()
                shutil.copy(src, tmp_path)
                print(f"[mavat_client] Downloaded: {download.suggested_filename} ({os.path.getsize(tmp_path):,} bytes)")

            except Exception as e:
                print(f"[mavat_client] Download failed for {plan_url}: {e}")
                await browser.close()
                return None

            await browser.close()

    except Exception as e:
        print(f"[mavat_client] Playwright error for {plan_url}: {e}")
        return None

    if not tmp_path or not os.path.exists(tmp_path):
        print(f"[mavat_client] No PDF file for {plan_url}")
        return None

    try:
        text = _extract_text(tmp_path)
    except Exception as e:
        print(f"[mavat_client] PDF extraction error: {e}")
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    if not text.strip():
        print(f"[mavat_client] PDF has no extractable text: {plan_url}")
        return None

    print(f"[mavat_client] Extracted {len(text):,} chars from {plan_url}")
    return text

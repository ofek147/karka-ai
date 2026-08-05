"""
mavat_client.py — Fetch PDF text from mavat.iplan.gov.il

Flow per plan:
  1. Load mavat page with Playwright (headless)
  2. Intercept the automatic REST API response → get doc list (rsPlanDocs)
  3. Click the "הוראות התכנית" button (sv4-docs) → intercept the PDF response
  4. Extract text with PyMuPDF

The REST API and PDF download both require Angular session state.
The only reliable way is to intercept responses during the Angular lifecycle.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import fitz  # PyMuPDF
from playwright.async_api import async_playwright


BASE_URL = "https://mavat.iplan.gov.il"


async def fetch_plan_pdf_text(plan_id: int | str) -> Optional[str]:
    """
    Fetch and extract text from all plan documents for the given mavat plan_id.
    Returns concatenated text or None if no PDF found.
    """
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()

            try:
                return await _fetch_with_page(page, plan_id)
            finally:
                await context.close()
                await browser.close()

    except Exception as e:
        print(f"[mavat] Error fetching plan {plan_id}: {e}")
        return None


async def _fetch_with_page(page, plan_id) -> Optional[str]:
    plan_id = str(plan_id)

    # Step 1: intercept the API + PDF responses
    api_data = {}
    pdf_results: list[tuple[str, bytes]] = []  # (doc_name, pdf_bytes)

    async def on_response(response):
        nonlocal api_data
        # Capture plan API
        if f"mid={plan_id}" in response.url and "SV4/1" in response.url:
            try:
                api_data = await response.json()
            except Exception:
                pass
            return
        # Capture PDF downloads
        try:
            body = await response.body()
            if body[:4] == b"%PDF":
                doc_name = response.url.split("fn=")[1].split("&")[0] if "fn=" in response.url else "doc"
                pdf_results.append((doc_name, body))
        except Exception:
            pass

    page.on("response", on_response)

    # Step 2: load page (Angular auto-fires the API call)
    await page.goto(
        f"{BASE_URL}/SV4/1/{plan_id}/310",
        wait_until="domcontentloaded",
        timeout=20000,
    )
    await asyncio.sleep(5)

    if not api_data:
        print(f"[mavat] No API data for plan {plan_id}")
        return None

    docs = api_data.get("rsPlanDocs", [])
    if not docs:
        print(f"[mavat] No documents for plan {plan_id}")
        return None

    print(f"[mavat] Plan {plan_id}: {len(docs)} docs")

    # Step 3: click sv4-docs button (הוראות התכנית) → triggers PDF download
    btn = page.locator("a.sv4-docs").first
    try:
        await btn.click(timeout=8000, force=True)
        await asyncio.sleep(6)
    except Exception as e:
        print(f"[mavat] sv4-docs click failed: {e}")

    # Step 4: also try sv4-circul (תשריט) if visible
    btn2 = page.locator("a.sv4-circul").first
    try:
        await btn2.click(timeout=5000, force=True)
        await asyncio.sleep(5)
    except Exception:
        pass

    if not pdf_results:
        print(f"[mavat] No PDF captured for plan {plan_id}")
        return None

    # Step 5: extract text from all PDFs
    texts = []
    for doc_name, pdf_bytes in pdf_results:
        try:
            pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text = "\n".join(p.get_text() for p in pdf_doc)
            pdf_doc.close()
            if text.strip():
                texts.append(f"=== {doc_name} ===\n{text.strip()}")
                print(f"[mavat] Plan {plan_id} / {doc_name}: {len(text)} chars")
        except Exception as e:
            print(f"[mavat] PyMuPDF error: {e}")

    return "\n\n".join(texts) if texts else None


# Legacy compat
async def fetch_plan_pdf_text_from_url(pl_url: str) -> Optional[str]:
    """
    Legacy wrapper: extract plan_id from pl_url and call fetch_plan_pdf_text.
    pl_url format: https://mavat.iplan.gov.il/SV4/1/{plan_id}/310
    """
    try:
        parts = pl_url.rstrip("/").split("/")
        for part in reversed(parts):
            if part.isdigit() and len(part) >= 7:
                return await fetch_plan_pdf_text(int(part))
    except Exception as e:
        print(f"[mavat] fetch_plan_pdf_text_from_url error: {e}")
    return None

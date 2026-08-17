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

OCR fallback (added 2026-08-17):
  If PyMuPDF returns empty/minimal text (scanned PDF) → fallback to Tesseract OCR:
  1. Convert PDF pages to images via pdftoppm (poppler-utils)
  2. Run Tesseract with Hebrew tessdata per page
  3. Collect text + confidence score per page → average confidence
  4. Return (text, ocr_confidence, extraction_method)

Return type changed to tuple:
  (text: Optional[str], ocr_confidence: Optional[float], extraction_method: str)
  extraction_method: "digital" | "ocr" | "none"
  ocr_confidence: 0-100 (Tesseract average word confidence), None if digital or failed

Note: only plans with active "הוראות" button (no gray-disabled class) yield a PDF.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional, Tuple

import fitz  # PyMuPDF
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

MAVAT_TIMEOUT = int(os.getenv("MAVAT_TIMEOUT_MS", "30000"))
MAVAT_LOAD_WAIT = int(os.getenv("MAVAT_LOAD_WAIT_S", "12"))  # seconds for Angular to render

# Minimum chars from digital extraction to skip OCR
_DIGITAL_MIN_CHARS = 200
# Tesseract language config — Hebrew primary, English fallback
_TESS_LANG = "heb+eng"
# Tesseract DPI for pdftoppm conversion (higher = better quality, slower)
_PDF_DPI = 200


def _extract_text_digital(pdf_path: str) -> str:
    """Extract all text from a PDF file using PyMuPDF (digital text only)."""
    doc = fitz.open(pdf_path)
    parts = [page.get_text("text") for page in doc if page.get_text("text").strip()]
    doc.close()
    return "\n".join(parts)


def _ocr_pdf(pdf_path: str) -> Tuple[str, float]:
    """
    OCR a scanned PDF using Tesseract.

    Flow:
      1. pdftoppm converts PDF pages → PPM images in a temp dir
      2. Tesseract reads each image with Hebrew tessdata
      3. Returns (combined_text, average_confidence)

    confidence is Tesseract's word-level mean confidence (0-100).
    Returns ("", 0.0) on failure.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        print("[mavat_client] pytesseract/Pillow not installed — OCR unavailable")
        return ("", 0.0)

    tmp_dir = tempfile.mkdtemp(prefix="karka_ocr_")
    try:
        # Step 1: convert PDF → images via pdftoppm
        prefix = os.path.join(tmp_dir, "page")
        result = subprocess.run(
            ["pdftoppm", "-r", str(_PDF_DPI), "-png", pdf_path, prefix],
            capture_output=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"[mavat_client] pdftoppm failed: {result.stderr.decode()[:200]}")
            return ("", 0.0)

        # Step 2: collect generated image files (sorted by page order)
        image_files = sorted(
            f for f in os.listdir(tmp_dir) if f.endswith(".png")
        )
        if not image_files:
            print("[mavat_client] pdftoppm produced no images")
            return ("", 0.0)

        all_text_parts: list[str] = []
        all_confidences: list[float] = []

        for img_file in image_files:
            img_path = os.path.join(tmp_dir, img_file)
            try:
                img = Image.open(img_path)

                # Get text + per-word confidence data
                data = pytesseract.image_to_data(
                    img,
                    lang=_TESS_LANG,
                    output_type=pytesseract.Output.DICT,
                    config="--psm 3",  # Fully automatic page segmentation
                )

                # Filter words with valid confidence (conf == -1 means no word)
                word_confs = [
                    int(c) for c in data["conf"]
                    if str(c).lstrip("-").isdigit() and int(c) >= 0
                ]
                page_text = pytesseract.image_to_string(
                    img,
                    lang=_TESS_LANG,
                    config="--psm 3",
                ).strip()

                if page_text:
                    all_text_parts.append(page_text)
                if word_confs:
                    all_confidences.append(sum(word_confs) / len(word_confs))

                print(
                    f"[mavat_client] OCR {img_file}: "
                    f"{len(page_text)} chars, "
                    f"conf={sum(word_confs)/len(word_confs):.1f}%" if word_confs else
                    f"[mavat_client] OCR {img_file}: {len(page_text)} chars, conf=n/a"
                )

            except Exception as e:
                print(f"[mavat_client] OCR error on {img_file}: {e}")
                continue

        combined_text = "\n\n".join(all_text_parts)
        avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

        print(
            f"[mavat_client] OCR complete: {len(image_files)} pages, "
            f"{len(combined_text)} chars total, avg confidence={avg_confidence:.1f}%"
        )
        return (combined_text, avg_confidence)

    except subprocess.TimeoutExpired:
        print("[mavat_client] pdftoppm timed out")
        return ("", 0.0)
    except Exception as e:
        print(f"[mavat_client] OCR pipeline error: {e}")
        return ("", 0.0)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def fetch_plan_pdf_text_from_url(
    plan_url: str,
) -> Tuple[Optional[str], Optional[float], str]:
    """
    Navigate to a mavat plan page, download the plan PDF via the
    'הוראות התכנית' button, and extract text.

    Extraction strategy:
      1. Try PyMuPDF digital text extraction
      2. If result < _DIGITAL_MIN_CHARS chars → fallback to Tesseract OCR
      3. Log extraction_method + ocr_confidence for every PDF

    Args:
        plan_url: mavat plan page URL (e.g. https://mavat.iplan.gov.il/SV4/1/{id}/310)

    Returns:
        Tuple of:
          - text (Optional[str]): extracted text, or None if unavailable
          - ocr_confidence (Optional[float]): Tesseract avg confidence (0-100), None if digital
          - extraction_method (str): "digital" | "ocr" | "none"
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
                return (None, None, "none")

            btn_class = await docs_btn.get_attribute("class") or ""
            if "gray-disabled" in btn_class:
                print(f"[mavat_client] הוראות button is disabled for {plan_url}")
                await browser.close()
                return (None, None, "none")

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
                return (None, None, "none")

            await browser.close()

    except Exception as e:
        print(f"[mavat_client] Playwright error for {plan_url}: {e}")
        return (None, None, "none")

    if not tmp_path or not os.path.exists(tmp_path):
        print(f"[mavat_client] No PDF file for {plan_url}")
        return (None, None, "none")

    try:
        # ── Step 1: try digital extraction ───────────────────────────────────
        digital_text = _extract_text_digital(tmp_path)

        if len(digital_text.strip()) >= _DIGITAL_MIN_CHARS:
            print(f"[mavat_client] Digital extraction: {len(digital_text):,} chars (method=digital)")
            return (digital_text, None, "digital")

        # ── Step 2: OCR fallback ──────────────────────────────────────────────
        print(
            f"[mavat_client] Digital text too short ({len(digital_text.strip())} chars) "
            f"— falling back to OCR: {plan_url}"
        )
        ocr_text, ocr_confidence = _ocr_pdf(tmp_path)

        if ocr_text.strip():
            print(
                f"[mavat_client] OCR extraction: {len(ocr_text):,} chars, "
                f"confidence={ocr_confidence:.1f}% (method=ocr)"
            )
            return (ocr_text, ocr_confidence, "ocr")

        # ── Step 3: both failed ───────────────────────────────────────────────
        print(f"[mavat_client] Both digital and OCR failed for {plan_url}")
        return (None, None, "none")

    except Exception as e:
        print(f"[mavat_client] Extraction error: {e}")
        return (None, None, "none")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

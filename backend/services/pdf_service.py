"""
pdf_service.py — ממיר HTML string ל-PDF bytes בזיכרון (weasyprint)

No disk writes: conversion is fully in-memory using BytesIO.
WeasyPrint renders Hebrew/RTL via the direction:rtl CSS on the page.
"""

import asyncio
import functools
from weasyprint import HTML as WeasyHTML


async def html_to_pdf(html: str) -> bytes:
    """
    Convert HTML string to PDF bytes.

    Runs WeasyPrint in a thread-pool executor to avoid blocking the
    asyncio event loop (WeasyPrint is synchronous/CPU-bound).

    Args:
        html: Fully rendered HTML string (including styles, UTF-8).

    Returns:
        PDF file content as bytes. No disk writes.
    """
    loop = asyncio.get_event_loop()

    def _render() -> bytes:
        return WeasyHTML(string=html).write_pdf()

    pdf_bytes: bytes = await loop.run_in_executor(None, _render)
    return pdf_bytes

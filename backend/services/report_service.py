"""
report_service.py — שולף נתונים על חלקה ומייצר סיכום טקסט

Flow:
1. govmap — parcel geometry (centroid EPSG:3857, area)
2. Convert centroid EPSG:3857 → TM35 (EPSG:2039) for iplan
3. iplan Layer 1 — plans with full metadata
4. iplan Layer 4 — land use zones
5. mavat — PDF text per plan → cached in DB
6. Claude — summarize each plan (Haiku), then final analysis (Sonnet)
7. Return formatted Hebrew text string
"""

from __future__ import annotations

import asyncio
import datetime
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.govmap_client import get_parcel_geometry
from ..clients.iplan_client import get_plans_by_centroid, get_land_use_by_centroid
from ..clients.mavat_client import fetch_plan_pdf_text_from_url
from ..services.claude_service import _call_claude, summarize_plan
from ..services.plan_cache_service import (
    get_cached_plan,
    get_cached_plan_text,
    set_cached_plan_text,
    set_cached_plan_summary,
)
from ..utils.report_utils import (
    _translate_status, _translate_yiud,
    _epoch_to_year, _classify_plan,
)


def _reproject(x: float, y: float) -> tuple:
    """Convert EPSG:3857 → EPSG:2039 (TM35)."""
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:3857", "EPSG:2039", always_xy=True).transform(x, y)


async def generate_report_text(gush: int, helka: int, db: Optional[AsyncSession] = None) -> str:
    """
    Fetch all data for a parcel and return a formatted Hebrew text report.

    Args:
        gush:  Block number (מספר גוש)
        helka: Parcel number (מספר חלקה)
        db:    Optional DB session for plan cache (PDF text + summaries)

    Returns:
        Formatted Hebrew text string.
    """
    # ── 1. govmap: parcel geometry ────────────────────────────────────────────
    parcel = await get_parcel_geometry(gush, helka)

    centroid_x = parcel.centroid_x   # EPSG:3857
    centroid_y = parcel.centroid_y   # EPSG:3857
    area_sqm   = parcel.area_sqm
    area_dunam = round(area_sqm / 1000, 3) if area_sqm else None

    # ── 2. Convert to TM35 for iplan ─────────────────────────────────────────
    cx_tm35: Optional[float] = None
    cy_tm35: Optional[float] = None
    if centroid_x and centroid_y:
        cx_tm35, cy_tm35 = _reproject(centroid_x, centroid_y)

    # ── 3. iplan: plans + land use (parallel) ─────────────────────────────────
    plans_raw: List[Any] = []
    land_use_raw: List[Any] = []
    if cx_tm35 and cy_tm35:
        plans_raw, land_use_raw = await asyncio.gather(
            _safe(get_plans_by_centroid(cx_tm35, cy_tm35), [], "plans"),
            _safe(get_land_use_by_centroid(cx_tm35, cy_tm35), [], "land_use"),
        )

    # ── 4. Sort plans: local(1) → district(2) → national(3) ──────────────────
    plans_raw.sort(key=lambda p: _classify_plan(p))

    # ── 5. Extract city name ──────────────────────────────────────────────────
    city = _extract_city(plans_raw)

    # ── 6. Build land use display ─────────────────────────────────────────────
    land_use_items: List[Dict] = []
    seen: set = set()
    for lu in land_use_raw:
        yiud = lu.yiud or lu.yiud_heb or ""
        if yiud and yiud not in seen:
            seen.add(yiud)
            land_use_items.append({
                "yiud":          yiud,
                "yiud_explained": _translate_yiud(yiud),
                "area_dunam":    lu.area_dunam,
            })

    # ── 7. Fetch PDF + summarize each plan (sequential, cached) ──────────────
    plan_summaries: List[str] = []
    if db is not None:
        fetch_candidates = [
            p for p in plans_raw
            if getattr(p, "pl_url", None) and getattr(p, "pl_number", None)
        ]
        for plan in fetch_candidates:
            last_modified = None
            if getattr(plan, "receiving_date", None):
                try:
                    last_modified = datetime.datetime.utcfromtimestamp(plan.receiving_date / 1000)
                except Exception:
                    pass

            cached_row = await get_cached_plan(db, plan.pl_number, last_modified=last_modified)

            if cached_row and cached_row.summary:
                plan_summaries.append(cached_row.summary)
                print(f"[report_service] Plan {plan.pl_number}: summary from cache")
                continue

            pdf_text = cached_row.pdf_text if cached_row else None
            if not pdf_text:
                pdf_text = await fetch_plan_pdf_text_from_url(plan.pl_url)
                if pdf_text:
                    await set_cached_plan_text(db, plan.pl_number, pdf_text, plan.pl_url)

            if not pdf_text:
                print(f"[report_service] Plan {plan.pl_number}: no PDF, skipping")
                continue

            try:
                label = plan.pl_name or plan.pl_number or plan.mavat_name or ""
                summary = await summarize_plan(
                    plan_name=label,
                    plan_number=plan.pl_number or "",
                    pdf_text=pdf_text,
                )
                await set_cached_plan_summary(db, plan.pl_number, summary)
                plan_summaries.append(summary)
                print(f"[report_service] Plan {plan.pl_number}: summarized ({len(summary)} chars)")
            except Exception as e:
                print(f"[report_service] Plan {plan.pl_number}: summarize error: {e}")

    # ── 8. Claude final analysis ──────────────────────────────────────────────
    yiud_list = ", ".join(lu["yiud"] for lu in land_use_items[:5]) or "לא ידוע"
    plans_list = "\n".join(
        f"- {p.pl_name or p.mavat_name or p.pl_number} ({_translate_status(p.station_desc or '')})"
        for p in plans_raw[:8]
    )
    summaries_block = (
        "\n\nסיכומי תכניות (מתוך PDFs רשמיים):\n"
        + "\n".join(f"- {s}" for s in plan_summaries)
    ) if plan_summaries else ""

    area_line = f"{area_sqm:.0f} מ\"ר ({area_dunam} דונם)" if area_sqm else "לא ידוע"
    city_line = f", {city}" if city else ""

    ai_prompt = (
        f"נתוני חלקה:\n"
        f"גוש {gush}, חלקה {helka}{city_line}\n"
        f"שטח: {area_line}\n"
        f"ייעודי קרקע: {yiud_list}\n\n"
        f"תכניות בתוקף:\n{plans_list}"
        f"{summaries_block}\n\n"
        "כתוב ניתוח תכנוני בעברית פשוטה (6-10 משפטים) עבור משקיע פרטי:\n"
        "1. מה המצב התכנוני הנוכחי של החלקה\n"
        "2. מה מותר לבנות (יחידות דיור, קומות, שטחים — אם ידוע)\n"
        "3. האם יש פוטנציאל לשינוי ייעוד או תוספת זכויות\n"
        "4. מה כדאי לשים לב אליו\n"
        "אל תיתן ייעוץ השקעתי. אל תשתמש ב-markdown."
    )

    ai_analysis = "ניתוח AI לא זמין כרגע."
    try:
        raw = await _call_claude([{"role": "user", "content": ai_prompt}])
        ai_analysis = re.sub(r'\*\*(.+?)\*\*', r'\1', raw)
        ai_analysis = re.sub(r'\*(.+?)\*', r'\1', ai_analysis)
        ai_analysis = re.sub(r'#{1,6}\s+', '', ai_analysis)
        ai_analysis = re.sub(r'⚠️', '', ai_analysis).strip()
    except Exception as e:
        print(f"[report_service] Claude error: {e}")

    # ── 9. Compose final text ─────────────────────────────────────────────────
    created_at = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        f"דוח תכנוני — גוש {gush}, חלקה {helka}",
        f"{'עיר: ' + city if city else ''}",
        f"שטח: {area_line}",
        f"תאריך הפקה: {created_at}",
        "",
        "ייעוד קרקע:",
        *[f"  • {lu['yiud']} ({lu['yiud_explained']})" for lu in land_use_items],
        "",
        "תכניות רלוונטיות:",
        *[
            f"  • {p.pl_name or p.mavat_name or p.pl_number} — {_translate_status(p.station_desc or '')}"
            f"{' [' + _epoch_to_year(p.pl_date_8 or p.pl_date7) + ']' if _epoch_to_year(p.pl_date_8 or getattr(p, 'pl_date7', None)) else ''}"
            for p in plans_raw[:8]
        ],
        "",
        "ניתוח תכנוני:",
        ai_analysis,
        "",
        "---",
        "karkAi — ניתוח קרקעות חכם | המידע אינו מהווה ייעוץ משפטי או השקעתי.",
    ]

    return "\n".join(line for line in lines if line is not None)


async def _safe(coro, default, label: str):
    """Run a coroutine safely, returning default on error."""
    try:
        return await coro
    except Exception as e:
        print(f"[report_service] {label} error: {e}")
        return default


def _extract_city(plans_raw: list) -> str:
    _DISTRICT_ONLY   = {"מרכז", "צפון", "דרום"}
    _DISTRICT_PREFIX = ("מחוז ", "district")

    def _is_district(name: str) -> bool:
        n = name.strip()
        if n in _DISTRICT_ONLY:
            return True
        return any(n.lower().startswith(p) for p in _DISTRICT_PREFIX)

    city = ""
    for p in plans_raw[:10]:
        county   = getattr(p, "plan_county_name", None) or ""
        district = getattr(p, "district_name",    None) or ""
        if county and not _is_district(county):
            return county.strip()
        if district and not _is_district(district) and not city:
            city = district.strip()
    return city

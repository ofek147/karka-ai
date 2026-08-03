"""
report_service.py — שולף נתונים לדוח ומרכיב HTML מ-Jinja2 template

Flow:
1. govmap — parcel geometry (centroid EPSG:3857, area, wkt) + real-estate stats (parallel)
2. Convert centroid EPSG:3857 → TM35 (EPSG:2039) for iplan
3. iplan Layer 1 — plans with full metadata
4. iplan Layer 4 — land use zones
5. Sort plans: local/detailed → district → national
6. Claude AI analysis paragraph
7. Render Jinja2 template → HTML string
"""

from __future__ import annotations

import asyncio
import datetime
import os
import re
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader
from pyproj import Transformer

from ..clients.govmap_client import get_parcel_geometry
from ..clients.iplan_client import get_plans_by_centroid, get_land_use_by_centroid
from ..clients.map_client import get_satellite_image_b64
from ..clients.real_estate_client import get_real_estate_stats, RealEstateStats
from ..services.claude_service import _call_claude
from ..utils.report_utils import (
    _translate_status, _translate_yiud,
    _epoch_to_year, _classify_plan,
)

# Template directory (../templates relative to this file)
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")

# CRS: govmap → EPSG:3857; iplan needs EPSG:2039 (TM35)
_T_3857_TO_TM35 = Transformer.from_crs("EPSG:3857", "EPSG:2039", always_xy=True)

# Satellite image defaults
_SAT_IMG_WIDTH  = 1200
_SAT_IMG_HEIGHT = 800
_SAT_BUFFER     = 400  # meters in EPSG:3857


def _wkt_to_svg_points(
    shape_wkt: str,
    centroid_x: float,
    centroid_y: float,
    img_width: int = _SAT_IMG_WIDTH,
    img_height: int = _SAT_IMG_HEIGHT,
    buffer: int = _SAT_BUFFER,
) -> str:
    """
    Convert WKT EPSG:3857 polygon coordinates to SVG pixel points string.
    The SVG viewBox matches the satellite image dimensions (default 1200x800).
    WKT may be POLYGON((x y z, ...)) with Z values — handled by stepping every 3.
    Returns empty string on failure.
    """
    if not shape_wkt:
        return ""
    try:
        nums = list(map(float, re.findall(r'[-\d.]+', shape_wkt)))
        if len(nums) < 4:
            return ""

        bbox_min_x = centroid_x - buffer
        bbox_min_y = centroid_y - buffer
        bbox_max_x = centroid_x + buffer
        bbox_max_y = centroid_y + buffer
        bbox_w = bbox_max_x - bbox_min_x
        bbox_h = bbox_max_y - bbox_min_y

        # Detect stride: 3 (x y z) if triplets, else 2 (x y)
        # Heuristic: if count divisible by 3 and not by 2 → stride=3; else try 2 first
        stride = 3 if (len(nums) % 3 == 0 and len(nums) % 2 != 0) else 2

        svg_points: list[str] = []
        for i in range(0, len(nums) - 1, stride):
            px = (nums[i] - bbox_min_x) / bbox_w * img_width
            # Y-axis is flipped: ArcGIS Y increases upward, SVG Y increases downward
            py = (1.0 - (nums[i + 1] - bbox_min_y) / bbox_h) * img_height
            svg_points.append(f"{px:.1f},{py:.1f}")

        return " ".join(svg_points)
    except Exception as e:
        print(f"[report_service] _wkt_to_svg_points error: {e}")
        return ""


async def generate_report_html(gush: int, helka: int) -> str:
    """
    Fetch all data for a parcel and render the Jinja2 report template.

    Args:
        gush: Block number (מספר גוש)
        helka: Parcel number (מספר חלקה)

    Returns:
        Rendered HTML string ready for PDF conversion.
    """
    # ── 1. govmap: parcel geometry + real-estate stats (in parallel) ─────────
    parcel, real_estate = await asyncio.gather(
        get_parcel_geometry(gush, helka),
        get_real_estate_stats(gush, helka),
    )


    centroid_x = parcel.centroid_x   # EPSG:3857
    centroid_y = parcel.centroid_y   # EPSG:3857
    area_sqm = parcel.area_sqm
    area_dunam = round(area_sqm / 1000, 3) if area_sqm else None

    # ── 1b. Satellite image (non-blocking, fail-safe) ─────────────────────────
    satellite_b64: Optional[str] = None
    if centroid_x and centroid_y:
        try:
            satellite_b64 = await get_satellite_image_b64(
                centroid_x, centroid_y,
                width=_SAT_IMG_WIDTH,
                height=_SAT_IMG_HEIGHT,
                buffer=_SAT_BUFFER,
            )
        except Exception as e:
            print(f"[report_service] satellite image error: {e}")

    # ── 1c. SVG polygon points (from WKT) ────────────────────────────────────
    shape_wkt_pixels: str = ""
    if satellite_b64 and parcel.shape_wkt and centroid_x and centroid_y:
        shape_wkt_pixels = _wkt_to_svg_points(
            parcel.shape_wkt, centroid_x, centroid_y,
            img_width=_SAT_IMG_WIDTH,
            img_height=_SAT_IMG_HEIGHT,
            buffer=_SAT_BUFFER,
        )

    # ── 2. Convert to TM35 for iplan ─────────────────────────────────────────
    cx_tm35: Optional[float] = None
    cy_tm35: Optional[float] = None
    if centroid_x and centroid_y:
        cx_tm35, cy_tm35 = _T_3857_TO_TM35.transform(centroid_x, centroid_y)

    # ── 3. iplan Layer 1: plans ───────────────────────────────────────────────
    plans_raw: List[Any] = []
    if cx_tm35 and cy_tm35:
        try:
            plans_raw = await get_plans_by_centroid(cx_tm35, cy_tm35)
        except Exception as e:
            print(f"[report_service] plans fetch error: {e}")

    # ── 4. iplan Layer 4: land use ────────────────────────────────────────────
    land_use_raw: List[Any] = []
    if cx_tm35 and cy_tm35:
        try:
            land_use_raw = await get_land_use_by_centroid(cx_tm35, cy_tm35)
        except Exception as e:
            print(f"[report_service] land_use fetch error: {e}")

    # ── 5. Sort plans: local(1) → district(2) → national(3) ──────────────────
    # Build (order, plan) tuples without mutating the Pydantic model
    plans_with_order = [(_classify_plan(p), p) for p in plans_raw]
    plans_with_order.sort(key=lambda t: t[0])

    # Build display dicts for template
    plans_display: List[Dict] = []
    for order, p in plans_with_order:
        raw_status = p.station_desc or p.internet_short_status or ""
        plans_display.append({
            "pl_name":             p.pl_name,
            "pl_number":           p.pl_number,
            "mavat_name":          p.mavat_name,
            "status_display":      _translate_status(raw_status),
            "plan_charactor_name": p.plan_charactor_name,
            "pl_objectives":       p.pl_objectives,
            "pl_url":              p.pl_url,
            "plan_type_order":     order,
            "date_display":        _epoch_to_year(p.pl_date_8 or p.pl_date7),
        })

    # ── 6. Land use display items ─────────────────────────────────────────────
    land_use_items: List[Dict] = []
    seen_yiud: set = set()
    for lu in land_use_raw:
        yiud = lu.yiud or lu.yiud_heb or ""
        if yiud and yiud not in seen_yiud:
            seen_yiud.add(yiud)
            land_use_items.append({
                "yiud":          yiud,
                "yiud_explained": _translate_yiud(yiud),
                "area_dunam":    lu.area_dunam,
            })

    # ── 7. Extract city name from plan metadata ───────────────────────────────
    # מחפש עיר/יישוב — plan_county_name עדיף על district_name (שהוא מחוז)
    # מסנן שמות מחוזות: "מרכז", "תל אביב" (מחוז), "ירושלים" (מחוז), "צפון", "דרום", "חיפה" (מחוז)
    _DISTRICT_NAMES = {"מרכז", "צפון", "דרום", "חיפה", "ירושלים", "תל אביב"}

    city = ""
    for p in plans_raw[:10]:
        county = getattr(p, "plan_county_name", None) or ""
        district = getattr(p, "district_name", None) or ""
        # county = עיר/רשות מקומית — עדיף
        if county and county.strip() not in _DISTRICT_NAMES:
            city = county.strip()
            break
        # district = מחוז — רק אם אין county טוב יותר
        if district and district.strip() not in _DISTRICT_NAMES:
            city = district.strip()
            # אל תפסיק — אולי יש county טוב יותר בהמשך

    # ── 8. Build timeline (plans with dates) ─────────────────────────────────
    timeline_plans = [
        d for d in plans_display
        if d.get("date_display")
    ]
    timeline_plans.sort(key=lambda d: d.get("date_display") or "0", reverse=True)

    # ── 9. Claude AI analysis ─────────────────────────────────────────────────
    yiud_list = ", ".join(lu["yiud"] for lu in land_use_items[:5]) if land_use_items else "לא ידוע"
    plans_summary = "; ".join(
        "{} ({})".format(p.get("pl_name") or p.get("mavat_name") or "", p.get("status_display") or "")
        for p in plans_display[:6]
        if p.get("pl_name") or p.get("mavat_name")
    )

    area_line = f"{area_sqm:.0f} מ\"ר" if area_sqm else "לא ידוע"
    city_line  = f", עיר {city}" if city else ""
    ai_prompt = (
        f"נתוני חלקה:\n"
        f"גוש {gush}, חלקה {helka}{city_line}\n"
        f"שטח: {area_line}\n"
        f"ייעודי קרקע: {yiud_list}\n"
        f"תכניות: {plans_summary}\n\n"
        "כתוב פסקה אחת קצרה (3-4 משפטים) בעברית פשוטה, המסבירה למשקיע פרטי "
        "מה המשמעות התכנונית המעשית של החלקה הזו — מה מותר לבנות, "
        "מה הסטטוס הנוכחי, ומה כדאי לשים לב אליו. "
        "אל תיתן ייעוץ השקעתי."
    )

    ai_analysis = ""
    try:
        ai_analysis = await _call_claude([{"role": "user", "content": ai_prompt}])
    except Exception as e:
        print(f"[report_service] Claude error: {e}")
        ai_analysis = "ניתוח AI לא זמין כרגע."

    # ── 10. Render template ───────────────────────────────────────────────────
    # (map_url removed — using Leaflet.js interactive map instead)
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=False)
    template = env.get_template("report.html")

    created_at = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    html = template.render(
        gush=gush,
        helka=helka,
        city=city,
        area_sqm=area_sqm,
        area_dunam=area_dunam,
        centroid_x=centroid_x,
        centroid_y=centroid_y,
        shape_wkt=parcel.shape_wkt,
        shape_wkt_pixels=shape_wkt_pixels,
        satellite_b64=satellite_b64,
        land_use_items=land_use_items,
        plans=plans_display,
        timeline_plans=timeline_plans,
        ai_analysis=ai_analysis,
        created_at=created_at,
        re=real_estate,
    )

    return html

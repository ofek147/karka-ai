"""
report_service.py — שולף נתונים על חלקה ומייצר ReportData מובנה

Flow:
1. govmap — parcel geometry (centroid EPSG:3857, area)
2. Convert centroid EPSG:3857 → TM35 (EPSG:2039) for iplan
3. iplan Layer 1 — plans with full metadata
4. iplan Layer 4 — land use zones
5. real_estate — עסקאות + מחיר למ"ר (parallel עם iplan)
6. mavat — PDF text per plan → cached in DB
7. Claude שלב 1 — summarize_plan() per plan → JSON (cached in DB as summary_json)
8. Claude שלב 2 — synthesize_plans() → JSON מסונתז
9. Calculations שכבה 3 — חישובי שווי + חלק יחסי
10. Claude final analysis — ניתוח Hebrew חופשי
11. Return ReportData מובנה
"""

from __future__ import annotations

import asyncio
import datetime
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.govmap_client import get_parcel_geometry
from ..clients.iplan_client import get_plans_by_centroid, get_land_use_by_centroid
from ..clients.mavat_client import fetch_plan_pdf_text_from_url
from ..clients.real_estate_client import get_real_estate_stats
from ..services.claude_service import _call_claude, summarize_plan, synthesize_plans
from ..services.plan_cache_service import (
    get_cached_plan,
    set_cached_plan_text,
    set_cached_plan_summary,
    get_cached_plan_summary_json,
    set_cached_plan_summary_json,
)
from ..services.calculations import compute_parcel_layer3
from ..utils.report_utils import (
    _translate_status, _translate_yiud,
    _epoch_to_year, _classify_plan,
)


def _reproject(x: float, y: float) -> tuple:
    """Convert EPSG:3857 → EPSG:2039 (TM35)."""
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:3857", "EPSG:2039", always_xy=True).transform(x, y)


def _parse_json_safe(raw: str) -> Optional[dict]:
    """Parse JSON string safely, return None on failure."""
    try:
        return json.loads(raw)
    except Exception:
        return None


# ── מבנה נתוני הדוח ──────────────────────────────────────────────────────────

@dataclass
class ReportData:
    """
    נתוני הדוח המלא — 3 שכבות + ניתוח.
    מוחזר מ-generate_report() ומשמש לעיבוד HTML ו-text.
    """
    # Layer 1 — ספציפי לחלקה
    gush: int
    helka: int
    city: str
    area_sqm: Optional[float]
    area_dunam: Optional[float]
    land_use_items: List[Dict]          # [{yiud, yiud_explained, area_dunam}]
    plans_raw: List[Any]                # PlanInfo objects

    # Layer 2 — גנרי מסינתזת תכניות
    plan_summaries_json: List[dict]     # תוצאות שלב 1 per plan
    synthesis: Optional[dict]          # תוצאת שלב 2 (synthesize_plans)

    # Layer 3 — חישובים
    calculations: Optional[dict]       # ParcelCalculations.to_dict()

    # ניתוח סופי
    ai_analysis: str
    plans_with_pdf: set
    plans_no_pdf: set

    # מטה
    created_at: str = field(default_factory=lambda: datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))


# ── פונקציה ראשית ────────────────────────────────────────────────────────────

async def generate_report(gush: int, helka: int, db: Optional[AsyncSession] = None) -> ReportData:
    """
    מייצר ReportData מלא לחלקה.

    Args:
        gush:  Block number (מספר גוש)
        helka: Parcel number (מספר חלקה)
        db:    Optional DB session for plan cache

    Returns:
        ReportData מובנה
    """
    # ── 1. govmap: parcel geometry ────────────────────────────────────────────
    parcel = await get_parcel_geometry(gush, helka)
    centroid_x = parcel.centroid_x
    centroid_y = parcel.centroid_y
    area_sqm   = parcel.area_sqm
    area_dunam = round(area_sqm / 1000, 3) if area_sqm else None

    # ── 2. Convert to TM35 ───────────────────────────────────────────────────
    cx_tm35: Optional[float] = None
    cy_tm35: Optional[float] = None
    if centroid_x and centroid_y:
        cx_tm35, cy_tm35 = _reproject(centroid_x, centroid_y)

    # ── 3. iplan + real_estate — parallel ────────────────────────────────────
    plans_raw: List[Any] = []
    land_use_raw: List[Any] = []
    re_stats = None

    if cx_tm35 and cy_tm35:
        plans_raw, land_use_raw, re_stats = await asyncio.gather(
            _safe(get_plans_by_centroid(cx_tm35, cy_tm35), [], "plans"),
            _safe(get_land_use_by_centroid(cx_tm35, cy_tm35), [], "land_use"),
            _safe(get_real_estate_stats(gush, helka), None, "real_estate"),
        )

    # ── 4. Sort plans ─────────────────────────────────────────────────────────
    plans_raw.sort(key=lambda p: _classify_plan(p))

    # ── 5. Extract city ───────────────────────────────────────────────────────
    city = _extract_city(plans_raw)

    # ── 6. Land use display ───────────────────────────────────────────────────
    land_use_items: List[Dict] = []
    seen: set = set()
    for lu in land_use_raw:
        yiud = lu.yiud or lu.yiud_heb or ""
        if yiud and yiud not in seen:
            seen.add(yiud)
            land_use_items.append({
                "yiud":           yiud,
                "yiud_explained": _translate_yiud(yiud),
                "area_dunam":     lu.area_dunam,
            })

    # ── 7. שלב 1: summarize each plan → JSON (cached as summary_json) ─────────
    plan_summaries_json: List[dict] = []
    plans_with_pdf: set = set()
    plans_no_pdf: set = set()

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

            # בדוק cache summary_json קודם
            cached_json_str = await get_cached_plan_summary_json(db, plan.pl_number)
            if cached_json_str:
                parsed = _parse_json_safe(cached_json_str)
                if parsed:
                    plan_summaries_json.append(parsed)
                    plans_with_pdf.add(plan.pl_number)
                    print(f"[report_service] Plan {plan.pl_number}: summary_json from cache")
                    continue

            # בדוק cache pdf_text
            cached_row = await get_cached_plan(db, plan.pl_number, last_modified=last_modified)
            pdf_text = cached_row.pdf_text if cached_row else None

            if not pdf_text:
                pdf_text = await fetch_plan_pdf_text_from_url(plan.pl_url)
                if pdf_text:
                    await set_cached_plan_text(db, plan.pl_number, pdf_text, plan.pl_url)

            if not pdf_text:
                plans_no_pdf.add(plan.pl_number)
                print(f"[report_service] Plan {plan.pl_number}: no PDF, skipping")
                continue

            try:
                label = plan.pl_name or plan.pl_number or plan.mavat_name or ""
                raw_json_str = await summarize_plan(
                    plan_name=label,
                    plan_number=plan.pl_number or "",
                    pdf_text=pdf_text,
                )
                # שמור ב-DB
                await set_cached_plan_summary_json(db, plan.pl_number, raw_json_str)
                # שמור גם ב-summary (legacy)
                await set_cached_plan_summary(db, plan.pl_number, raw_json_str)

                parsed = _parse_json_safe(raw_json_str)
                if parsed:
                    plan_summaries_json.append(parsed)
                    plans_with_pdf.add(plan.pl_number)
                    print(f"[report_service] Plan {plan.pl_number}: summarized JSON ({len(raw_json_str)} chars)")
                else:
                    print(f"[report_service] Plan {plan.pl_number}: JSON parse failed, skipping")
                    plans_no_pdf.add(plan.pl_number)

            except Exception as e:
                plans_no_pdf.add(plan.pl_number)
                print(f"[report_service] Plan {plan.pl_number}: summarize error: {e}")

    # ── 8. שלב 2: synthesize_plans → JSON מסונתז ─────────────────────────────
    synthesis: Optional[dict] = None
    if plan_summaries_json:
        try:
            raw_synthesis = await synthesize_plans(plan_summaries_json)
            synthesis = _parse_json_safe(raw_synthesis)
            if not synthesis:
                print(f"[report_service] synthesis JSON parse failed, using first plan summary")
                synthesis = plan_summaries_json[0] if plan_summaries_json else None
        except Exception as e:
            print(f"[report_service] synthesize_plans error: {e}")

    # ── 9. שכבה 3: חישובים ───────────────────────────────────────────────────
    calculations: Optional[dict] = None
    if synthesis:
        try:
            calc = compute_parcel_layer3(
                parcel_size_sqm=area_sqm,
                synthesis=synthesis,
                re_stats=re_stats,
                approval_years=7,
            )
            calculations = calc.to_dict()
        except Exception as e:
            print(f"[report_service] calculations error: {e}")

    # ── 10. Claude final analysis ─────────────────────────────────────────────
    yiud_list = ", ".join(lu["yiud"] for lu in land_use_items[:5]) or "לא ידוע"
    def _plan_status(p) -> str:
        """internet_short_status הוא האמין — station_desc מחזיר 'אחר' כברירת מחדל בiplan."""
        iss = (p.internet_short_status or "").strip()
        if iss:
            return iss
        return _translate_status(p.station_desc or "")

    plans_list = "\n".join(
        f"- {p.pl_name or p.mavat_name or p.pl_number} ({_plan_status(p)})"
        for p in plans_raw[:8]
    )
    area_line = f"{area_sqm:.0f} מ\"ר ({area_dunam} דונם)" if area_sqm else "לא ידוע"
    city_line = f", {city}" if city else ""

    # הוסף נתוני סינתזה וחישובים לפרומפט
    synthesis_block = ""
    if synthesis:
        u = synthesis.get("total_units")
        sz = synthesis.get("plan_size_dunam")
        stage = synthesis.get("plan_stage", "")
        timeline = synthesis.get("timeline_estimate", "")
        primary = synthesis.get("primary_plan", "")
        has_detailed = synthesis.get("has_detailed_plan", False)
        # P2: ציטוט מקור ליד נתונים כמותיים
        src_note = f" (מקור: {primary})" if primary else ""
        synthesis_block = f"\n\nסינתזת תכניות: שלב: {stage}, ציר זמן: {timeline}"
        if u and sz:
            synthesis_block += f"\nנתוני תכנית{src_note}: {u:,} יח\"ד על {sz:,} דונם — אלו נתוני התכנית הכוללת, לא ספציפיים לחלקה"
        synthesis_block += f"\nהיתרי בנייה: {'קיימת תכנית מפורטת בתוקף' if has_detailed else 'נדרשת תכנית מפורטת'}"
        if synthesis.get("warnings"):
            synthesis_block += f"\nאזהרות: {'; '.join(synthesis['warnings'][:3])}"

    calc_block = ""
    if calculations:
        av = calculations.get("available_land_value")
        unav = calculations.get("unavailable_land_value")
        ppm = calculations.get("price_per_sqm")
        eu = calculations.get("estimated_units_for_parcel")
        note = calculations.get("price_note", "")
        calc_block = (
            f"\n\nנתונים כלכליים (לצרכי הצגה בלבד):"
            f"\n- מחיר למ\"ר: ₪{ppm:,.0f} ({note})" if ppm else ""
        )
        # estimated_units הוסר — לא רלוונטי לחלקה (מבוסס יחס אזורי מתמל)
        if av:
            calc_block += f"\n- שווי קרקע זמינה (ל-100 מ\"ר): ₪{av:,.0f}"
        if unav:
            calc_block += f"\n- שווי קרקע לא זמינה (7 שנים): ₪{unav:,.0f}"

    # P2 — breakdown שטחי ייעוד לפי Layer 4
    residential_sqm = 0.0
    non_residential_sqm = 0.0
    RESIDENTIAL_KEYWORDS = ("מגורים",)
    NON_RESIDENTIAL_KEYWORDS = ("דרך", "שצפ", "שטח ציבורי", "מבנצ", "מוסדות ציבור")
    for lu in land_use_items:
        yiud_str = lu.get("yiud", "")
        area_d = lu.get("area_dunam") or 0
        area_m = area_d * 1000
        if any(k in yiud_str for k in RESIDENTIAL_KEYWORDS):
            residential_sqm += area_m
        elif any(k in yiud_str for k in NON_RESIDENTIAL_KEYWORDS):
            non_residential_sqm += area_m

    yiud_breakdown = ""
    if residential_sqm > 0 or non_residential_sqm > 0:
        yiud_breakdown = f"\nשטח מגורים בחלקה: ~{residential_sqm:,.0f} מ\u0022ר | שטחים לא לבנייה: ~{non_residential_sqm:,.0f} מ\u0022ר"

    ai_prompt = (
        f"נתוני חלקה:\n"
        f"גוש {gush}, חלקה {helka}{city_line}\n"
        f"שטח: {area_line}{yiud_breakdown}\n"
        f"ייעודי קרקע: {yiud_list}\n\n"
        f"תכניות רלוונטיות:\n{plans_list}"
        f"{synthesis_block}"
        f"{calc_block}\n\n"
        "כתוב ניתוח תכנוני בעברית פשוטה עבור משקיע פרטי. 7-10 משפטים. ללא markdown.\n"
        "התחל ישירות — ללא 'הנה', 'בהחלט', 'היי'.\n"
        "חובה לכסות לפי הסדר:\n"
        "1. מצב תכנוני נוכחי — האם ניתן להוציא היתר ישירות או נדרשת תכנית מפורטת.\n"
        "2. מה מותר לבנות — לפי ייעוד (מגורים ב'/ד', מבנ\"צ, שצ\"פ) וכמה מהחלקה פנוי לבנייה.\n"
        "3. מגבלות ספציפיות — שימור, דרכים מוצעות, שטחים ציבוריים.\n"
        "4. פוטנציאל ריאלי — הערכה לפי ייעוד + שטח + סוג בנייה (לא מחישוב תמל).\n"
        "5. ציר זמן משוער — כמה שנים עד מימוש.\n"
        "6. שווי כלכלי — מה מחיר השוק אומר על הקרקע (אם יש נתונים).\n"
        "7. מה חובה לבדוק לפני קנייה.\n"
        "אל תיתן ייעוץ השקעתי. אל תציין יח\"ד מבוססות יחס אזורי מתמל."
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

    return ReportData(
        gush=gush,
        helka=helka,
        city=city,
        area_sqm=area_sqm,
        area_dunam=area_dunam,
        land_use_items=land_use_items,
        plans_raw=plans_raw,
        plan_summaries_json=plan_summaries_json,
        synthesis=synthesis,
        calculations=calculations,
        ai_analysis=ai_analysis,
        plans_with_pdf=plans_with_pdf,
        plans_no_pdf=plans_no_pdf,
    )

# ── פונקציות עזר ─────────────────────────────────────────────────────────────

async def _safe(coro, default, label: str):
    """Run a coroutine safely, returning default on error."""
    try:
        result = await coro
        if isinstance(result, list):
            print(f"[report_service] {label}: {len(result)}")
        else:
            print(f"[report_service] {label}: ok")
        return result
    except Exception as e:
        import traceback
        print(f"[report_service] {label} ERROR: {e}")
        print(traceback.format_exc()[-500:])
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


# ── Backward compatibility ────────────────────────────────────────────────────

async def generate_report_text(gush: int, helka: int, db=None) -> str:
    """
    Legacy wrapper — מחזיר text string.
    Worker.py קורא לפונקציה הזו — נשמרת לתאימות לאחור.
    """
    data = await generate_report(gush, helka, db=db)
    return _report_data_to_text(data)


def _report_data_to_text(data: ReportData) -> str:
    """המר ReportData ל-text string (לשימוש ב-email / legacy)."""
    area_line = f"{data.area_sqm:.0f} מ\"ר ({data.area_dunam} דונם)" if data.area_sqm else "לא ידוע"

    # בנה map pl_number → plan_type + can_issue_permit מסיכומי שלב א'
    plan_type_map = {}
    for s in (data.plan_summaries_json or []):
        num = s.get("plan_number", "")
        pt = s.get("plan_type", "")
        can = s.get("can_issue_permit", None)
        if num:
            plan_type_map[num] = (pt, can)

    def _plan_type_tag(p) -> str:
        """תג plan_type ברור — מתארית/ארצית = אינה מזכה בהיתר, מפורטת = מזכה"""
        num = p.pl_number or ""
        pt, can = plan_type_map.get(num, ("", None))
        if can is True:
            return " [מפורטת — מזכה בהיתר]"
        if can is False and pt:
            type_label = pt if pt else "מתארית/ארצית"
            return f" [{type_label} — אינה מזכה בהיתר ישירות]"
        return ""

    lines = [
        f"דוח תכנוני — גוש {data.gush}, חלקה {data.helka}",
        f"{'עיר: ' + data.city if data.city else ''}",
        f"שטח: {area_line}",
        f"תאריך הפקה: {data.created_at}",
        "",
        "ייעוד קרקע:",
        *[f"  • {lu['yiud']}" for lu in data.land_use_items],
        "",
        "תכניות רלוונטיות:",
        *[
            f"  • {p.pl_name or p.mavat_name or p.pl_number}"
            f"{' (' + ((p.internet_short_status or '').strip() or _translate_status(p.station_desc or '')) + ')' if ((p.internet_short_status or '').strip() or _translate_status(p.station_desc or '')) else ''}"
            f"{_plan_type_tag(p)}"
            f"{' [' + _epoch_to_year(p.pl_date_8 or getattr(p, 'pl_date7', None)) + ']' if _epoch_to_year(p.pl_date_8 or getattr(p, 'pl_date7', None)) else ''}"
            for p in data.plans_raw[:8]
        ],
    ]

    # הערכה כלכלית — שכבה 3
    # estimated_units + sqm_per_unit הוסרו — חישוב מתמל לא רלוונטי לחלקה ספציפית
    if data.calculations:
        c = data.calculations
        calc_lines = ["", "הערכה כלכלית:"]
        if c.get("price_per_sqm"):
            note = "*" if c.get("price_source") == "fallback" else ""
            calc_lines.append(f"  • מחיר למ\"ר (ממוצע עסקאות שכונה, 3 שנים): ₪{c['price_per_sqm']:,.0f}{note}")
        if c.get("apartment_price_100"):
            calc_lines.append(f"  • מחיר דירה 100 מ\"ר: ₪{c['apartment_price_100']:,.0f}")
        if c.get("available_land_value"):
            calc_lines.append(f"  • שווי קרקע זמינה ליח\"ד תיאורטית של 100 מ\"ר בנייה: ₪{c['available_land_value']:,.0f}")
        if c.get("unavailable_land_value"):
            years = c.get("approval_years", 7)
            calc_lines.append(f"  • שווי קרקע לא זמינה (היוון {years} שנות המתנה): ₪{c['unavailable_land_value']:,.0f}")
        if c.get("price_source") == "fallback":
            calc_lines.append("  * מחיר דוגמתי — יעודכן לפי נתוני שוק")
        if len(calc_lines) > 2:
            lines += calc_lines

    lines += [
        "",
        "ניתוח תכנוני:",
        data.ai_analysis,
        "",
        "---",
        "karkAi — ניתוח קרקעות חכם | המידע אינו מהווה ייעוץ משפטי או השקעתי.",
    ]

    return "\n".join(line for line in lines if line is not None)

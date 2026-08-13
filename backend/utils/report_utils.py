"""
report_utils.py — Shared utilities for the karka-ai report engine.

Contains status/land-use translation maps and small helper functions
used by report_service.py and potentially other services.
"""

import datetime
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Status translation
# ---------------------------------------------------------------------------

# (substring_to_match, short_display_label)
# התרגום קצר בלבד — יופיע בסוגריים ליד שם התכנית
_STATUS_MAP = [
    ("בוטלה",                   "בוטלה"),
    ("אחסון",                    "ארכיב"),
    ("הכרעה בהתנגדויות",   "בתהליך אישור"),
    ("לפני הפקדה",               "לפני הפקדה"),
    ("בהפקדה",                   "בהפקדה"),
    ("הפקדה",                    "בהפקדה"),
    ("תקף",                      "בתוקף"),
    ("מאושר",                    "בתוקף"),
    ("בתכנון",                   "בתכנון"),
]

# ערכים שצריך להסיר לחלוטין (גנריים ולא אינפורמטיביים)
_STATUS_REMOVE = {"אחר", "other", "none", ""}


def _translate_status(status: str) -> str:
    """
    מחזיר תווית קצרה לסטטוס תכנית.
    אם אין תרגום — מחזיר את ה-station_desc המקורי מiplan.
    אם הערך גנרי (אחר/none) — מחזיר ריק.
    """
    if not status:
        return ""
    s = status.strip()
    if s.lower() in _STATUS_REMOVE:
        return ""
    for key, val in _STATUS_MAP:
        if key in s:
            return val
    # החזר את הערך המקורי מiplan — כנראה כבר עברית קריאה
    return s


# ---------------------------------------------------------------------------
# Land-use (yiud) translation
# ---------------------------------------------------------------------------

_YIUD_MAP: Dict[str, str] = {
    "מגורים א":    "מגורים א' (בנייה צמודת קרקע נמוכה — בתים פרטיים)",
    "מגורים א'":   "מגורים א' (בנייה צמודת קרקע נמוכה — בתים פרטיים)",
    "מגורים ב":    "מגורים ב' (בנייה צמודת קרקע — בתים פרטיים)",
    "מגורים ב'":   "מגורים ב' (בנייה צמודת קרקע — בתים פרטיים)",
    "מגורים ג":    "מגורים ג' (בנייה נמוכה — 2–4 קומות)",
    "מגורים ג'":   "מגורים ג' (בנייה נמוכה — 2–4 קומות)",
    "מגורים ד":    "מגורים ד' (בנייה רוויה — בניינים רב-קומתיים)",
    "מגורים ד'":   "מגורים ד' (בנייה רוויה — בניינים רב-קומתיים)",
    "מגורים ה":    "מגורים ה' (בנייה רוויה גבוהה)",
    "מגורים ה'":   "מגורים ה' (בנייה רוויה גבוהה)",
    "מגורים":      "מגורים (אזור בנייה למגורים)",
    'שצ"פ':        'שצ"פ (שטח ציבורי פתוח — גן/פארק)',
    'מבנ"צ':       'מבנ"צ (מבנים ומוסדות ציבור — בית ספר, קליניקה וכו\')',
    "תעסוקה":      "תעסוקה (אזור תעשייה / עסקים)",
    "מסחר":        "מסחר (שימוש מסחרי)",
    "תיירות":      "תיירות ואירוח",
    "דרך מוצעת":   "דרך מוצעת (שמורת דרך עתידית — לא ניתן לבנות)",
    "דרך":         "דרך (שמורת דרך — לא ניתן לבנות)",
    "חקלאי":       "חקלאי (שטח חקלאי — הגבלות בנייה)",
    "חקלאית":      "חקלאית (שטח חקלאי — הגבלות בנייה)",
    "שטח פתוח":    "שטח פתוח (אין היתר בנייה)",
    "יער":         "יער / טבע (שמורה — אסור לבנות)",
    "תשתיות":      "תשתיות (מבני ציבור ותשתית)",
    "מלונאות":     "מלונאות / הכנסת אורחים",
    "ספורט":       "ספורט ופנאי",
    "בינוי פנים":  "בינוי פנים (אזור מגורים מוסדר)",
}


def _translate_yiud(yiud: str) -> str:
    """Add plain-language explanation to land-use type."""
    if not yiud:
        return yiud or ""
    y = yiud.strip()
    # Exact match first
    if y in _YIUD_MAP:
        return _YIUD_MAP[y]
    # Longest prefix match
    best = None
    for key, val in _YIUD_MAP.items():
        if y.startswith(key) or key in y:
            if best is None or len(key) > len(best[0]):
                best = (key, val)
    if best:
        return best[1]
    return y


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _epoch_to_year(epoch_ms: Optional[int]) -> Optional[str]:
    """Convert epoch milliseconds to year string."""
    if not epoch_ms:
        return None
    try:
        return str(datetime.datetime.fromtimestamp(epoch_ms / 1000).year)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Plan classification
# ---------------------------------------------------------------------------

def _classify_plan(plan: Any) -> int:
    """Return sort order: 1 = local/detailed, 2 = district, 3 = national."""
    charactor = (getattr(plan, "plan_charactor_name", "") or "").lower()
    mavat = (getattr(plan, "mavat_name", "") or "").lower()
    pl_name = (getattr(plan, "pl_name", "") or "").lower()
    combined = mavat + " " + pl_name
    if any(k in combined for k in ("תמא", "תתל", "תמל")):
        return 3
    if "ארצית" in charactor:
        return 3
    if "מחוזית" in charactor:
        return 2
    return 1

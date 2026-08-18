"""
plan_graph_service.py — דטרמיניסטי לחלוטין, ללא Claude.

בונה גרף יחסים בין תכניות מתוך relations[] שחולצו בשלב 1,
ופותר שתי שאלות:
  1. governing_plan  — התכנית הקובעת הנוכחית (מאושרת, מזכה בזכויות)
  2. forward_plan    — התכנית המתקדמת ביותר שטרם אושרה

כללים (לפי סעיפים 129-131 לחוק התכנון והבנייה):
  - ברירת מחדל: תכנית ברמה גבוהה יותר גוברת
  - אבל: grants_permits=true / contains_detailed_provisions=true
    גוברים על ברירת המחדל (בדיוק כמנגנון "אלא אם נאמר אחרת")
  - תכנית שבוטלה על ידי תכנית מאושרת אחרת = לא active
  - overlays (is_overlay=True) = לא נכנסות לגרף הזכויות

confidence:
  high  — relations חולצו מסעיף 1.6 ברור
  low   — relations חסרות/לא ודאיות → ברירת מחדל היררכית
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


# ── סדר ברירת מחדל היררכי (גבוה = גובר) ──────────────────────────────────

_PLAN_TYPE_RANK = {
    "ארצית":   4,
    "מחוזית":  3,
    "מתארית":  2,
    "מפורטת":  1,
}

# סטטוסים שנחשבים "מאושרים" (מ-iplan internet_short_status)
_APPROVED_STATUSES = {
    "התכנית אושרה", "פרסום אישור", "בתוקף", "אושרה",
}

# סטטוסים "בדרך לאישור" (forward_plan candidates)
_IN_PROGRESS_STATUSES = {
    "בתהליך הפקדה", "בהפקדה", "הפקדה", "בדיון", "בתכנון",
    "הכרעה בהתנגדויות", "לפני הפקדה",
}

# עדיפות forward_plan (נמוך = מתקדם יותר)
_FORWARD_STAGE_PRIORITY = {
    "הכרעה בהתנגדויות": 1,
    "בהפקדה": 2,
    "הפקדה": 2,
    "בתהליך הפקדה": 3,
    "בדיון": 4,
    "לפני הפקדה": 5,
    "בתכנון": 6,
}


# ── מבנה נתונים ───────────────────────────────────────────────────────────

@dataclass
class PlanNode:
    """ייצוג פנימי של תכנית בגרף."""
    plan_number: str
    plan_name: str
    plan_stage: str           # מ-iplan (אמין יותר מ-PDF)
    plan_type: str            # ארצית/מחוזית/מתארית/מפורטת
    grants_permits_scope: Optional[str]   # "general_building_rights" | "narrow_purpose" | "none" | null
    can_issue_permit: Optional[bool]

    @property
    def grants_permits(self) -> bool:
        """Derived: True if scope is general or narrow (any kind of permit)."""
        return self.grants_permits_scope in ("general_building_rights", "narrow_purpose")
    is_overlay: bool
    relations: List[dict]     # [{target, type, note}]
    relations_confidence: str  # "high" | "low"


@dataclass
class GraphResult:
    """תוצאת פתרון הגרף."""
    governing_plan: Optional[str]          # שם תכנית קובעת, או None
    governing_plan_number: Optional[str]
    governing_confidence: str              # "high" | "low" | "none"
    governing_basis: str                   # "explicit_1.6" | "statutory_default" | "grants_permits"

    forward_plan: Optional[str]            # שם תכנית עתידית, או None
    forward_plan_number: Optional[str]
    forward_stage: Optional[str]

    overlay_plans: List[str]               # שמות תכניות overlay
    low_confidence_plans: List[str]        # תכניות שrelations שלהן confidence:low

    resolution_notes: List[str] = field(default_factory=list)  # הסברים לפתרון


# ── migration helper ─────────────────────────────────────────────────────────

def _migrate_grants_permits(s: dict) -> Optional[str]:
    """
    Backward-compat: cache ישן שומר grants_permits: bool (לפני schema חדש).
    אם summary_json מכיל grants_permits=True (ישן) ואין grants_permits_scope —
    נחשב כ-null (ambiguous) כי לא יודעים אם זה general או narrow.
    re-extraction יפתור את זה.
    """
    old = s.get("grants_permits")
    if old is True:
        return None  # ambiguous — re-extraction needed
    return "none"   # grants_permits=False → not granting any permit


# ── בניית הגרף ───────────────────────────────────────────────────────────

def build_graph(plan_summaries: List[dict], iplan_status_map: dict) -> List[PlanNode]:
    """
    בנה רשימת PlanNode מתוך plan_summaries (שלב 1 JSON) + iplan status.

    Args:
        plan_summaries: רשימת dict מ-summarize_plan()
        iplan_status_map: {pl_number: internet_short_status} מ-iplan Layer 1

    Returns:
        רשימת PlanNode מוכנה לפתרון
    """
    nodes = []
    for s in plan_summaries:
        pnum = s.get("plan_number", "")
        # iplan status גובר על מה שClaude חילץ מה-PDF
        iplan_stage = iplan_status_map.get(pnum, "")
        stage = iplan_stage or s.get("plan_stage", "") or ""

        nodes.append(PlanNode(
            plan_number=pnum,
            plan_name=s.get("plan_name", pnum),
            plan_stage=stage,
            plan_type=s.get("plan_type", ""),
            grants_permits_scope=s.get("grants_permits_scope") or _migrate_grants_permits(s),
            can_issue_permit=s.get("can_issue_permit"),
            is_overlay=bool(s.get("is_overlay", False)),
            relations=s.get("relations") or [],
            relations_confidence=s.get("relations_confidence", "low"),
        ))
    return nodes


# ── פתרון הגרף ───────────────────────────────────────────────────────────

def resolve_graph(nodes: List[PlanNode]) -> GraphResult:
    """
    פתור מי governing_plan ומי forward_plan.

    Logic:
    1. הסר overlays מהגרף הראשי (מוצגים בנפרד)
    2. הסר תכניות שבוטלו על ידי תכנית מאושרת אחרת
    3. מבין הנותרות שמאושרות:
       a. אם יש grants_permits=true → זו הקובעת (אפילו אם ארצית)
       b. אחרת → הגבוהה ביותר שלא "כפופה" לאחרת מהרשימה
    4. forward_plan = המתקדמת ביותר שטרם אושרה
    """
    notes = []
    overlay_plans = [n.plan_name for n in nodes if n.is_overlay]
    low_conf = [n.plan_name for n in nodes if n.relations_confidence == "low" and not n.is_overlay]

    # תכניות שמשתתפות בגרף הזכויות
    rights_nodes = [n for n in nodes if not n.is_overlay]

    # מי בוטל?
    cancelled = _find_cancelled(rights_nodes)

    # תכניות מאושרות ופעילות
    approved = [
        n for n in rights_nodes
        if _is_approved(n.plan_stage) and n.plan_number not in cancelled
    ]

    # תכניות בתהליך
    in_progress = [
        n for n in rights_nodes
        if _is_in_progress(n.plan_stage) and n.plan_number not in cancelled
    ]

    # ── governing_plan ──────────────────────────────────────────────────
    governing: Optional[PlanNode] = None
    governing_basis = "none"
    governing_confidence = "none"

    # עדיפות 1: grants_permits_scope=="general_building_rights" מתכנית מאושרת
    # narrow_purpose לא נכנסת לgoverning — מזכה בהיתר לנושא צר בלבד
    gp_candidates = [n for n in approved if n.grants_permits_scope == "general_building_rights"]
    if gp_candidates:
        governing = max(gp_candidates, key=lambda n: _plan_rank(n))
        governing_basis = "grants_permits"
        governing_confidence = governing.relations_confidence
        notes.append(f"governing_plan נקבע לפי grants_permits_scope=general_building_rights: {governing.plan_name}")

    # עדיפות 2: תכנית מפורטת מאושרת שלא כפופה לאחרת
    if not governing:
        detailed = [n for n in approved if n.plan_type == "מפורטת"]
        not_superseded = [n for n in detailed if not _is_superseded(n, approved)]
        if not_superseded:
            # אם יש כמה תכניות מפורטות — בחר את האחרונה בזמן (pl_date גבוה יותר)
            governing = not_superseded[-1]  # לאחרונה ברשימה (sorted by date in iplan)
            governing_basis = "approved_detailed_plan"
            governing_confidence = governing.relations_confidence
            notes.append(f"governing_plan: תכנית מפורטת מאושרת {governing.plan_name}")

    # עדיפות 3: ברירת מחדל היררכית — הגבוהה ביותר שמאושרת ולא כפופה
    if not governing and approved:
        not_superseded = [n for n in approved if not _is_superseded(n, approved)]
        if not_superseded:
            governing = max(not_superseded, key=lambda n: _plan_rank(n))
            governing_basis = "statutory_default"
            governing_confidence = "low"
            notes.append(f"governing_plan לפי ברירת מחדל היררכית: {governing.plan_name}")

    if low_conf:
        notes.append(f"תכניות עם confidence:low ביחסים (ברירת מחדל היררכית): {', '.join(low_conf)}")

    # ── forward_plan ────────────────────────────────────────────────────
    forward: Optional[PlanNode] = None
    if in_progress:
        forward = min(in_progress, key=lambda n: (
            _FORWARD_STAGE_PRIORITY.get(n.plan_stage, 99),
            -_plan_rank(n),
        ))
        notes.append(f"forward_plan: {forward.plan_name} ({forward.plan_stage})")

    return GraphResult(
        governing_plan=governing.plan_name if governing else None,
        governing_plan_number=governing.plan_number if governing else None,
        governing_confidence=governing_confidence,
        governing_basis=governing_basis,
        forward_plan=forward.plan_name if forward else None,
        forward_plan_number=forward.plan_number if forward else None,
        forward_stage=forward.plan_stage if forward else None,
        overlay_plans=overlay_plans,
        low_confidence_plans=low_conf,
        resolution_notes=notes,
    )


# ── פונקציות עזר ─────────────────────────────────────────────────────────

def _is_approved(stage: str) -> bool:
    s = (stage or "").strip()
    # exact match first, then substring (avoid 'לא בתוקף' matching 'בתוקף')
    if s in _APPROVED_STATUSES:
        return True
    # substring only for multi-word statuses that are always unambiguous
    return any(a in s for a in ("התכנית אושרה", "פרסום אישור"))


def _is_in_progress(stage: str) -> bool:
    s = (stage or "").strip()
    return any(p in s for p in _IN_PROGRESS_STATUSES)


def _plan_rank(node: PlanNode) -> int:
    """ציון היררכי לתכנית — גבוה יותר = עדיפות גבוהה יותר."""
    return _PLAN_TYPE_RANK.get(node.plan_type, 0)


def _find_cancelled(nodes: List[PlanNode]) -> set:
    """
    מוצא תכניות שבוטלו על ידי תכנית אחרת מאושרת.
    רק ביטול מתכנית מאושרת ספציפית = ביטול תקף.
    """
    approved_numbers = {n.plan_number for n in nodes if _is_approved(n.plan_stage)}
    cancelled = set()
    for n in nodes:
        if n.plan_number not in approved_numbers:
            continue
        for rel in (n.relations or []):
            if rel.get("type") == "ביטול":
                target = rel.get("target", "")
                if target:
                    cancelled.add(target)
    return cancelled


def _is_superseded(node: PlanNode, approved: List[PlanNode]) -> bool:
    """
    האם תכנית זו "כפופה" לתכנית אחרת מאושרת ברשימה?
    בודק אם node מדווחת על כפיפות ל-target שנמצא ברשימת approved.
    """
    approved_numbers = {n.plan_number for n in approved if n.plan_number != node.plan_number}
    for rel in (node.relations or []):
        if rel.get("type") == "כפיפות":
            target = rel.get("target", "")
            if target in approved_numbers:
                return True
    return False

"""
calculations.py — חישובי שכבה 3 לדוח karka-ai

מקבל נתוני שכבה 1 (חלקה מ-govmap) + שכבה 2 (סינתזת תכניות) + מחיר למ"ר
ומחשב את הערכים הכלכליים לדוח.

נוסחאות:
    sqm_per_unit          = plan_size_dunam × 1000 / total_units
    relative_share        = parcel_size_sqm / (plan_size_dunam × 1000)
    available_land_value  = (price_per_sqm × 100) - היטל_השבחה_50% - (13000 × 100) - רווח_יזמי_15%
    unavailable_land_value = available_land_value × (1.20)^(-approval_years)
    apartment_price_100   = price_per_sqm × 100
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── קבועים ──────────────────────────────────────────────────────────────────

# עלות פיתוח ותשתיות ל-100 מ"ר (₪)
DEVELOPMENT_COST_PER_UNIT = 13_000 * 100  # 1,300,000 ₪

# שיעור היטל השבחה (מחצית מהעלייה בשווי)
BETTERMENT_LEVY_RATE = 0.50

# שולי רווח יזמי
DEVELOPER_MARGIN_RATE = 0.15

# תשואת היוון לחישוב שווי קרקע לא זמינה
DISCOUNT_RATE = 1.20

# מחיר דוגמתי כשאין נתוני עסקאות (₪ למ"ר)
FALLBACK_PRICE_PER_SQM = 20_000
FALLBACK_NOTE = "מחיר דוגמתי — יעודכן לפי נתוני שוק בשלב 2"


# ── מבני נתונים ──────────────────────────────────────────────────────────────

@dataclass
class PriceSource:
    """מקור נתוני מחיר למ"ר."""
    price_per_sqm: float
    source: str          # "live" | "fallback"
    note: Optional[str] = None
    deal_count: int = 0
    trend_pct: Optional[float] = None
    trend_direction: str = "unknown"


@dataclass
class ParcelCalculations:
    """תוצאות חישובי שכבה 3 לחלקה."""

    # נתוני קלט
    parcel_size_sqm: Optional[float]
    plan_size_dunam: Optional[float]
    total_units: Optional[int]
    price_source: PriceSource

    # חישובים
    sqm_per_unit: Optional[float] = field(init=False, default=None)
    relative_share: Optional[float] = field(init=False, default=None)
    estimated_units_for_parcel: Optional[float] = field(init=False, default=None)
    apartment_price_100: Optional[float] = field(init=False, default=None)
    available_land_value: Optional[float] = field(init=False, default=None)
    unavailable_land_value: Optional[float] = field(init=False, default=None)

    # שנות אישור משוערות (לחישוב לא זמינה)
    approval_years: int = 7

    def __post_init__(self):
        self._compute()

    def _compute(self):
        p = self.price_source.price_per_sqm

        # מ"ר קרקע ליח"ד
        if self.plan_size_dunam and self.total_units and self.total_units > 0:
            self.sqm_per_unit = round(
                (self.plan_size_dunam * 1000) / self.total_units, 1
            )

        # חלק יחסי + יחידות לחלקה
        if self.parcel_size_sqm and self.plan_size_dunam and self.plan_size_dunam > 0:
            self.relative_share = round(
                self.parcel_size_sqm / (self.plan_size_dunam * 1000), 4
            )
            if self.total_units:
                self.estimated_units_for_parcel = round(
                    self.relative_share * self.total_units, 2
                )

        # מחיר דירה 100 מ"ר
        self.apartment_price_100 = round(p * 100)

        # שווי קרקע זמינה
        # = (מחיר × 100) - היטל 50% - עלות פיתוח - רווח יזמי 15%
        gross = p * 100
        betterment = gross * BETTERMENT_LEVY_RATE
        after_betterment = gross - betterment
        after_dev = after_betterment - DEVELOPMENT_COST_PER_UNIT
        available = after_dev * (1 - DEVELOPER_MARGIN_RATE)
        self.available_land_value = round(max(available, 0))

        # שווי קרקע לא זמינה (היוון לפי שנות אישור)
        if self.available_land_value and self.available_land_value > 0:
            self.unavailable_land_value = round(
                self.available_land_value / (DISCOUNT_RATE ** self.approval_years)
            )
        else:
            self.unavailable_land_value = 0

    def to_dict(self) -> dict:
        """המר לdict לשימוש בדוח."""
        return {
            "price_per_sqm": self.price_source.price_per_sqm,
            "price_source": self.price_source.source,
            "price_note": self.price_source.note,
            "deal_count": self.price_source.deal_count,
            "trend_pct": self.price_source.trend_pct,
            "trend_direction": self.price_source.trend_direction,
            "sqm_per_unit": self.sqm_per_unit,
            "relative_share": self.relative_share,
            "estimated_units_for_parcel": self.estimated_units_for_parcel,
            "apartment_price_100": self.apartment_price_100,
            "available_land_value": self.available_land_value,
            "unavailable_land_value": self.unavailable_land_value,
            "approval_years": self.approval_years,
        }


# ── פונקציות ציבוריות ─────────────────────────────────────────────────────────

def build_price_source_from_real_estate(re_stats) -> PriceSource:
    """
    בנה PriceSource מתוצאות real_estate_client.get_real_estate_stats().
    עדיפות: שכונה_1y → שכונה_3y → עיר_1y → עיר_3y → fallback.
    """
    candidates = [
        (re_stats.neighborhood_1y, re_stats.neighborhood_deal_count, "neighborhood_1y"),
        (re_stats.neighborhood_3y, re_stats.neighborhood_deal_count, "neighborhood_3y"),
        (re_stats.settlement_1y, 0, "settlement_1y"),
        (re_stats.settlement_3y, 0, "settlement_3y"),
    ]
    for price, count, label in candidates:
        if price and price > 0:
            return PriceSource(
                price_per_sqm=price,
                source="live",
                note=f"ממוצע עסקאות {label.replace('_', ' ')} (govmap)",
                deal_count=getattr(re_stats, f"neighborhood_deal_count", count),
                trend_pct=re_stats.trend_pct,
                trend_direction=re_stats.trend_direction,
            )

    # fallback
    return PriceSource(
        price_per_sqm=FALLBACK_PRICE_PER_SQM,
        source="fallback",
        note=FALLBACK_NOTE,
        deal_count=0,
    )


def compute_parcel_layer3(
    parcel_size_sqm: Optional[float],
    synthesis: dict,
    re_stats=None,
    approval_years: int = 7,
) -> ParcelCalculations:
    """
    חישובי שכבה 3 לחלקה.

    Args:
        parcel_size_sqm: שטח החלקה במ"ר (מ-govmap)
        synthesis: dict תוצאת synthesize_plans() (שלב 2)
        re_stats: RealEstateStats | None
        approval_years: שנות המתנה משוערות לאישור

    Returns:
        ParcelCalculations עם כל הנתונים
    """
    plan_size_dunam = synthesis.get("plan_size_dunam")
    total_units = synthesis.get("total_units")

    # המר strings ל-numbers אם צריך
    if isinstance(plan_size_dunam, str):
        try:
            plan_size_dunam = float(plan_size_dunam)
        except (ValueError, TypeError):
            plan_size_dunam = None

    if isinstance(total_units, str):
        try:
            total_units = int(float(total_units))
        except (ValueError, TypeError):
            total_units = None

    # מקור מחיר
    if re_stats is not None:
        price_source = build_price_source_from_real_estate(re_stats)
    else:
        price_source = PriceSource(
            price_per_sqm=FALLBACK_PRICE_PER_SQM,
            source="fallback",
            note=FALLBACK_NOTE,
        )

    return ParcelCalculations(
        parcel_size_sqm=parcel_size_sqm,
        plan_size_dunam=plan_size_dunam,
        total_units=total_units,
        price_source=price_source,
        approval_years=approval_years,
    )

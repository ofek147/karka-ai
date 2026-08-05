"""
real_estate_client.py — עסקאות נדל"ן מ-govmap real-estate API

3 endpoints:
- street-deals/{gush}-{helka}       → עסקאות על החלקה עצמה
- neighborhood-deals/{gush}-{helka} → עסקאות באותה שכונה
- settlement-deals/{gush}-{helka}   → עסקאות בעיר כולה

מחזיר ממוצע מחיר למ"ר לכל טווח (1/3/5 שנים) + מגמה.
ללא API token — endpoint פתוח לחלוטין.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional

import httpx

BASE = "https://www.govmap.gov.il/api/real-estate"


def _headers() -> dict:
    return {
        "Origin": "https://karka-ai.co.il",
        "Referer": "https://karka-ai.co.il/",
        "x-trace-id": str(uuid.uuid4()),
        "User-Agent": "Mozilla/5.0 (compatible; karka-ai/1.0)",
    }


def _start_date(years_back: int) -> str:
    d = datetime.now() - timedelta(days=365 * years_back)
    return d.strftime("%Y-%m")


def _end_date() -> str:
    return datetime.now().strftime("%Y-%m")


def _avg_price_per_sqm(deals: list) -> Optional[float]:
    """ממוצע מחיר למ"ר — מסנן עסקאות עם שטח 0 או 1 (לא מייצגות)."""
    valid = [d for d in deals if d.get("assetArea", 0) > 5 and d.get("dealAmount", 0) > 0]
    if not valid:
        return None
    prices = [d["dealAmount"] / d["assetArea"] for d in valid]
    return round(sum(prices) / len(prices))


async def _fetch_deals(endpoint: str, gush: int, helka: int, years_back: int) -> list:
    """שולף עסקאות מ-endpoint נתון עבור טווח זמן."""
    polygon_id = f"{gush}-{helka}"
    params = {
        "limit": 200,
        "offset": 0,
        "startDate": _start_date(years_back),
        "endDate": _end_date(),
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{BASE}/{endpoint}/{polygon_id}",
            headers=_headers(),
            params=params,
        )
        r.raise_for_status()
        return r.json().get("data", [])


@dataclass
class RealEstateStats:
    """תוצאות שליפת נתוני שוק נדל"ן לחלקה."""

    # ממוצע מחיר למ"ר — 3 טווחים × 3 רמות
    parcel_1y: Optional[float]
    parcel_3y: Optional[float]
    parcel_5y: Optional[float]
    neighborhood_1y: Optional[float]
    neighborhood_3y: Optional[float]
    neighborhood_5y: Optional[float]
    settlement_1y: Optional[float]
    settlement_3y: Optional[float]
    settlement_5y: Optional[float]
    # מגמה: % שינוי בין 1y ל-5y (בשכונה — הכי מייצג)
    trend_pct: Optional[float]       # חיובי = עלייה, שלילי = ירידה
    trend_direction: str             # "up" | "down" | "stable" | "unknown"
    # מספר עסקאות שנמצאו
    parcel_deal_count: int
    neighborhood_deal_count: int


async def get_real_estate_stats(gush: int, helka: int) -> RealEstateStats:
    """
    שולף נתוני עסקאות מ-3 endpoints ב-3 טווחים.
    מחשב ממוצעי מחיר למ"ר + מגמה.

    Args:
        gush:  מספר גוש
        helka: מספר חלקה

    Returns:
        RealEstateStats עם נתוני מחיר למ"ר ומגמה,
        או ערכי None בכל השדות אם השליפה נכשלה.
    """
    try:
        # שלוף כל הנתונים במקביל — 5 שנים, נחתוך אחר כך לטווחים קצרים
        # Total budget: 20s for all 3 endpoints combined
        parcel_5y_raw, neighborhood_5y_raw, settlement_5y_raw = await asyncio.wait_for(
            asyncio.gather(
                _fetch_deals("street-deals", gush, helka, 5),
                _fetch_deals("neighborhood-deals", gush, helka, 5),
                _fetch_deals("settlement-deals", gush, helka, 5),
            ),
            timeout=20.0,
        )

        # חתוך לטווחים קצרים יותר מתוך הנתונים שכבר יש
        now = datetime.now()

        def filter_years(deals: list, years: int) -> list:
            """מחזיר רק עסקאות מהשנים האחרונות."""
            cutoff = now - timedelta(days=365 * years)
            result = []
            for d in deals:
                raw_date = d.get("dealDate")
                if not raw_date:
                    continue
                try:
                    # תמיכה ב-ISO עם/בלי Z
                    deal_dt = datetime.fromisoformat(raw_date.replace("Z", ""))
                    if deal_dt > cutoff:
                        result.append(d)
                except ValueError:
                    continue
            return result

        parcel_1y = filter_years(parcel_5y_raw, 1)
        parcel_3y = filter_years(parcel_5y_raw, 3)
        neighborhood_1y = filter_years(neighborhood_5y_raw, 1)
        neighborhood_3y = filter_years(neighborhood_5y_raw, 3)
        settlement_1y = filter_years(settlement_5y_raw, 1)
        settlement_3y = filter_years(settlement_5y_raw, 3)

        # מגמה — לפי שכונה (הכי מייצג כי יש יותר עסקאות)
        n_1y_avg = _avg_price_per_sqm(neighborhood_1y)
        n_5y_avg = _avg_price_per_sqm(neighborhood_5y_raw)

        # Need at least 3 deals in each period for a meaningful trend
        n_1y_count = len(neighborhood_1y)
        n_5y_count = len(neighborhood_5y_raw)
        if n_1y_avg and n_5y_avg and n_5y_avg > 0 and n_1y_count >= 3 and n_5y_count >= 3:
            trend_pct = round(((n_1y_avg - n_5y_avg) / n_5y_avg) * 100, 1)
            # Cap at reasonable range — data anomalies protection
            if abs(trend_pct) > 60:
                trend_pct = None
                direction = "unknown"
            elif trend_pct > 2:
                direction = "up"
            elif trend_pct < -2:
                direction = "down"
            else:
                direction = "stable"
        else:
            trend_pct = None
            direction = "unknown"

        return RealEstateStats(
            parcel_1y=_avg_price_per_sqm(parcel_1y),
            parcel_3y=_avg_price_per_sqm(parcel_3y),
            parcel_5y=_avg_price_per_sqm(parcel_5y_raw),
            neighborhood_1y=_avg_price_per_sqm(neighborhood_1y),
            neighborhood_3y=_avg_price_per_sqm(neighborhood_3y),
            neighborhood_5y=_avg_price_per_sqm(neighborhood_5y_raw),
            settlement_1y=_avg_price_per_sqm(settlement_1y),
            settlement_3y=_avg_price_per_sqm(settlement_3y),
            settlement_5y=_avg_price_per_sqm(settlement_5y_raw),
            trend_pct=trend_pct,
            trend_direction=direction,
            parcel_deal_count=len(parcel_5y_raw),
            neighborhood_deal_count=len(neighborhood_5y_raw),
        )

    except Exception as e:
        print(f"[real_estate] ERROR: {e}")
        return RealEstateStats(
            parcel_1y=None, parcel_3y=None, parcel_5y=None,
            neighborhood_1y=None, neighborhood_3y=None, neighborhood_5y=None,
            settlement_1y=None, settlement_3y=None, settlement_5y=None,
            trend_pct=None, trend_direction="unknown",
            parcel_deal_count=0, neighborhood_deal_count=0,
        )

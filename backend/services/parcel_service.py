"""
parcel_service.py — Business logic for parcel data retrieval.
Single source of truth for gush/helka lookups.
"""
from typing import Optional
from ..clients.govmap_client import get_full_parcel_info
from ..clients.iplan_client import get_plans_by_centroid
from ..models.parcel import ParcelFullData
from ..config import settings


def _to_tm35(x: float, y: float):
    """Convert EPSG:3857 (Web Mercator) to EPSG:2039 (Israeli TM35)."""
    try:
        from pyproj import Transformer
        transformer = Transformer.from_crs("EPSG:3857", "EPSG:2039", always_xy=True)
        return transformer.transform(x, y)
    except Exception:
        return None, None


async def get_parcel_data(gush: int, helka: int) -> ParcelFullData:
    """
    Main entry: fetch full parcel data for gush+helka.
    Returns ParcelFullData with geometry + plans + govmap extras.
    Cached by caller (router or cache layer).
    """
    source = "mock" if (settings.mock_mode or not settings.govmap_token) else "live"

    # Step 1: govmap — geometry + land_use + taba
    full = await get_full_parcel_info(gush, helka)
    geometry = full["parcel"]

    # Step 2: iplan — תכניות בניה (requires TM35 coords)
    plans = []
    if geometry.centroid_x and geometry.centroid_y:
        tm35_x, tm35_y = _to_tm35(geometry.centroid_x, geometry.centroid_y)
        if tm35_x and tm35_y:
            try:
                plans = await get_plans_by_centroid(tm35_x, tm35_y)
            except Exception as e:
                print(f"[parcel_service] iplan failed: {e}")

    return ParcelFullData(
        gush=gush,
        helka=helka,
        geometry=geometry,
        plans=plans,
        source=source,
        land_use=full.get("land_use", []),
        taba=full.get("taba", []),
        is_agricultural=full.get("is_agricultural", False),
    )

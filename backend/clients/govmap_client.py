"""
govmap.gov.il parcel data client — PRODUCTION READY

All endpoints tested live on 2026-07-30.
API base: https://www.govmap.gov.il/api/layers-catalog/
Auth: apiToken in body + x-trace-id: <uuid4> header
Domain: karka-ai.co.il (APPROVED in govmap developer portal)
Coordinates: EPSG:3857 (Web Mercator) — NOT TM35/EPSG:2039
"""

import uuid
import re as _re
from datetime import datetime
import httpx
from typing import Optional, List, Dict, Any
from ..config import settings
from ..models.parcel import ParcelGovmap

_BASE = "https://www.govmap.gov.il/api/layers-catalog"
_DOMAIN = "https://karka-ai.co.il"

# Known layer IDs
LAYER_PARCEL_ALL = "15"
LAYER_LAND_USE = "212150"       # ייעוד קרקע
LAYER_TABA_RMI = "11"           # רצף מגרשי תב"ע - רמ"י
LAYER_TABA = "186"              # תב"עות - נתיבי ישראל
LAYER_AGRI_PARCELS = "350"      # חלקות חקלאיות

# Hebrew field name → Python key
_FIELD_MAP = {
    "מספר גוש": "gush_num",
    "תת גוש": "gush_suffix",
    'חלקה': "parcel",
    'שטח רשום (מ"ר)': "legal_area",
    "סטטוס": "status_text",
    "הערה": "note",
}


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Origin": _DOMAIN,
        "Referer": f"{_DOMAIN}/",
        "x-trace-id": str(uuid.uuid4()),
        "User-Agent": "Mozilla/5.0 (compatible; karka-ai/1.0)",
    }


def _parse_fields(fields: list) -> dict:
    result = {}
    for f in fields:
        key = _FIELD_MAP.get(f.get("fieldName", ""))
        if key:
            result[key] = f.get("fieldValue")
    return result


async def search_by_gush(gush: int, helka: Optional[int] = None) -> List[Dict]:
    """
    Search parcels by gush number.
    Returns list of matching entities with fields.
    If helka specified, filters to that specific parcel.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_BASE}/entitiesByFieldWithMultipleValue",
            headers=_headers(),
            json={
                "layer": "PARCEL_ALL",
                "field": "gush_num",
                "value": [str(gush)],
                "apiToken": settings.govmap_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    entities_raw = (data.get("data") or [{}])[0].get("entities") or []
    results = []
    for e in entities_raw:
        parsed = _parse_fields(e.get("fields", []))
        parsed["object_id"] = e.get("objectId")
        parsed["centroid_x"] = (e.get("centroid") or [None, None])[0]
        parsed["centroid_y"] = (e.get("centroid") or [None, None])[1]
        results.append(parsed)

    if helka is not None:
        # govmap may return parcel as string or int — normalise both sides
        results = [r for r in results if str(r.get("parcel", "")) == str(helka)]

    return results


async def get_parcel_polygon(centroid_x: float, centroid_y: float) -> Optional[Dict]:
    """
    Get full polygon geometry for a parcel using its centroid coordinates.
    Returns GeoJSON Feature with MultiPolygon geometry + properties.
    Coordinates in EPSG:3857.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{_BASE}/apps/parcel-search/address",
            headers=_headers(),
            params={"x": centroid_x, "y": centroid_y},
        )
        resp.raise_for_status()
        return resp.json()


async def get_entities_at_point(x: float, y: float, layer_ids: List[str] = None) -> List[Dict]:
    """
    Get all layer entities at a given point.
    Useful for getting land-use, taba, etc. at a parcel location.
    """
    if layer_ids is None:
        layer_ids = [LAYER_PARCEL_ALL, LAYER_LAND_USE, LAYER_TABA_RMI]

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_BASE}/entitiesByPoint",
            headers=_headers(),
            json={
                "point": [x, y],
                "layers": [{"layerId": lid} for lid in layer_ids],
                "tolerance": 10,
                "apiToken": settings.govmap_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    results = []
    for layer_data in (data.get("data") or []):
        layer_result = {
            "layer_name": layer_data.get("name"),
            "caption": layer_data.get("caption"),
            "entities": [],
        }
        for e in (layer_data.get("entities") or []):
            parsed = _parse_fields(e.get("fields", []))
            parsed["object_id"] = e.get("objectId")
            layer_result["entities"].append(parsed)
        results.append(layer_result)
    return results


async def _find_centroid_via_realestate(gush: int, helka: int):
    """Fallback: estimate centroid from street-deals polygon, verify via entitiesByPoint."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"https://www.govmap.gov.il/api/real-estate/street-deals/{gush}-{helka}",
                headers={k: v for k, v in _headers().items() if k != 'Content-Type'},
                params={"limit": 1, "offset": 0, "startDate": "1998-01",
                        "endDate": datetime.now().strftime("%Y-%m")},
            )
            if r.status_code != 200:
                return None, None, None
            deals = r.json().get("data", [])
            if not deals or not deals[0].get("shape"):
                return None, None, None

            # Parse polygon centroid
            nums = list(map(float, _re.findall(r'[-\d.]+', deals[0]["shape"])))
            xs, ys = nums[0::2], nums[1::2]
            cx_est = sum(xs) / len(xs)
            cy_est = sum(ys) / len(ys)

            # Verify via entitiesByPoint
            ep = await client.post(
                f"{_BASE}/entitiesByPoint",
                headers=_headers(),
                json={"point": [cx_est, cy_est],
                      "layers": [{"layerId": LAYER_PARCEL_ALL}],
                      "tolerance": 100,
                      "apiToken": settings.govmap_token},
            )
            ep.raise_for_status()
            for layer_data in (ep.json().get("data") or []):
                for entity in (layer_data.get("entities") or []):
                    parsed = _parse_fields(entity.get("fields", []))
                    if parsed.get("parcel") == helka:
                        cx = (entity.get("centroid") or [cx_est, cy_est])[0]
                        cy = (entity.get("centroid") or [cx_est, cy_est])[1]
                        area = parsed.get("legal_area")
                        return cx, cy, area
    except Exception as e:
        print(f"[govmap] realestate fallback failed: {e}")
    return None, None, None


async def get_parcel_geometry(gush: int, helka: int) -> ParcelGovmap:
    """
    Main entry point: fetch full parcel data for gush+helka.

    Flow:
    1. search_by_gush → find matching helka → get centroid
    2. get_parcel_polygon(centroid) → get WKT polygon

    mock_mode=True → returns mock data
    """
    if settings.mock_mode or not settings.govmap_token:
        return _mock_parcel(gush, helka)

    try:
        # Step 1: find parcel in batch (entitiesByFieldWithMultipleValue)
        matches = await search_by_gush(gush, helka)

        if matches:
            match = matches[0]
            cx, cy = match.get("centroid_x"), match.get("centroid_y")
            area = match.get("legal_area")
        else:
            # Fallback: estimate centroid from real-estate API polygon
            cx, cy, area = await _find_centroid_via_realestate(gush, helka)
            if not cx:
                print(f"[govmap] helka {helka} not found in gush {gush}")
                return ParcelGovmap(gush=gush, helka=helka, shape_wkt=None,
                                    centroid_x=None, centroid_y=None, area_sqm=None)

        # Step 2: get polygon
        shape_wkt = None
        if cx and cy:
            try:
                geo = await get_parcel_polygon(cx, cy)
                if geo and isinstance(geo, dict):
                    props = geo.get("properties", {})
                    shape_wkt = props.get("polygoncoordinates")
            except Exception as e:
                print(f"[govmap] polygon fetch failed: {e}")

        return ParcelGovmap(
            gush=gush,
            helka=helka,
            shape_wkt=shape_wkt,
            centroid_x=cx,
            centroid_y=cy,
            area_sqm=float(area) if area else None,
        )

    except Exception as e:
        print(f"[govmap] ERROR get_parcel_geometry({gush},{helka}): {e}")
        return ParcelGovmap(gush=gush, helka=helka, shape_wkt=None,
                            centroid_x=None, centroid_y=None, area_sqm=None)


async def get_full_parcel_info(gush: int, helka: int) -> Dict[str, Any]:
    """
    Extended info: parcel + land use + taba layers at same point.
    Returns dict with parcel, land_use, taba, is_agricultural keys.
    """
    parcel = await get_parcel_geometry(gush, helka)

    extra = {}
    if parcel.centroid_x and parcel.centroid_y:
        try:
            layers = await get_entities_at_point(
                parcel.centroid_x, parcel.centroid_y,
                layer_ids=[LAYER_LAND_USE, LAYER_TABA_RMI, LAYER_AGRI_PARCELS]
            )
            for layer in layers:
                name = (layer.get("layer_name") or "").lower()
                caption = (layer.get("caption") or "").lower()
                lid_hint = name + caption
                if "212150" in lid_hint or "ייעוד" in lid_hint or "land" in lid_hint:
                    extra["land_use"] = layer.get("entities", [])
                elif "retzef" in lid_hint or "taba" in lid_hint or "תב" in lid_hint or "מגרש" in lid_hint:
                    extra["taba"] = layer.get("entities", [])
                elif "agri" in lid_hint or "חקלא" in lid_hint or "350" in lid_hint:
                    extra["agri"] = layer.get("entities", [])
        except Exception as e:
            print(f"[govmap] get_full_parcel_info layers failed: {e}")

    return {
        "parcel": parcel,
        "land_use": extra.get("land_use", []),
        "taba": extra.get("taba", []),
        "is_agricultural": bool(extra.get("agri")),
    }


def _mock_parcel(gush: int, helka: int) -> ParcelGovmap:
    _MOCK = {
        (6111, 50): ParcelGovmap(
            gush=6111, helka=50,
            shape_wkt="MULTIPOLYGON Z (((179450 663850 0,179550 663850 0,179550 663950 0,179450 663950 0,179450 663850 0)))",
            centroid_x=3872286.0, centroid_y=3773752.0, area_sqm=850.0,
        ),
    }
    return _MOCK.get((gush, helka), ParcelGovmap(
        gush=gush, helka=helka, shape_wkt=None,
        centroid_x=None, centroid_y=None, area_sqm=None,
    ))

"""
govmap.gov.il parcel geometry client.

ARCHITECTURE NOTE (reverse-engineered from GovmapApi.js):
----------------------------------------------------------
govmap's public SDK is iframe + postMessage based — not a simple REST API.
The JS SDK posts messages to a govmap iframe which runs queries internally.

HOWEVER — the SDK also uses axios for direct HTTP calls to underlying services.
Based on the SDK source, the REST layer uses:
  - Base URL: configuration.apiBaseUrl (likely https://api.govmap.gov.il or similar)
  - Auth: apiToken passed as URL param (?apiToken=xxx) OR Bearer header
  - Domain lock: server validates Origin/Referer against registered domain

LIVE MODE — requires:
  1. GOVMAP_TOKEN in .env (register at govmap.gov.il/developer)
  2. Domain karka-ai.co.il registered in govmap developer account
  3. Python must send: Referer: https://karka-ai.co.il

PARCEL QUERY ENDPOINT (to be confirmed once token is received):
  Candidate 1 (ArcGIS REST — likely):
    GET https://ags2.govmap.gov.il/arcgis/rest/services/Parcel/MapServer/0/query
    ?where=GUSH=6111 AND PARCEL=50
    &outFields=GUSH,PARCEL,Shape_Area
    &returnGeometry=true
    &geometryType=esriGeometryPolygon
    &f=json
    &apiToken={token}

  Candidate 2 (govmap internal service):
    POST https://api.govmap.gov.il/v1/intersectFeatures
    Body: { layer: "PARCEL_ALL", whereClause: "GUSH=X AND PARCEL=Y", getShapes: true }
    Headers: { Authorization: "Bearer {token}", Referer: "https://karka-ai.co.il" }

TODO: Once token received → test Candidate 1 first (simpler), then Candidate 2.

Coordinate system: Israeli TM35 (EPSG:2039)
  X: 100,000–300,000 | Y: 370,000–810,000
"""

import re
import httpx
from typing import Optional, Tuple
from ..config import settings
from ..models.parcel import ParcelGovmap

# ── mock data for development ──────────────────────────────────────────────────
_MOCK_DATA: dict[tuple[int, int], ParcelGovmap] = {
    (6111, 50): ParcelGovmap(
        gush=6111,
        helka=50,
        shape_wkt="POLYGON((179450 663850,179550 663850,179550 663950,179450 663950,179450 663850))",
        centroid_x=179500.0,
        centroid_y=663900.0,
        area_sqm=850.0,
    ),
    (7103, 43): ParcelGovmap(
        gush=7103,
        helka=43,
        shape_wkt="POLYGON((179680 664030,179690 664030,179690 664045,179680 664045,179680 664030))",
        centroid_x=179685.0,
        centroid_y=664037.0,
        area_sqm=150.0,
    ),
}

# ── govmap REST candidates ─────────────────────────────────────────────────────
# Candidate 1: ArcGIS REST (most likely — govmap is ArcGIS based)
_ARCGIS_PARCEL_URL = (
    "https://ags2.govmap.gov.il/arcgis/rest/services/Parcel/MapServer/0/query"
)

# Candidate 2: govmap internal API
_GOVMAP_API_URL = "https://api.govmap.gov.il/v1/intersectFeatures"


def _calc_centroid(wkt: str) -> Tuple[Optional[float], Optional[float]]:
    """Extract centroid from WKT POLYGON string (TM35 coords)."""
    coords = re.findall(r"([\d.]+)\s+([\d.]+)", wkt)
    if not coords:
        return None, None
    xs = [float(c[0]) for c in coords]
    ys = [float(c[1]) for c in coords]
    return sum(xs) / len(xs), sum(ys) / len(ys)


async def _try_arcgis(gush: int, helka: int, token: str) -> Optional[ParcelGovmap]:
    """Attempt Candidate 1: ArcGIS REST query."""
    params = {
        "where": f"GUSH={gush} AND PARCEL={helka}",
        "outFields": "GUSH,PARCEL,Shape_Area",
        "returnGeometry": "true",
        "geometryType": "esriGeometryPolygon",
        "outSR": "2039",
        "f": "json",
        "apiToken": token,
    }
    headers = {
        "Referer": f"https://{settings.govmap_domain}",
        "Origin": f"https://{settings.govmap_domain}",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(_ARCGIS_PARCEL_URL, params=params, headers=headers)
        r.raise_for_status()
        data = r.json()

    features = data.get("features", [])
    if not features:
        return None

    feat = features[0]
    geom = feat.get("geometry", {})
    attrs = feat.get("attributes", {})
    rings = geom.get("rings", [[]])
    ring = rings[0] if rings else []

    if not ring:
        return None

    coords_str = ",".join(f"{x} {y}" for x, y in ring)
    wkt = f"POLYGON(({coords_str}))"
    cx = sum(p[0] for p in ring) / len(ring)
    cy = sum(p[1] for p in ring) / len(ring)
    area = attrs.get("Shape_Area")

    return ParcelGovmap(
        gush=gush,
        helka=helka,
        shape_wkt=wkt,
        centroid_x=cx,
        centroid_y=cy,
        area_sqm=float(area) if area else None,
    )


async def _try_govmap_api(gush: int, helka: int, token: str) -> Optional[ParcelGovmap]:
    """Attempt Candidate 2: govmap internal intersectFeatures endpoint."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Referer": f"https://{settings.govmap_domain}",
        "Origin": f"https://{settings.govmap_domain}",
        "Content-Type": "application/json",
    }
    body = {
        "layer": "PARCEL_ALL",
        "whereClause": f"GUSH={gush} AND PARCEL={helka}",
        "getShapes": True,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(_GOVMAP_API_URL, json=body, headers=headers)
        r.raise_for_status()
        data = r.json()

    # Response shape TBD — parse when we have real data
    results = data.get("results") or data.get("features") or []
    if not results:
        return None

    first = results[0]
    wkt = first.get("wkt") or first.get("shape_wkt") or first.get("geometry")
    area = first.get("area") or first.get("shape_area")

    if not wkt:
        return None

    cx, cy = _calc_centroid(wkt)
    return ParcelGovmap(
        gush=gush,
        helka=helka,
        shape_wkt=wkt,
        centroid_x=cx,
        centroid_y=cy,
        area_sqm=float(area) if area else None,
    )


# ── public interface ───────────────────────────────────────────────────────────

async def get_parcel_geometry(gush: int, helka: int) -> ParcelGovmap:
    """
    Fetch parcel geometry from govmap.

    mock_mode=True (default) → returns mock data for development.
    mock_mode=False + GOVMAP_TOKEN set → tries live govmap API.
    """
    if settings.mock_mode or not settings.govmap_token:
        parcel = _MOCK_DATA.get((gush, helka))
        if parcel:
            return parcel
        return ParcelGovmap(
            gush=gush,
            helka=helka,
            shape_wkt=None,
            centroid_x=179500.0,
            centroid_y=663900.0,
            area_sqm=None,
        )

    # ── live mode ──────────────────────────────────────────────────────────────
    token = settings.govmap_token

    # Try Candidate 1 (ArcGIS REST — most likely to work)
    try:
        result = await _try_arcgis(gush, helka, token)
        if result:
            return result
    except Exception as e:
        print(f"[govmap] ArcGIS candidate failed: {e}")

    # Fallback: Candidate 2 (govmap internal API)
    try:
        result = await _try_govmap_api(gush, helka, token)
        if result:
            return result
    except Exception as e:
        print(f"[govmap] govmap API candidate failed: {e}")

    # If both fail — return partial data with centroid from iplan fallback
    print(f"[govmap] WARNING: both candidates failed for gush={gush} helka={helka}")
    return ParcelGovmap(
        gush=gush,
        helka=helka,
        shape_wkt=None,
        centroid_x=None,
        centroid_y=None,
        area_sqm=None,
    )

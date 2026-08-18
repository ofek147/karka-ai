import json
import re
import ssl
import httpx
from typing import List, Optional
from ..models.parcel import PlanInfo, LandUseInfo

# iplan.gov.il uses an older TLS config that Python 3.12+ OpenSSL 3.x rejects
# by default. A legacy SSL context with SECLEVEL=1 is needed.
def _iplan_ssl() -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
    return ctx

_IPLAN_SSL = _iplan_ssl()

LAYER_1_URL = "https://ags.iplan.gov.il/arcgisiplan/rest/services/PlanningPublic/Xplan/MapServer/1/query"
LAYER_4_URL = "https://ags.iplan.gov.il/arcgisiplan/rest/services/PlanningPublic/Xplan/MapServer/4/query"
BBOX_BUFFER = 100  # meters (TM35 units) — fallback when no WKT available


def _wkt_to_esri_rings(wkt: str) -> Optional[dict]:
    """
    Convert a WKT MULTIPOLYGON Z (EPSG:3857) → ArcGIS esriGeometryPolygon (EPSG:2039).
    Returns None if conversion fails (caller falls back to bbox).
    """
    try:
        from pyproj import Transformer
        t = Transformer.from_crs("EPSG:3857", "EPSG:2039", always_xy=True)
        # strip Z values and collect all rings
        nums_flat = list(map(float, re.findall(r'[-\d.]+', wkt)))
        # WKT coords are x y z triplets; strip Z → pairs
        coords = [(nums_flat[i], nums_flat[i+1]) for i in range(0, len(nums_flat), 3)]
        if not coords:
            return None
        projected = [list(t.transform(x, y)) for x, y in coords]
        return {
            "rings": [projected],
            "spatialReference": {"wkid": 2039},
        }
    except Exception as e:
        print(f"[iplan_client] WKT→rings failed: {e}")
        return None

LAYER_1_FIELDS = ",".join([
    "pl_name", "pl_number",
    "station_desc", "internet_short_status",
    "plan_charactor_name", "pl_landuse_string",
    "pl_objectives", "pl_url",
    "district_name", "plan_county_name",
    "ja_concat",
    "receiving_date", "depositing_date",
    "pl_date7", "pl_date_8",
    "pq_authorised_quantity_120", "quantity_delta_120",
    "pl_area_dunam",
    "shape_area",
])

LAYER_4_FIELDS = "mavat_name,mavat_code,pl_name,pl_number,station_desc,station,legal_area,shape_area"


async def get_plans_by_centroid(
    cx: float,
    cy: float,
    shape_wkt: Optional[str] = None,
) -> List[PlanInfo]:
    """
    Layer 1 — תכניות בניה מקוונות עם מלוא המטאדטה.
    If shape_wkt (MULTIPOLYGON Z, EPSG:3857) is provided, queries by the full
    parcel polygon instead of a centroid bbox — catches plans on parcel edges.
    """
    in_sr      = "2039"
    esri_poly  = _wkt_to_esri_rings(shape_wkt) if shape_wkt else None
    if esri_poly:
        geometry_param = json.dumps(esri_poly)
        geometry_type  = "esriGeometryPolygon"
        print(f"[iplan_client] Layer1 query by parcel polygon ({len(esri_poly['rings'][0])} vertices)")
    else:
        geometry_param = f"{cx-BBOX_BUFFER},{cy-BBOX_BUFFER},{cx+BBOX_BUFFER},{cy+BBOX_BUFFER}"
        geometry_type  = "esriGeometryEnvelope"
        print(f"[iplan_client] Layer1 query by bbox (buffer={BBOX_BUFFER}m) — no WKT")
    params = {
        "f": "json",
        "geometry": geometry_param,
        "geometryType": geometry_type,
        "inSR": in_sr,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": LAYER_1_FIELDS,
        "returnGeometry": False,
    }
    async with httpx.AsyncClient(verify=_IPLAN_SSL, timeout=30) as client:
        r = await client.get(LAYER_1_URL, params=params)
        r.raise_for_status()
        data = r.json()

    plans = []
    for feature in data.get("features", []):
        attrs = feature.get("attributes", {})
        mavat = attrs.get("plan_charactor_name") or attrs.get("pl_number") or "לא ידוע"
        plans.append(PlanInfo(
            mavat_name=mavat,
            pl_name=attrs.get("pl_name"),
            pl_number=attrs.get("pl_number"),
            station_desc=attrs.get("station_desc"),
            internet_short_status=attrs.get("internet_short_status"),
            plan_charactor_name=attrs.get("plan_charactor_name"),
            pl_landuse_string=attrs.get("pl_landuse_string"),
            pl_objectives=attrs.get("pl_objectives"),
            pl_url=attrs.get("pl_url"),
            district_name=attrs.get("district_name"),
            plan_county_name=attrs.get("plan_county_name"),
            ja_concat=attrs.get("ja_concat"),
            receiving_date=attrs.get("receiving_date"),
            depositing_date=attrs.get("depositing_date"),
            pl_date7=attrs.get("pl_date7"),
            pl_date_8=attrs.get("pl_date_8"),
            pq_authorised_quantity_120=attrs.get("pq_authorised_quantity_120"),
            quantity_delta_120=attrs.get("quantity_delta_120"),
            pl_area_dunam=attrs.get("pl_area_dunam"),
            shape_area=attrs.get("shape_area"),
        ))

    plans.sort(key=lambda p: p.pl_date_8 or 0, reverse=True)
    return plans


# Backward compat alias
get_plans_layer1 = get_plans_by_centroid


async def get_land_use_by_centroid(
    cx: float,
    cy: float,
    shape_wkt: Optional[str] = None,
) -> List[LandUseInfo]:
    """
    Layer 4 — ייעודי קרקע לפי תא שטח.
    If shape_wkt is provided, queries by full parcel polygon.
    """
    in_sr      = "2039"
    esri_poly  = _wkt_to_esri_rings(shape_wkt) if shape_wkt else None
    if esri_poly:
        geometry_param = json.dumps(esri_poly)
        geometry_type  = "esriGeometryPolygon"
        print(f"[iplan_client] Layer4 query by parcel polygon")
    else:
        geometry_param = f"{cx-BBOX_BUFFER},{cy-BBOX_BUFFER},{cx+BBOX_BUFFER},{cy+BBOX_BUFFER}"
        geometry_type  = "esriGeometryEnvelope"
        print(f"[iplan_client] Layer4 query by bbox — no WKT")
    params = {
        "f": "json",
        "geometry": geometry_param,
        "geometryType": geometry_type,
        "inSR": in_sr,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": LAYER_4_FIELDS,
        "returnGeometry": False,
    }
    async with httpx.AsyncClient(verify=_IPLAN_SSL, timeout=30) as client:
        r = await client.get(LAYER_4_URL, params=params)
        r.raise_for_status()
        data = r.json()

    results = []
    for feature in data.get("features", []):
        attrs = feature.get("attributes", {})
        legal_area_sqm = attrs.get("legal_area")
        area_dunam = round(legal_area_sqm / 1000, 3) if legal_area_sqm else None
        results.append(LandUseInfo(
            yiud=attrs.get("mavat_name"),
            area_dunam=area_dunam,
            plan_name=attrs.get("pl_name"),
            plan_num=attrs.get("pl_number"),
            yt=str(attrs.get("mavat_code")) if attrs.get("mavat_code") else None,
            plan_status=attrs.get("station_desc"),
        ))
    return results

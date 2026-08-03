import httpx
from typing import List
from ..models.parcel import PlanInfo, LandUseInfo

LAYER_1_URL = "https://ags.iplan.gov.il/arcgisiplan/rest/services/PlanningPublic/Xplan/MapServer/1/query"
LAYER_4_URL = "https://ags.iplan.gov.il/arcgisiplan/rest/services/PlanningPublic/Xplan/MapServer/4/query"
BBOX_BUFFER = 100  # meters (TM35 units)

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


async def get_plans_by_centroid(cx: float, cy: float) -> List[PlanInfo]:
    """Layer 1 — תכניות בניה מקוונות עם מלוא המטאדטה."""
    bbox = f"{cx-BBOX_BUFFER},{cy-BBOX_BUFFER},{cx+BBOX_BUFFER},{cy+BBOX_BUFFER}"
    params = {
        "f": "json",
        "geometry": bbox,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "2039",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": LAYER_1_FIELDS,
        "returnGeometry": False,
    }
    async with httpx.AsyncClient(timeout=30) as client:
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


async def get_land_use_by_centroid(cx: float, cy: float) -> List[LandUseInfo]:
    """Layer 4 — ייעודי קרקע לפי תא שטח."""
    bbox = f"{cx-BBOX_BUFFER},{cy-BBOX_BUFFER},{cx+BBOX_BUFFER},{cy+BBOX_BUFFER}"
    params = {
        "f": "json",
        "geometry": bbox,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "2039",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": LAYER_4_FIELDS,
        "returnGeometry": False,
    }
    async with httpx.AsyncClient(timeout=15) as client:
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
            yiud_heb=attrs.get("mavat_name"),
            area_dunam=area_dunam,
            plan_name=attrs.get("pl_name"),
            plan_num=attrs.get("pl_number"),
            yt=str(attrs.get("mavat_code")) if attrs.get("mavat_code") else None,
            plan_status=attrs.get("station_desc"),
        ))
    return results

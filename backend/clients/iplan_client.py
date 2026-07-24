import httpx
from typing import List
from ..models.parcel import PlanInfo

IPLAN_URL = "https://ags.iplan.gov.il/arcgisiplan/rest/services/PlanningPublic/Xplan/MapServer/4/query"
BBOX_BUFFER = 50  # meters (TM35 units)


async def get_plans_by_centroid(cx: float, cy: float) -> List[PlanInfo]:
    bbox = f"{cx - BBOX_BUFFER},{cy - BBOX_BUFFER},{cx + BBOX_BUFFER},{cy + BBOX_BUFFER}"
    params = {
        "f": "json",
        "geometry": bbox,
        "geometryType": "esriGeometryEnvelope",
        "inSR": "2039",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "mavat_name,pl_name,pl_number,station_desc,shape_area",
        "returnGeometry": False,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(IPLAN_URL, params=params)
        r.raise_for_status()
        data = r.json()

    plans = []
    for feature in data.get("features", []):
        attrs = feature.get("attributes", {})
        plans.append(PlanInfo(
            mavat_name=attrs.get("mavat_name") or "לא ידוע",
            pl_name=attrs.get("pl_name"),
            pl_number=attrs.get("pl_number"),
            station_desc=attrs.get("station_desc"),
            shape_area=attrs.get("shape_area"),
        ))
    return plans

from pydantic import BaseModel
from typing import Optional, List


class ParcelGovmap(BaseModel):
    gush: int
    helka: int
    shape_wkt: Optional[str] = None
    centroid_x: Optional[float] = None
    centroid_y: Optional[float] = None
    area_sqm: Optional[float] = None


class PlanInfo(BaseModel):
    mavat_name: str
    pdf_text: Optional[str] = None  # extracted from mavat PDF, populated by plan_cache_service
    pl_name: Optional[str] = None
    pl_number: Optional[str] = None
    station_desc: Optional[str] = None
    shape_area: Optional[float] = None
    internet_short_status: Optional[str] = None
    plan_charactor_name: Optional[str] = None
    pl_landuse_string: Optional[str] = None
    pl_objectives: Optional[str] = None
    pl_url: Optional[str] = None
    district_name: Optional[str] = None
    plan_county_name: Optional[str] = None
    ja_concat: Optional[str] = None
    receiving_date: Optional[int] = None
    depositing_date: Optional[int] = None
    pl_date7: Optional[int] = None
    pl_date_8: Optional[int] = None
    pq_authorised_quantity_120: Optional[float] = None
    quantity_delta_120: Optional[float] = None
    pl_area_dunam: Optional[float] = None


class LandUseInfo(BaseModel):
    yiud: Optional[str] = None         # mavat_name — zone type
    yiud_heb: Optional[str] = None     # mavat_name (same, for compat)
    area_dunam: Optional[float] = None
    plan_name: Optional[str] = None
    plan_num: Optional[str] = None
    yt: Optional[str] = None           # mavat_code as string
    plan_status: Optional[str] = None  # station_desc (plan approval status)


class ParcelFullData(BaseModel):
    gush: int
    helka: int
    geometry: Optional[ParcelGovmap] = None
    plans: List[PlanInfo] = []
    source: str  # "live" | "mock" | "cache"
    land_use: list = []
    taba: list = []
    is_agricultural: bool = False


class AskRequest(BaseModel):
    gush: int
    helka: int
    question: str


class AskResponse(BaseModel):
    gush: int
    helka: int
    question: str
    answer: str
    source: str  # "mock" | "live" | "cache"

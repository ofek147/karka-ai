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
    pl_name: Optional[str] = None
    pl_number: Optional[str] = None
    station_desc: Optional[str] = None
    shape_area: Optional[float] = None


class ParcelFullData(BaseModel):
    gush: int
    helka: int
    geometry: Optional[ParcelGovmap] = None
    plans: List[PlanInfo] = []
    source: str  # "live" | "mock" | "cache"


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

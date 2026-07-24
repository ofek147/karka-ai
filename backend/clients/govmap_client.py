from ..config import settings
from ..models.parcel import ParcelGovmap

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


async def get_parcel_geometry(gush: int, helka: int) -> ParcelGovmap:
    if settings.mock_mode or not settings.govmap_token:
        parcel = _MOCK_DATA.get((gush, helka))
        if parcel:
            return parcel
        # generic fallback for any gush/helka not in mock table
        return ParcelGovmap(
            gush=gush,
            helka=helka,
            shape_wkt=None,
            centroid_x=179500.0,
            centroid_y=663900.0,
            area_sqm=None,
        )

    # Live mode — activated once GOVMAP_TOKEN is set in .env
    # TODO: reverse-engineer govmap SDK network calls and implement here
    raise NotImplementedError("govmap live mode requires token — set GOVMAP_TOKEN in .env")

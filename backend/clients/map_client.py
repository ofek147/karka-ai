"""
map_client.py — Static satellite map image from ArcGIS World Imagery.
Returns PNG bytes for PDF embedding.
Coordinates: input EPSG:3857 (Web Mercator), ArcGIS bbox = EPSG:3857.
"""
import httpx
from typing import Optional
import base64

ARCGIS_IMAGERY = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
BUFFER = 500  # meters in EPSG:3857 — enough context around parcel


async def get_satellite_image_b64(
    centroid_x: float,
    centroid_y: float,
    width: int = 1200,
    height: int = 800,
    buffer: int = BUFFER,
) -> Optional[str]:
    """
    Fetch satellite image from ArcGIS.
    Returns base64 encoded PNG string for embedding in HTML <img src="data:image/png;base64,...">
    Returns None on failure.
    """
    bbox = f"{centroid_x-buffer},{centroid_y-buffer},{centroid_x+buffer},{centroid_y+buffer}"
    params = {
        "bbox": bbox,
        "bboxSR": "3857",
        "imageSR": "3857",
        "size": f"{width},{height}",
        "format": "png",
        "f": "image",
        "layers": "show:0",
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(ARCGIS_IMAGERY, params=params)
            r.raise_for_status()
            return base64.b64encode(r.content).decode()
    except Exception as e:
        print(f"[map_client] satellite fetch failed: {e}")
        return None

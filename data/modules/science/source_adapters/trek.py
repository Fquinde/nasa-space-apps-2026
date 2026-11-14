"""
TERRAIN-X NASA Trek WMTS Adapter
Interfaces with NASA Moon Trek and Mars Trek Web Map Tile Services (WMTS).
Official Docs:
- Moon: https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon
- Mars: https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=mars

CRITICAL SCIENTIFIC CAVEAT:
WMTS delivers 8-bit visual rendering tiles (JPEG/PNG) intended for human
visualization and contextual overlays. WMTS TILES MUST NEVER BE USED TO
COMPUTE METRIC ELEVATIONS OR SLOPES. True DEM rasters (GeoTIFF / PDS IMG)
are required for physical calculations.
"""

from typing import Dict
from modules.science.source_adapters.base import BaseAdapter
from modules.science.schemas import SourceRecord


class TrekWMTSClient(BaseAdapter):
    """
    Adapter for NASA Trek visualization services.
    """

    MOON_WMTS_BASE = "https://trek.nasa.gov/tiles/Moon/EQ"
    MARS_WMTS_BASE = "https://trek.nasa.gov/tiles/Mars/EQ"

    def get_tile_template(self, body: str, layer_name: str) -> str:
        """
        Returns the standard OGC WMTS REST tile template URL.
        """
        base = self.MOON_WMTS_BASE if body.lower() == "moon" else self.MARS_WMTS_BASE
        return f"{base}/{layer_name}/1.0.0/default/default028mm/{{TileMatrix}}/{{TileRow}}/{{TileCol}}.png"

    def get_source_record(self, body: str, layer_name: str) -> SourceRecord:
        body_crs = "IAU_2015:30100" if body.lower() == "moon" else "IAU_2015:49900"
        return SourceRecord(
            id=f"TREK_WMTS_{body.upper()}_{layer_name}",
            agency="NASA Solar System Treks Project",
            product=f"{layer_name} WMTS Visual Basemap",
            version="1.0.0",
            url=f"{self.MOON_WMTS_BASE if body.lower() == 'moon' else self.MARS_WMTS_BASE}/{layer_name}/1.0.0/WMTSCapabilities.xml",
            license="NASA Open Data Policy (Visual use only - not for metric elevation)",
            crs=body_crs,
            resolution_m=None
        )


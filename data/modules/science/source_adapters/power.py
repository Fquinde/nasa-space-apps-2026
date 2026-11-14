"""
TERRAIN-X NASA POWER (Prediction Of Worldwide Energy Resources) Adapter
Queries NASA POWER Daily API for meteorological and climatological context.
Official Docs: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
"""

from typing import Any, Dict, Optional
from modules.science.source_adapters.base import BaseAdapter
from modules.science.schemas import SourceRecord


class POWERClient(BaseAdapter):
    """
    Adapter for NASA POWER Daily Point API.
    Used to extract aridity index proxies and thermal variation for terrestrial analog sites.
    """

    BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

    def get_climatology(
        self,
        lat: float,
        lon: float,
        start_date: str = "20230101",
        end_date: str = "20230105",
        parameters: str = "T2M,PRECTOTCORR"
    ) -> Dict[str, Any]:
        """
        Retrieves meteorological data for a geographic coordinate.
        - T2M: Temperature at 2 Meters (C)
        - PRECTOTCORR: Precipitation Corrected (mm/day)
        """
        params = {
            "parameters": parameters,
            "community": "RE",
            "longitude": lon,
            "latitude": lat,
            "start": start_date,
            "end": end_date,
            "format": "JSON"
        }
        return self.get_json(self.BASE_URL, params=params)

    def get_source_record(self) -> SourceRecord:
        return SourceRecord(
            id="NASA_POWER_DAILY_POINT",
            agency="NASA Langley Research Center",
            product="POWER Surface Meteorology and Solar Energy Daily",
            version="v2.0",
            url="https://power.larc.nasa.gov/",
            crs="EPSG:4326",
            resolution_m=55000.0  # ~0.5 x 0.625 degree resolution
        )


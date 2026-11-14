"""
TERRAIN-X NASA CMR (Common Metadata Repository) Adapter
Connects to NASA CMR search API and CMR-STAC.
Discovers collection concept-ids dynamically rather than hardcoding.
"""

from typing import Any, Dict, List, Optional
from modules.science.source_adapters.base import BaseAdapter
from modules.science.schemas import SourceRecord


class CMRClient(BaseAdapter):
    """
    Adapter for NASA CMR Collections and Granules search.
    Official Docs: https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html
    """

    BASE_URL = "https://cmr.earthdata.nasa.gov/search"

    def search_collection_concept_id(self, short_name: str, version: Optional[str] = None) -> Optional[str]:
        """
        Dynamically finds the latest CMR Concept ID for a given short name.
        Example: short_name='ASTGTM', version='003' -> 'C1711961296-LPCLOUD'
        """
        params: Dict[str, Any] = {"short_name": short_name, "page_size": 1}
        if version:
            params["version"] = version

        data = self.get_json(f"{self.BASE_URL}/collections.json", params=params)
        entries = data.get("feed", {}).get("entry", [])
        if entries:
            return entries[0].get("id")
        return None

    def search_granules(
        self,
        concept_id: str,
        bbox: Optional[List[float]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Queries granules for a specific concept-id and optional bounding box [min_lon, min_lat, max_lon, max_lat].
        """
        params: Dict[str, Any] = {"collection_concept_id": concept_id, "page_size": limit}
        if bbox:
            params["bounding_box"] = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"

        data = self.get_json(f"{self.BASE_URL}/granules.json", params=params)
        return data.get("feed", {}).get("entry", [])

    def get_source_record(self, short_name: str, product_title: str) -> SourceRecord:
        concept_id = self.search_collection_concept_id(short_name)
        return SourceRecord(
            id=f"NASA_CMR_{short_name}",
            agency="NASA",
            product=product_title,
            version="V3/Latest",
            url=f"https://cmr.earthdata.nasa.gov/search/concepts/{concept_id or short_name}.html",
            crs="EPSG:4326",
            resolution_m=30.0 if "DEM" in product_title or "AST" in short_name else None
        )


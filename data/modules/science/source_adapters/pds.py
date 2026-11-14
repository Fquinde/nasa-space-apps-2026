"""
TERRAIN-X NASA Planetary Data System (PDS) Adapter
Interfaces with the PDS Search API v1 for planetary mission metadata.
Official Docs: https://nasa-pds.github.io/pds-api/
"""

from typing import Any, Dict, List, Optional
from modules.science.source_adapters.base import BaseAdapter
from modules.science.schemas import SourceRecord


class PDSClient(BaseAdapter):
    """
    Client for NASA PDS API v1.
    Distinguishes high-level mission metadata from granular spatial queries.
    """

    BASE_URL = "https://pds.nasa.gov/api/search/1"

    def query_products(self, query_str: str = "*:*", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Queries PDS products matching Solr-compatible syntax.
        """
        params = {"q": query_str, "limit": limit}
        try:
            data = self.get_json(f"{self.BASE_URL}/products", params=params)
            return data.get("data", [])
        except Exception:
            return []

    def get_source_record(self, instrument_name: str, target_body: str) -> SourceRecord:
        return SourceRecord(
            id=f"PDS_{instrument_name.upper()}_{target_body.upper()}",
            agency="NASA PDS",
            product=f"{instrument_name} Planetary Archive",
            version="PDS4",
            url=f"https://pds.nasa.gov/api/search/1/products?limit=1",
            crs="IAU_2015:30100" if target_body.lower() == "moon" else "IAU_2015:49900",
            resolution_m=None
        )


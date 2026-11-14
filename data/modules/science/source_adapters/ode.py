"""
TERRAIN-X Washington University ODE (Orbital Data Explorer) Adapter
Interfaces with ODE REST services for spatial searching of Lunar & Martian datasets.
Official Docs: https://oderest.rsl.wustl.edu/
"""

from typing import Any, Dict, List, Optional
from modules.science.source_adapters.base import BaseAdapter
from modules.science.schemas import SourceRecord


class ODEClient(BaseAdapter):
    """
    Client for Washington University ODE REST API.
    Provides targeted spatial querying for LOLA (Moon) and MOLA (Mars) products.
    """

    BASE_URL = "https://oderest.rsl.wustl.edu/live2/"

    def search_products(
        self,
        target_body: str,
        product_type: str,
        limit: int = 5,
        min_lat: Optional[float] = None,
        max_lat: Optional[float] = None,
        western_lon: Optional[float] = None,
        eastern_lon: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Queries ODE REST API for specific instrument product types on Moon or Mars.
        Example: target_body='moon', product_type='LOLA_EDR'
                 target_body='mars', product_type='MOLA_MEGDR'
        """
        params: Dict[str, Any] = {
            "target": target_body.lower(),
            "query": "product",
            "pt": product_type,
            "output": "JSON",
            "limit": limit
        }
        if min_lat is not None and max_lat is not None:
            params["minlat"] = min_lat
            params["maxlat"] = max_lat
        if western_lon is not None and eastern_lon is not None:
            params["westernlon"] = western_lon
            params["easternlon"] = eastern_lon

        try:
            data = self.get_json(self.BASE_URL, params=params)
            ode_results = data.get("ODEResults", {})
            products = ode_results.get("Products", {}).get("Product", [])
            if isinstance(products, dict):
                return [products]
            return products if isinstance(products, list) else []
        except Exception:
            return []

    def get_source_record(self, target_body: str, product_type: str) -> SourceRecord:
        body_crs = "IAU_2015:30100" if target_body.lower() == "moon" else "IAU_2015:49900"
        res_m = 30.0 if "LOLA" in product_type else (463.0 if "MOLA" in product_type else 100.0)
        return SourceRecord(
            id=f"ODE_{target_body.upper()}_{product_type.upper()}",
            agency="NASA / WUSTL ODE",
            product=f"{product_type} on {target_body.capitalize()}",
            version="1.0",
            url=f"{self.BASE_URL}?target={target_body.lower()}&query=product&pt={product_type}",
            crs=body_crs,
            resolution_m=res_m
        )


"""
TERRAIN-X Base Source Adapter
Provides reliable HTTP requests with configurable timeouts, bounded retries,
and local disk-based response caching to prevent duplicate network traffic.
"""

import hashlib
import json
import os
import time
from typing import Any, Dict, Optional
import requests


class BaseAdapter:
    """
    Base HTTP client with automated disk caching, retry logic, and audit headers.
    """

    def __init__(self, cache_dir: str = "cache", timeout_s: float = 12.0, max_retries: int = 2):
        self.cache_dir = cache_dir
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        os.makedirs(self.cache_dir, exist_ok=True)

    def _cache_key(self, method: str, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        serialized = f"{method.upper()}|{url}|{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get_json(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Performs a cached HTTP GET returning JSON.
        """
        key = self._cache_key("GET", url, params)
        cache_path = os.path.join(self.cache_dir, f"{key}.json")

        if use_cache and os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

        req_headers = {"User-Agent": "TERRAIN-X-PlanetaryAnalog/1.0", "Accept": "application/json"}
        if headers:
            req_headers.update(headers)

        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.get(url, params=params, headers=req_headers, timeout=self.timeout_s)
                resp.raise_for_status()
                data = resp.json()
                if use_cache:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                return data
            except (requests.RequestException, ValueError) as err:
                last_err = err
                time.sleep(0.5 * (attempt + 1))

        raise RuntimeError(f"HTTP GET failed after {self.max_retries} retries for {url}: {last_err}")


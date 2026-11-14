"""
Tests for BaseAdapter caching behavior.
Verifies that duplicate requests hit the local cache and remain deterministic.
"""

import os
import shutil
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from modules.science.source_adapters.base import BaseAdapter


def test_reproducible_disk_cache():
    """
    Benchmark 6: Two calls to the same endpoint hit the local cache and return identical payloads.
    """
    temp_dir = tempfile.mkdtemp()
    try:
        adapter = BaseAdapter(cache_dir=temp_dir, timeout_s=5.0)
        url = "https://mock.nasa.gov/api/data"
        params = {"query": "dem", "limit": 1}

        mock_payload = {"status": "success", "results": [{"id": "ITEM_1", "val": 42}]}

        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_payload
            mock_resp.status_code = 200
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            # Call 1: Network fetch, should write to cache
            call1 = adapter.get_json(url, params=params, use_cache=True)
            assert mock_get.call_count == 1
            assert call1 == mock_payload

            # Call 2: Should read directly from disk cache, network NOT called again
            call2 = adapter.get_json(url, params=params, use_cache=True)
            assert mock_get.call_count == 1  # Still 1!
            assert call2 == mock_payload
            assert call1 == call2

            # Verify cache file exists on disk
            cache_files = os.listdir(temp_dir)
            assert len(cache_files) == 1
            assert cache_files[0].endswith(".json")

    finally:
        shutil.rmtree(temp_dir)


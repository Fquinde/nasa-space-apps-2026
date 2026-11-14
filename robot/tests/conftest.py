"""Fixtures comunes. Ningún test necesita robot ni Internet."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from terrainx_robot.fixtures.synthetic import write_synthetic_session
from terrainx_robot.storage.scan_store import ScanStore


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Aísla los tests de cualquier configuración TERRAINX_* del entorno del usuario."""
    import os

    for key in list(os.environ):
        if key.startswith("TERRAINX_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture
def store(data_dir: Path) -> ScanStore:
    return ScanStore(data_dir)


@pytest.fixture
def synthetic_session(data_dir: Path) -> Path:
    info = write_synthetic_session(data_dir / "sessions", n_frames=6, seed=11)
    return data_dir / "sessions" / info.session_id

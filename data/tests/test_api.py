"""
Tests for FastAPI REST endpoints (Contracts 1.0).
Verifies HTTP response status codes and schema conformance.
"""

from fastapi.testclient import TestClient
from modules.science.api import app

client = TestClient(app)


def test_api_list_sources():
    resp = client.get("/api/v1/sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert len(sources) >= 5
    ids = [s["id"] for s in sources]
    assert any("NASA_CMR" in sid for sid in ids)
    assert any("ODE" in sid for sid in ids)


def test_api_list_mission_profiles():
    resp = client.get("/api/v1/mission-profiles")
    assert resp.status_code == 200
    profiles = resp.json()
    assert len(profiles) >= 2
    profile_ids = [p["id"] for p in profiles]
    assert "LUNAR_VOLCANIC_CAVITY_V1" in profile_ids


def test_api_get_site():
    resp = client.get("/api/v1/sites/ES_LANZAROTE_CORONA")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "ES_LANZAROTE_CORONA"
    assert data["status"] == "positive_control"
    assert "earth_geojson" in data

    # 404 on missing site
    resp_404 = client.get("/api/v1/sites/NON_EXISTENT_SITE")
    assert resp_404.status_code == 404


def test_api_post_assessment():
    payload = {
        "site_id": "ES_LANZAROTE_CORONA",
        "mission_id": "LUNAR_VOLCANIC_CAVITY_V1"
    }
    resp = client.post("/api/v1/assessments", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["site_id"] == "ES_LANZAROTE_CORONA"
    assert data["score"] is not None
    assert data["score"] > 0.80
    assert data["completeness"] == 1.0


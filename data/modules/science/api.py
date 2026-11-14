"""
TERRAIN-X REST API (Contracts 1.0)
Exposes official REST endpoints for web applications, frontend integration, and pipeline execution:
- GET  /api/v1/sources
- GET  /api/v1/mission-profiles
- GET  /api/v1/sites/{id}
- GET  /api/v1/sites
- POST /api/v1/assessments
- GET  /api/v1/validation/benchmark
- GET  /api/v1/validation/sensitivity
"""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from modules.science.schemas import AnalogSite, Assessment, MissionProfile, SourceRecord
from modules.science.features.catalog import ANALOG_CATALOG, get_all_sites, get_site_by_id
from modules.science.score import AnalogScorer, DEFAULT_MISSION_PROFILES
from modules.science.validation import run_benchmark_evaluation, run_weight_sensitivity_analysis

app = FastAPI(
    title="TERRAIN-X Planetary Analog Science API",
    version="1.0.0",
    description="Scientific evaluation engine matching Earth analog sites with Lunar and Martian mission profiles."
)


class AssessmentRequest(BaseModel):
    site_id: str = Field(..., description="Target candidate site ID (e.g. 'ES_LANZAROTE_CORONA')")
    mission_id: str = Field(..., description="Target mission profile ID (e.g. 'LUNAR_VOLCANIC_CAVITY_V1')")


@app.get("/api/v1/sources", response_model=List[SourceRecord])
def list_sources():
    """
    Returns registered official NASA, PDS, ODE, and partner data source records.
    """
    from modules.science.source_adapters import CMRClient, PDSClient, ODEClient, TrekWMTSClient, POWERClient
    cmr = CMRClient()
    pds = PDSClient()
    ode = ODEClient()
    trek = TrekWMTSClient()
    pwr = POWERClient()

    return [
        cmr.get_source_record("ASTGTM", "ASTER Global Digital Elevation Model V003"),
        cmr.get_source_record("NASADEM", "NASADEM Merged DEM Global 1 arcsecond"),
        pwr.get_source_record(),
        ode.get_source_record("moon", "LOLA_EDR"),
        ode.get_source_record("mars", "MOLA_MEGDR"),
        trek.get_source_record("moon", "LRO_LOLA_ClrShade_Global_128ppd_v04"),
        trek.get_source_record("mars", "Mars_MGS_MOLA_ClrShade_merge_global_463m"),
        pds.get_source_record("LROC", "Moon")
    ]


@app.get("/api/v1/mission-profiles", response_model=List[MissionProfile])
def list_mission_profiles():
    """
    Returns all registered operational mission profiles and feature weights.
    """
    return list(DEFAULT_MISSION_PROFILES.values())


@app.get("/api/v1/sites", response_model=List[AnalogSite])
def list_sites():
    """
    Returns all candidate analog sites, controls, and associated citations.
    """
    return get_all_sites()


@app.get("/api/v1/sites/{site_id}", response_model=AnalogSite)
def get_site(site_id: str):
    """
    Retrieves a single candidate site by ID with GeoJSON boundaries.
    """
    site = get_site_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"AnalogSite '{site_id}' not found in catalog.")
    return site


@app.post("/api/v1/assessments", response_model=Assessment)
def create_assessment(req: AssessmentRequest):
    """
    Evaluates an Earth analog site against a designated mission profile.
    """
    site = get_site_by_id(req.site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site '{req.site_id}' not found.")
    if req.mission_id not in DEFAULT_MISSION_PROFILES:
        raise HTTPException(status_code=400, detail=f"Mission profile '{req.mission_id}' not found.")

    scorer = AnalogScorer()
    return scorer.evaluate_site(site, req.mission_id)


@app.get("/api/v1/validation/benchmark")
def get_benchmark(mission_id: str = "LUNAR_VOLCANIC_CAVITY_V1"):
    """
    Executes a complete benchmark run across all catalog sites.
    """
    assessments = run_benchmark_evaluation(mission_id)
    return {"mission_id": mission_id, "rankings": assessments}


@app.get("/api/v1/validation/sensitivity")
def get_sensitivity(mission_id: str = "LUNAR_VOLCANIC_CAVITY_V1"):
    """
    Executes a multi-profile weight sensitivity study.
    """
    return run_weight_sensitivity_analysis(mission_id)


"""
TERRAIN-X Science Schemas (External Contracts 1.0)
Defines strictly typed Pydantic models for data provenance, mission profiles,
analog sites, planetary terrain assets, and mission suitability assessments.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class SourceRecord(BaseModel):
    """
    Data provenance record tracking original dataset heritage, licensing,
    and geometric resolution.
    """
    id: str = Field(..., description="Unique source identifier (e.g. 'NASADEM_HGT_V001')")
    agency: str = Field(..., description="Issuing agency: NASA, ESA, USGS, JAXA, etc.")
    product: str = Field(..., description="Scientific product code or name")
    version: str = Field(..., description="Product version string")
    url: str = Field(..., description="Access URL or landing page")
    doi: Optional[str] = Field(None, description="Digital Object Identifier if assigned")
    acquired_at: Optional[str] = Field(None, description="Original acquisition date or range")
    downloaded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    license: Optional[str] = Field("Open / NASA Public Domain", description="Data license")
    crs: str = Field(..., description="Coordinate Reference System (e.g. 'EPSG:4326', 'IAU_2015:30100')")
    resolution_m: Optional[float] = Field(None, description="Nominal ground resolution in meters")
    hash: Optional[str] = Field(None, description="SHA256 checksum of the asset or metadata payload")


class MissionProfile(BaseModel):
    """
    Operational test profile specifying requirements for Earth analog testing.
    Represents functional test constraints for a target planetary environment.
    """
    id: str = Field(..., description="Profile ID (e.g. 'LUNAR_LAVA_TUBE_ACCESS_V1')")
    label: str = Field(..., description="Human-readable mission profile label")
    target_body: Literal["Moon", "Mars"] = Field(..., description="Target planetary body")
    target_region: str = Field(..., description="Target planetary analog region (e.g. 'Marius Hills', 'Arsia Mons')")
    features: List[str] = Field(..., description="List of physical terrain features evaluated")
    weights: Dict[str, float] = Field(..., description="Relative weights for feature matching, summing to 1.0")
    required_features: List[str] = Field(..., description="Critical features that must be present; missing triggers insufficient_evidence")
    version: str = Field(default="1.0.0", description="Profile schema version")


class AnalogSite(BaseModel):
    """
    Candidate Earth analog site with real spatial boundaries, verified features,
    and cited geological literature.
    """
    id: str = Field(..., description="Site code (e.g. 'ES_LANZAROTE_CORONA')")
    name: str = Field(..., description="Full descriptive name")
    earth_geojson: Dict[str, Any] = Field(..., description="GeoJSON Polygon/MultiPolygon geometry in WGS84")
    earth_crs: str = Field(default="EPSG:4326", description="Native coordinate system of earth_geojson")
    local_utm_epsg: str = Field(..., description="Projected metric CRS for local Euclidean and slope calculations")
    feature_values: Dict[str, Optional[float]] = Field(..., description="Extracted numerical and categorical metric values")
    sources: List[str] = Field(default_factory=list, description="List of source IDs backing this site's metrics")
    coverage: str = Field(default="local_aoi", description="Spatial coverage extent descriptor")
    status: Literal["positive_control", "negative_control", "candidate", "novel_candidate"] = Field(
        ..., description="Validation status of the analog site"
    )
    cave_evidence: Optional[List[str]] = Field(
        default=None,
        description="Evidence types supporting subterranean cavity existence (e.g. 'observed_skylight', 'surveyed_lava_tube')"
    )


class TerrainAsset(BaseModel):
    """
    Reference to a localized raster or vector terrain asset (Earth, Moon, or Mars).
    """
    id: str = Field(..., description="Unique asset ID")
    site_id: str = Field(..., description="Associated AnalogSite or planetary target ID")
    body: Literal["Earth", "Moon", "Mars"] = Field(..., description="Planetary body")
    kind: Literal["dem", "slope", "roughness", "wmts_visual", "surface_temp", "reflectance"] = Field(...)
    url: str = Field(..., description="Asset file path, remote URL, or tile template")
    crs: str = Field(..., description="Native CRS string")
    vertical_datum: Optional[str] = Field(None, description="Vertical reference (e.g. EGM96, Lunar Geoid, Mars Datum)")
    resolution_m: float = Field(..., description="Spatial resolution in meters per pixel")
    bounds: List[float] = Field(..., description="Bounding box [min_x, min_y, max_x, max_y] in native CRS")
    synthetic_fixture: bool = Field(default=False, description="Flag indicating if asset is a deterministic test fixture")


class Assessment(BaseModel):
    """
    Evaluation result scoring how closely an Earth site mimics a Mission Profile.
    """
    id: str = Field(..., description="Unique assessment run ID")
    mission_id: str = Field(..., description="Target MissionProfile ID")
    site_id: str = Field(..., description="Evaluated AnalogSite ID")
    score: Optional[float] = Field(None, description="Normalized similarity score in range [0, 1]. None if insufficient evidence.")
    completeness: float = Field(..., description="Fraction of required feature weights available in range [0, 1]")
    confidence: float = Field(..., description="Confidence metric reflecting data resolution, provenance, and freshness")
    feature_scores: Dict[str, float] = Field(default_factory=dict, description="Per-feature similarity contributions in [0, 1]")
    feature_contributions: Dict[str, float] = Field(default_factory=dict, description="Weighted contribution of each feature to the final score")
    warnings: List[str] = Field(default_factory=list, description="Scientific caveats, missing variables, or datum limits")
    method_version: str = Field(default="TERRAIN-X-V1.0.0", description="Algorithm version identifier")

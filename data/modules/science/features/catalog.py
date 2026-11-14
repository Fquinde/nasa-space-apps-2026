"""
TERRAIN-X Candidate Analog Sites Catalog
Reproducible catalog of Earth analog sites with verified coordinates,
local metric projections, cited geological sources, and validation status.

Controls:
- Positive Controls: Lanzarote (Corona Tube System) & Lava Beds (Valentine Cave)
- Candidate Sites: Mauna Loa Hawaii & Laki Fissure Iceland
- Negative Control: Yungay Atacama Desert (Hyperarid sedimentary evaporite - no basaltic tubes)
"""

from typing import Dict, List, Optional
from modules.science.schemas import AnalogSite


ANALOG_CATALOG: Dict[str, AnalogSite] = {
    "ES_LANZAROTE_CORONA": AnalogSite(
        id="ES_LANZAROTE_CORONA",
        name="Corona Volcanic Lava Tube System (Lanzarote, Canary Islands, Spain)",
        earth_geojson={
            "type": "Polygon",
            "coordinates": [[
                [-13.465, 29.130],
                [-13.435, 29.130],
                [-13.435, 29.165],
                [-13.465, 29.165],
                [-13.465, 29.130]
            ]]
        },
        earth_crs="EPSG:4326",
        local_utm_epsg="EPSG:32628",  # WGS 84 / UTM zone 28N
        feature_values={
            "volcanic_context": 1.0,               # Verified oceanic island tholeiitic/alkaline basalt
            "cave_accessibility_evidence": 1.0,   # Cueva de los Verdes / Jameos del Agua surveyed skylights
            "slope_mean_deg": 6.8,                # Low-to-moderate volcanic shield slopes
            "roughness_tri_m": 2.4,               # Aa & Pahoehoe basalt blocks
            "surface_aridity_proxy": 0.88,        # Semi-arid volcanic desert, minimal vegetation cover
            "subsurface_thermal_stability": 0.92  # Cavity interior buffered at ~18C year-round
        },
        sources=[
            "ESA_PANGAEA_2017_2024",
            "Sauro_et_al_2020_Earth_Science_Reviews",
            "IGN_Spain_National_Topographic_DEM"
        ],
        coverage="local_aoi_25km2",
        status="positive_control",
        cave_evidence=["observed_skylight", "speleological_survey", "radar_sounder_ground_truth"]
    ),

    "US_LAVA_BEDS_VALENTINE": AnalogSite(
        id="US_LAVA_BEDS_VALENTINE",
        name="Valentine Cave / Lava Beds National Monument (California, USA)",
        earth_geojson={
            "type": "Polygon",
            "coordinates": [[
                [-121.540, 41.690],
                [-121.490, 41.690],
                [-121.490, 41.730],
                [-121.540, 41.730],
                [-121.540, 41.690]
            ]]
        },
        earth_crs="EPSG:4326",
        local_utm_epsg="EPSG:32610",  # WGS 84 / UTM zone 10N
        feature_values={
            "volcanic_context": 1.0,               # Medicine Lake shield volcano basalt
            "cave_accessibility_evidence": 0.95,  # Multiple walk-in skylights and collapsed lava tube trenches
            "slope_mean_deg": 7.5,                # Moderate gentle basalt plateau
            "roughness_tri_m": 3.1,               # Broken basaltic breakdown blocks
            "surface_aridity_proxy": 0.72,        # High desert shrubland with low moisture
            "subsurface_thermal_stability": 0.88  # Perennially cold buffered subsurface
        },
        sources=[
            "USGS_Scientific_Investigations_Report_2014_5038",
            "Garry_et_al_2012_LPSC_43",
            "USGS_3DEP_10m_DEM"
        ],
        coverage="local_aoi_30km2",
        status="positive_control",
        cave_evidence=["observed_skylight", "speleological_survey", "lidar_cave_mapping"]
    ),

    "US_HAWAII_MAUNA_LOA": AnalogSite(
        id="US_HAWAII_MAUNA_LOA",
        name="Mauna Loa Southwest Rift Zone & HI-SEAS Analog (Hawaii, USA)",
        earth_geojson={
            "type": "Polygon",
            "coordinates": [[
                [-155.620, 19.450],
                [-155.560, 19.450],
                [-155.560, 19.510],
                [-155.620, 19.510],
                [-155.620, 19.450]
            ]]
        },
        earth_crs="EPSG:4326",
        local_utm_epsg="EPSG:32604",  # WGS 84 / UTM zone 4N
        feature_values={
            "volcanic_context": 1.0,               # Active basaltic shield volcano
            "cave_accessibility_evidence": 0.80,  # Young lava tubes, some unstable collapse features
            "slope_mean_deg": 12.3,               # Moderate to steep volcanic flank
            "roughness_tri_m": 4.6,               # Highly rugged aa lava flows
            "surface_aridity_proxy": 0.65,        # Sub-alpine volcanic barren
            "subsurface_thermal_stability": 0.75  # Geothermal warmth in certain young tubes
        },
        sources=[
            "NASA_HI_SEAS_Mission_Reports",
            "USGS_Hawaiian_Volcano_Observatory_HVO",
            "USGS_3DEP_1m_Lidar"
        ],
        coverage="local_aoi_40km2",
        status="candidate",
        cave_evidence=["observed_skylight", "active_volcanic_monitoring"]
    ),

    "IS_SURTSEY_LAKI": AnalogSite(
        id="IS_SURTSEY_LAKI",
        name="Laki Volcanic Fissures & Eldgja (Southern Highlands, Iceland)",
        earth_geojson={
            "type": "Polygon",
            "coordinates": [[
                [-18.350, 63.950],
                [-18.150, 63.950],
                [-18.150, 64.100],
                [-18.350, 64.100],
                [-18.350, 63.950]
            ]]
        },
        earth_crs="EPSG:4326",
        local_utm_epsg="EPSG:32627",  # WGS 84 / UTM zone 27N
        feature_values={
            "volcanic_context": 1.0,               # Massive flood basalt fissure eruption
            "cave_accessibility_evidence": 0.45,  # Few sustained tube skylights; mainly open fissure grabens
            "slope_mean_deg": 14.1,               # Tephra cones and crater rows
            "roughness_tri_m": 5.2,               # High roughness, jagged basalt tephra
            "surface_aridity_proxy": 0.35,        # High precipitation, cold subarctic climate
            "subsurface_thermal_stability": 0.60  # Near-freezing ground temperatures
        },
        sources=[
            "Icelandic_Meteorological_Office_IMO",
            "Thordarson_Self_1993_Bull_Volcanol",
            "ArcticDEM_Release_7"
        ],
        coverage="regional_strip_60km2",
        status="candidate",
        cave_evidence=["fissure_grabens", "partial_overhangs"]
    ),

    "CL_ATACAMA_YUNGAY": AnalogSite(
        id="CL_ATACAMA_YUNGAY",
        name="Yungay Hyperarid Core (Atacama Desert, Chile) - NEGATIVE CONTROL",
        earth_geojson={
            "type": "Polygon",
            "coordinates": [[
                [-70.020, -24.080],
                [-69.960, -24.080],
                [-69.960, -24.020],
                [-70.020, -24.020],
                [-70.020, -24.080]
            ]]
        },
        earth_crs="EPSG:4326",
        local_utm_epsg="EPSG:32619",  # WGS 84 / UTM zone 19S
        feature_values={
            "volcanic_context": 0.0,               # Sedimentary alluvial / sulfate-nitrate evaporite (NOT basaltic)
            "cave_accessibility_evidence": 0.0,   # No basaltic lava tubes or volcanic skylights
            "slope_mean_deg": 3.2,                # Flat playa and gentle alluvial plains
            "roughness_tri_m": 0.8,               # Fine-grained saline regolith
            "surface_aridity_proxy": 1.0,         # Hyperarid Earth analog (used for Mars soil tests, not caves)
            "subsurface_thermal_stability": 0.20  # Extreme diurnal surface thermal swings (>40C)
        },
        sources=[
            "NASA_Astrobiology_Institute_Atacama_Field_Reports",
            "Navarro_Gonzalez_et_al_2003_Science",
            "NASADEM_HGT_V001"
        ],
        coverage="local_aoi_35km2",
        status="negative_control",
        cave_evidence=[]
    )
}


def get_all_sites() -> List[AnalogSite]:
    return list(ANALOG_CATALOG.values())


def get_site_by_id(site_id: str) -> Optional[AnalogSite]:
    return ANALOG_CATALOG.get(site_id)


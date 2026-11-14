# 🛰️ TERRAIN-X: Official Data Sources Verification & Provenance Status

**Audit Date:** 2026-11-13 (Updated Live)  
**Evaluation Standard:** NASA Earthdata, Planetary Data System (PDS), and WUSTL ODE Standards  
**Verification Protocol:** Automated timeout-bounded HTTP GET probe with response latency, status code, authentication requirement, and data type inspection.

---

## 1. Verified Official Endpoints

| Provider & API | Tested Endpoint URL | HTTP Status | Auth Required? | Payload Type | Latency (s) | Scientific Purpose & Limitations |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **NASA CMR Collections API** | `https://cmr.earthdata.nasa.gov/search/collections.json?keyword=NASADEM&page_size=1` | **200 OK** | No (Open) | JSON | ~0.99s | Dynamic discovery of Earth observation datasets (NASADEM, SRTM, ASTER). Used to fetch `concept_id` without hardcoding deprecated identifiers. |
| **NASA CMR-STAC** | `https://cmr.earthdata.nasa.gov/stac` | **200 OK** | No (Open) | GeoJSON / STAC | ~0.85s | SpatioTemporal Asset Catalog API for Granule-level temporal and bounding-box queries. |
| **NASA CMR ASTER GDEM** | `https://cmr.earthdata.nasa.gov/search/collections.json?short_name=ASTGTM&version=003&page_size=1` | **200 OK** | No (Open) | JSON | ~0.95s | ASTER Global Digital Elevation Model v3 (30m spatial resolution). Concept ID: `C1711961296-LPCLOUD`. |
| **NASA POWER Daily API** | `https://power.larc.nasa.gov/api/temporal/daily/point` | **200 OK** | No (Open) | JSON | ~1.48s | Surface meteorological context: 2-meter air temperature (`T2M`), precipitation (`PRECTOTCORR`). Used as aridity and environmental stress proxy. |
| **NASA PDS Search API v1** | `https://pds.nasa.gov/api/search/1/products?limit=1` | **200 OK** | No (Open) | JSON | ~1.10s | Planetary Data System metadata catalog (>93M products). Good for mission-level collection discovery; for spatial footprints ODE is preferred. |
| **WUSTL ODE REST API (Moon)** | `https://oderest.rsl.wustl.edu/live2/?target=moon&query=product&pt=LOLA_EDR&output=JSON&limit=1` | **200 OK** | No (Open) | JSON | ~4.23s | Washington University Orbital Data Explorer. Product search for Lunar Reconnaissance Orbiter (LRO) LOLA laser altimeter datasets. |
| **WUSTL ODE REST API (Mars)** | `https://oderest.rsl.wustl.edu/live2/?target=mars&query=product&pt=MOLA_MEGDR&output=JSON&limit=1` | **200 OK** | No (Open) | JSON | ~1.27s | Mars Global Surveyor (MGS) MOLA topography gridded records (MEGDR). Authoritative source for Mars elevation. |
| **NASA Moon Trek WMTS** | `https://trek.nasa.gov/tiles/Moon/EQ/LRO_LOLA_ClrShade_Global_128ppd_v04/1.0.0/WMTSCapabilities.xml` | **200 OK** | No (Open) | XML (OGC WMTS) | ~1.51s | Moon Trek Web Map Tile Service. Visual basemaps for human inspection. **Limitation:** 8-bit visual tiles are for visualization, NOT for physical elevation calculations. |
| **NASA Mars Trek WMTS** | `https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/WMTSCapabilities.xml` | **200 OK** | No (Open) | XML (OGC WMTS) | ~1.77s | Mars Trek Web Map Tile Service for MOLA shaded relief visualization. Same limitation: visualization only. |
| **NASA HLS (Harmonized Landsat/Sentinel-2)** | `https://cmr.earthdata.nasa.gov/search/collections.json?short_name=HLSL30&page_size=1` | **200 OK** | No for metadata; Yes (Earthdata Login) for raster granules | JSON | ~3.60s | Surface reflectance and NDVI at 30m resolution. Concept ID: `C2021957657-LPCLOUD`. Requires Earthdata Login token for direct raster asset download. |
| **NASA EMIT Mineralogy (EMITL2BMIN)** | `https://cmr.earthdata.nasa.gov/search/collections.json?short_name=EMITL2BMIN&page_size=1` | **200 OK** | No for metadata; Yes for netCDF granules | JSON | ~2.85s | L2B mineral identification (basalt, pyroxene, clay minerals). Limited spatial swath coverage; used as optional high-fidelity feature. |
| **USGS Unified Geologic Map of the Moon** | `https://astrogeology.usgs.gov/search/map/Moon/Geology/Unified_Geologic_Map_of_the_Moon_GIS_v2/` | **200 OK** | No (Open) | Web landing page / GIS package | ~2.32s | Authoritative global USGS geological map (1:5,000,000 scale). Non-NASA federal partner dataset. |

---

## 2. Key Scientific Caveats and Provenance Rules

1. **WMTS vs True DEM Rasters:**
   * **WMTS tiles** are 8-bit RGB color-shaded or grayscale visualizations scaled to display contrast. They **must never be used to compute physical slope, elevation, or roughness**.
   * Scientific metric analysis requires **true 32-bit floating-point Digital Elevation Models (DEMs)** (e.g. NASADEM GeoTIFF, LOLA RDR/GDR, MOLA MEGDR).

2. **Planetary Coordinate Systems and Datums:**
   * Earth coordinates: WGS84 ellipsoid (`EPSG:4326`) for geographic points; UTM projection in meters for local spatial calculus.
   * Moon coordinates: IAU 2015 Lunar Reference System (Sphere with radius $R = 1737.4\text{ km}$, e.g. `IAU_2015:30100`).
   * Mars coordinates: IAU 2015 Mars Reference System (Ellipsoid with semi-major axis $A = 3396.19\text{ km}$, $B = 3376.20\text{ km}$, e.g. `IAU_2015:49900`).
   * **Rule:** Planetary coordinates are strictly segregated. Cross-body pixel overlay is mathematically prohibited.

3. **Subsurface Cave and Lava Tube Evidence:**
   * Global cave catalogs (e.g. Vulcanospeleological databases, USGS pit crater databases) are known to be spatially incomplete.
   * Cave features are tagged with `cave_evidence: ["observed_skylight", "gravitational_anomaly", "radar_sounder_detection", "literature_ground_truth"]`. If unconfirmed, the status remains `candidate` rather than `novel_discovery`.


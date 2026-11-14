# 🪐 TERRAIN-X: Planetary Analog Evaluation Engine (Data Module)

> **Official Challenge 2026:** *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*  
> **Subsystem:** `nasa-space-apps-2026/data`  
> **Target Profile:** Exploration and ingress testing in volcanic basaltic terrains with accessible subsurface cavities (lava tubes & collapse pit skylights).

---

## 📖 Table of Contents
1. [Overview & Scientific Rationale](#overview--scientific-rationale)
2. [Directory Structure](#directory-structure)
3. [Prerequisites & Installation (Windows, Linux, macOS)](#prerequisites--installation)
4. [Live Probing of Official NASA/Planetary APIs](#live-probing-of-official-apis)
5. [CLI Usage (Ranking, Sensitivity & Inspection)](#cli-usage)
6. [REST API Execution (Contracts 1.0)](#rest-api-execution)
7. [Running the Automated Test Suite](#running-the-automated-test-suite)
8. [Geospatial & Planetary Science Concepts](#geospatial--planetary-science-concepts)
9. [Troubleshooting & FAQ](#troubleshooting--faq)

---

## 1. Overview & Scientific Rationale

TERRAIN-X compares candidate terrestrial locations against Lunar and Martian environments for an **operational mission testing profile**, not universal planetary equivalence. 

### Initial Mission Profile: Volcanic Cavity & Skylight Access
* **Target Planetary Analogs:**
  * **Moon:** Marius Hills Pit / Oceanus Procellarum Mare Basalts
  * **Mars:** Arsia Mons Volcanic Pits / Tharsis Montes
* **Operational Goal:** Assess terrestrial test readiness for autonomous quadruped robots, tethered descent anchors, subterranean LiDAR/IMU mapping, and radio propagation in basaltic tubes.
* **Core Principle:** Strict provenance, transparent scoring, refusal to convert missing data to zero, and geodetic coordinate guards preventing cross-body spatial overlay.

---

## 2. Directory Structure

```text
nasa-space-apps-2026/data/
├── README.md                      <- Complete installation and user manual
├── requirements.txt               <- Pinned Python dependencies
├── pyproject.toml                 <- Modern packaging specification
├── probe_sources.py               <- Real-time HTTP API auditor
├── probe_results.json             <- Cached API audit output
├── docs/
│   ├── SOURCES_STATUS.md          <- Official sources audit & geodetic caveats
│   ├── SAMPLE_RESULTS.md          <- Benchmark rankings & sensitivity report
│   └── BEGINNERS_GUIDE.md         <- Plain-English GIS & planetary geodesy tutorial
├── modules/
│   └── science/
│       ├── schemas.py             <- Pydantic models (External Contracts 1.0)
│       ├── score.py               <- AnalogScorer & MissionProfile logic
│       ├── validation.py          <- Benchmark evaluations & sensitivity engine
│       ├── api.py                 <- FastAPI REST endpoints
│       ├── cli.py                 <- Command-line interface
│       ├── source_adapters/       <- Typed API clients with disk caching
│       │   ├── base.py            <- Cached HTTP requests with retries
│       │   ├── cmr.py             <- NASA CMR (NASADEM, ASTER, HLS, EMIT)
│       │   ├── pds.py             <- NASA Planetary Data System (PDS4)
│       │   ├── ode.py             <- WUSTL Orbital Data Explorer (Moon/Mars)
│       │   ├── trek.py            <- NASA Moon/Mars Trek WMTS capabilities
│       │   └── power.py           <- NASA POWER Daily meteorology & solar API
│       ├── processing/            <- Robust geomorphometry & geodesy
│       │   ├── planetary.py       <- IAU Moon/Mars coordinate guards
│       │   ├── dem.py             <- Horn's slope & Riley's TRI roughness
│       │   └── quality.py         <- Nodata filtering & raster integrity
│       └── features/
│           ├── catalog.py         <- 5 candidate Earth analog sites & controls
│           └── extractors.py      <- Gaussian normalization & feature extraction
├── fixtures/
│   └── synthetic_dem.py           <- Deterministic flat, tilted & nodata test rasters
├── cache/                         <- Local disk cache for API queries
└── tests/                         <- Pytest test suite (18 unit/integration tests)
```

---

## 3. Prerequisites & Installation

Supported platforms: **Windows 10/11**, **Ubuntu/Debian Linux**, **macOS (Intel & Apple Silicon)**.  
Python Version: **Python 3.10 to 3.14+**.

### Step 1: Open Terminal in the `data` directory
```bash
cd "c:\Users\Usuario\OneDrive\Escritorio\github\nasa-space-apps-2026\data"
```

### Step 2: Install Dependencies
```bash
# Windows (PowerShell or Command Prompt)
python -m pip install -r requirements.txt

# Linux / macOS
python3 -m pip install -r requirements.txt
```

---

## 4. Live Probing of Official NASA/Planetary APIs

Verify live network connectivity to all official NASA, PDS, ODE, and WMTS services:

```bash
python probe_sources.py
```

Inspect the generated provenance audit report in:
* [`docs/SOURCES_STATUS.md`](docs/SOURCES_STATUS.md)

---

## 5. CLI Usage

The command-line tool allows instant ranking and sensitivity inspection.

### A. Rank all Candidate Sites against Lunar Profile
```bash
python modules/science/cli.py rank --mission LUNAR_VOLCANIC_CAVITY_V1
```

### B. Rank Candidate Sites against Martian Profile
```bash
python modules/science/cli.py rank --mission MARS_LAVA_TUBE_COLLAPSE_V1
```

### C. Run Weight Sensitivity Perturbation Analysis ($\pm 25\%$)
```bash
python modules/science/cli.py sensitivity --mission LUNAR_VOLCANIC_CAVITY_V1
```

### D. Inspect a Specific Candidate Site by ID
```bash
python modules/science/cli.py site --id ES_LANZAROTE_CORONA
```

---

## 6. REST API Execution (Contracts 1.0)

Launch the FastAPI microservice on `localhost:8000`:

```bash
uvicorn modules.science.api:app --reload --host 127.0.0.1 --port 8000
```

### Official Endpoints
* `GET /api/v1/sources`: List official verified data sources (NASA CMR, PDS, ODE, Trek, POWER).
* `GET /api/v1/mission-profiles`: List operational mission profiles, weights, and targets.
* `GET /api/v1/sites`: List candidate sites, boundaries, and cited references.
* `GET /api/v1/sites/{site_id}`: Retrieve a single candidate site by ID.
* `POST /api/v1/assessments`: Run evaluation scoring for a candidate site against a mission profile.
* `GET /api/v1/validation/benchmark`: Full ranking table across all catalog sites.
* `GET /api/v1/validation/sensitivity`: Weight sensitivity perturbation trajectory.

Interactive Swagger API documentation is available at `http://127.0.0.1:8000/docs`.

---

## 7. Running the Automated Test Suite

Execute the 18 automated tests covering geomorphometry, planetary guards, scoring, caching, and API contracts:

```bash
python -m pytest -v
```

Expected output:
```text
tests/test_api.py::test_api_list_sources PASSED
tests/test_api.py::test_api_list_mission_profiles PASSED
tests/test_api.py::test_api_get_site PASSED
tests/test_api.py::test_api_post_assessment PASSED
tests/test_cache.py::test_reproducible_disk_cache PASSED
tests/test_dem.py::test_flat_raster_slope_is_zero PASSED
tests/test_dem.py::test_tilted_plane_known_slope PASSED
tests/test_dem.py::test_nodata_raster_rejection PASSED
tests/test_dem.py::test_dem_statistics_structure PASSED
tests/test_planetary.py::test_planetary_crs_guards_rejection PASSED
tests/test_planetary.py::test_valid_crs_acceptance PASSED
tests/test_planetary.py::test_cross_body_spatial_overlay_rejected PASSED
tests/test_planetary.py::test_planetary_circumference PASSED
tests/test_scorer.py::test_missing_essential_feature_triggers_insufficient_evidence PASSED
tests/test_scorer.py::test_scorer_reproducibility PASSED
tests/test_validation.py::test_positive_vs_negative_control_discrimination PASSED
tests/test_validation.py::test_weight_sensitivity_stability PASSED
tests/test_validation.py::test_provenance_manifest_completeness PASSED
======================= 18 passed in 5.0s =======================
```

---

## 8. Geospatial & Planetary Science Concepts

For an in-depth, plain-English tutorial explaining:
* Digital Elevation Models (DEMs) and Rasters
* Coordinate Reference Systems (CRS) and why you cannot compute slopes in degrees
* Horn's Slope algorithm and Riley's Terrain Ruggedness Index (TRI)
* Planetary datums (Moon IAU radius $1,737.4\text{ km}$, Mars radius $3,396.2\text{ km}$)
* Why WMTS tiles are for visualization, not metric height calculations

See [`docs/BEGINNERS_GUIDE.md`](docs/BEGINNERS_GUIDE.md).

---

## 9. Troubleshooting & FAQ

### Q: Why do I get `ModuleNotFoundError: No module named 'modules'`?
Run your command from the `data` directory using `python -m modules.science.cli` or `python modules/science/cli.py` (which includes automated path injection).

### Q: Why do planetary rasters fail if I use `EPSG:4326`?
`EPSG:4326` is the terrestrial WGS84 ellipsoid. The Moon is a sphere with a radius of $1,737.4\text{ km}$, and Mars has an equatorial radius of $3,396.2\text{ km}$. Using an Earth ellipsoid on Mars produces massive metric distortion and is physically invalid. TERRAIN-X guards prevent this silently corrupting your calculations.

### Q: Does Earthdata Login require a paid subscription?
No. NASA Earthdata Login is **100% free and open** for research and public exploration. An account is only required when directly downloading raw raster granules (e.g. HLS or EMIT); metadata discovery via CMR, CMR-STAC, and POWER is completely open.

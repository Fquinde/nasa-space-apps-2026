"""
TERRAIN-X Digital Elevation Model (DEM) Processing
Computes robust geomorphometric indicators:
- Slope (degrees) via Horn's finite-difference method
- Terrain Ruggedness Index (TRI, Riley et al., 1999)
- Local relief variation and elevation percentiles

Pedagogical note for beginners:
- A DEM is a 2D matrix where each cell represents an elevation in meters.
- Cell size (dx, dy) must be supplied in METERS, not degrees. If your DEM
  is in degrees (e.g. EPSG:4326), 1 degree is ~111,320m at the equator but shrinks
  with latitude. You must reproject to a metric CRS (e.g. UTM) before computing slope!
"""

from typing import Any, Dict, Optional, Tuple
import numpy as np


def compute_slope_horn(
    dem: np.ndarray,
    cell_size_x_m: float,
    cell_size_y_m: float,
    nodata: Optional[float] = None
) -> np.ndarray:
    """
    Computes slope in degrees using Horn's 3x3 finite-difference algorithm (GDAL standard).

    Parameters:
    - dem: 2D numpy array of elevation values in meters.
    - cell_size_x_m: Grid cell width in meters along the X axis.
    - cell_size_y_m: Grid cell height in meters along the Y axis.
    - nodata: Optional value identifying missing / unmeasured cells.

    Returns:
    - slope_deg: 2D numpy array of slope angles in degrees (0 to 90).
      Boundary edges and masked nodata cells contain np.nan.

    Why this formula?
    Horn's method weights adjacent orthogonal cells twice as much as diagonal cells,
    minimizing directional bias on natural terrain:
      [a b c]
      [d e f]
      [g h i]
      dz/dx = ((c + 2f + i) - (a + 2d + g)) / (8 * dx)
      dz/dy = ((g + 2h + i) - (a + 2b + c)) / (8 * dy)
      slope = arctan(sqrt((dz/dx)^2 + (dz/dy)^2))
    """
    if dem.ndim != 2:
        raise ValueError(f"Expected 2D elevation grid, received shape {dem.shape}")
    if dem.shape[0] < 3 or dem.shape[1] < 3:
        raise ValueError(f"Grid shape {dem.shape} too small for 3x3 window.")
    if cell_size_x_m <= 0 or cell_size_y_m <= 0:
        raise ValueError("Cell sizes must be strictly positive numbers in meters.")

    arr = np.array(dem, dtype=np.float64, copy=True)
    if nodata is not None:
        arr[arr == nodata] = np.nan

    # 3x3 neighbor slices
    a = arr[:-2, :-2]
    b = arr[:-2, 1:-1]
    c = arr[:-2, 2:]
    d = arr[1:-1, :-2]
    # e is the central cell
    f = arr[1:-1, 2:]
    g = arr[2:, :-2]
    h = arr[2:, 1:-1]
    i = arr[2:, 2:]

    # Finite differences
    dz_dx = ((c + 2.0 * f + i) - (a + 2.0 * d + g)) / (8.0 * cell_size_x_m)
    dz_dy = ((g + 2.0 * h + i) - (a + 2.0 * b + c)) / (8.0 * cell_size_y_m)

    rise_run = np.sqrt(dz_dx**2 + dz_dy**2)
    slope_rad = np.arctan(rise_run)
    slope_deg_inner = np.degrees(slope_rad)

    # Pad output to retain identical input shape (edges set to NaN)
    slope_deg = np.full_like(arr, np.nan)
    slope_deg[1:-1, 1:-1] = slope_deg_inner

    return slope_deg


def compute_terrain_ruggedness_index(dem: np.ndarray, nodata: Optional[float] = None) -> np.ndarray:
    """
    Calculates Riley's Terrain Ruggedness Index (TRI).
    Measures the root-mean-square difference between a center cell and its 8 neighbors:
    TRI = sqrt( sum( (neighbor_k - center)^2 ) / 8 )
    Units: meters of local roughness.
    """
    arr = np.array(dem, dtype=np.float64, copy=True)
    if nodata is not None:
        arr[arr == nodata] = np.nan

    center = arr[1:-1, 1:-1]
    diff_sq_sum = np.zeros_like(center)

    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if di == 0 and dj == 0:
                continue
            neighbor = arr[1 + di : arr.shape[0] - 1 + di, 1 + dj : arr.shape[1] - 1 + dj]
            diff_sq_sum += (neighbor - center) ** 2

    tri_inner = np.sqrt(diff_sq_sum / 8.0)
    tri = np.full_like(arr, np.nan)
    tri[1:-1, 1:-1] = tri_inner
    return tri


def extract_dem_statistics(
    dem: np.ndarray,
    cell_size_x_m: float,
    cell_size_y_m: float,
    nodata: Optional[float] = None,
    source_id: str = "TERRAIN_DEM"
) -> Dict[str, Any]:
    """
    Computes a comprehensive suite of geomorphometric statistics.
    Every returned variable includes explicit units and source attribution.
    """
    valid_elev = dem[dem != nodata] if nodata is not None else dem
    valid_elev = valid_elev[~np.isnan(valid_elev)]

    if len(valid_elev) == 0:
        return {
            "source_id": source_id,
            "status": "empty_or_all_nodata",
            "valid_pixel_count": 0
        }

    slope_grid = compute_slope_horn(dem, cell_size_x_m, cell_size_y_m, nodata)
    valid_slope = slope_grid[~np.isnan(slope_grid)]

    tri_grid = compute_terrain_ruggedness_index(dem, nodata)
    valid_tri = tri_grid[~np.isnan(tri_grid)]

    stats = {
        "source_id": source_id,
        "valid_pixel_count": int(len(valid_elev)),
        "elevation_min_m": float(np.min(valid_elev)),
        "elevation_max_m": float(np.max(valid_elev)),
        "elevation_mean_m": float(np.mean(valid_elev)),
        "elevation_p50_m": float(np.percentile(valid_elev, 50)),
        "elevation_iqr_m": float(np.percentile(valid_elev, 75) - np.percentile(valid_elev, 25)),
        "elevation_std_m": float(np.std(valid_elev)),
        "slope_mean_deg": float(np.mean(valid_slope)) if len(valid_slope) > 0 else 0.0,
        "slope_p90_deg": float(np.percentile(valid_slope, 90)) if len(valid_slope) > 0 else 0.0,
        "slope_max_deg": float(np.max(valid_slope)) if len(valid_slope) > 0 else 0.0,
        "tri_mean_m": float(np.mean(valid_tri)) if len(valid_tri) > 0 else 0.0,
        "tri_max_m": float(np.max(valid_tri)) if len(valid_tri) > 0 else 0.0,
        "roughness_metric": "Riley_TRI_m"
    }
    return stats


"""
TERRAIN-X Synthetic Raster Fixtures for Deterministic Testing
Generates mathematically known elevation grids to verify slope, roughness,
and nodata handling according to rigorous geospatial benchmarks.
"""

import math
import numpy as np


def create_flat_dem(rows: int = 50, cols: int = 50, elevation_m: float = 500.0) -> np.ndarray:
    """
    Creates a perfectly flat elevation grid.
    Theoretical slope everywhere: exactly 0.0 degrees.
    """
    return np.full((rows, cols), elevation_m, dtype=np.float64)


def create_tilted_plane_dem(
    rows: int = 50,
    cols: int = 50,
    cell_size_m: float = 30.0,
    slope_angle_deg: float = 15.0,
    base_elevation_m: float = 100.0
) -> np.ndarray:
    """
    Creates an idealized tilted planar surface inclined along the X axis.
    Slope is constant across all non-edge cells:
      z(x, y) = base_elevation + x * tan(slope_angle_deg)
    """
    slope_rad = math.radians(slope_angle_deg)
    tan_theta = math.tan(slope_rad)

    x_indices = np.arange(cols, dtype=np.float64)
    x_coords_m = x_indices * cell_size_m

    dem = np.zeros((rows, cols), dtype=np.float64)
    for r in range(rows):
        dem[r, :] = base_elevation_m + x_coords_m * tan_theta

    return dem


def create_nodata_dem(
    rows: int = 50,
    cols: int = 50,
    nodata_value: float = -9999.0,
    nodata_fraction: float = 0.60
) -> np.ndarray:
    """
    Creates a DEM contaminated with a high ratio of nodata values.
    Used to test quality validation rejection thresholds.
    """
    dem = np.full((rows, cols), 300.0, dtype=np.float64)
    mask = np.random.rand(rows, cols) < nodata_fraction
    dem[mask] = nodata_value
    return dem


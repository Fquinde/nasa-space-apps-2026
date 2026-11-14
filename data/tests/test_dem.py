"""
Tests for Digital Elevation Model (DEM) and geomorphometry processing.
Verifies flat raster, known slope, and nodata rejection.
"""

import math
import numpy as np
import pytest

from fixtures.synthetic_dem import create_flat_dem, create_tilted_plane_dem, create_nodata_dem
from modules.science.processing.dem import compute_slope_horn, compute_terrain_ruggedness_index, extract_dem_statistics
from modules.science.processing.quality import validate_raster_quality, QualityAssessmentError


def test_flat_raster_slope_is_zero():
    """
    Benchmark 1: Flat raster must yield exactly 0.0 degrees slope (within 1e-4 tolerance).
    """
    flat = create_flat_dem(rows=40, cols=40, elevation_m=250.0)
    slope = compute_slope_horn(flat, cell_size_x_m=30.0, cell_size_y_m=30.0)

    # Exclude boundary NaN cells
    valid_slope = slope[~np.isnan(slope)]
    assert len(valid_slope) > 0
    assert np.allclose(valid_slope, 0.0, atol=1e-4), f"Max slope found: {np.max(valid_slope)}"


def test_tilted_plane_known_slope():
    """
    Benchmark 2: Tilted planar surface with known angle (e.g. 20 degrees)
    must produce exactly that angle across all interior cells.
    """
    expected_angle = 20.0
    cell_size = 25.0
    plane = create_tilted_plane_dem(
        rows=40,
        cols=40,
        cell_size_m=cell_size,
        slope_angle_deg=expected_angle,
        base_elevation_m=100.0
    )
    slope = compute_slope_horn(plane, cell_size_x_m=cell_size, cell_size_y_m=cell_size)

    valid_slope = slope[~np.isnan(slope)]
    assert len(valid_slope) > 0
    # Mean slope should match expected angle within 1e-3 degrees
    assert np.allclose(valid_slope, expected_angle, atol=1e-3), (
        f"Expected {expected_angle} deg, got mean {np.mean(valid_slope)} deg"
    )


def test_nodata_raster_rejection():
    """
    Benchmark 3: Raster with excessive nodata (> 50%) must be rejected with QualityAssessmentError.
    """
    corrupt_dem = create_nodata_dem(rows=40, cols=40, nodata_fraction=0.65)
    with pytest.raises(QualityAssessmentError) as exc_info:
        validate_raster_quality(corrupt_dem, nodata=-9999.0, max_nodata_ratio=0.50)

    assert "exceeds maximum allowable" in str(exc_info.value)


def test_dem_statistics_structure():
    """
    Verifies that DEM statistics include all mandatory geomorphometric attributes.
    """
    dem = create_tilted_plane_dem(rows=20, cols=20, cell_size_m=30.0, slope_angle_deg=10.0)
    stats = extract_dem_statistics(dem, cell_size_x_m=30.0, cell_size_y_m=30.0, source_id="TEST_SRTM")

    assert stats["source_id"] == "TEST_SRTM"
    assert "slope_mean_deg" in stats
    assert "tri_mean_m" in stats
    assert stats["slope_mean_deg"] > 0.0
    assert stats["valid_pixel_count"] == 400


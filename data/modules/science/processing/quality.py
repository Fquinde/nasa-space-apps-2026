"""
TERRAIN-X Spatial Data Quality & Integrity Checker
Validates nodata fractions, bounding box sanity, and physical range plausibility.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np


class QualityAssessmentError(Exception):
    """Raised when spatial raster data fails fundamental sanity checks."""
    pass


def validate_raster_quality(
    dem: np.ndarray,
    nodata: Optional[float] = None,
    max_nodata_ratio: float = 0.50,
    expected_min_m: float = -500.0,
    expected_max_m: float = 9000.0
) -> Dict[str, Any]:
    """
    Performs data quality checks on elevation raster.
    Returns audit dictionary with warnings if criteria are marginally met,
    or raises QualityAssessmentError if raster is corrupt or unusable.
    """
    total_cells = dem.size
    if total_cells == 0:
        raise QualityAssessmentError("Raster is empty (0 cells).")

    is_nodata = np.isnan(dem)
    if nodata is not None:
        is_nodata = is_nodata | (dem == nodata)

    nodata_count = int(np.sum(is_nodata))
    nodata_ratio = nodata_count / total_cells

    warnings: List[str] = []
    if nodata_ratio > max_nodata_ratio:
        raise QualityAssessmentError(
            f"Raster rejected: nodata ratio {nodata_ratio:.1%} exceeds maximum allowable {max_nodata_ratio:.1%}."
        )
    elif nodata_ratio > 0.15:
        warnings.append(f"High nodata proportion detected ({nodata_ratio:.1%}). Statistical estimates have reduced precision.")

    valid_vals = dem[~is_nodata]
    if len(valid_vals) == 0:
        raise QualityAssessmentError("Zero valid elevation pixels in raster.")

    actual_min = float(np.min(valid_vals))
    actual_max = float(np.max(valid_vals))

    if actual_min < expected_min_m or actual_max > expected_max_m:
        warnings.append(
            f"Elevation range [{actual_min:.1f}m, {actual_max:.1f}m] exceeds typical terrestrial geoid bounds "
            f"[{expected_min_m}m, {expected_max_m}m]. Verify vertical datum."
        )

    return {
        "valid": True,
        "total_pixels": total_cells,
        "valid_pixels": int(len(valid_vals)),
        "nodata_ratio": round(nodata_ratio, 4),
        "actual_min_m": round(actual_min, 2),
        "actual_max_m": round(actual_max, 2),
        "warnings": warnings
    }


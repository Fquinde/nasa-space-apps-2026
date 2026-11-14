"""
Tests for Planetary CRS guards and geodetic rules.
Ensures extraterrestrial bodies (Moon, Mars) are never silently assigned WGS84.
"""

import pytest
from modules.science.processing.planetary import (
    PlanetaryCRSGuard,
    MOON_RADIUS_M,
    MARS_SEMI_MAJOR_M,
    EARTH_WGS84_A_M,
)


def test_planetary_crs_guards_rejection():
    """
    Benchmark 4: Planetary CRS cannot be converted silently to Earth WGS84 (EPSG:4326).
    """
    # Lunar raster assigned EPSG:4326 must raise ValueError
    with pytest.raises(ValueError) as exc_moon:
        PlanetaryCRSGuard.validate_body_crs("Moon", "EPSG:4326")
    assert "Planetary Guard Violation" in str(exc_moon.value)

    # Martian raster assigned EPSG:4326 must raise ValueError
    with pytest.raises(ValueError) as exc_mars:
        PlanetaryCRSGuard.validate_body_crs("Mars", "EPSG:4326")
    assert "Planetary Guard Violation" in str(exc_mars.value)

    # Terrestrial site assigned Martian CRS must raise ValueError
    with pytest.raises(ValueError) as exc_earth:
        PlanetaryCRSGuard.validate_body_crs("Earth", "IAU_2015:49900")
    assert "Geodetic Contamination" in str(exc_earth.value)


def test_valid_crs_acceptance():
    """
    Verifies valid IAU coordinate systems pass guard validation.
    """
    assert PlanetaryCRSGuard.validate_body_crs("Moon", "IAU_2015:30100") is True
    assert PlanetaryCRSGuard.validate_body_crs("Mars", "IAU_2015:49900") is True
    assert PlanetaryCRSGuard.validate_body_crs("Earth", "EPSG:4326") is True


def test_cross_body_spatial_overlay_rejected():
    """
    Enforces that direct raster superposition between distinct bodies is blocked.
    """
    with pytest.raises(TypeError) as exc:
        PlanetaryCRSGuard.prevent_cross_body_overlay("Earth", "Moon")
    assert "Cross-Body Spatial Overlay Rejected" in str(exc.value)


def test_planetary_circumference():
    """
    Validates standard IAU equatorial dimensions.
    Moon radius ~1737.4 km, Earth radius ~6378.1 km.
    """
    c_moon = PlanetaryCRSGuard.get_body_equatorial_circumference_m("Moon")
    c_earth = PlanetaryCRSGuard.get_body_equatorial_circumference_m("Earth")

    assert c_moon < c_earth
    assert round(MOON_RADIUS_M) == 1737400


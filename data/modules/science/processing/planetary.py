"""
TERRAIN-X Planetary Geodesy & Coordinate Guards
Enforces IAU (International Astronomical Union) planetary coordinate standards.
Prevents cross-body contamination (e.g. applying Earth WGS84 to Moon/Mars).
"""

from typing import Tuple

# Standard Planetary Radii (in meters) established by IAU 2015
MOON_RADIUS_M: float = 1737400.0
MARS_SEMI_MAJOR_M: float = 3396190.0
MARS_SEMI_MINOR_M: float = 3376200.0
EARTH_WGS84_A_M: float = 6378137.0
EARTH_WGS84_B_M: float = 6356752.3142


class PlanetaryCRSGuard:
    """
    Validates that rasters and vectors carry appropriate datums for their host body.
    Blocks silent reprojection of extraterrestrial bodies into terrestrial coordinate systems.
    """

    EARTH_VALID_PREFIXES = ("EPSG:4326", "EPSG:3857", "EPSG:326", "EPSG:327", "WGS84", "WGS 84")
    MOON_VALID_PREFIXES = ("IAU_2015:30100", "IAU2015:30100", "LUNA", "MOON", "IAU:30100", "GCS_MOON_2000")
    MARS_VALID_PREFIXES = ("IAU_2015:49900", "IAU2015:49900", "MARS", "IAU:49900", "GCS_MARS_2000")

    @classmethod
    def validate_body_crs(cls, body: str, crs_string: str) -> bool:
        """
        Ensures that a CRS string matches the expected planetary body.
        Raises ValueError if a dangerous cross-body assignment is detected.
        """
        body_upper = body.upper()
        crs_upper = crs_string.upper()

        if body_upper == "EARTH":
            for bad in ("MOON", "MARS", "LUNA", "30100", "49900"):
                if bad in crs_upper:
                    raise ValueError(f"Geodetic Contamination: Terrestrial site assigned extraterrestrial CRS '{crs_string}'.")
            return True

        elif body_upper == "MOON":
            for bad in ("EPSG:4326", "EPSG:3857", "WGS84", "MARS", "49900"):
                if bad in crs_upper:
                    raise ValueError(f"Planetary Guard Violation: Lunar raster assigned invalid or terrestrial CRS '{crs_string}'. Must use IAU Lunar system (e.g. IAU_2015:30100).")
            return True

        elif body_upper == "MARS":
            for bad in ("EPSG:4326", "EPSG:3857", "WGS84", "MOON", "LUNA", "30100"):
                if bad in crs_upper:
                    raise ValueError(f"Planetary Guard Violation: Martian raster assigned invalid or terrestrial CRS '{crs_string}'. Must use IAU Mars system (e.g. IAU_2015:49900).")
            return True

        raise ValueError(f"Unknown planetary body '{body}'. Supported: Earth, Moon, Mars.")

    @classmethod
    def prevent_cross_body_overlay(cls, body_a: str, body_b: str) -> None:
        """
        Enforces that pixel-by-pixel map overlay cannot occur between distinct planetary bodies.
        Comparison must occur strictly in normalized feature space, never by direct raster superposition.
        """
        if body_a.lower() != body_b.lower():
            raise TypeError(
                f"Cross-Body Spatial Overlay Rejected: Cannot spatially overlay {body_a} and {body_b}. "
                "Bodies possess distinct physical radii, gravitational datums, and non-overlapping coordinate spaces. "
                "Use feature vector comparison in AnalogScorer instead."
            )

    @classmethod
    def get_body_equatorial_circumference_m(cls, body: str) -> float:
        import math
        if body.lower() == "moon":
            return 2.0 * math.pi * MOON_RADIUS_M
        elif body.lower() == "mars":
            return 2.0 * math.pi * MARS_SEMI_MAJOR_M
        elif body.lower() == "earth":
            return 2.0 * math.pi * EARTH_WGS84_A_M
        raise ValueError(f"Unknown body: {body}")


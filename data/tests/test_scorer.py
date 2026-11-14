"""
Tests for AnalogScorer and MissionProfile evaluation.
Verifies missing essential features trigger insufficient_evidence and scoring is deterministic.
"""

import pytest
from modules.science.schemas import AnalogSite
from modules.science.features.catalog import ANALOG_CATALOG
from modules.science.score import AnalogScorer, DEFAULT_MISSION_PROFILES


def test_missing_essential_feature_triggers_insufficient_evidence():
    """
    Benchmark 5: Scorer with missing essential feature must return score=None
    and issue an insufficient_evidence warning.
    """
    scorer = AnalogScorer()

    # Create incomplete site with missing 'cave_accessibility_evidence' (which is required)
    incomplete_site = AnalogSite(
        id="TEST_INCOMPLETE_SITE",
        name="Test Incomplete Volcanic Site",
        earth_geojson={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
        earth_crs="EPSG:4326",
        local_utm_epsg="EPSG:32631",
        feature_values={
            "volcanic_context": 1.0,
            "cave_accessibility_evidence": None,  # MISSING ESSENTIAL FEATURE
            "slope_mean_deg": 6.5,
            "roughness_tri_m": 2.2
        },
        sources=["TEST_SOURCE"],
        status="candidate"
    )

    assessment = scorer.evaluate_site(incomplete_site, "LUNAR_VOLCANIC_CAVITY_V1")

    assert assessment.score is None
    assert any("insufficient_evidence" in w for w in assessment.warnings)
    assert assessment.completeness < 1.0


def test_scorer_reproducibility():
    """
    Benchmark 7: Repeated evaluations of the same site must produce identical scores and contributions.
    """
    scorer = AnalogScorer()
    site = ANALOG_CATALOG["ES_LANZAROTE_CORONA"]

    run1 = scorer.evaluate_site(site, "LUNAR_VOLCANIC_CAVITY_V1")
    run2 = scorer.evaluate_site(site, "LUNAR_VOLCANIC_CAVITY_V1")

    assert run1.score is not None
    assert run1.score == run2.score
    assert run1.completeness == run2.completeness
    assert run1.confidence == run2.confidence
    assert run1.feature_scores == run2.feature_scores
    assert run1.feature_contributions == run2.feature_contributions


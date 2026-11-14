"""
Tests for scientific validation, control discrimination, and sensitivity analysis.
Ensures positive controls rank highest, negative controls are penalized, and provenance is complete.
"""

import pytest
from modules.science.validation import (
    run_benchmark_evaluation,
    run_weight_sensitivity_analysis,
    format_validation_markdown_table,
)
from modules.science.features.catalog import ANALOG_CATALOG


def test_positive_vs_negative_control_discrimination():
    """
    Benchmark 8: Positive controls (Lanzarote, Lava Beds) must substantially outscore
    the negative control (Yungay Atacama).
    """
    assessments = run_benchmark_evaluation("LUNAR_VOLCANIC_CAVITY_V1")

    scores_by_id = {a.site_id: a.score for a in assessments}

    lanzarote_score = scores_by_id.get("ES_LANZAROTE_CORONA")
    lava_beds_score = scores_by_id.get("US_LAVA_BEDS_VALENTINE")
    atacama_score = scores_by_id.get("CL_ATACAMA_YUNGAY")

    assert lanzarote_score is not None
    assert lava_beds_score is not None
    assert atacama_score is not None

    # Positive controls should score high (> 0.80)
    assert lanzarote_score > 0.85
    assert lava_beds_score > 0.80

    # Negative control lacks volcanic context and cave evidence, score must be low (< 0.25)
    assert atacama_score < 0.25

    # Positive controls must decisively outrank negative control
    assert lanzarote_score > atacama_score * 3.0


def test_weight_sensitivity_stability():
    """
    Verifies that +/-25% perturbation of weights preserves positive vs negative ranking order.
    """
    res = run_weight_sensitivity_analysis("LUNAR_VOLCANIC_CAVITY_V1", perturbation_pct=0.25)
    assert res["ranking_order_stable"] is True

    trajectories = res["site_trajectories"]
    lanzarote = trajectories["ES_LANZAROTE_CORONA"]
    atacama = trajectories["CL_ATACAMA_YUNGAY"]

    # In all weight schemes, positive control remains far superior to negative control
    assert lanzarote["score_baseline"] > atacama["score_baseline"]
    assert lanzarote["score_cave_heavy"] > atacama["score_cave_heavy"]
    assert lanzarote["score_topo_heavy"] > atacama["score_topo_heavy"]


def test_provenance_manifest_completeness():
    """
    Benchmark 9: Every candidate site in the catalog must cite at least one verified
    geological source and carry a defined validation status.
    """
    for site_id, site in ANALOG_CATALOG.items():
        assert len(site.sources) > 0, f"Site {site_id} lacks source provenance attribution."
        assert site.status in ("positive_control", "negative_control", "candidate", "novel_candidate")
        assert site.local_utm_epsg.startswith("EPSG:")
        assert site.earth_geojson["type"] in ("Polygon", "MultiPolygon")


"""
TERRAIN-X Feature Extraction & Normalization
Maps raw physical variables (degrees, meters, ratios) into normalized similarity indices [0, 1].
Pedagogical explanation of every normalization formula is provided in docstrings.
"""

import math
from typing import Any, Dict, Optional


def normalize_categorical_match(actual: Optional[float], expected: float = 1.0) -> float:
    """
    Computes categorical similarity [0, 1].
    If actual is None or not provided, returns 0.0.
    """
    if actual is None:
        return 0.0
    return max(0.0, min(1.0, 1.0 - abs(actual - expected)))


def normalize_continuous_target(
    actual: Optional[float],
    target: float,
    tolerance: float
) -> float:
    """
    Computes continuous similarity [0, 1] using a Gaussian bell-curve penalty:
      similarity = exp( -0.5 * ((actual - target) / tolerance)^2 )

    Why Gaussian?
    - If actual == target, similarity = 1.0 (perfect match).
    - As actual deviates, similarity smoothly decays towards 0.0 without discontinuous steps.
    - If actual is None, returns 0.0 (unmeasured).
    """
    if actual is None or tolerance <= 0:
        return 0.0
    diff = actual - target
    return float(math.exp(-0.5 * (diff / tolerance) ** 2))


def extract_site_features_similarity(
    site_features: Dict[str, Optional[float]],
    target_specs: Dict[str, Dict[str, float]]
) -> Dict[str, float]:
    """
    Transforms raw site feature values into per-feature similarity scores [0, 1].

    Parameters:
    - site_features: Dict mapping feature_id -> actual value (e.g. {'slope_mean_deg': 6.8})
    - target_specs: Dict mapping feature_id -> {'target': float, 'tolerance': float, 'type': 'continuous'|'categorical'}
    """
    similarity_scores: Dict[str, float] = {}

    for feat_id, spec in target_specs.items():
        actual_val = site_features.get(feat_id)
        if actual_val is None:
            continue

        feat_type = spec.get("type", "continuous")
        if feat_type == "categorical":
            sim = normalize_categorical_match(actual_val, spec.get("target", 1.0))
        else:
            sim = normalize_continuous_target(
                actual_val,
                target=spec["target"],
                tolerance=spec.get("tolerance", 1.0)
            )
        similarity_scores[feat_id] = round(sim, 4)

    return similarity_scores


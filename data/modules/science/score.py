"""
TERRAIN-X AnalogScorer & Mission Profiles
Calculates reproducible, explainable mission suitability scores.
Strictly separates:
- score: weighted similarity in [0, 1] (or None if insufficient evidence)
- completeness: fraction of profile features available in [0, 1]
- confidence: heuristic based on ground-truth provenance and data fidelity
- warnings: explicit caveats (missing features, datum differences, resolution limits)
"""

import uuid
from typing import Dict, List, Optional
from modules.science.schemas import AnalogSite, Assessment, MissionProfile
from modules.science.features.extractors import extract_site_features_similarity

DEFAULT_MISSION_PROFILES: Dict[str, MissionProfile] = {
    "LUNAR_VOLCANIC_CAVITY_V1": MissionProfile(
        id="LUNAR_VOLCANIC_CAVITY_V1",
        label="Lunar Mare Basalt Lava Tube & Skylight Access Test Profile",
        target_body="Moon",
        target_region="Marius Hills Pit / Oceanus Procellarum",
        features=[
            "volcanic_context",
            "cave_accessibility_evidence",
            "slope_mean_deg",
            "roughness_tri_m",
            "surface_aridity_proxy",
            "subsurface_thermal_stability"
        ],
        weights={
            "volcanic_context": 0.25,
            "cave_accessibility_evidence": 0.30,
            "slope_mean_deg": 0.15,
            "roughness_tri_m": 0.15,
            "surface_aridity_proxy": 0.05,
            "subsurface_thermal_stability": 0.10
        },
        required_features=["volcanic_context", "cave_accessibility_evidence"],
        version="1.0.0"
    ),

    "MARS_LAVA_TUBE_COLLAPSE_V1": MissionProfile(
        id="MARS_LAVA_TUBE_COLLAPSE_V1",
        label="Martian Shield Volcanic Cavity & Skylight Descent Test Profile",
        target_body="Mars",
        target_region="Arsia Mons Volcanic Pits / Tharsis Montes",
        features=[
            "volcanic_context",
            "cave_accessibility_evidence",
            "slope_mean_deg",
            "roughness_tri_m",
            "surface_aridity_proxy",
            "subsurface_thermal_stability"
        ],
        weights={
            "volcanic_context": 0.25,
            "cave_accessibility_evidence": 0.30,
            "slope_mean_deg": 0.15,
            "roughness_tri_m": 0.15,
            "surface_aridity_proxy": 0.10,
            "subsurface_thermal_stability": 0.05
        },
        required_features=["volcanic_context", "cave_accessibility_evidence"],
        version="1.0.0"
    )
}

# Profile-specific physical target specs (target values, tolerance)
FEATURE_SPECIFICATIONS: Dict[str, Dict[str, Dict[str, float]]] = {
    "LUNAR_VOLCANIC_CAVITY_V1": {
        "volcanic_context": {"target": 1.0, "type": "categorical"},
        "cave_accessibility_evidence": {"target": 1.0, "type": "categorical"},
        "slope_mean_deg": {"target": 7.0, "tolerance": 3.5, "type": "continuous"},   # Lunar mare slope ~5-8 deg
        "roughness_tri_m": {"target": 2.5, "tolerance": 1.5, "type": "continuous"},  # Basaltic blocky regolith
        "surface_aridity_proxy": {"target": 1.0, "tolerance": 0.3, "type": "continuous"},
        "subsurface_thermal_stability": {"target": 1.0, "tolerance": 0.2, "type": "continuous"}
    },
    "MARS_LAVA_TUBE_COLLAPSE_V1": {
        "volcanic_context": {"target": 1.0, "type": "categorical"},
        "cave_accessibility_evidence": {"target": 1.0, "type": "categorical"},
        "slope_mean_deg": {"target": 8.5, "tolerance": 4.0, "type": "continuous"},   # Flank of shield volcano
        "roughness_tri_m": {"target": 3.0, "tolerance": 1.8, "type": "continuous"},
        "surface_aridity_proxy": {"target": 1.0, "tolerance": 0.25, "type": "continuous"},
        "subsurface_thermal_stability": {"target": 1.0, "tolerance": 0.25, "type": "continuous"}
    }
}


class AnalogScorer:
    """
    Evaluates analog sites against target mission profiles with full mathematical reproducibility.
    """

    def __init__(self, profiles: Optional[Dict[str, MissionProfile]] = None):
        self.profiles = profiles or DEFAULT_MISSION_PROFILES

    def evaluate_site(self, site: AnalogSite, mission_id: str) -> Assessment:
        """
        Calculates similarity score, completeness, and confidence.
        If any required feature is missing, returns score=None with insufficient_evidence warning.
        """
        if mission_id not in self.profiles:
            raise KeyError(f"Unknown mission profile '{mission_id}'. Available: {list(self.profiles.keys())}")

        profile = self.profiles[mission_id]
        specs = FEATURE_SPECIFICATIONS.get(mission_id, {})
        warnings: List[str] = []

        # 1. Check required features
        missing_required = []
        for req in profile.required_features:
            val = site.feature_values.get(req)
            if val is None:
                missing_required.append(req)

        # 2. Extract per-feature similarities
        similarities = extract_site_features_similarity(site.feature_values, specs)

        # 3. Compute available weights and completeness
        total_profile_weight = sum(profile.weights.values())
        available_weight = 0.0
        weighted_similarity_sum = 0.0
        feature_contributions: Dict[str, float] = {}

        for feat, weight in profile.weights.items():
            if site.feature_values.get(feat) is not None:
                available_weight += weight
                sim = similarities.get(feat, 0.0)
                contribution = weight * sim
                weighted_similarity_sum += contribution
                feature_contributions[feat] = round(contribution, 4)

        completeness = round(available_weight / total_profile_weight, 4) if total_profile_weight > 0 else 0.0

        # 4. Handle insufficient evidence
        final_score: Optional[float] = None
        if missing_required:
            warnings.append(
                f"insufficient_evidence: Critical required features missing: {missing_required}. "
                "Overall score withheld to avoid false-positive analog certification."
            )
        elif available_weight > 0:
            # Normalized score over available weights
            raw_score = weighted_similarity_sum / available_weight
            final_score = round(float(raw_score), 4)

        # 5. Compute confidence heuristic
        # Confidence increases with:
        # - Number of verified ground sources (min 1, max 3+)
        # - Speleological survey ground truth
        # - Completeness of feature vector
        source_count_factor = min(1.0, len(site.sources) / 3.0)
        ground_truth_factor = 1.0 if (site.cave_evidence and "speleological_survey" in site.cave_evidence) else 0.6
        confidence = round(0.4 * completeness + 0.3 * source_count_factor + 0.3 * ground_truth_factor, 4)

        # Scientific provenance caveats
        if site.status == "negative_control":
            warnings.append("Evaluated site is a designated NEGATIVE CONTROL. Low suitability is expected and intended.")
        if profile.target_body in ("Moon", "Mars"):
            warnings.append(
                f"Functional Analog Assessment: Assesses mechanical and morphological test suitability for {profile.target_body}. "
                "Does NOT represent physical 1:1 atmospheric, gravity (Moon ~1/6g, Mars ~3/8g), or radiation equivalence."
            )

        return Assessment(
            id=str(uuid.uuid4())[:8],
            mission_id=mission_id,
            site_id=site.id,
            score=final_score,
            completeness=completeness,
            confidence=confidence,
            feature_scores=similarities,
            feature_contributions=feature_contributions,
            warnings=warnings,
            method_version="TERRAIN-X-V1.0.0"
        )


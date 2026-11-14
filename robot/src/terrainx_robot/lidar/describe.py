"""Estadística descriptiva de una nube (comando `inspect`).

Qué hace
    Resume la nube SIN interpretarla: límites, extensión, percentiles de altura,
    distancia horizontal al origen del frame, paso de rejilla observado y el
    nivel Z más poblado (posible suelo, solo como hipótesis). Está pensado para
    la verificación física: comparar estas cifras con medidas de cinta métrica.
Unidades: las de la nube (metros asumidos).
"""

from __future__ import annotations

import numpy as np


def _round(values, ndigits: int = 4):
    return np.round(np.asarray(values, dtype=np.float64), ndigits).tolist()


def observed_grid_step(values: np.ndarray) -> float | None:
    """Menor separación positiva entre coordenadas distintas de un eje."""
    unique = np.unique(np.round(values, 6))
    if unique.size < 2:
        return None
    diffs = np.diff(unique)
    diffs = diffs[diffs > 1e-6]
    return float(np.round(diffs.min(), 6)) if diffs.size else None


def describe_points(points: np.ndarray, declared_resolution: float | None = None) -> dict:
    pts = np.asarray(points, dtype=np.float64)
    n = int(pts.shape[0])
    if n == 0:
        return {"point_count": 0}
    mins, maxs = pts.min(axis=0), pts.max(axis=0)
    z = pts[:, 2]
    r = np.hypot(pts[:, 0], pts[:, 1])
    steps = {axis: observed_grid_step(pts[:, i]) for i, axis in enumerate("xyz")}
    bin_size = declared_resolution or 0.05
    levels, counts = np.unique(np.round(z / bin_size).astype(np.int64), return_counts=True)
    top = int(np.argmax(counts))
    out = {
        "point_count": n,
        "bounds_min": _round(mins),
        "bounds_max": _round(maxs),
        "extent": _round(maxs - mins),
        "centroid": _round(pts.mean(axis=0)),
        "z_percentiles": dict(zip(["p1", "p5", "p50", "p95", "p99"], _round(np.percentile(z, [1, 5, 50, 95, 99])))),
        "horizontal_distance_from_frame_origin": {
            "min": round(float(r.min()), 4),
            "p50": round(float(np.median(r)), 4),
            "max": round(float(r.max()), 4),
            "note": "distancia al origen (0,0) del frame, que no es necesariamente la posición del robot",
        },
        "observed_grid_step": steps,
        "most_populated_z_level": {
            "z": round(float(levels[top] * bin_size), 4),
            "points": int(counts[top]),
            "fraction": round(float(counts[top] / n), 4),
            "note": "hipótesis de suelo u otra superficie horizontal dominante; no verificada",
        },
    }
    if declared_resolution:
        consistent = all(s is None or abs(s - declared_resolution) < 1e-6 for s in steps.values())
        out["grid_step_consistent_with_declared_resolution"] = consistent
        out["declared_resolution"] = declared_resolution
    return out

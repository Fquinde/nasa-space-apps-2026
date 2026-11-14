"""Validación de nubes de puntos.

Qué hace
    Comprueba forma y tipo, elimina puntos NaN/infinitos y puntos con
    coordenadas absurdas, y limita el tamaño máximo. Devuelve la nube limpia y
    un informe con lo eliminado (nada se descarta en silencio).
Entradas
    points: array (N,3); límites configurables.
Salidas
    (ndarray (M,3) float64, ValidationReport)
Unidades
    metros (las de la nube de entrada).
Errores
    PointCloudError si la forma es incorrecta; PointCloudTooLarge si N supera
    el máximo (evita bloqueos con datos malformados).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

DEFAULT_MAX_POINTS = 5_000_000
# Comprobación de cordura: ninguna coordenada del Go2 debería superar 1 km
# respecto al origen de su frame en una prueba terrestre. No es un filtro de rango
# del sensor (el rango real no está verificado), solo detecta datos corruptos.
DEFAULT_MAX_ABS_COORD_M = 1000.0


class PointCloudError(ValueError):
    pass


class PointCloudTooLarge(PointCloudError):
    pass


@dataclass
class ValidationReport:
    input_count: int = 0
    non_finite_removed: int = 0
    out_of_bounds_removed: int = 0
    output_count: int = 0
    max_abs_coord_m: float = DEFAULT_MAX_ABS_COORD_M
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def validate_points(
    points: np.ndarray,
    *,
    max_points: int = DEFAULT_MAX_POINTS,
    max_abs_coord_m: float = DEFAULT_MAX_ABS_COORD_M,
) -> tuple[np.ndarray, ValidationReport]:
    try:
        arr = np.asarray(points, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise PointCloudError(f"la nube no es numérica: {exc}") from exc
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise PointCloudError(f"se esperaba forma (N,3) y llegó {arr.shape}")
    report = ValidationReport(input_count=int(arr.shape[0]), max_abs_coord_m=max_abs_coord_m)
    if arr.shape[0] > max_points:
        raise PointCloudTooLarge(f"{arr.shape[0]} puntos superan el máximo de {max_points}")
    if arr.shape[0] == 0:
        report.warnings.append("nube vacía")
        return arr.reshape(0, 3), report

    finite = np.all(np.isfinite(arr), axis=1)
    report.non_finite_removed = int((~finite).sum())
    arr = arr[finite]
    in_bounds = np.all(np.abs(arr) <= max_abs_coord_m, axis=1)
    report.out_of_bounds_removed = int((~in_bounds).sum())
    arr = arr[in_bounds]
    report.output_count = int(arr.shape[0])
    if report.non_finite_removed:
        report.warnings.append(f"{report.non_finite_removed} puntos NaN/inf eliminados")
    if report.out_of_bounds_removed:
        report.warnings.append(
            f"{report.out_of_bounds_removed} puntos con |coord| > {max_abs_coord_m} m eliminados"
        )
    return arr, report

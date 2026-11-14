"""Construcción de LidarFrame a partir de un mensaje del robot (vivo o grabado).

Qué hace
    Un único camino de código para el modo en vivo y el modo replay: recibe los
    metadatos tal como llegaron en ``message["data"]`` y el payload comprimido,
    decodifica con voxel_codec y devuelve un LidarFrame. Si la decodificación
    falla, el frame se conserva con ``decode_error`` y 0 puntos (no se inventa nada).

Campos de metadatos conocidos (los que leen los ejemplos oficiales de la
librería: stamp, frame_id, resolution, src_size, origin, width). Cualquier
otro campo se guarda en ``extra_fields`` para poder descubrirlo con el robot real.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from ..models import LidarFrameInfo, PointType
from ..util import json_safe
from .voxel_codec import VoxelDecodeError, decode_voxel_map

DECODER_NAME = "terrainx.voxel_codec (réplica de unitree_webrtc_connect native 2.2.0)"
KNOWN_META_KEYS = ("stamp", "frame_id", "resolution", "src_size", "origin", "width")


@dataclass
class LidarFrame:
    info: LidarFrameInfo
    points: np.ndarray  # (N,3) float64
    raw_compressed: bytes | None = None
    raw_meta: dict[str, Any] = field(default_factory=dict)


def _as_float_list(value: Any, length: int) -> list[float] | None:
    try:
        arr = np.asarray(value, dtype=np.float64).reshape(length)
    except (TypeError, ValueError):
        return None
    return arr.tolist()


def _as_int_list(value: Any) -> list[int] | None:
    try:
        return [int(v) for v in value]
    except (TypeError, ValueError):
        return None


def _as_number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def frame_from_message(
    *,
    seq: int,
    topic: str,
    meta: dict[str, Any],
    compressed: bytes | None,
    host_received_utc: datetime,
) -> LidarFrame:
    """Decodifica un mensaje de mapa de vóxeles y devuelve un LidarFrame."""
    meta = dict(meta or {})
    meta.pop("data", None)  # el payload nunca forma parte de los metadatos
    safe_meta = json_safe(meta)

    origin = _as_float_list(meta.get("origin"), 3)
    resolution = _as_number(meta.get("resolution"))
    src_size_raw = meta.get("src_size")
    src_size = int(src_size_raw) if isinstance(src_size_raw, (int, float)) else None
    width = _as_int_list(meta.get("width")) if meta.get("width") is not None else None
    stamp = meta.get("stamp")
    if not isinstance(stamp, (int, float, str)) and stamp is not None:
        stamp = str(stamp)

    points = np.empty((0, 3), dtype=np.float64)
    error: str | None = None
    if compressed is None:
        error = "mensaje sin payload binario"
    elif origin is None or resolution is None or src_size is None:
        error = "faltan origin/resolution/src_size en los metadatos"
    else:
        try:
            decoded = decode_voxel_map(compressed, src_size, origin, resolution)
            points = decoded.points
            if width is not None and len(width) == 3 and list(decoded.grid_shape) != width:
                # No es un error de decodificación, pero sí una incoherencia a registrar.
                safe_meta["_terrainx_width_mismatch"] = {
                    "declared_width": width,
                    "decoded_grid_shape": list(decoded.grid_shape),
                }
        except VoxelDecodeError as exc:
            error = str(exc)

    info = LidarFrameInfo(
        seq=seq,
        topic=topic,
        host_received_utc=host_received_utc,
        robot_stamp_raw=stamp,
        frame_id=str(meta["frame_id"]) if meta.get("frame_id") is not None else None,
        origin=origin,
        resolution=resolution,
        width=width,
        src_size=src_size,
        point_count=int(points.shape[0]),
        point_type=PointType.VOXEL_OCCUPANCY,
        decoder=DECODER_NAME,
        decode_error=error,
        extra_fields={k: v for k, v in safe_meta.items() if k not in KNOWN_META_KEYS},
    )
    return LidarFrame(info=info, points=points, raw_compressed=compressed, raw_meta=safe_meta)

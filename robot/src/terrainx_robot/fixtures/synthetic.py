"""Generador de sesiones SINTÉTICAS con el formato de mensaje del Go2.

Qué hace
    Construye una escena geométrica conocida, la convierte en mapas de vóxeles
    con el MISMO formato binario que publica el robot (voxel_codec.encode) y la
    graba como sesión replay. Sirve para probar todo el pipeline sin robot.
    La sesión queda marcada evidence_class=synthetic_test y demo=true; cada
    mensaje de telemetría lleva además "_synthetic": true.

Escena (coordenadas en metros, frame "synthetic_frame", resolución 0.05 m)
    - suelo plano en z = 0.00 en toda la rejilla (6.4 m x 6.4 m)
    - caja de 0.50 m x 0.50 m x 0.50 m de alto, centrada en (1.25, 0.00)
      (cara superior en z = 0.50 m): obstáculo de altura conocida para Fase 2
    - pared vertical en x = 2.80 m, de y = -2.0 a 2.0 m y hasta z = 1.20 m
    Cada frame "ve" un subconjunto aleatorio (semilla fija) de la escena, para
    probar la acumulación.

Nota: width = [128, 128, 38] se toma del valor por defecto del ejemplo oficial
plot_lidar_stream.py; no está verificado que el robot use ese valor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import numpy as np

from ..adapters.go2_topics import LIDAR_VOXEL_COMPRESSED, LOW_STATE
from ..lidar.voxel_codec import encode_voxel_map
from ..models import DeliveryMode, EvidenceClass, RobotDescriptor, ScanContext, SessionInfo
from ..storage.session_log import SessionRecorder
from ..util import new_id, software_versions, utc_now

RESOLUTION = 0.05
ORIGIN = (-3.2, -3.2, -0.6)
Z_SLICES = 38
FRAME_ID = "synthetic_frame"
FLOOR_Z_M = 0.0
BOX_TOP_Z_M = 0.5


def _k(value_m: float, axis: int) -> int:
    return int(round((value_m - ORIGIN[axis]) / RESOLUTION))


def scene_indices() -> np.ndarray:
    """Índices (N,3) únicos de la escena completa."""
    cells: set[tuple[int, int, int]] = set()
    kz_floor = _k(FLOOR_Z_M, 2)
    for x in range(128):
        for y in range(128):
            cells.add((x, y, kz_floor))
    # Caja: x 1.00..1.50, y -0.25..0.25, z 0.05..0.50 (cara superior + 4 laterales)
    x0, x1 = _k(1.0, 0), _k(1.5, 0)
    y0, y1 = _k(-0.25, 1), _k(0.25, 1)
    z0, z1 = _k(0.05, 2), _k(BOX_TOP_Z_M, 2)
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            cells.add((x, y, z1))
            for z in range(z0, z1 + 1):
                if x in (x0, x1) or y in (y0, y1):
                    cells.add((x, y, z))
    # Pared: x = 2.80, y -2.0..2.0, z 0.05..1.20
    xw = _k(2.8, 0)
    for y in range(_k(-2.0, 1), _k(2.0, 1) + 1):
        for z in range(_k(0.05, 2), _k(1.2, 2) + 1):
            cells.add((xw, y, z))
    return np.array(sorted(cells), dtype=np.int64)


@dataclass
class SyntheticFrame:
    t_rel_s: float
    meta: dict
    payload: bytes
    indices: np.ndarray


def generate_frames(n_frames: int = 8, *, seed: int = 7, visible_fraction: float = 0.85) -> list[SyntheticFrame]:
    if n_frames <= 0:
        raise ValueError("n_frames debe ser > 0")
    scene = scene_indices()
    rng = np.random.default_rng(seed)
    frames = []
    for i in range(n_frames):
        idx = scene[rng.random(len(scene)) < visible_fraction]
        payload, src_size = encode_voxel_map(idx, Z_SLICES)
        t = round(i * 0.1, 3)
        meta = {
            "stamp": t,  # sintético: segundos desde el inicio de la sesión
            "frame_id": FRAME_ID,
            "resolution": RESOLUTION,
            "src_size": src_size,
            "origin": list(ORIGIN),
            "width": [128, 128, Z_SLICES],
        }
        frames.append(SyntheticFrame(t_rel_s=t, meta=meta, payload=payload, indices=idx))
    return frames


def synthetic_lowstate(i: int) -> dict:
    """Mensaje con la ESTRUCTURA de rt/lf/lowstate (campos de los ejemplos oficiales)."""
    return {
        "_synthetic": True,
        "imu_state": {"rpy": [0.0, 0.0, 0.0]},
        "bms_state": {"soc": 90 - i},
        "power_v": 25.0,
    }


def write_synthetic_session(sessions_root: Path, *, n_frames: int = 8, seed: int = 7) -> SessionInfo:
    info = SessionInfo(
        session_id=new_id("session-synthetic"),
        created_utc=utc_now(),
        robot=RobotDescriptor(
            robot_id="synthetic-go2-like",
            platform="synthetic_generator",
            adapter="synthetic_generator",
            delivery_mode=DeliveryMode.REPLAY,
        ),
        evidence_class=EvidenceClass.SYNTHETIC_TEST,
        scan_context=ScanContext.SYNTHETIC,
        demo=True,
        generator="terrainx_robot.fixtures.synthetic",
        software=software_versions(),
        notes=(
            "Escena SINTÉTICA: suelo z=0, caja de 0.50 m, pared en x=2.80 m. "
            f"semilla={seed}, frames={n_frames}. NO es una medición."
        ),
    )
    recorder = SessionRecorder(sessions_root, info)
    t0 = utc_now()
    for i, frame in enumerate(generate_frames(n_frames, seed=seed)):
        recorder.record_lidar_at(
            topic=LIDAR_VOXEL_COMPRESSED,
            host_utc=t0 + timedelta(seconds=frame.t_rel_s),
            meta=frame.meta,
            raw=frame.payload,
            t_rel_s=frame.t_rel_s,
        )
        if i % 2 == 0:
            t = frame.t_rel_s + 0.05
            recorder.record_json(
                topic=LOW_STATE,
                host_utc=t0 + timedelta(seconds=t),
                data=synthetic_lowstate(i),
                t_rel_s=t,
            )
    return recorder.close()

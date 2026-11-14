from datetime import datetime, timezone

import numpy as np
import pytest

from terrainx_robot.fixtures.synthetic import generate_frames
from terrainx_robot.lidar.accumulator import CaptureAccumulator
from terrainx_robot.lidar.frames import frame_from_message
from terrainx_robot.lidar.validation import PointCloudError, PointCloudTooLarge, validate_points
from terrainx_robot.models import PointType

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)


def _frame(sf, seq=1, **meta_overrides):
    meta = {**sf.meta, **meta_overrides}
    return frame_from_message(seq=seq, topic="rt/utlidar/voxel_map_compressed", meta=meta,
                              compressed=sf.payload, host_received_utc=T0)


# ------------------------------------------------------------------ frames
def test_frame_desde_mensaje():
    sf = generate_frames(1, seed=5)[0]
    fr = _frame(sf, extra_key="x")
    assert fr.info.decode_error is None
    assert fr.info.point_count == len(sf.indices) == fr.points.shape[0]
    assert fr.info.point_type is PointType.VOXEL_OCCUPANCY
    assert fr.info.frame_id == "synthetic_frame"
    assert fr.info.extra_fields == {"extra_key": "x"}  # campos desconocidos se conservan
    assert fr.raw_compressed == sf.payload


def test_frame_registra_incoherencia_de_width():
    fr = _frame(generate_frames(1)[0], width=[128, 128, 99])
    assert "_terrainx_width_mismatch" in fr.raw_meta


def test_frame_sin_metadatos_no_inventa_puntos():
    sf = generate_frames(1)[0]
    meta = dict(sf.meta)
    del meta["origin"]
    fr = frame_from_message(seq=1, topic="t", meta=meta, compressed=sf.payload, host_received_utc=T0)
    assert fr.info.decode_error and fr.points.shape == (0, 3)
    fr2 = frame_from_message(seq=2, topic="t", meta=sf.meta, compressed=None, host_received_utc=T0)
    assert fr2.info.decode_error and fr2.info.point_count == 0


# -------------------------------------------------------------- validación
def test_validacion_elimina_nan_inf_y_absurdos():
    pts = np.array([[0, 0, 0], [np.nan, 0, 0], [0, np.inf, 0], [5000, 0, 0], [1, 2, 3]], dtype=float)
    clean, rep = validate_points(pts)
    assert clean.shape == (2, 3)
    assert rep.non_finite_removed == 2 and rep.out_of_bounds_removed == 1
    assert rep.warnings


def test_validacion_forma_incorrecta_y_tamano():
    with pytest.raises(PointCloudError):
        validate_points(np.zeros((4, 2)))
    with pytest.raises(PointCloudError):
        validate_points([["a", "b", "c"]])
    with pytest.raises(PointCloudTooLarge):
        validate_points(np.zeros((11, 3)), max_points=10)
    clean, rep = validate_points(np.zeros((0, 3)))
    assert clean.shape == (0, 3) and "nube vacía" in rep.warnings


# -------------------------------------------------------------- acumulación
def test_acumulacion_sin_duplicados():
    frames = generate_frames(4, seed=9)
    acc = CaptureAccumulator("accumulate")
    for i, sf in enumerate(frames):
        assert acc.add(_frame(sf, seq=i))
    cloud = acc.result()
    union = {tuple(r) for f in frames for r in f.indices.tolist()}
    assert cloud.points.shape[0] == len(union)
    assert cloud.frames_used == 4 and cloud.frames_rejected == 0
    assert cloud.deduplication["removed"] > 0


def test_modo_last_conserva_solo_el_ultimo():
    frames = generate_frames(3, seed=9)
    acc = CaptureAccumulator("last")
    for i, sf in enumerate(frames):
        acc.add(_frame(sf, seq=i))
    assert acc.result().points.shape[0] == len(frames[-1].indices)


def test_rechaza_frames_incoherentes():
    a, b = generate_frames(2, seed=4)
    acc = CaptureAccumulator()
    assert acc.add(_frame(a))
    assert not acc.add(_frame(b, frame_id="otro_frame"))
    assert not acc.add(_frame(b, resolution=0.1))
    bad = _frame(b)
    bad.info.decode_error = "x"
    assert not acc.add(bad)
    cloud = acc.result()
    assert cloud.rejection_reasons == {
        "frame_id_mismatch": 1, "resolution_mismatch": 1, "decode_error": 1,
    }
    assert cloud.frames_used == 1


def test_acumulador_respeta_maximo():
    acc = CaptureAccumulator(max_points=100)
    with pytest.raises(PointCloudTooLarge):
        acc.add(_frame(generate_frames(1)[0]))

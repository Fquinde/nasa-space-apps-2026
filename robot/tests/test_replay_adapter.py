import numpy as np
import pytest

from conftest import run
from terrainx_robot.adapters.base import CaptureError, ConnectionFailed
from terrainx_robot.adapters.replay import ReplayAdapter
from terrainx_robot.fixtures.synthetic import generate_frames
from terrainx_robot.models import (
    CaptureState,
    ConnectionState,
    DeliveryMode,
    EvidenceClass,
    PointType,
)
from terrainx_robot.probe.capability_probe import run_probe
from terrainx_robot.storage.ply import write_ply
from terrainx_robot.storage.session_log import SessionReader


def _capture(adapter, duration=None, **kw):
    async def go():
        await adapter.connect()
        try:
            return await adapter.capture(duration, **kw)
        finally:
            await adapter.disconnect()

    return run(go())


def test_captura_desde_sesion_sintetica(store, synthetic_session):
    adapter = ReplayAdapter(synthetic_session, store)
    meta = _capture(adapter)
    union = {tuple(r) for f in generate_frames(6, seed=11) for r in f.indices.tolist()}
    assert meta.point_count == len(union)
    assert meta.evidence_class is EvidenceClass.SYNTHETIC_TEST
    assert meta.delivery_mode is DeliveryMode.REPLAY and meta.demo is True
    assert meta.robot.adapter == "replay"
    assert meta.geometry.point_type is PointType.VOXEL_OCCUPANCY
    assert meta.capture.session_id == SessionReader(synthetic_session).info.session_id
    # timestamp_utc = hora ORIGINAL de adquisición, no la del replay
    first = next(SessionReader(synthetic_session).records())
    assert meta.timestamp_utc == first["t_host_utc"]
    assert meta.capture.acquisition_first_utc == first["t_host_utc"]
    assert adapter.connection_state is ConnectionState.DISCONNECTED
    assert adapter.capture_state is CaptureState.COMPLETE


def test_ventana_de_duracion_y_modo_last(store, synthetic_session):
    meta = _capture(ReplayAdapter(synthetic_session, store), 0.25)
    assert meta.capture.frames_used == 3  # frames en t = 0.0, 0.1, 0.2
    last = _capture(ReplayAdapter(synthetic_session, store), mode="last")
    assert last.point_count == len(generate_frames(6, seed=11)[-1].indices)


def test_estado_y_errores_de_uso(store, synthetic_session):
    adapter = ReplayAdapter(synthetic_session, store)
    assert adapter.get_status().connection_state is ConnectionState.DISCONNECTED
    with pytest.raises(CaptureError):
        run(adapter.start_capture())  # sin conectar

    async def go():
        await adapter.connect()
        assert adapter.get_status().connection_state is ConnectionState.READY_READONLY
        with pytest.raises(CaptureError):
            await adapter.stop_capture()  # sin captura en curso
        await adapter.start_capture()
        with pytest.raises(CaptureError):
            await adapter.start_capture()  # doble captura
        await adapter.abort_capture()
        await adapter.disconnect()

    run(go())


def test_sondeo_en_replay(store, synthetic_session):
    report = run(run_probe(ReplayAdapter(synthetic_session, store), window_s=None))
    caps = {c.name: c for c in report.capabilities}
    assert report.overall_status == "ok"
    assert caps["lidar_point_data"].status.value == "available"
    assert caps["lidar_point_data"].details["resolution"] == 0.05
    assert caps["battery_soc"].status.value == "available"
    assert caps["motion_control"].status.value == "disabled_by_policy"
    assert caps["robot_pose_topic"].status.value == "unavailable"
    assert any("SINTÉTICA" in c for c in report.caveats)
    assert any("REPLAY" in c for c in report.caveats)


def test_regrabar_conserva_la_evidencia(store, synthetic_session):
    meta = _capture(ReplayAdapter(synthetic_session, store), record_session=True)
    new = SessionReader(store.data_dir / "sessions" / meta.capture.session_id)
    assert new.info.evidence_class is EvidenceClass.SYNTHETIC_TEST and new.info.demo
    assert new.verify() and new.info.lidar_records == 6


def test_sesion_alterada_no_se_reproduce(store, synthetic_session):
    path = synthetic_session / "messages.jsonl"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    adapter = ReplayAdapter(synthetic_session, store)
    with pytest.raises(ConnectionFailed) as exc:
        run(adapter.connect())
    assert exc.value.code == "session_integrity"
    assert adapter.connection_state is ConnectionState.FAILED


def test_ply_con_metadatos_hereda_la_procedencia(store, synthetic_session):
    original = _capture(ReplayAdapter(synthetic_session, store))
    ply = store.scans_dir / original.id / original.files["ply"].path
    again = _capture(ReplayAdapter(ply, store))
    assert again.evidence_class is EvidenceClass.SYNTHETIC_TEST
    assert again.point_count == original.point_count
    assert again.frame_id == original.frame_id
    assert again.provenance["replay_source"]["source_scan_id"] == original.id
    np.testing.assert_allclose(
        np.sort(store.load_points(again.id), axis=0), np.sort(store.load_points(original.id), axis=0), atol=1e-6
    )


def test_ply_sin_metadatos_exige_evidencia_declarada(store, tmp_path):
    ply = tmp_path / "ajeno.ply"
    write_ply(ply, np.array([[0, 0, 0], [1, 1, 1.0]]))
    with pytest.raises(ValueError):
        ReplayAdapter(ply, store)
    meta = _capture(ReplayAdapter(ply, store, evidence_class=EvidenceClass.ROBOT_MEASURED))
    assert meta.evidence_class is EvidenceClass.ROBOT_MEASURED and meta.demo is False
    assert meta.geometry.point_type is PointType.UNKNOWN
    assert any("DECLARADA por el operador" in c for c in meta.caveats)


def test_fuente_inexistente(store, tmp_path):
    with pytest.raises(ConnectionFailed):
        ReplayAdapter(tmp_path / "nada.txt", store)

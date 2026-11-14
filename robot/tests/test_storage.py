import json
from datetime import datetime, timezone

import numpy as np
import pytest
from pydantic import ValidationError

from terrainx_robot.fixtures.synthetic import generate_frames
from terrainx_robot.lidar.accumulator import CaptureAccumulator
from terrainx_robot.lidar.frames import frame_from_message
from terrainx_robot.models import (
    Body,
    DeliveryMode,
    EvidenceClass,
    RobotDescriptor,
    ScanContext,
    ScanMetadata,
    SessionInfo,
)
from terrainx_robot.storage.ply import read_ply
from terrainx_robot.storage.scan_store import ScanStoreError
from terrainx_robot.storage.session_log import SessionError, SessionReader, SessionRecorder
from terrainx_robot.util import sha256_file

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
ROBOT = RobotDescriptor(robot_id="test", adapter="test", delivery_mode=DeliveryMode.REPLAY)


def _cloud(n_frames=3):
    acc = CaptureAccumulator()
    for i, sf in enumerate(generate_frames(n_frames, seed=2)):
        acc.add(frame_from_message(seq=i, topic="rt/utlidar/voxel_map_compressed", meta=sf.meta,
                                   compressed=sf.payload, host_received_utc=T0))
    return acc.result()


def _save(store, evidence=EvidenceClass.SYNTHETIC_TEST, context=ScanContext.SYNTHETIC):
    return store.save(_cloud(), robot=ROBOT, evidence_class=evidence, delivery_mode=DeliveryMode.REPLAY,
                      scan_context=context, capture_start=T0, capture_end=T0)


# ----------------------------------------------------------------- escaneos
def test_guardar_escaneo_completo(store):
    cloud = _cloud()
    meta = store.save(cloud, robot=ROBOT, evidence_class=EvidenceClass.SYNTHETIC_TEST,
                      delivery_mode=DeliveryMode.REPLAY, scan_context=ScanContext.SYNTHETIC,
                      capture_start=T0, capture_end=T0)
    folder = store.scans_dir / meta.id
    ply = folder / meta.files["ply"].path
    assert ply.is_file() and (folder / f"{meta.id}.metadata.json").is_file()
    assert sha256_file(ply) == meta.files["ply"].sha256
    assert meta.point_count == cloud.points.shape[0] == read_ply(ply).points.shape[0]
    assert meta.demo is True and meta.quality_flag == "synthetic_test_data"
    assert meta.unit == "m" and meta.registration.status == "local_only"
    assert meta.file_url == f"scans/{meta.id}/{meta.id}.ply"
    assert any("SINTÉTICOS" in c for c in meta.caveats)
    assert any("ASUMIDA" in c for c in meta.caveats)
    sums = (folder / "SHA256SUMS").read_text().splitlines()
    assert len(sums) == 2 and sums[0].startswith(meta.files["ply"].sha256)
    # El JSON es válido frente al modelo (contrato)
    ScanMetadata.model_validate_json((folder / f"{meta.id}.metadata.json").read_text(encoding="utf-8"))


def test_verificar_detecta_alteraciones(store):
    meta = _save(store)
    assert store.verify(meta.id)["ok"]
    ply = store.scans_dir / meta.id / meta.files["ply"].path
    data = bytearray(ply.read_bytes())
    data[-1] ^= 0xFF
    ply.write_bytes(bytes(data))
    assert not store.verify(meta.id)["ok"]
    with pytest.raises(ScanStoreError):
        store.export(meta.id, store.data_dir / "export")


def test_exportar_listar_y_cargar(store, tmp_path):
    meta = _save(store)
    target = store.export(meta.id, tmp_path / "out")
    assert (target / f"{meta.id}.ply").is_file()
    assert [m.id for m in store.list()] == [meta.id]
    assert store.load_points(meta.id).shape == (meta.point_count, 3)


def test_ids_maliciosos_y_nube_vacia(store):
    with pytest.raises(ScanStoreError):
        store.load_metadata("../../etc")
    with pytest.raises(ScanStoreError):
        store.load_metadata("no-existe")
    empty = _cloud()
    empty.points = np.empty((0, 3))
    with pytest.raises(ScanStoreError):
        store.save(empty, robot=ROBOT, evidence_class=EvidenceClass.SYNTHETIC_TEST,
                   delivery_mode=DeliveryMode.REPLAY, scan_context=ScanContext.SYNTHETIC,
                   capture_start=T0, capture_end=T0)


def test_fallo_al_guardar_no_deja_restos(store):
    # robot_measured en la Luna viola el contrato: no debe quedar carpeta a medias
    moon_robot = ROBOT.model_copy(update={"body": Body.MOON})
    with pytest.raises(ValidationError):
        store.save(_cloud(), robot=moon_robot, evidence_class=EvidenceClass.ROBOT_MEASURED,
                   delivery_mode=DeliveryMode.LIVE, scan_context=ScanContext.CONTROLLED_TEST,
                   capture_start=T0, capture_end=T0)
    assert not store.scans_dir.exists() or not any(store.scans_dir.iterdir())


def test_reglas_de_procedencia_en_el_modelo(store):
    meta = _save(store)
    data = meta.model_dump(mode="json")
    data["demo"] = False  # sintético sin demo=true
    with pytest.raises(ValidationError):
        ScanMetadata.model_validate(data)
    data.update(demo=True, evidence_class="robot_measured")  # real marcado como demo
    with pytest.raises(ValidationError):
        ScanMetadata.model_validate(data)


# ----------------------------------------------------------------- sesiones
def _session_info(evidence=EvidenceClass.SYNTHETIC_TEST):
    return SessionInfo(session_id="s1", created_utc=T0, robot=ROBOT, evidence_class=evidence,
                       scan_context=ScanContext.SYNTHETIC, demo=evidence is EvidenceClass.SYNTHETIC_TEST,
                       generator="test", software={})


def test_sesion_ida_y_vuelta(tmp_path):
    rec = SessionRecorder(tmp_path, _session_info())
    rec.record_lidar(topic="lidar", host_utc=T0, meta={"origin": [0, 0, 0], "data": "ignorado"}, raw=b"\x00\x01\xff")
    rec.record_json(topic="rt/lf/lowstate", host_utc=T0, data={"bms_state": {"soc": 50}, "blob": b"\x10"})
    info = rec.close()
    assert info.record_count == 2 and info.messages_sha256
    reader = SessionReader(tmp_path / "s1")
    assert reader.verify()
    recs = list(reader.records())
    assert recs[0]["raw"] == b"\x00\x01\xff" and "data" not in recs[0]["meta"]
    assert recs[1]["data"] == {"bms_state": {"soc": 50}, "blob": b"\x10"}


def test_sesion_alterada_o_corrupta(tmp_path):
    rec = SessionRecorder(tmp_path, _session_info())
    rec.record_json(topic="t", host_utc=T0, data={"a": 1})
    rec.close()
    reader = SessionReader(tmp_path / "s1")
    with open(reader.messages_path, "a", encoding="utf-8") as fh:
        fh.write("{esto no es json\n")
    assert not reader.verify()
    with pytest.raises(SessionError):
        list(reader.records())
    with pytest.raises(SessionError):
        SessionReader(tmp_path / "no-existe")


def test_sesion_real_no_puede_ser_demo():
    with pytest.raises(ValidationError):
        SessionInfo(session_id="x", created_utc=T0, robot=ROBOT, evidence_class=EvidenceClass.ROBOT_MEASURED,
                    scan_context=ScanContext.CONTROLLED_TEST, demo=True, generator="t", software={})


def test_metadatos_json_sin_bytes_crudos(store):
    meta = _save(store)
    text = (store.scans_dir / meta.id / f"{meta.id}.metadata.json").read_text(encoding="utf-8")
    assert "__bytes_b64__" not in text
    assert json.loads(text)["schema_version"].startswith("terrainx.robot.scan/")

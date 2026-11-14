"""CLI de extremo a extremo (offline), datos sintéticos, inspect y librería instalada."""

import json

import numpy as np
import pytest

from terrainx_robot.cli import main
from terrainx_robot.fixtures.synthetic import BOX_TOP_Z_M, FLOOR_Z_M, generate_frames, scene_indices
from terrainx_robot.lidar.describe import describe_points
from terrainx_robot.lidar.voxel_codec import indices_to_points


def _cli(tmp_path, *args):
    return main(["--data-dir", str(tmp_path / "data"), "--env-file", str(tmp_path / "none.env"), *args])


def test_flujo_offline_completo(tmp_path, capsys):
    assert _cli(tmp_path, "demo-session", "--frames", "4") == 0
    assert _cli(tmp_path, "capture", "--source", "replay", "--input", "latest") == 0
    assert _cli(tmp_path, "probe", "--source", "replay", "--input", "latest") == 0
    capsys.readouterr()
    assert _cli(tmp_path, "list-scans", "--json") == 0
    scans = json.loads(capsys.readouterr().out)
    assert len(scans) == 1 and scans[0]["evidence_class"] == "synthetic_test" and scans[0]["demo"] is True
    scan_id = scans[0]["id"]
    assert _cli(tmp_path, "verify-scan", scan_id) == 0
    assert _cli(tmp_path, "inspect", scan_id) == 0
    assert _cli(tmp_path, "export-scan", scan_id, "--dest", str(tmp_path / "out")) == 0
    assert (tmp_path / "out" / scan_id / f"{scan_id}.ply").is_file()
    probes = list((tmp_path / "data" / "probes").glob("*.json"))
    assert len(probes) == 1 and json.loads(probes[0].read_text(encoding="utf-8"))["overall_status"] == "ok"
    assert (tmp_path / "data" / "logs" / "terrainx_robot.log").is_file()


def test_exportar_esquemas(tmp_path):
    out = tmp_path / "schemas"
    assert _cli(tmp_path, "export-schemas", "--out", str(out)) == 0
    names = sorted(p.name for p in out.glob("*.schema.json"))
    assert names == ["capability_report.schema.json", "robot_status.schema.json",
                     "scan_metadata.schema.json", "session_info.schema.json"]
    schema = json.loads((out / "scan_metadata.schema.json").read_text(encoding="utf-8"))
    for field in ("id", "scan_context", "frame_id", "unit", "timestamp_utc", "point_count", "file_url"):
        assert field in schema["required"]  # campos del contrato 1.0 siguen siendo obligatorios


def test_errores_claros_en_cli(tmp_path, capsys, monkeypatch):
    assert _cli(tmp_path, "capture", "--source", "go2", "--duration", "1") == 1
    assert "missing_address" in capsys.readouterr().err
    assert _cli(tmp_path, "capture", "--source", "replay") == 1
    assert _cli(tmp_path, "capture", "--source", "replay", "--input", "latest") == 1  # sin sesiones
    monkeypatch.setenv("TERRAINX_GO2_METHOD", "Remote")
    assert _cli(tmp_path, "info") == 1
    assert "deshabilitado" in capsys.readouterr().err


def test_escena_sintetica_tiene_la_geometria_declarada():
    pts = indices_to_points(scene_indices(), (-3.2, -3.2, -0.6), 0.05)
    z_levels = np.round(pts[:, 2], 6)
    assert np.isclose(z_levels.min(), FLOOR_Z_M)
    box = pts[(pts[:, 0] > 0.9) & (pts[:, 0] < 1.6) & (np.abs(pts[:, 1]) < 0.3)]
    assert np.isclose(box[:, 2].max(), BOX_TOP_Z_M)  # obstáculo de altura conocida
    a = generate_frames(2, seed=5)
    b = generate_frames(2, seed=5)
    assert [f.payload for f in a] == [f.payload for f in b]  # determinista


def test_describe_plano():
    xs, ys = np.meshgrid(np.arange(0, 1, 0.05), np.arange(0, 1, 0.05))
    pts = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
    d = describe_points(pts, 0.05)
    assert d["most_populated_z_level"]["z"] == 0.0 and d["most_populated_z_level"]["fraction"] == 1.0
    assert d["observed_grid_step"]["x"] == 0.05 and d["grid_step_consistent_with_declared_resolution"]
    assert describe_points(np.empty((0, 3))) == {"point_count": 0}


@pytest.mark.go2lib
def test_api_de_la_libreria_instalada():
    pytest.importorskip("unitree_webrtc_connect")
    from terrainx_robot.adapters.library_check import run_library_checks

    results = run_library_checks()
    failed = [(name, detail) for name, ok, detail in results if not ok]
    assert not failed, failed

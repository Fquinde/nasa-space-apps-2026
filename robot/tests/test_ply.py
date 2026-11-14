import numpy as np
import pytest

from terrainx_robot.storage.ply import PlyError, read_ply, write_ply

PTS = np.array([[0.0, 0.0, 0.0], [1.25, -2.5, 0.05], [-3.2, 3.15, 1.2]])


@pytest.mark.parametrize("binary", [True, False])
def test_ida_y_vuelta(tmp_path, binary):
    path = tmp_path / "a.ply"
    write_ply(path, PTS, binary=binary, comments=["frame_id test", "con\nsalto"])
    data = read_ply(path)
    np.testing.assert_allclose(data.points, PTS, atol=1e-6)
    assert data.format == ("binary_little_endian" if binary else "ascii")
    assert "frame_id test" in data.comments
    assert "con salto" in data.comments  # sin saltos de línea en la cabecera


def test_precision_double(tmp_path):
    pts = np.array([[0.123456789012, 1e-9, 1000.000001]])
    write_ply(tmp_path / "d.ply", pts, precision="float64")
    np.testing.assert_array_equal(read_ply(tmp_path / "d.ply").points, pts)


def test_big_endian_y_propiedades_extra(tmp_path):
    header = b"ply\nformat binary_big_endian 1.0\nelement vertex 2\nproperty float x\nproperty float y\n" \
             b"property float z\nproperty uchar intensity\nend_header\n"
    rows = np.array([(1, 2, 3, 7), (4, 5, 6, 9)], dtype=[("x", ">f4"), ("y", ">f4"), ("z", ">f4"), ("i", "u1")])
    (tmp_path / "b.ply").write_bytes(header + rows.tobytes())
    np.testing.assert_allclose(read_ply(tmp_path / "b.ply").points, [[1, 2, 3], [4, 5, 6]])


@pytest.mark.parametrize(
    "content",
    [
        b"noply\n",
        b"ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nproperty float y\nend_header\n1 2\n",
        b"ply\nformat binary_little_endian 1.0\nelement vertex 5\nproperty float x\nproperty float y\n"
        b"property float z\nend_header\n\x00\x00",
        b"ply\nformat ascii 1.0\nelement vertex 2\nproperty float x\nproperty float y\nproperty float z\n"
        b"end_header\n1 2 3\n",
        b"ply\nformat ascii 1.0\nelement face 1\nproperty list uchar int vertex_indices\nend_header\n",
        b"ply\nformat ascii 1.0\nelement vertex 1\n",
    ],
    ids=["magia", "falta_z", "binario_truncado", "ascii_truncado", "sin_vertex", "sin_end_header"],
)
def test_archivos_invalidos(tmp_path, content):
    path = tmp_path / "bad.ply"
    path.write_bytes(content)
    with pytest.raises(PlyError):
        read_ply(path)


def test_no_escribe_nan(tmp_path):
    with pytest.raises(PlyError):
        write_ply(tmp_path / "n.ply", np.array([[np.nan, 0, 0]]))
    assert not (tmp_path / "n.ply").exists()

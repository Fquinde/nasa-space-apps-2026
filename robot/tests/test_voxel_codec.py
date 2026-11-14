import lz4.block
import numpy as np
import pytest

from terrainx_robot.fixtures.synthetic import generate_frames
from terrainx_robot.lidar.voxel_codec import (
    BYTES_PER_SLICE,
    VoxelDecodeError,
    decode_voxel_map,
    decompress,
    encode_voxel_map,
)

ORIGIN = [-3.2, -3.2, -0.6]
RES = 0.05


def _rows(a):
    return {tuple(r) for r in np.asarray(a).tolist()}


def test_roundtrip_exacto():
    rng = np.random.default_rng(0)
    idx = np.unique(
        np.column_stack([rng.integers(0, 128, 500), rng.integers(0, 128, 500), rng.integers(0, 10, 500)]),
        axis=0,
    )
    payload, src = encode_voxel_map(idx, 10)
    assert src == 10 * BYTES_PER_SLICE
    dec = decode_voxel_map(payload, src, ORIGIN, RES)
    assert _rows(dec.indices) == _rows(idx)
    np.testing.assert_allclose(dec.points, dec.indices * RES + np.array(ORIGIN))
    assert dec.grid_shape == (128, 128, 10)
    assert dec.partial_slice_bytes == 0


@pytest.mark.parametrize(
    "voxel, byte_index, byte_value",
    [
        ((0, 0, 0), 0, 0x80),  # bit más significativo = x 0
        ((7, 0, 0), 0, 0x01),
        ((8, 0, 0), 1, 0x80),
        ((0, 1, 0), 16, 0x80),  # 16 bytes por fila Y
        ((0, 0, 1), 2048, 0x80),  # 2048 bytes por capa Z
    ],
)
def test_orden_de_bits_y_disposicion(voxel, byte_index, byte_value):
    payload, src = encode_voxel_map(np.array([voxel]), 2)
    raw = decompress(payload, src)
    assert raw[byte_index] == byte_value
    assert sum(1 for b in raw if b) == 1
    dec = decode_voxel_map(payload, src, [0, 0, 0], 1.0)
    assert dec.indices.tolist() == [list(voxel)]


def test_capa_parcial_se_informa():
    raw = bytearray(BYTES_PER_SLICE + 100)
    raw[BYTES_PER_SLICE + 5] = 0x80  # vóxel en la capa z=1 incompleta
    payload = lz4.block.compress(bytes(raw), store_size=False)
    dec = decode_voxel_map(payload, len(raw), [0, 0, 0], 1.0)
    assert dec.partial_slice_bytes == 100
    assert dec.grid_shape == (128, 128, 2)
    assert dec.indices.tolist() == [[40, 0, 1]]


def test_rejilla_vacia():
    payload, src = encode_voxel_map(np.empty((0, 3)), 3)
    dec = decode_voxel_map(payload, src, ORIGIN, RES)
    assert dec.points.shape == (0, 3)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"resolution": 0},
        {"resolution": -0.05},
        {"resolution": float("nan")},
        {"origin": [0, 0]},
        {"origin": [0, float("inf"), 0]},
        {"src_size": 0},
        {"src_size": 10**9},
        {"src_size": 2048 * 3 + 1},  # no coincide con el tamaño real
    ],
)
def test_parametros_invalidos(kwargs):
    payload, src = encode_voxel_map(np.array([[1, 2, 0]]), 3)
    args = {"compressed": payload, "src_size": src, "origin": ORIGIN, "resolution": RES}
    args.update(kwargs)
    with pytest.raises(VoxelDecodeError):
        decode_voxel_map(**args)


def test_payload_corrupto_o_vacio():
    with pytest.raises(VoxelDecodeError):
        decode_voxel_map(b"\xff\x00garbage", 2048, ORIGIN, RES)
    with pytest.raises(VoxelDecodeError):
        decode_voxel_map(b"", 2048, ORIGIN, RES)


def test_encode_fuera_de_rejilla():
    with pytest.raises(VoxelDecodeError):
        encode_voxel_map(np.array([[128, 0, 0]]), 2)
    with pytest.raises(VoxelDecodeError):
        encode_voxel_map(np.array([[0, 0, 2]]), 2)


@pytest.mark.go2lib
def test_identico_al_decodificador_native_de_la_libreria():
    native = pytest.importorskip("unitree_webrtc_connect.lidar.lidar_decoder_native")
    decoder = native.LidarDecoder()
    for seed in (1, 2, 3):
        for frame in generate_frames(3, seed=seed):
            theirs = decoder.decode(frame.payload, frame.meta)["points"]
            ours = decode_voxel_map(
                frame.payload, frame.meta["src_size"], frame.meta["origin"], frame.meta["resolution"]
            ).points
            assert theirs.shape == ours.shape
            assert np.array_equal(theirs, ours)  # mismo orden y mismos bits

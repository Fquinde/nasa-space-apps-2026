"""Codificación/decodificación del mapa de vóxeles comprimido que publica el Go2.

Qué hace
    Convierte el payload binario del topic ``rt/utlidar/voxel_map_compressed``
    en coordenadas XYZ, replicando EXACTAMENTE el decodificador "native" de
    unitree_webrtc_connect 2.2.0 (``lidar/lidar_decoder_native.py``, que incluye
    su propio aviso de licencia de tipo BSD). Lo reimplementamos para:
      1. reproducir sesiones grabadas sin instalar la pila WebRTC,
      2. añadir validaciones explícitas (tamaños, parámetros, corrupción),
      3. generar datos sintéticos con el mismo formato (encode).
    ``tests/test_voxel_codec.py`` compara ambos decodificadores bit a bit.

Formato (deducido del código fuente de la librería; Unitree no lo documenta)
    - payload = bloque LZ4 sin cabecera cuyo tamaño descomprimido es ``src_size``.
    - descomprimido = bitmask de ocupación. Cada capa Z ocupa 2048 bytes (0x800);
      dentro de una capa, cada fila Y ocupa 16 bytes (0x10) = 128 bits en X.
      El bit más significativo de cada byte corresponde al desplazamiento x=0.
    - índice (x, y, z) -> punto = origin + índice * resolution.
    Por tanto los puntos son VÓXELES OCUPADOS cuantizados a ``resolution``,
    no retornos crudos del sensor.

Entradas
    bytes comprimidos, src_size (int), origin (3 floats), resolution (float > 0).
Salidas
    ndarray (N,3) float64 en las unidades de origin/resolution. Se ASUMEN metros
    (resolución por defecto 0.05 en la librería), pendiente de verificación física.
Errores
    VoxelDecodeError si los parámetros o el payload son inválidos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import lz4.block
import numpy as np

GRID_X = 128
GRID_Y = 128
BYTES_PER_ROW = GRID_X // 8  # 16
BYTES_PER_SLICE = BYTES_PER_ROW * GRID_Y  # 2048
# Límite de seguridad contra payloads anómalos (512 capas = 1 MiB descomprimido).
MAX_SRC_SIZE = 512 * BYTES_PER_SLICE


class VoxelDecodeError(ValueError):
    """El mensaje LiDAR no se puede decodificar de forma fiable."""


@dataclass(frozen=True)
class DecodedVoxelMap:
    points: np.ndarray  # (N,3) float64
    indices: np.ndarray  # (N,3) int64 en orden [x, y, z]
    grid_shape: tuple[int, int, int]  # (x, y, capas z completas)
    partial_slice_bytes: int  # bytes sobrantes si src_size no es múltiplo de 2048


def _check_origin_resolution(origin: Sequence[float], resolution: float) -> tuple[np.ndarray, float]:
    try:
        origin_arr = np.asarray(origin, dtype=np.float64).reshape(3)
    except (TypeError, ValueError) as exc:
        raise VoxelDecodeError(f"origin debe tener 3 valores numéricos: {origin!r}") from exc
    if not np.all(np.isfinite(origin_arr)):
        raise VoxelDecodeError(f"origin contiene valores no finitos: {origin!r}")
    try:
        res = float(resolution)
    except (TypeError, ValueError) as exc:
        raise VoxelDecodeError(f"resolution no numérica: {resolution!r}") from exc
    if not math.isfinite(res) or res <= 0:
        raise VoxelDecodeError(f"resolution debe ser > 0: {resolution!r}")
    return origin_arr, res


def _check_src_size(src_size: int) -> int:
    try:
        size = int(src_size)
    except (TypeError, ValueError) as exc:
        raise VoxelDecodeError(f"src_size no entero: {src_size!r}") from exc
    if size <= 0 or size > MAX_SRC_SIZE:
        raise VoxelDecodeError(f"src_size fuera de rango (1..{MAX_SRC_SIZE}): {size}")
    return size


def decompress(compressed: bytes, src_size: int) -> bytes:
    """Descomprime el bloque LZ4 y comprueba que el tamaño coincide con src_size."""
    if not isinstance(compressed, (bytes, bytearray, memoryview)) or len(compressed) == 0:
        raise VoxelDecodeError("payload LiDAR vacío o no binario")
    size = _check_src_size(src_size)
    try:
        out = lz4.block.decompress(bytes(compressed), uncompressed_size=size)
    except Exception as exc:  # lz4 lanza LZ4BlockError / ValueError según versión
        raise VoxelDecodeError(f"payload LZ4 corrupto o src_size incorrecto: {exc}") from exc
    if len(out) != size:
        raise VoxelDecodeError(f"tamaño descomprimido {len(out)} != src_size {size}")
    return out


def occupancy_to_indices(buffer: bytes) -> np.ndarray:
    """Bitmask de ocupación -> índices (N,3) [x, y, z] en el mismo orden que la librería."""
    arr = np.frombuffer(buffer, dtype=np.uint8)
    nonzero = np.flatnonzero(arr)
    if nonzero.size == 0:
        return np.empty((0, 3), dtype=np.int64)
    bits = np.unpackbits(arr[nonzero]).reshape(-1, 8).astype(bool)  # MSB primero
    z = nonzero // BYTES_PER_SLICE
    remainder = nonzero % BYTES_PER_SLICE
    y = remainder // BYTES_PER_ROW
    x_base = (remainder % BYTES_PER_ROW) * 8
    x = x_base[:, None] + np.arange(8)[None, :]
    yy = np.broadcast_to(y[:, None], x.shape)
    zz = np.broadcast_to(z[:, None], x.shape)
    return np.column_stack((x[bits], yy[bits], zz[bits])).astype(np.int64)


def indices_to_points(indices: np.ndarray, origin: Sequence[float], resolution: float) -> np.ndarray:
    """Índices de vóxel -> coordenadas: origin + índice * resolution."""
    origin_arr, res = _check_origin_resolution(origin, resolution)
    return indices.astype(np.float64) * res + origin_arr


def decode_voxel_map(
    compressed: bytes, src_size: int, origin: Sequence[float], resolution: float
) -> DecodedVoxelMap:
    """Decodifica un mensaje completo. Ver docstring del módulo."""
    origin_arr, res = _check_origin_resolution(origin, resolution)
    raw = decompress(compressed, src_size)
    indices = occupancy_to_indices(raw)
    points = indices.astype(np.float64) * res + origin_arr
    full_slices, partial = divmod(len(raw), BYTES_PER_SLICE)
    return DecodedVoxelMap(
        points=points,
        indices=indices,
        grid_shape=(GRID_X, GRID_Y, full_slices + (1 if partial else 0)),
        partial_slice_bytes=partial,
    )


def points_to_indices(points: np.ndarray, origin: Sequence[float], resolution: float) -> np.ndarray:
    """Coordenadas -> índice de vóxel más cercano (solo para generar datos de prueba)."""
    origin_arr, res = _check_origin_resolution(origin, resolution)
    return np.rint((np.asarray(points, dtype=np.float64) - origin_arr) / res).astype(np.int64)


def encode_voxel_map(indices: np.ndarray, z_slices: int) -> tuple[bytes, int]:
    """Índices (N,3) [x,y,z] -> (payload LZ4, src_size). Inversa de decode.

    Se usa para generar sesiones SINTÉTICAS con el formato del robot.
    """
    if z_slices <= 0 or z_slices * BYTES_PER_SLICE > MAX_SRC_SIZE:
        raise VoxelDecodeError(f"z_slices fuera de rango: {z_slices}")
    idx = np.asarray(indices, dtype=np.int64).reshape(-1, 3)
    if idx.size and (
        idx[:, 0].min() < 0
        or idx[:, 0].max() >= GRID_X
        or idx[:, 1].min() < 0
        or idx[:, 1].max() >= GRID_Y
        or idx[:, 2].min() < 0
        or idx[:, 2].max() >= z_slices
    ):
        raise VoxelDecodeError("índices fuera de la rejilla 128 x 128 x z_slices")
    grid = np.zeros((z_slices, GRID_Y, GRID_X), dtype=bool)
    if idx.size:
        grid[idx[:, 2], idx[:, 1], idx[:, 0]] = True
    raw = np.packbits(grid, axis=-1).tobytes()  # bitorder 'big': MSB = x offset 0
    return lz4.block.compress(raw, store_size=False), len(raw)

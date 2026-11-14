"""Lectura y escritura de nubes de puntos en formato PLY (Stanford).

Qué hace
    write_ply: escribe vértices x, y, z (float32 por defecto, o float64) en
    binary_little_endian (compacto) o ascii (legible). Los metadatos esenciales
    se repiten como comentarios de cabecera para que el PLY no pierda contexto
    si se separa de su JSON.
    read_ply: lee PLY ascii / binary_little_endian / binary_big_endian cuyo
    primer elemento sea 'vertex' con propiedades x, y, z (ignora el resto).
Unidades: las de la nube (metros en TERRAIN-X).
Errores: PlyError para cabeceras inválidas, archivos truncados o tamaños excesivos.
"""

from __future__ import annotations

import io
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal

import numpy as np

_PLY_TYPES = {
    "char": "i1", "int8": "i1", "uchar": "u1", "uint8": "u1",
    "short": "i2", "int16": "i2", "ushort": "u2", "uint16": "u2",
    "int": "i4", "int32": "i4", "uint": "u4", "uint32": "u4",
    "float": "f4", "float32": "f4", "double": "f8", "float64": "f8",
}
_MAX_HEADER_BYTES = 64 * 1024
DEFAULT_MAX_VERTICES = 20_000_000


class PlyError(ValueError):
    pass


@dataclass
class PlyData:
    points: np.ndarray  # (N,3) float64
    format: str
    comments: list[str] = field(default_factory=list)
    vertex_properties: list[str] = field(default_factory=list)


def _sanitize_comment(text: str) -> str:
    clean = " ".join(str(text).split())  # sin saltos de línea
    return clean.encode("ascii", errors="replace").decode("ascii")


def write_ply(
    path: Path,
    points: np.ndarray,
    *,
    binary: bool = True,
    comments: Iterable[str] = (),
    precision: Literal["float32", "float64"] = "float32",
) -> None:
    pts = np.asarray(points, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 3:
        raise PlyError(f"se esperaba (N,3), llegó {pts.shape}")
    if not np.all(np.isfinite(pts)):
        raise PlyError("la nube contiene NaN/inf: valídela antes de exportar")
    ply_type = "float" if precision == "float32" else "double"
    lines = ["ply", f"format {'binary_little_endian' if binary else 'ascii'} 1.0"]
    lines += [f"comment {_sanitize_comment(c)}" for c in comments]
    lines += [
        f"element vertex {pts.shape[0]}",
        f"property {ply_type} x",
        f"property {ply_type} y",
        f"property {ply_type} z",
        "end_header",
    ]
    header = ("\n".join(lines) + "\n").encode("ascii")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(header)
        if binary:
            fh.write(pts.astype("<f4" if precision == "float32" else "<f8").tobytes())
        else:
            buf = io.StringIO()
            np.savetxt(buf, pts, fmt="%.9g" if precision == "float32" else "%.17g", delimiter=" ")
            fh.write(buf.getvalue().encode("ascii"))
    os.replace(tmp, path)


def read_ply(path: Path, *, max_vertices: int = DEFAULT_MAX_VERTICES) -> PlyData:
    path = Path(path)
    with open(path, "rb") as fh:
        header_lines: list[str] = []
        consumed = 0
        while True:
            raw = fh.readline()
            if not raw:
                raise PlyError("cabecera PLY incompleta (falta end_header)")
            consumed += len(raw)
            if consumed > _MAX_HEADER_BYTES:
                raise PlyError("cabecera PLY demasiado grande")
            line = raw.decode("ascii", errors="replace").strip()
            header_lines.append(line)
            if line == "end_header":
                break
        if not header_lines or header_lines[0] != "ply":
            raise PlyError("no es un archivo PLY (falta la palabra mágica 'ply')")

        fmt = None
        comments: list[str] = []
        elements: list[tuple[str, int, list[tuple[str, str]]]] = []
        for line in header_lines[1:-1]:
            parts = line.split()
            if not parts:
                continue
            key = parts[0]
            if key == "format":
                if len(parts) < 2:
                    raise PlyError("línea 'format' inválida")
                fmt = parts[1]
            elif key in ("comment", "obj_info"):
                comments.append(line[len(key):].strip())
            elif key == "element":
                if len(parts) != 3:
                    raise PlyError(f"línea 'element' inválida: {line}")
                try:
                    elements.append((parts[1], int(parts[2]), []))
                except ValueError as exc:
                    raise PlyError(f"recuento inválido: {line}") from exc
            elif key == "property":
                if not elements:
                    raise PlyError("propiedad antes de cualquier elemento")
                if parts[1] == "list":
                    elements[-1][2].append(("list", parts[-1]))
                else:
                    if len(parts) != 3 or parts[1] not in _PLY_TYPES:
                        raise PlyError(f"propiedad no soportada: {line}")
                    elements[-1][2].append((parts[1], parts[2]))
            else:
                raise PlyError(f"línea de cabecera desconocida: {line}")

        if fmt not in ("ascii", "binary_little_endian", "binary_big_endian"):
            raise PlyError(f"formato PLY no soportado: {fmt}")
        if not elements or elements[0][0] != "vertex":
            raise PlyError("el primer elemento debe ser 'vertex'")
        _, count, props = elements[0]
        if count < 0 or count > max_vertices:
            raise PlyError(f"número de vértices fuera de rango: {count}")
        names = [n for _, n in props]
        if any(t == "list" for t, _ in props):
            raise PlyError("propiedades de tipo lista en 'vertex' no soportadas")
        for axis in ("x", "y", "z"):
            if axis not in names:
                raise PlyError(f"falta la propiedad '{axis}' en 'vertex'")

        if fmt == "ascii":
            rows = []
            for i in range(count):
                raw = fh.readline()
                if not raw:
                    raise PlyError(f"PLY truncado: {i} de {count} vértices")
                values = raw.split()
                if len(values) < len(props):
                    raise PlyError(f"vértice {i} con {len(values)} valores (se esperaban {len(props)})")
                rows.append(values[: len(props)])
            try:
                table = np.asarray(rows, dtype=np.float64).reshape(count, len(props))
            except ValueError as exc:
                raise PlyError(f"valores no numéricos en PLY ascii: {exc}") from exc
            cols = {n: table[:, i] for i, n in enumerate(names)}
        else:
            endian = "<" if fmt == "binary_little_endian" else ">"
            dtype = np.dtype([(n, endian + _PLY_TYPES[t]) for t, n in props])
            needed = dtype.itemsize * count
            data = fh.read(needed)
            if len(data) < needed:
                raise PlyError(f"PLY truncado: {len(data)} de {needed} bytes de vértices")
            table = np.frombuffer(data, dtype=dtype, count=count)
            cols = {n: table[n].astype(np.float64) for n in names}

    points = np.column_stack((cols["x"], cols["y"], cols["z"])) if count else np.empty((0, 3))
    return PlyData(points=points, format=fmt, comments=comments, vertex_properties=names)

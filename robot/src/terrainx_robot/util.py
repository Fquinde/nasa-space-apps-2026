"""Utilidades comunes: tiempo UTC, identificadores, hashes, JSON seguro y versiones.

Qué hace: funciones pequeñas que usan varios módulos.
Errores: no lanza excepciones propias.
"""

from __future__ import annotations

import base64
import hashlib
import importlib.metadata
import json
import os
import platform
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


def utc_now() -> datetime:
    """Hora actual en UTC (con zona horaria explícita)."""
    return datetime.now(timezone.utc)


def iso_utc(dt: datetime) -> str:
    """ISO-8601 en UTC terminado en 'Z' (p. ej. 2026-11-14T11:00:00.123456Z)."""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def new_id(prefix: str, when: datetime | None = None) -> str:
    """Identificador ordenable y único: <prefijo>-AAAAMMDDTHHMMSSZ-<6 hex aleatorios>."""
    when = when or utc_now()
    return f"{prefix}-{when.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}-{secrets.token_hex(3)}"


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """SHA-256 en hexadecimal de un archivo, leído por bloques."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk_size), b""):
            digest.update(block)
    return digest.hexdigest()


def json_safe(obj: Any) -> Any:
    """Convierte estructuras con numpy/bytes/datetime en tipos serializables a JSON.

    - bytes -> {"__bytes_b64__": "<base64>"} (reversible con from_json_safe)
    - numpy -> listas / escalares Python
    - datetime -> ISO-8601 UTC
    """
    if isinstance(obj, dict):
        return {str(k): json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return {"__bytes_b64__": base64.b64encode(bytes(obj)).decode("ascii")}
    if isinstance(obj, datetime):
        return iso_utc(obj)
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    return str(obj)


def from_json_safe(obj: Any) -> Any:
    """Inversa parcial de json_safe: reconstruye los bytes codificados en base64."""
    if isinstance(obj, dict):
        if set(obj.keys()) == {"__bytes_b64__"}:
            return base64.b64decode(obj["__bytes_b64__"])
        return {k: from_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [from_json_safe(v) for v in obj]
    return obj


def write_json_atomic(path: Path, data: Any) -> None:
    """Escribe JSON (UTF-8, indentado) de forma atómica: archivo temporal + rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(json_safe(data), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def _dist_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def software_versions() -> dict[str, str | None]:
    """Versiones del software implicado, para la procedencia de cada dato."""
    from . import __version__

    return {
        "terrainx_robot": __version__,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": _dist_version("numpy"),
        "lz4": _dist_version("lz4"),
        "pydantic": _dist_version("pydantic"),
        "unitree_webrtc_connect": _dist_version("unitree_webrtc_connect"),
    }

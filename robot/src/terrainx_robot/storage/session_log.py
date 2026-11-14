"""Grabación y lectura de sesiones de datos crudos (para replay offline).

Qué hace
    SessionRecorder escribe, mensaje a mensaje, lo que llega del robot:
        <data_dir>/sessions/<session_id>/messages.jsonl
        <data_dir>/sessions/<session_id>/session.json   (al cerrar, con SHA-256)
    Los mensajes LiDAR se guardan con su payload comprimido ORIGINAL en base64,
    de modo que el replay vuelve a decodificar exactamente lo mismo que llegó.
    SessionReader lee y verifica una sesión.

Formato de cada línea de messages.jsonl
    {"seq", "t_host_utc", "t_rel_s", "topic", "kind": "lidar_voxel_compressed" | "json",
     "meta": {...} (LiDAR), "payload_b64": "..." (LiDAR), "data": ... (json)}

Errores: SessionError (sesión inexistente, corrupta o hash alterado).
Nota: una sesión real puede contener identificadores del robot; la carpeta
runtime/ está en .gitignore.
"""

from __future__ import annotations

import base64
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from ..models import SessionInfo
from ..util import from_json_safe, iso_utc, json_safe, sha256_file, utc_now, write_json_atomic

KIND_LIDAR = "lidar_voxel_compressed"
KIND_JSON = "json"


class SessionError(RuntimeError):
    pass


class SessionRecorder:
    def __init__(self, sessions_root: Path, info: SessionInfo) -> None:
        self.info = info
        self.folder = Path(sessions_root) / info.session_id
        self.folder.mkdir(parents=True, exist_ok=False)
        self._fh = open(self.folder / info.messages_file, "w", encoding="utf-8", newline="\n")
        self._t0 = time.monotonic()
        self._seq = 0
        self._closed = False

    def _write(self, record: dict[str, Any]) -> None:
        if self._closed:
            raise SessionError("la sesión ya está cerrada")
        self._seq += 1
        record = {"seq": self._seq, **record}
        self._fh.write(json.dumps(json_safe(record), ensure_ascii=False) + "\n")
        self.info.record_count += 1

    def record_lidar(self, *, topic: str, host_utc: datetime, meta: dict, raw: bytes) -> None:
        meta = {k: v for k, v in (meta or {}).items() if k != "data"}
        self._write(
            {
                "t_host_utc": iso_utc(host_utc),
                "t_rel_s": round(time.monotonic() - self._t0, 6),
                "topic": topic,
                "kind": KIND_LIDAR,
                "meta": meta,
                "payload_b64": base64.b64encode(bytes(raw)).decode("ascii"),
            }
        )
        self.info.lidar_records += 1

    def record_json(self, *, topic: str, host_utc: datetime, data: Any, t_rel_s: float | None = None) -> None:
        self._write(
            {
                "t_host_utc": iso_utc(host_utc),
                "t_rel_s": round(time.monotonic() - self._t0, 6) if t_rel_s is None else t_rel_s,
                "topic": topic,
                "kind": KIND_JSON,
                "data": data,
            }
        )
        self.info.json_records += 1

    def record_lidar_at(self, *, topic: str, host_utc: datetime, meta: dict, raw: bytes, t_rel_s: float) -> None:
        """Variante con tiempo relativo explícito (generador sintético determinista)."""
        meta = {k: v for k, v in (meta or {}).items() if k != "data"}
        self._write(
            {
                "t_host_utc": iso_utc(host_utc),
                "t_rel_s": t_rel_s,
                "topic": topic,
                "kind": KIND_LIDAR,
                "meta": meta,
                "payload_b64": base64.b64encode(bytes(raw)).decode("ascii"),
            }
        )
        self.info.lidar_records += 1

    def close(self) -> SessionInfo:
        if self._closed:
            return self.info
        self._fh.close()
        self._closed = True
        self.info.closed_utc = utc_now()
        self.info.messages_sha256 = sha256_file(self.folder / self.info.messages_file)
        write_json_atomic(self.folder / "session.json", self.info.model_dump(mode="json"))
        return self.info

    def __enter__(self) -> "SessionRecorder":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class SessionReader:
    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)
        meta_path = self.folder / "session.json"
        if not meta_path.is_file():
            raise SessionError(f"no es una sesión (falta session.json): {self.folder}")
        try:
            self.info = SessionInfo.model_validate_json(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SessionError(f"session.json inválido: {exc}") from exc
        self.messages_path = self.folder / self.info.messages_file
        if not self.messages_path.is_file():
            raise SessionError(f"falta {self.info.messages_file} en {self.folder}")

    def verify(self) -> bool:
        return (
            self.info.messages_sha256 is not None
            and sha256_file(self.messages_path) == self.info.messages_sha256
        )

    def records(self) -> Iterator[dict[str, Any]]:
        """Itera los mensajes. Los payload LiDAR se devuelven ya como bytes ('raw')."""
        with open(self.messages_path, "r", encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, start=1):
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise SessionError(f"línea {line_no} corrupta: {exc}") from exc
                if not isinstance(rec, dict) or "kind" not in rec or "topic" not in rec:
                    raise SessionError(f"línea {line_no} sin 'kind'/'topic'")
                if rec["kind"] == KIND_LIDAR:
                    try:
                        rec["raw"] = base64.b64decode(rec.pop("payload_b64"), validate=True)
                    except (KeyError, ValueError) as exc:
                        raise SessionError(f"línea {line_no}: payload LiDAR inválido") from exc
                elif rec["kind"] == KIND_JSON:
                    rec["data"] = from_json_safe(rec.get("data"))
                else:
                    raise SessionError(f"línea {line_no}: tipo desconocido {rec['kind']!r}")
                rec["t_host_utc"] = datetime.fromisoformat(rec["t_host_utc"].replace("Z", "+00:00"))
                yield rec

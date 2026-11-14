"""Adaptador de reproducción offline (sin robot ni Internet).

Qué hace
    Reproduce por el MISMO camino de código que el robot real:
      - una sesión grabada (carpeta con session.json + messages.jsonl), ya sea
        real (robot_measured) o sintética (synthetic_test);
      - un archivo PLY (p. ej. un escaneo exportado o una nube de terceros).
    La clase de evidencia la fija la fuente, no el adaptador:
      - sesión: la de session.json;
      - PLY con su <id>.metadata.json al lado: la de esos metadatos;
      - PLY sin metadatos: debe declararla el operador (no se adivina).
    Todo lo que produce lleva delivery_mode = "replay".

Entradas: ruta de la fuente; speed (0 = lo más rápido posible; 1 = tiempo real).
Errores: ConnectionFailed si la sesión está corrupta o el PLY es inválido;
         ValueError si falta la clase de evidencia de un PLY sin metadatos.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from ..lidar.frames import LidarFrame
from ..models import (
    DeliveryMode,
    EvidenceClass,
    LidarFrameInfo,
    PointType,
    RobotDescriptor,
    ScanContext,
    ScanMetadata,
)
from ..storage.ply import PlyError, read_ply
from ..storage.scan_store import ScanStore
from ..storage.session_log import KIND_LIDAR, SessionError, SessionReader
from ..util import sha256_file, utc_now
from .base import ConnectionFailed, RobotAdapter


class ReplayAdapter(RobotAdapter):
    adapter_name = "replay"

    def __init__(
        self,
        source: Path,
        store: ScanStore,
        *,
        speed: float = 0.0,
        evidence_class: EvidenceClass | None = None,
        scan_context: ScanContext | None = None,
        robot_id: str | None = None,
    ) -> None:
        self.source = Path(source)
        self.speed = float(speed)
        self._reader: SessionReader | None = None
        self._ply_points = None
        self._ply_frame_id = "unknown_ply_frame"
        self._ply_point_type = PointType.UNKNOWN
        self._ply_resolution: float | None = None
        self._ply_source_scan: str | None = None
        self._manual_evidence = False

        if self.source.is_dir():
            try:
                self._reader = SessionReader(self.source)
            except SessionError as exc:
                raise ConnectionFailed("invalid_session", str(exc)) from exc
            info = self._reader.info
            if evidence_class is not None and evidence_class is not info.evidence_class:
                raise ValueError(
                    f"la sesión es {info.evidence_class.value}; la clase de evidencia no se puede cambiar"
                )
            descriptor = info.robot.model_copy(
                update={"adapter": self.adapter_name, "delivery_mode": DeliveryMode.REPLAY}
            )
            evidence, context = info.evidence_class, info.scan_context
            self.kind = "session"
        elif self.source.suffix.lower() == ".ply" and self.source.is_file():
            sidecar = self.source.with_name(self.source.stem + ".metadata.json")
            if sidecar.is_file():
                meta = ScanMetadata.model_validate_json(sidecar.read_text(encoding="utf-8"))
                if evidence_class is not None and evidence_class is not meta.evidence_class:
                    raise ValueError(
                        f"el PLY tiene metadatos con evidence_class={meta.evidence_class.value}; no se puede cambiar"
                    )
                descriptor = meta.robot.model_copy(
                    update={"adapter": self.adapter_name, "delivery_mode": DeliveryMode.REPLAY}
                )
                evidence, context = meta.evidence_class, meta.scan_context
                self._ply_frame_id = meta.frame_id
                self._ply_point_type = meta.geometry.point_type
                self._ply_resolution = meta.geometry.voxel_resolution_m
                self._ply_source_scan = meta.id
            else:
                if evidence_class is None:
                    raise ValueError(
                        "PLY sin metadatos: indique la clase de evidencia (--evidence-class); "
                        "su origen no se puede deducir del archivo"
                    )
                evidence = evidence_class
                context = scan_context or (
                    ScanContext.SYNTHETIC
                    if evidence is EvidenceClass.SYNTHETIC_TEST
                    else ScanContext.CONTROLLED_TEST
                )
                descriptor = RobotDescriptor(
                    robot_id=robot_id or "origen-no-declarado",
                    platform="unknown",
                    adapter=self.adapter_name,
                    delivery_mode=DeliveryMode.REPLAY,
                )
                self._manual_evidence = True
            self.kind = "ply"
        else:
            raise ConnectionFailed(
                "invalid_source", f"la fuente de replay no es una sesión ni un .ply: {self.source}"
            )
        super().__init__(
            descriptor=descriptor, store=store, evidence_class=evidence, scan_context=context
        )

    # ------------------------------------------------------------- ciclo de vida
    async def _open(self) -> None:
        if self._reader is not None:
            if not self._reader.verify():
                raise ConnectionFailed(
                    "session_integrity",
                    f"el SHA-256 de {self._reader.messages_path.name} no coincide con session.json",
                    "La sesión se modificó después de grabarse: no se reproduce.",
                )
        else:
            try:
                self._ply_points = read_ply(self.source).points
            except PlyError as exc:
                raise ConnectionFailed("invalid_ply", f"PLY inválido: {exc}") from exc

    async def _close(self) -> None:
        return None

    async def _run_window(self, duration_s: float | None) -> None:
        if self._reader is not None:
            previous = 0.0
            for rec in self._reader.records():
                t_rel = float(rec.get("t_rel_s") or 0.0)
                if duration_s is not None and t_rel > duration_s:
                    break
                await asyncio.sleep(max(0.0, (t_rel - previous) / self.speed) if self.speed > 0 else 0)
                previous = t_rel
                if rec["kind"] == KIND_LIDAR:
                    self._ingest_lidar_message(
                        topic=rec["topic"], meta=rec.get("meta") or {}, raw=rec["raw"], host_utc=rec["t_host_utc"]
                    )
                else:
                    self._ingest_json(topic=rec["topic"], data=rec.get("data"), host_utc=rec["t_host_utc"])
            return
        # PLY: un único frame con todos los puntos del archivo.
        points = self._ply_points
        now = utc_now()
        self._seq += 1
        topic = f"file:{self.source.name}"
        info = LidarFrameInfo(
            seq=self._seq,
            topic=topic,
            host_received_utc=now,
            frame_id=self._ply_frame_id,
            resolution=self._ply_resolution,
            point_count=int(points.shape[0]),
            point_type=self._ply_point_type,
            decoder="terrainx.storage.ply.read_ply",
        )
        self.monitor.observe(topic, now, {"point_count": int(points.shape[0])})
        self._ingest_frame(LidarFrame(info=info, points=points))
        await asyncio.sleep(0)

    # ------------------------------------------------------------- ganchos
    def _source_session_id(self) -> str | None:
        return self._reader.info.session_id if self._reader else None

    def _extra_provenance(self) -> dict:
        if self._reader is not None:
            return {
                "replay_source": {
                    "type": "session",
                    "session_id": self._reader.info.session_id,
                    "messages_sha256": self._reader.info.messages_sha256,
                    "generator": self._reader.info.generator,
                }
            }
        return {
            "replay_source": {
                "type": "ply",
                "file": self.source.name,
                "sha256": sha256_file(self.source),
                "source_scan_id": self._ply_source_scan,
            }
        }

    def _extra_caveats(self) -> list[str]:
        if self._manual_evidence:
            return [
                f"Clase de evidencia '{self.evidence_class.value}' DECLARADA por el operador al "
                "reproducir un PLY sin metadatos; no verificada por el sistema."
            ]
        return []

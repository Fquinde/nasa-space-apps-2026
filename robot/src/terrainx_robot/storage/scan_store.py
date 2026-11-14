"""Almacén de escaneos: PLY + metadatos JSON + SHA-256.

Qué hace
    Guarda cada escaneo en su propia carpeta:
        <data_dir>/scans/<scan_id>/<scan_id>.ply
        <data_dir>/scans/<scan_id>/<scan_id>.metadata.json
        <data_dir>/scans/<scan_id>/SHA256SUMS   (formato de sha256sum)
    Lista, verifica (recalcula hashes) y exporta escaneos.
    Genera automáticamente las advertencias (caveats) de procedencia: tipo de
    punto, unidades/ejes no verificados, ausencia de pose y georreferencia.
Errores: ScanStoreError (escaneo inexistente, hash alterado, nube vacía).
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

import numpy as np

from ..lidar.accumulator import AccumulatedCloud
from ..models import (
    Body,
    CaptureInfo,
    DeliveryMode,
    EvidenceClass,
    FileRef,
    GeometryInfo,
    PointType,
    ProcessingInfo,
    RobotDescriptor,
    ScanContext,
    ScanMetadata,
    Verification,
)
from ..util import new_id, sha256_file, software_versions, write_json_atomic
from .ply import read_ply, write_ply


class ScanStoreError(RuntimeError):
    pass


def _caveats(
    cloud: AccumulatedCloud,
    *,
    evidence_class: EvidenceClass,
    delivery_mode: DeliveryMode,
    session_id: str | None,
    pose_source: str | None,
) -> list[str]:
    notes: list[str] = []
    if evidence_class is EvidenceClass.SYNTHETIC_TEST:
        notes.append(
            "DATOS SINTÉTICOS generados por software para pruebas: no representan "
            "ninguna medición física."
        )
    if cloud.point_type is PointType.VOXEL_OCCUPANCY:
        origin = (
            "con el FORMATO del mapa que publica el robot por WebRTC (generado por software)"
            if evidence_class is EvidenceClass.SYNTHETIC_TEST
            else "del mapa que publica el robot por WebRTC"
        )
        notes.append(
            f"Cada punto es un vóxel ocupado (celda de {cloud.resolution} m) {origin}; "
            "no son retornos crudos del LiDAR. Error de cuantización de hasta una celda."
        )
    elif cloud.point_type is PointType.UNKNOWN:
        notes.append("Tipo de punto desconocido (nube importada sin metadatos de origen).")
    notes.append(
        "Unidad 'm' ASUMIDA: ni el robot ni la librería declaran unidades. "
        "Pendiente de verificación física (docs/VERIFICACION_FISICA.md)."
    )
    notes.append(
        f"Convención de ejes del frame '{cloud.frame_id}' no verificada "
        "(orientación de X/Y/Z y origen pendientes de comprobar con el robot)."
    )
    if pose_source is None:
        notes.append(
            "Sin pose asociada: la nube está en el frame del robot, no georreferenciada "
            "(registration.status = local_only)."
        )
    if cloud.mode == "accumulate" and cloud.frames_used > 1:
        notes.append(
            f"Unión de {cloud.frames_used} mapas sucesivos: si el robot se desplazó, la "
            "coherencia depende de su estimación interna de posición (no verificada)."
        )
    if delivery_mode is DeliveryMode.REPLAY:
        notes.append(f"Entregado en modo replay (sesión de origen: {session_id or 'archivo PLY'}).")
    return notes


class ScanStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.scans_dir = self.data_dir / "scans"

    # ----------------------------------------------------------------- guardar
    def save(
        self,
        cloud: AccumulatedCloud,
        *,
        robot: RobotDescriptor,
        evidence_class: EvidenceClass,
        delivery_mode: DeliveryMode,
        scan_context: ScanContext,
        capture_start: datetime,
        capture_end: datetime,
        session_id: str | None = None,
        pose_source: str | None = None,
        binary: bool = True,
        extra_caveats: tuple[str, ...] = (),
        extra_provenance: dict | None = None,
    ) -> ScanMetadata:
        if cloud.points.shape[0] == 0:
            raise ScanStoreError("no se guarda una nube vacía")
        scan_id = new_id("scan", capture_start)
        folder = self.scans_dir / scan_id
        folder.mkdir(parents=True, exist_ok=False)
        try:
            return self._write_scan(
                folder, scan_id, cloud, robot=robot, evidence_class=evidence_class,
                delivery_mode=delivery_mode, scan_context=scan_context,
                capture_start=capture_start, capture_end=capture_end, session_id=session_id,
                pose_source=pose_source, binary=binary, extra_caveats=extra_caveats,
                extra_provenance=extra_provenance,
            )
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise

    def _write_scan(
        self,
        folder: Path,
        scan_id: str,
        cloud: AccumulatedCloud,
        *,
        robot: RobotDescriptor,
        evidence_class: EvidenceClass,
        delivery_mode: DeliveryMode,
        scan_context: ScanContext,
        capture_start: datetime,
        capture_end: datetime,
        session_id: str | None,
        pose_source: str | None,
        binary: bool,
        extra_caveats: tuple[str, ...],
        extra_provenance: dict | None,
    ) -> ScanMetadata:
        ply_name = f"{scan_id}.ply"
        meta_name = f"{scan_id}.metadata.json"
        frame_id = cloud.frame_id or "unknown_robot_frame"
        demo = evidence_class is EvidenceClass.SYNTHETIC_TEST
        encoding = "binary_little_endian float32" if binary else "ascii float32"

        write_ply(
            folder / ply_name,
            cloud.points,
            binary=binary,
            comments=[
                f"terrainx scan_id {scan_id}",
                f"frame_id {frame_id}",
                "unit m (assumed, unverified)",
                f"point_type {cloud.point_type.value}",
                f"evidence_class {evidence_class.value}",
                f"delivery_mode {delivery_mode.value}",
                f"demo {'true' if demo else 'false'}",
            ],
        )
        ply_ref = FileRef(
            path=ply_name,
            sha256=sha256_file(folder / ply_name),
            bytes=(folder / ply_name).stat().st_size,
            format=f"PLY {encoding}",
        )

        pts = cloud.points
        first, last = cloud.first_info, cloud.last_info
        provenance = {
            "software": software_versions(),
            "adapter": robot.adapter,
            "session_id": session_id,
        }
        provenance.update(extra_provenance or {})
        meta = ScanMetadata(
            id=scan_id,
            scan_context=scan_context,
            frame_id=frame_id,
            # Hora de adquisición del primer frame usado (en replay, la original).
            timestamp_utc=first.host_received_utc if first else capture_start,
            point_count=int(pts.shape[0]),
            file_url=f"scans/{scan_id}/{ply_name}",
            pose_source=pose_source,
            robot=robot,
            body=robot.body,
            evidence_class=evidence_class,
            delivery_mode=delivery_mode,
            demo=demo,
            capture=CaptureInfo(
                start_utc=capture_start,
                end_utc=capture_end,
                duration_s=max(0.0, (capture_end - capture_start).total_seconds()),
                acquisition_first_utc=first.host_received_utc if first else None,
                acquisition_last_utc=last.host_received_utc if last else None,
                mode=cloud.mode,
                topic=cloud.topic,
                frames_received=cloud.frames_received,
                frames_used=cloud.frames_used,
                frames_rejected=cloud.frames_rejected,
                rejection_reasons=cloud.rejection_reasons,
                robot_stamp_first_raw=first.robot_stamp_raw if first else None,
                robot_stamp_last_raw=last.robot_stamp_raw if last else None,
                session_id=session_id,
            ),
            geometry=GeometryInfo(
                point_type=cloud.point_type,
                voxel_resolution_m=cloud.resolution,
                coordinate_rule=(
                    "punto = origin + índice_vóxel * resolution (fórmula del decodificador; "
                    "no documentado si el punto es esquina o centro del vóxel)"
                    if cloud.point_type is PointType.VOXEL_OCCUPANCY
                    else "coordenadas tal como venían en el archivo de origen"
                ),
                bounds_min=pts.min(axis=0).round(6).tolist(),
                bounds_max=pts.max(axis=0).round(6).tolist(),
                units_verification=Verification.UNVERIFIED,
                axes_verification=Verification.UNVERIFIED,
                axes_note=f"frame_id declarado por la fuente: {cloud.frame_id!r}",
            ),
            processing=ProcessingInfo(
                decoder=cloud.decoder or "none",
                validation=cloud.validation,
                deduplication=cloud.deduplication,
                filters_applied=[],
                ply_encoding=encoding,
            ),
            files={"ply": ply_ref},
            provenance=provenance,
            quality_flag=(
                "synthetic_test_data" if demo else "unverified_units_and_axes"
            ),
            caveats=_caveats(
                cloud,
                evidence_class=evidence_class,
                delivery_mode=delivery_mode,
                session_id=session_id,
                pose_source=pose_source,
            )
            + list(extra_caveats),
        )
        write_json_atomic(folder / meta_name, meta.model_dump(mode="json"))
        meta_hash = sha256_file(folder / meta_name)
        (folder / "SHA256SUMS").write_text(
            f"{ply_ref.sha256}  {ply_name}\n{meta_hash}  {meta_name}\n", encoding="ascii", newline="\n"
        )
        return meta

    # --------------------------------------------------------------- consultar
    def _folder(self, scan_id: str) -> Path:
        if not scan_id or any(sep in scan_id for sep in ("/", "\\", "..")):
            raise ScanStoreError(f"identificador de escaneo inválido: {scan_id!r}")
        folder = self.scans_dir / scan_id
        if not (folder / f"{scan_id}.metadata.json").is_file():
            raise ScanStoreError(f"no existe el escaneo {scan_id}")
        return folder

    def load_metadata(self, scan_id: str) -> ScanMetadata:
        folder = self._folder(scan_id)
        text = (folder / f"{scan_id}.metadata.json").read_text(encoding="utf-8")
        return ScanMetadata.model_validate_json(text)

    def load_points(self, scan_id: str) -> np.ndarray:
        meta = self.load_metadata(scan_id)
        return read_ply(self._folder(scan_id) / meta.files["ply"].path).points

    def list(self) -> list[ScanMetadata]:
        if not self.scans_dir.is_dir():
            return []
        out = []
        for folder in sorted(self.scans_dir.iterdir()):
            if (folder / f"{folder.name}.metadata.json").is_file():
                out.append(self.load_metadata(folder.name))
        return sorted(out, key=lambda m: m.timestamp_utc)

    def verify(self, scan_id: str) -> dict:
        """Recalcula los hashes. ok=False si el PLY o los metadatos se alteraron."""
        folder = self._folder(scan_id)
        meta = self.load_metadata(scan_id)
        result = {"scan_id": scan_id, "files": {}, "ok": True}
        ply_path = folder / meta.files["ply"].path
        actual = sha256_file(ply_path) if ply_path.is_file() else None
        result["files"]["ply"] = {"expected": meta.files["ply"].sha256, "actual": actual}
        if actual != meta.files["ply"].sha256:
            result["ok"] = False
        sums = folder / "SHA256SUMS"
        if sums.is_file():
            for line in sums.read_text(encoding="ascii").splitlines():
                expected, _, name = line.partition("  ")
                target = folder / name
                got = sha256_file(target) if target.is_file() else None
                result["files"][name] = {"expected": expected, "actual": got}
                if got != expected:
                    result["ok"] = False
        else:
            result["ok"] = False
            result["files"]["SHA256SUMS"] = {"expected": "present", "actual": None}
        return result

    def export(self, scan_id: str, dest_dir: Path) -> Path:
        """Copia la carpeta del escaneo a dest_dir tras verificar su integridad."""
        check = self.verify(scan_id)
        if not check["ok"]:
            raise ScanStoreError(f"integridad fallida en {scan_id}: {check['files']}")
        target = Path(dest_dir) / scan_id
        if target.exists():
            raise ScanStoreError(f"el destino ya existe: {target}")
        shutil.copytree(self._folder(scan_id), target)
        return target

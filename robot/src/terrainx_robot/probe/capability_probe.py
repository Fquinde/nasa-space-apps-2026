"""CapabilityProbe: qué puede hacer REALMENTE el robot (o la fuente) conectado.

Qué hace
    Conecta el adaptador, escucha durante una ventana sin capturar ni mover nada,
    y clasifica cada capacidad según lo OBSERVADO:
        available    -> el dato llegó durante la ventana
        unavailable  -> se buscó y no llegó
        declared     -> solo lo declara el operador (modelo, firmware)
        not_probed / disabled_by_policy -> fuera del alcance de Fase 1
    Si la conexión falla, el informe lo dice con su causa (overall_status=failed)
    en vez de inventar capacidades.
Salidas: CapabilityReport (JSON en <data_dir>/probes/).
"""

from __future__ import annotations

from typing import Any

from ..adapters.base import CaptureError, ConnectionFailed, RobotAdapter
from ..adapters.go2_topics import (
    LIDAR_STATE,
    MULTIPLE_STATE,
    ROBOT_POSE,
    TOPIC_PURPOSE,
)
from ..models import (
    CapabilityItem,
    CapabilityReport,
    CapabilityStatus,
    DeliveryMode,
    EvidenceClass,
    RobotStatus,
)
from ..util import new_id, software_versions, utc_now


def _window_text(window_s: float | None) -> str:
    return "toda la fuente reproducida" if window_s is None else f"{window_s} s"


def _topic_capability(name: str, topic: str, status: RobotStatus, window_s: float | None) -> CapabilityItem:
    seen = {t.topic: t for t in status.topics}
    obs = seen.get(topic)
    if obs:
        return CapabilityItem(
            name=name,
            status=CapabilityStatus.AVAILABLE,
            evidence=f"{obs.messages} mensajes en {topic} durante la ventana",
            details={"topic": topic, "rate_hz": obs.rate_hz, "payload_structure": obs.payload_structure},
        )
    return CapabilityItem(
        name=name,
        status=CapabilityStatus.UNAVAILABLE,
        evidence=f"ningún mensaje en {topic} en {_window_text(window_s)} ({TOPIC_PURPOSE.get(topic, '')})",
        details={"topic": topic},
    )


def _value_capability(name: str, value: Any, source: str) -> CapabilityItem:
    if value is None:
        return CapabilityItem(
            name=name, status=CapabilityStatus.UNAVAILABLE, evidence=f"no se recibió {source}"
        )
    return CapabilityItem(
        name=name,
        status=CapabilityStatus.AVAILABLE,
        evidence=f"recibido {source}",
        details={"last_value": value},
    )


def derive_capabilities(adapter: RobotAdapter, status: RobotStatus, window_s: float | None) -> list[CapabilityItem]:
    caps: list[CapabilityItem] = []
    frames = status.lidar_frames_received
    decoded_ok = frames - adapter.lidar_decode_errors
    info = adapter.last_lidar_frame_info
    if decoded_ok > 0 and info is not None:
        lidar_topics = [t for t in status.topics if t.topic == info.topic]
        caps.append(
            CapabilityItem(
                name="lidar_point_data",
                status=CapabilityStatus.AVAILABLE,
                evidence=f"{decoded_ok} de {frames} frames LiDAR decodificados",
                details={
                    "topic": info.topic,
                    "rate_hz": lidar_topics[0].rate_hz if lidar_topics else None,
                    "point_type": info.point_type.value,
                    "frame_id": info.frame_id,
                    "resolution": info.resolution,
                    "width": info.width,
                    "src_size": info.src_size,
                    "last_point_count": info.point_count,
                    "extra_metadata_fields": sorted(info.extra_fields.keys()),
                    "units": "ASUMIDAS en metros (no declaradas): verificar físicamente",
                },
            )
        )
    elif frames > 0:
        caps.append(
            CapabilityItem(
                name="lidar_point_data",
                status=CapabilityStatus.UNAVAILABLE,
                evidence=f"llegaron {frames} frames pero ninguno se pudo decodificar",
                details={"last_error": adapter.last_decode_error},
            )
        )
    else:
        caps.append(
            CapabilityItem(
                name="lidar_point_data",
                status=CapabilityStatus.UNAVAILABLE,
                evidence=f"no llegó ningún frame LiDAR en {_window_text(window_s)}",
            )
        )
    caps.append(
        CapabilityItem(
            name="lidar_raw_returns",
            status=CapabilityStatus.UNKNOWN,
            evidence=(
                "Por WebRTC (librería 2.2.0) el LiDAR llega como mapa de vóxeles ocupados; "
                "no se ha observado una nube de retornos crudos por esta vía. Otras vías "
                "(p. ej. SDK oficial en modelos EDU) no se han evaluado."
            ),
        )
    )
    tel = status.telemetry
    caps.append(_value_capability("battery_soc", tel.battery_soc_pct, "bms_state.soc (lowstate)"))
    caps.append(
        _value_capability(
            "imu_attitude", tel.imu_rpy_raw or tel.imu_quaternion_raw, "imu_state (lowstate/sportmodestate)"
        )
    )
    caps.append(_value_capability("odometry_position", tel.position_raw, "position (sportmodestate)"))
    caps.append(_topic_capability("robot_pose_topic", ROBOT_POSE, status, window_s))
    caps.append(_topic_capability("lidar_state_topic", LIDAR_STATE, status, window_s))
    caps.append(_topic_capability("config_state_topic", MULTIPLE_STATE, status, window_s))
    caps.append(
        CapabilityItem(
            name="video_stream",
            status=CapabilityStatus.NOT_PROBED,
            evidence="la librería ofrece vídeo, pero queda fuera del alcance de Fase 1",
        )
    )
    caps.append(
        CapabilityItem(
            name="motion_control",
            status=CapabilityStatus.DISABLED_BY_POLICY,
            evidence="Fase 1 es de solo lectura: el guardián bloquea toda orden de movimiento",
        )
    )
    desc = adapter.descriptor
    caps.append(
        CapabilityItem(
            name="model_variant",
            status=CapabilityStatus.DECLARED if desc.model_variant != "unknown" else CapabilityStatus.UNKNOWN,
            evidence="declarado por el operador" if desc.model_variant != "unknown" else "no declarado",
            details={"value": desc.model_variant},
        )
    )
    caps.append(
        CapabilityItem(
            name="firmware_version",
            status=CapabilityStatus.DECLARED if desc.firmware_version else CapabilityStatus.UNKNOWN,
            evidence="declarado por el operador" if desc.firmware_version else "no declarado",
            details={"value": desc.firmware_version},
        )
    )
    return caps


def _overall(caps: list[CapabilityItem]) -> str:
    """ok = llegaron LiDAR decodificable Y alguna telemetría; si falta algo, degraded."""
    lidar_ok = any(c.name == "lidar_point_data" and c.status is CapabilityStatus.AVAILABLE for c in caps)
    telemetry_ok = any(
        c.status is CapabilityStatus.AVAILABLE
        for c in caps
        if c.name in ("battery_soc", "imu_attitude", "odometry_position", "robot_pose_topic")
    )
    return "ok" if lidar_ok and telemetry_ok else "degraded"


def _base_caveats(adapter: RobotAdapter) -> list[str]:
    notes = [
        "'available' significa que el dato se OBSERVÓ durante la ventana; sus unidades y "
        "ejes siguen sin verificar físicamente.",
        "Modelo y firmware no se obtienen por las vías usadas en Fase 1: solo constan si el "
        "operador los declara.",
    ]
    if adapter.descriptor.delivery_mode is DeliveryMode.REPLAY:
        notes.insert(0, "Informe en modo REPLAY: describe la fuente grabada, no un robot conectado.")
    if adapter.evidence_class is EvidenceClass.SYNTHETIC_TEST:
        notes.insert(0, "FUENTE SINTÉTICA: las capacidades son simuladas, no del robot.")
    return notes


async def run_probe(
    adapter: RobotAdapter,
    *,
    window_s: float | None = 10.0,
    network_preflight: dict | None = None,
    record_session: bool = False,
) -> CapabilityReport:
    created = utc_now()
    connection: dict[str, Any] = {
        "adapter": adapter.adapter_name,
        "delivery_mode": adapter.descriptor.delivery_mode.value,
    }
    try:
        await adapter.connect()
    except ConnectionFailed as exc:
        connection.update(exc.as_dict())
        status = adapter.get_status()
        return CapabilityReport(
            report_id=new_id("probe", created),
            created_utc=created,
            robot=adapter.descriptor,
            evidence_class=adapter.evidence_class,
            overall_status="failed",
            observation_window_s=None,
            connection=connection,
            network_preflight=network_preflight,
            capabilities=[],
            topics=status.topics,
            software=software_versions(),
            caveats=_base_caveats(adapter) + ["La conexión falló: no se ha observado ninguna capacidad."],
        )
    session_id = None
    try:
        try:
            info = await adapter.observe(window_s, record_session=record_session, notes="sondeo de capacidades")
            session_id = info.session_id if info else None
        except CaptureError as exc:
            # p. ej. pérdida de conexión a mitad de ventana: se informa, no se oculta.
            connection["window_error"] = str(exc)
        status = adapter.get_status()
    finally:
        extra = getattr(adapter, "connection_info", None)
        if extra:
            connection.update(extra)
        await adapter.disconnect()
    connection["connection_state_at_end_of_window"] = status.connection_state.value
    connection["last_error"] = status.last_error
    connection["readonly_guard"] = status.readonly_guard
    if session_id:
        connection["recorded_session_id"] = session_id
    caps = derive_capabilities(adapter, status, window_s)
    return CapabilityReport(
        report_id=new_id("probe", created),
        created_utc=created,
        robot=adapter.descriptor,
        evidence_class=adapter.evidence_class,
        overall_status=_overall(caps),
        observation_window_s=window_s,
        connection=connection,
        network_preflight=network_preflight,
        capabilities=caps,
        topics=status.topics,
        software=software_versions(),
        caveats=_base_caveats(adapter),
    )

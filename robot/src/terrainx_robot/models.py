"""Modelos de datos del módulo de robótica (propuesta de contrato 1.1-draft).

Qué hace: define con Pydantic v2 los registros que produce el módulo:
  - ScanMetadata      -> escaneo LiDAR exportado (amplía RobotScan 1.0 del dossier §6.1)
  - CapabilityReport  -> qué puede hacer REALMENTE el robot conectado
  - RobotStatus       -> estado de conexión/captura + telemetría resumida
  - SessionInfo       -> sesión de datos crudos grabada para replay
Los campos del contrato 1.0 conservan nombre y significado. Los añadidos están
marcados como "1.1-draft" y deben aprobarlos Ciencia y Plataforma
(ver contracts/README.md).

Unidades: coordenadas en metros (ASUMIDO para el Go2, ver Verification);
tiempos en UTC.
Errores: pydantic.ValidationError si un registro viola las reglas de procedencia.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CONTRACT_VERSION = "1.1-draft"


class _Model(BaseModel):
    # json_schema_serialization_defaults_required: en el esquema exportado, todo campo
    # que el JSON emitido contiene siempre (aunque tenga valor por defecto) es obligatorio.
    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)


# --------------------------------------------------------------------------- enums


class Body(str, Enum):
    """Cuerpo planetario donde se ADQUIRIÓ físicamente el dato."""

    EARTH = "earth"
    MOON = "moon"
    MARS = "mars"


class EvidenceClass(str, Enum):
    """Origen del dato (eje 1 de procedencia)."""

    ROBOT_MEASURED = "robot_measured"  # medido físicamente por un robot
    ORBITAL_NASA = "orbital_nasa"  # producto científico NASA (lo produce Ciencia)
    DERIVED = "derived"  # cálculo sobre otros datos
    SYNTHETIC_TEST = "synthetic_test"  # generado por software para pruebas


class DeliveryMode(str, Enum):
    """Vía por la que llegó el dato (eje 2 de procedencia)."""

    LIVE = "live"
    REPLAY = "replay"
    EMULATED_LINK = "emulated_link"


class ScanContext(str, Enum):
    """Contexto de la adquisición (dossier §6.2: 'controlled_test')."""

    CONTROLLED_TEST = "controlled_test"
    FIELD_CAMPAIGN = "field_campaign"
    SYNTHETIC = "synthetic"


class ConnectionState(str, Enum):
    """Estado de la conexión. Valores tomados del dossier §6.4."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY_READONLY = "ready_readonly"
    DEGRADED = "degraded"
    FAILED = "failed"


class CaptureState(str, Enum):
    """Estado de la captura. Valores tomados del dossier §6.4 (+ 'idle')."""

    IDLE = "idle"
    CAPTURING = "capturing"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class CapabilityStatus(str, Enum):
    AVAILABLE = "available"  # observado durante el sondeo
    UNAVAILABLE = "unavailable"  # se buscó y no se observó
    DECLARED = "declared"  # lo declara el operador, no se ha medido
    NOT_PROBED = "not_probed"  # fuera del alcance de esta fase
    DISABLED_BY_POLICY = "disabled_by_policy"  # deshabilitado a propósito (p. ej. movimiento)
    UNKNOWN = "unknown"


class Verification(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"


class PointType(str, Enum):
    """Qué representa cada punto de la nube."""

    VOXEL_OCCUPANCY = "voxel_occupancy"  # vóxel ocupado de un mapa (Go2 vía WebRTC)
    RAW_RETURNS = "raw_returns"  # retorno crudo del sensor
    UNKNOWN = "unknown"


# --------------------------------------------------------------------- descriptores


class RobotDescriptor(_Model):
    robot_id: str
    platform: str = "unitree_go2"
    body: Body = Body.EARTH
    model_variant: Literal["AIR", "PRO", "EDU", "unknown"] = "unknown"
    model_variant_source: Literal["declared_by_operator", "unknown"] = "unknown"
    firmware_version: str | None = None
    firmware_source: Literal["declared_by_operator", "unknown"] = "unknown"
    adapter: str
    delivery_mode: DeliveryMode


class LidarFrameInfo(_Model):
    """Metadatos de UN mensaje LiDAR, tal como llegó (sin los puntos)."""

    seq: int
    topic: str
    host_received_utc: datetime
    robot_stamp_raw: float | int | str | None = None
    frame_id: str | None = None
    origin: list[float] | None = None
    resolution: float | None = None
    width: list[int] | None = None
    src_size: int | None = None
    point_count: int = 0
    point_type: PointType = PointType.UNKNOWN
    decoder: str
    decode_error: str | None = None
    extra_fields: dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------- telemetría


class TopicObservation(_Model):
    topic: str
    messages: int
    first_seen_utc: datetime | None = None
    last_seen_utc: datetime | None = None
    rate_hz: float | None = None
    payload_structure: dict[str, str] = Field(default_factory=dict)


class TelemetrySnapshot(_Model):
    """Telemetría resumida. Un valor ausente es None, NUNCA 0."""

    battery_soc_pct: float | None = None
    power_v: float | None = None
    imu_rpy_raw: list[float] | None = None
    imu_quaternion_raw: list[float] | None = None
    position_raw: list[float] | None = None
    velocity_raw: list[float] | None = None
    body_height_m: float | None = None
    source_topics: list[str] = Field(default_factory=list)
    updated_utc: datetime | None = None
    units_note: str = (
        "Nombres de campo tomados de los ejemplos oficiales de unitree_webrtc_connect "
        "(lowstate, sportmodestate). Las unidades de los campos *_raw no están "
        "documentadas: pendiente de verificación física."
    )


class RobotStatus(_Model):
    schema_version: str = f"terrainx.robot.status/{CONTRACT_VERSION}"
    robot: RobotDescriptor
    connection_state: ConnectionState
    capture_state: CaptureState
    read_only: bool = True
    evidence_class: EvidenceClass
    last_error: str | None = None
    lidar_frames_received: int = 0
    last_lidar_utc: datetime | None = None
    telemetry: TelemetrySnapshot
    topics: list[TopicObservation] = Field(default_factory=list)
    readonly_guard: dict[str, int] = Field(default_factory=dict)
    updated_utc: datetime


# ---------------------------------------------------------------- capacidades


class CapabilityItem(_Model):
    name: str
    status: CapabilityStatus
    evidence: str
    details: dict[str, Any] = Field(default_factory=dict)


class CapabilityReport(_Model):
    schema_version: str = f"terrainx.robot.capability_report/{CONTRACT_VERSION}"
    report_id: str
    created_utc: datetime
    robot: RobotDescriptor
    evidence_class: EvidenceClass
    overall_status: Literal["ok", "degraded", "failed"]
    observation_window_s: float | None  # None = se reprodujo la fuente completa (replay)
    connection: dict[str, Any]
    network_preflight: dict[str, Any] | None = None
    capabilities: list[CapabilityItem]
    topics: list[TopicObservation]
    software: dict[str, str | None]
    caveats: list[str]


# -------------------------------------------------------------------- escaneos


class FileRef(_Model):
    path: str  # relativo a la carpeta del escaneo
    sha256: str
    bytes: int
    format: str


class CaptureInfo(_Model):
    # Ventana de la operación de captura (en replay: cuándo se reprodujo).
    start_utc: datetime
    end_utc: datetime
    duration_s: float
    # Momento de llegada al PC de los datos usados (en replay: la hora ORIGINAL).
    acquisition_first_utc: datetime | None = None
    acquisition_last_utc: datetime | None = None
    mode: Literal["accumulate", "last", "single_file"]
    topic: str | None = None
    frames_received: int
    frames_used: int
    frames_rejected: int
    rejection_reasons: dict[str, int] = Field(default_factory=dict)
    robot_stamp_first_raw: float | int | str | None = None
    robot_stamp_last_raw: float | int | str | None = None
    session_id: str | None = None


class GeometryInfo(_Model):
    point_type: PointType
    voxel_resolution_m: float | None = None
    coordinate_rule: str
    bounds_min: list[float] | None = None
    bounds_max: list[float] | None = None
    units_verification: Verification = Verification.UNVERIFIED
    axes_verification: Verification = Verification.UNVERIFIED
    axes_note: str


class ProcessingInfo(_Model):
    decoder: str
    validation: dict[str, Any]
    deduplication: dict[str, Any]
    filters_applied: list[str] = Field(default_factory=list)
    ply_encoding: str


class RegistrationStub(_Model):
    """Registro espacial (dossier §6.2). En Fase 1 siempre 'local_only'."""

    status: Literal["local_only"] = "local_only"
    method: Literal["none"] = "none"
    target_frame: str | None = None
    transform_4x4: list[list[float]] | None = None
    rmse_m: float | None = None


class ScanMetadata(_Model):
    schema_version: str = f"terrainx.robot.scan/{CONTRACT_VERSION}"
    # --- Contrato 1.0 (dossier §6.1, RobotScan) ---
    id: str
    scan_context: ScanContext
    frame_id: str
    unit: Literal["m"] = "m"
    timestamp_utc: datetime
    point_count: int
    file_url: str
    pose_source: str | None = None
    source_record_id: str | None = None
    registration: RegistrationStub = Field(default_factory=RegistrationStub)
    # --- Propuesta 1.1-draft ---
    robot: RobotDescriptor
    body: Body
    evidence_class: EvidenceClass
    delivery_mode: DeliveryMode
    demo: bool
    capture: CaptureInfo
    geometry: GeometryInfo
    processing: ProcessingInfo
    files: dict[str, FileRef]
    provenance: dict[str, Any]
    quality_flag: str
    caveats: list[str]

    @model_validator(mode="after")
    def _provenance_rules(self) -> "ScanMetadata":
        # Regla del dossier §6.5: los datos de prueba se marcan demo=true.
        if self.evidence_class is EvidenceClass.SYNTHETIC_TEST and not self.demo:
            raise ValueError("evidence_class=synthetic_test exige demo=true")
        if self.evidence_class is EvidenceClass.ROBOT_MEASURED and self.demo:
            raise ValueError("una medición robótica real no puede marcarse demo=true")
        # Hoy no hay robots desplegados en la Luna ni en Marte: un ensayo
        # terrestre (aunque emule un enlace planetario) es body=earth.
        if self.evidence_class is EvidenceClass.ROBOT_MEASURED and self.body is not Body.EARTH:
            raise ValueError(
                "robot_measured solo admite body=earth hasta que exista un robot "
                "desplegado en otro cuerpo (cambio de contrato)"
            )
        if self.point_count < 0:
            raise ValueError("point_count negativo")
        return self


# --------------------------------------------------------------------- sesiones


class SessionInfo(_Model):
    schema_version: str = f"terrainx.robot.session/{CONTRACT_VERSION}"
    session_id: str
    created_utc: datetime
    closed_utc: datetime | None = None
    robot: RobotDescriptor
    evidence_class: EvidenceClass
    scan_context: ScanContext
    demo: bool
    generator: str
    software: dict[str, str | None]
    record_count: int = 0
    lidar_records: int = 0
    json_records: int = 0
    messages_file: str = "messages.jsonl"
    messages_sha256: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _demo_rule(self) -> "SessionInfo":
        if self.evidence_class is EvidenceClass.SYNTHETIC_TEST and not self.demo:
            raise ValueError("una sesión synthetic_test exige demo=true")
        if self.evidence_class is EvidenceClass.ROBOT_MEASURED and self.demo:
            raise ValueError("una sesión con datos reales no puede marcarse demo=true")
        return self

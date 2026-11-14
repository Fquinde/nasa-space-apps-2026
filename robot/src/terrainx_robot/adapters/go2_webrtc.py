"""Adaptador del Unitree Go2 físico por WebRTC (unitree_webrtc_connect 2.2.0).

Qué hace (Fase 1, SOLO LECTURA)
    1. Conecta por LocalAP o LocalSTA (Remote está prohibido por configuración).
    2. Instala el guardián de solo lectura sobre el canal de datos: ningún
       mensaje fuera de la lista blanca puede salir hacia el robot.
    3. Sustituye el decodificador LiDAR de la librería por uno "passthrough"
       que entrega el payload comprimido ORIGINAL; nosotros decodificamos con
       voxel_codec (mismo algoritmo que "native") y podemos grabar los bytes tal
       como llegaron.
    4. Se suscribe a topics de lectura (ver go2_topics.DEFAULT_READONLY_TOPICS).
    5. Si TERRAINX_GO2_ENABLE_LIDAR=true, activa el flujo LiDAR igual que el
       ejemplo oficial: disableTrafficSaving(True) + "on" en rt/utlidar/switch.
       NO se envía "off" al desconectar: no sabemos si el robot usa el LiDAR para
       sus propias protecciones y no alteramos su estado más de lo necesario.

Qué NO hace
    No envía órdenes de movimiento, no usa la nube de Unitree, no lee ni
    imprime la clave AES (se redacta de cualquier mensaje de error).

Pendiente de comprobar con el robot real: conexión en Windows, frecuencia y
contenido real de cada topic, unidades y ejes (docs/VERIFICACION_FISICA.md).
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable

from ..config import Settings
from ..models import ConnectionState, DeliveryMode, EvidenceClass, ScanContext
from ..storage.scan_store import ScanStore
from ..util import utc_now
from .base import CaptureError, ConnectionFailed, RobotAdapter
from .go2_topics import (
    DEFAULT_READONLY_TOPICS,
    EXPLORATORY_TOPICS,
    LIDAR_SWITCH,
    VERIFIED_LIBRARY_VERSION,
)
from .readonly_guard import ReadOnlyChannelGuard

log = logging.getLogger(__name__)

PASSTHROUGH_KEY = "terrainx_raw_payload"

# (nombre de la excepción en la librería, código, sugerencia para el operador)
_ERROR_TABLE: tuple[tuple[str, str, str], ...] = (
    ("AesKeyRequiredError", "aes_key_required",
     "El firmware exige la clave AES-128 propia del robot (según la librería: Go2 >= 1.1.15). "
     "Guárdela en un archivo FUERA del repositorio y apunte TERRAINX_GO2_AES_KEY_FILE a él."),
    ("AesKeyRejectedError", "aes_key_rejected",
     "El robot rechazó la clave AES configurada: compruebe que corresponde a ESTE robot."),
    ("RobotBusyError", "robot_busy",
     "Otro cliente WebRTC está conectado (normalmente la app oficial de Unitree). "
     "El robot admite un solo cliente: ciérrelo e inténtelo de nuevo."),
    ("LocalSignalingPortError", "signaling_unreachable",
     "No responden los puertos de señalización 9991/8081: compruebe IP, red Wi-Fi, "
     "cortafuegos y que el robot está encendido."),
    ("NoSdpAnswerError", "no_sdp_answer",
     "El robot no devolvió respuesta SDP: compruebe enlace Wi-Fi y que no haya otro cliente conectándose."),
    ("DataChannelTimeoutError", "datachannel_timeout",
     "El canal de datos no se abrió a tiempo: enlace lento o inestable, o cortafuegos bloqueando UDP."),
)


class PassthroughLidarDecoder:
    """Sustituto del decodificador de la librería: devuelve el payload intacto.

    La librería 2.2.0 llama a ``datachannel.decoder.decode(binario, metadatos)``
    para los mensajes binarios de topics que contienen 'utlidar' y coloca el
    resultado en ``message['data']['data']``.
    """

    def decode(self, compressed_data: bytes, metadata: dict) -> dict:
        return {PASSTHROUGH_KEY: bytes(compressed_data)}

    def get_decoder_name(self) -> str:
        return "TerrainXPassthrough"


def _import_library() -> Any:
    try:
        import unitree_webrtc_connect as lib
    except ImportError as exc:
        raise ConnectionFailed(
            "library_missing",
            f"unitree_webrtc_connect no está instalada: {exc}",
            'Instale el extra del Go2:  .\\.venv\\Scripts\\python.exe -m pip install -e ".[go2]"',
        ) from exc
    return lib


def redact(text: str, secret: str | None) -> str:
    """Elimina la clave (completa o su prefijo de 8 caracteres) de un texto."""
    if not secret:
        return text
    for fragment in {secret, secret[:8]}:
        for variant in {fragment, fragment.lower(), fragment.upper()}:
            text = text.replace(variant, "<clave-redactada>")
    return text


class Go2WebRTCAdapter(RobotAdapter):
    adapter_name = "go2_webrtc"

    def __init__(
        self,
        settings: Settings,
        store: ScanStore,
        *,
        scan_context: ScanContext = ScanContext.CONTROLLED_TEST,
        topics: tuple[str, ...] | None = None,
        explore: bool = False,
        library_loader: Callable[[], Any] | None = None,
    ) -> None:
        if scan_context is ScanContext.SYNTHETIC:
            raise ValueError("el robot real no puede producir scan_context='synthetic'")
        super().__init__(
            descriptor=settings.robot_descriptor(adapter=self.adapter_name, delivery_mode=DeliveryMode.LIVE),
            store=store,
            evidence_class=EvidenceClass.ROBOT_MEASURED,
            scan_context=scan_context,
        )
        self._settings = settings
        self._topics = tuple(topics or DEFAULT_READONLY_TOPICS) + (EXPLORATORY_TOPICS if explore else ())
        self._load_library = library_loader or _import_library
        self._conn: Any = None
        self._guard: ReadOnlyChannelGuard | None = None
        self._closing = False
        self.connection_info: dict[str, Any] = {}

    # ------------------------------------------------------------------ errores
    def _secret(self) -> str | None:
        key = self._settings.go2.aes_key
        return key.get_secret_value() if key else None

    def _map_error(self, lib: Any, exc: BaseException) -> ConnectionFailed:
        for name, code, hint in _ERROR_TABLE:
            cls = getattr(lib, name, None)
            if isinstance(cls, type) and isinstance(exc, cls):
                # AesKeyRejectedError incluye un fragmento de la clave: no usamos su texto.
                message = name if code == "aes_key_rejected" else f"{name}: {exc}"
                return ConnectionFailed(code, redact(message, self._secret()), hint)
        if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
            return ConnectionFailed(
                "connect_timeout",
                f"sin conexión tras {self._settings.go2.connect_timeout_s} s",
                "Compruebe que el PC está en la misma red que el robot y que la IP es correcta.",
            )
        if isinstance(exc, ValueError) and "network" in str(exc).lower():
            return ConnectionFailed(
                "discovery_failed",
                redact(str(exc), self._secret()),
                "El descubrimiento por número de serie falló: configure TERRAINX_GO2_IP.",
            )
        return ConnectionFailed(
            "connection_error", redact(f"{type(exc).__name__}: {exc}", self._secret()), None
        )

    # ------------------------------------------------------------- ciclo de vida
    async def _open(self) -> None:
        go2 = self._settings.go2
        if go2.method == "LocalSTA" and not (go2.ip or go2.serial):
            raise ConnectionFailed(
                "missing_address",
                "LocalSTA necesita TERRAINX_GO2_IP o TERRAINX_GO2_SERIAL",
                "Configure la IP del robot en robot/.env (vea .env.example).",
            )
        lib = self._load_library()
        lib_version = getattr(lib, "__version__", None)
        try:
            import importlib.metadata

            lib_version = importlib.metadata.version("unitree_webrtc_connect")
        except Exception:
            pass
        self.connection_info = {
            "method": go2.method,
            "address": go2.ip or ("serial configurado" if go2.serial else "192.168.12.1 (LocalAP)"),
            "aes_key": "configurada" if go2.aes_key else "no configurada",
            "library_version": lib_version,
            "library_version_verified": lib_version == VERIFIED_LIBRARY_VERSION,
            "subscribed_topics": list(self._topics),
        }
        if lib_version != VERIFIED_LIBRARY_VERSION:
            log.warning(
                "unitree_webrtc_connect %s instalada; el adaptador se verificó con %s",
                lib_version, VERIFIED_LIBRARY_VERSION,
            )

        kwargs: dict[str, Any] = {}
        if go2.method == "LocalSTA":
            if go2.ip:
                kwargs["ip"] = go2.ip
            else:
                kwargs["serialNumber"] = go2.serial
        if go2.aes_key:
            kwargs["aes_128_key"] = go2.aes_key.get_secret_value()
        method = getattr(lib.WebRTCConnectionMethod, go2.method)
        self._closing = False
        conn = lib.UnitreeWebRTCConnection(method, **kwargs)
        self._conn = conn
        try:
            await asyncio.wait_for(conn.connect(), timeout=go2.connect_timeout_s)
        except BaseException as exc:
            await self._safe_disconnect()
            raise self._map_error(lib, exc) from exc

        datachannel = conn.datachannel
        # 1) Guardián: a partir de aquí ningún mensaje no permitido sale del PC.
        self._guard = ReadOnlyChannelGuard(datachannel.channel)
        # 2) Payload LiDAR original, sin decodificar por la librería.
        datachannel.decoder = PassthroughLidarDecoder()
        # 3) Vigilancia de la conexión (pérdida de Wi-Fi, cierre remoto).
        pc = conn.pc

        @pc.on("connectionstatechange")
        def _on_connection_state() -> None:
            state = getattr(pc, "connectionState", None)
            if state in ("failed", "closed") and not self._closing:
                self._set_connection_state(
                    ConnectionState.DISCONNECTED, f"conexión WebRTC perdida (estado: {state})"
                )

        # 4) Suscripciones de lectura.
        for topic in self._topics:
            datachannel.pub_sub.subscribe(topic, self._make_callback(topic))
        # 5) Activación del flujo LiDAR (no es una orden de movimiento).
        if go2.enable_lidar:
            try:
                ok = await asyncio.wait_for(datachannel.disableTrafficSaving(True), timeout=5)
                self.connection_info["disable_traffic_saving"] = "ok" if ok else "respuesta distinta de ok"
            except Exception as exc:  # no bloquea: se informa en el sondeo
                self.connection_info["disable_traffic_saving"] = f"sin confirmar ({type(exc).__name__})"
            datachannel.pub_sub.publish_without_callback(LIDAR_SWITCH, "on")
            self.connection_info["lidar_switch"] = "on enviado"
        else:
            self.connection_info["lidar_switch"] = "no enviado (TERRAINX_GO2_ENABLE_LIDAR=false)"

    async def _safe_disconnect(self) -> None:
        conn, self._conn = self._conn, None
        if conn is None:
            return
        self._closing = True
        try:
            await asyncio.wait_for(conn.disconnect(), timeout=10)
        except Exception as exc:
            log.warning("Error al cerrar la conexión: %s", redact(str(exc), self._secret()))

    async def _close(self) -> None:
        await self._safe_disconnect()

    async def _run_window(self, duration_s: float | None) -> None:
        if duration_s is None or duration_s <= 0:
            raise CaptureError("con el robot real hay que indicar una duración > 0 s")
        deadline = asyncio.get_running_loop().time() + duration_s
        while True:
            if self.connection_state is ConnectionState.DISCONNECTED:
                raise CaptureError(f"conexión perdida durante la ventana: {self.last_error}")
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                return
            await asyncio.sleep(min(0.25, remaining))

    # ------------------------------------------------------------- mensajes
    def _make_callback(self, topic: str) -> Callable[[Any], None]:
        def callback(message: Any) -> None:
            try:
                self._on_message(topic, message)
            except Exception:  # un mensaje raro no debe tumbar el canal
                log.exception("Error procesando un mensaje de %s", topic)

        return callback

    def _on_message(self, topic: str, message: Any) -> None:
        host_utc = utc_now()
        data = message.get("data") if isinstance(message, dict) else None
        inner = data.get("data") if isinstance(data, dict) else None
        if isinstance(inner, dict) and PASSTHROUGH_KEY in inner:
            meta = {k: v for k, v in data.items() if k != "data"}
            self._ingest_lidar_message(topic=topic, meta=meta, raw=inner[PASSTHROUGH_KEY], host_utc=host_utc)
            return
        if isinstance(data, str):
            try:
                data = json.loads(data)  # p. ej. rt/multiplestate llega como texto JSON
            except json.JSONDecodeError:
                pass
        self._ingest_json(topic=topic, data=data, host_utc=host_utc)

    # ------------------------------------------------------------- ganchos
    def _guard_counters(self) -> dict[str, int]:
        return self._guard.counters() if self._guard else {}

    def _extra_provenance(self) -> dict:
        return {"connection": dict(self.connection_info)}

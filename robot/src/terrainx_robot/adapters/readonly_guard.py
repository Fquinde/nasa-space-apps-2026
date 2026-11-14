"""Guardián de solo lectura del canal de datos WebRTC.

Qué hace
    Envuelve ``channel.send`` del canal de datos (el punto por el que pasa TODO
    mensaje saliente de unitree_webrtc_connect 2.2.0) y deja pasar únicamente
    una lista blanca:
      - subscribe / unsubscribe / heartbeat / validation (protocolo y lectura)
      - rtc_inner_req con req_type de mantenimiento del enlace
        (disable_traffic_saving, public_network_status, respuesta a rtt_probe)
      - msg al topic rt/utlidar/switch con "on"/"off" (activar el flujo LiDAR)
    Todo lo demás (peticiones "req" a rt/api/sport/request, rt/lowcmd,
    rt/wirelesscontroller, vídeo/audio, subida de archivos...) se BLOQUEA y
    lanza ReadOnlyViolation sin llegar a enviarse.

Por qué aquí
    Es una defensa en profundidad: el código de Fase 1 no contiene órdenes de
    movimiento, pero si alguien las añadiera por error, no saldrían del PC.
    No sustituye a la parada de emergencia física del robot.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from typing import Any, Callable

from .go2_topics import LIDAR_SWITCH

log = logging.getLogger(__name__)

ALWAYS_ALLOWED_TYPES = frozenset({"subscribe", "unsubscribe", "heartbeat", "validation"})
ALLOWED_INNER_REQ = frozenset(
    {"disable_traffic_saving", "public_network_status", "rtt_probe_send_from_mechine"}
)
ALLOWED_MSG = {LIDAR_SWITCH: frozenset({"on", "off"})}


class ReadOnlyViolation(PermissionError):
    """Se intentó enviar al robot un mensaje fuera de la lista blanca de solo lectura."""


def check_outgoing(message: Any) -> tuple[bool, str]:
    """Decide si un mensaje saliente está permitido. Devuelve (permitido, motivo)."""
    if not isinstance(message, str):
        return False, "mensaje no textual bloqueado"
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return False, "mensaje no JSON bloqueado"
    if not isinstance(payload, dict):
        return False, "mensaje JSON sin objeto raíz bloqueado"
    msg_type = payload.get("type")
    topic = payload.get("topic", "")
    if msg_type in ALWAYS_ALLOWED_TYPES:
        return True, str(msg_type)
    if msg_type == "rtc_inner_req":
        data = payload.get("data")
        req_type = data.get("req_type") if isinstance(data, dict) else None
        if req_type in ALLOWED_INNER_REQ:
            return True, f"rtc_inner_req:{req_type}"
        return False, f"rtc_inner_req req_type={req_type!r} bloqueado (modo solo lectura)"
    if msg_type == "msg" and topic in ALLOWED_MSG:
        if payload.get("data") in ALLOWED_MSG[topic]:
            return True, f"msg:{topic}"
        return False, f"msg a {topic} con dato no permitido"
    return False, f"type={msg_type!r} topic={topic!r} bloqueado (modo solo lectura)"


class ReadOnlyChannelGuard:
    def __init__(self, channel: Any, on_block: Callable[[str], None] | None = None) -> None:
        self._channel = channel
        self._original_send = channel.send
        self._on_block = on_block
        self.allowed: Counter[str] = Counter()
        self.blocked: Counter[str] = Counter()
        channel.send = self._guarded_send  # sombrea el método de la instancia

    def _guarded_send(self, message: Any) -> Any:
        ok, reason = check_outgoing(message)
        if not ok:
            self.blocked[reason] += 1
            log.warning("Mensaje saliente BLOQUEADO por el guardián de solo lectura: %s", reason)
            if self._on_block:
                self._on_block(reason)
            raise ReadOnlyViolation(reason)
        self.allowed[reason] += 1
        return self._original_send(message)

    def counters(self) -> dict[str, int]:
        out = {f"allowed:{k}": v for k, v in self.allowed.items()}
        out.update({f"blocked:{k}": v for k, v in self.blocked.items()})
        out["blocked_total"] = sum(self.blocked.values())
        return out

    def uninstall(self) -> None:
        self._channel.send = self._original_send

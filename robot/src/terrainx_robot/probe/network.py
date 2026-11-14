"""Comprobación de red previa a la conexión (solo lectura).

Qué hace
    Intenta abrir una conexión TCP (sin enviar datos) a los dos puertos de
    señalización que usa unitree_webrtc_connect 2.2.0:
        9991 -> flujo 'con_notify' (según la librería: firmware Go2 posterior a 1.1.11;
                desde 1.1.15 exige clave AES por dispositivo)
        8081 -> flujo legado '/offer' (firmware Go2 anterior a 1.1.11)
    Es solo una PISTA sobre la generación de firmware, no una lectura de versión.
"""

from __future__ import annotations

import socket

SIGNALING_PORTS = (9991, 8081)
LOCAL_AP_IP = "192.168.12.1"  # IP fija que usa la librería en modo LocalAP


def tcp_port_open(ip: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def signaling_preflight(ip: str, timeout: float = 1.5) -> dict:
    ports = {port: tcp_port_open(ip, port, timeout) for port in SIGNALING_PORTS}
    if ports[9991]:
        hint = (
            "puerto 9991 abierto (con_notify): firmware posterior a 1.1.11 según la librería; "
            "si es >= 1.1.15 hará falta la clave AES del robot"
        )
    elif ports[8081]:
        hint = "solo 8081 abierto (/offer legado): firmware anterior a 1.1.11 según la librería"
    else:
        hint = "ningún puerto de señalización accesible: revise IP, red, cortafuegos o encendido"
    return {
        "ip": ip,
        "port_9991_open": ports[9991],
        "port_8081_open": ports[8081],
        "firmware_generation_hint": hint,
        "method": "conexión TCP sin envío de datos",
    }

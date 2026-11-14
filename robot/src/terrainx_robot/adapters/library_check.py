"""Comprobación de la API REAL de unitree_webrtc_connect instalada (sin robot).

Qué hace
    Antes de conectar con el Go2, verifica que la versión instalada mantiene
    todo aquello de lo que depende Go2WebRTCAdapter:
      - versión instalada vs. versión verificada (2.2.0)
      - clases y excepciones públicas usadas
      - nombres de topic (RTC_TOPIC)
      - el gancho del decodificador LiDAR (datachannel.decoder.decode)
      - equivalencia bit a bit entre nuestro voxel_codec y su decodificador native
Salidas: lista de (comprobación, ok, detalle).
"""

from __future__ import annotations

import importlib.metadata
import inspect

import numpy as np

from .go2_topics import VERIFIED_LIBRARY_VERSION, check_against_library

REQUIRED_EXPORTS = (
    "UnitreeWebRTCConnection",
    "WebRTCConnectionMethod",
    "WebRTCDataChannel",
    "AesKeyRequiredError",
    "AesKeyRejectedError",
    "RobotBusyError",
    "LocalSignalingPortError",
    "NoSdpAnswerError",
    "DataChannelTimeoutError",
)


def run_library_checks() -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []
    try:
        version = importlib.metadata.version("unitree_webrtc_connect")
    except importlib.metadata.PackageNotFoundError:
        return [("instalada", False, 'no instalada: pip install -e ".[go2]"')]
    results.append(
        (
            "versión",
            version == VERIFIED_LIBRARY_VERSION,
            f"instalada {version}; verificada {VERIFIED_LIBRARY_VERSION}",
        )
    )
    import unitree_webrtc_connect as lib

    missing = [name for name in REQUIRED_EXPORTS if not hasattr(lib, name)]
    results.append(("exportaciones públicas", not missing, "faltan: " + ", ".join(missing) if missing else "ok"))

    methods = getattr(lib, "WebRTCConnectionMethod", None)
    has_methods = methods is not None and all(hasattr(methods, m) for m in ("LocalAP", "LocalSTA"))
    results.append(("métodos LocalAP/LocalSTA", has_methods, "ok" if has_methods else "no encontrados"))

    problems = check_against_library()
    results.append(("topics RTC_TOPIC", not problems, "; ".join(problems) if problems else "ok"))

    dc_cls = lib.WebRTCDataChannel
    try:
        source = inspect.getsource(dc_cls.deal_array_buffer_for_lidar) + inspect.getsource(
            dc_cls.deal_array_buffer_for_normal
        )
        hook_ok = "self.decoder.decode(" in source
    except (OSError, TypeError, AttributeError) as exc:
        hook_ok, source = False, str(exc)
    results.append(
        ("gancho del decodificador LiDAR", hook_ok, "datachannel.decoder.decode(binario, metadatos)" if hook_ok else "cambió")
    )

    # Equivalencia con el decodificador native de la librería sobre datos sintéticos.
    try:
        from unitree_webrtc_connect.lidar.lidar_decoder_native import LidarDecoder as NativeDecoder

        from ..fixtures.synthetic import generate_frames
        from ..lidar.voxel_codec import decode_voxel_map

        frame = generate_frames(1, seed=3)[0]
        theirs = NativeDecoder().decode(frame.payload, frame.meta)["points"]
        ours = decode_voxel_map(
            frame.payload, frame.meta["src_size"], frame.meta["origin"], frame.meta["resolution"]
        ).points
        same = theirs.shape == ours.shape and np.array_equal(theirs, ours)
        detail = f"{ours.shape[0]} puntos idénticos" if same else f"difieren: {theirs.shape} vs {ours.shape}"
    except Exception as exc:  # noqa: BLE001 - se informa, no se oculta
        same, detail = False, f"{type(exc).__name__}: {exc}"
    results.append(("decodificador native == voxel_codec", same, detail))
    return results

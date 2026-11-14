"""Go2WebRTCAdapter con una librería FALSA (sin robot): conexión, errores, guardián.

Los datos LiDAR de estos tests son sintéticos y se escriben en carpetas
temporales que pytest borra; nunca se presentan como mediciones.
"""

import asyncio
import json
import struct
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from conftest import run
from terrainx_robot.adapters.base import CaptureError, ConnectionFailed
from terrainx_robot.adapters.go2_topics import DEFAULT_READONLY_TOPICS, LIDAR_SWITCH, LIDAR_VOXEL_COMPRESSED
from terrainx_robot.adapters.go2_webrtc import Go2WebRTCAdapter, PassthroughLidarDecoder
from terrainx_robot.adapters.readonly_guard import ReadOnlyViolation
from terrainx_robot.config import Go2Settings, Settings
from terrainx_robot.fixtures.synthetic import generate_frames
from terrainx_robot.models import ConnectionState, DeliveryMode, EvidenceClass, ScanContext

KEY = "0123456789abcdef0123456789abcdef"


# ----------------------------------------------------------- librería falsa
class FakeChannel:
    readyState = "open"

    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


class FakePubSub:
    def __init__(self, channel):
        self.channel = channel
        self.subscriptions = {}

    def subscribe(self, topic, callback=None):
        self.subscriptions[topic] = callback
        self.channel.send(json.dumps({"type": "subscribe", "topic": topic}))

    def publish_without_callback(self, topic, data=None, msg_type=None):
        self.channel.send(json.dumps({"type": msg_type or "msg", "topic": topic, "data": data}))


class FakeDataChannel:
    def __init__(self):
        self.channel = FakeChannel()
        self.pub_sub = FakePubSub(self.channel)
        self.decoder = "decodificador de la librería"

    async def disableTrafficSaving(self, switch):
        self.pub_sub.publish_without_callback(
            "", {"req_type": "disable_traffic_saving", "instruction": "on"}, "rtc_inner_req"
        )
        return True


class FakePC:
    def __init__(self):
        self.connectionState = "connected"
        self.handlers = {}

    def on(self, event):
        def deco(fn):
            self.handlers.setdefault(event, []).append(fn)
            return fn

        return deco

    def fire(self, state):
        self.connectionState = state
        for fn in self.handlers.get("connectionstatechange", []):
            fn()


class FakeErrors:
    class AesKeyRequiredError(RuntimeError):
        pass

    class AesKeyRejectedError(RuntimeError):
        pass

    class RobotBusyError(RuntimeError):
        pass

    class LocalSignalingPortError(RuntimeError):
        pass

    class NoSdpAnswerError(RuntimeError):
        pass

    class DataChannelTimeoutError(RuntimeError):
        pass


def make_lib(connect_error=None, connect_delay=0.0):
    instances = []

    class FakeConn:
        def __init__(self, method, **kwargs):
            self.method, self.kwargs = method, kwargs
            self.datachannel = FakeDataChannel()
            self.pc = FakePC()
            self.disconnected = False
            instances.append(self)

        async def connect(self):
            if connect_delay:
                await asyncio.sleep(connect_delay)
            if connect_error:
                raise connect_error

        async def disconnect(self):
            self.disconnected = True

    lib = SimpleNamespace(
        WebRTCConnectionMethod=SimpleNamespace(LocalAP="AP", LocalSTA="STA"),
        UnitreeWebRTCConnection=FakeConn,
        **{k: v for k, v in vars(FakeErrors).items() if not k.startswith("_")},
    )
    lib.instances = instances
    return lib


def settings(tmp_path, **go2):
    base = dict(method="LocalSTA", ip="192.168.8.181", connect_timeout_s=2.0)
    base.update(go2)
    return Settings(data_dir=tmp_path / "data", robot_id="go2-test", go2=Go2Settings(**base))


def adapter_for(tmp_path, store, lib, **go2):
    return Go2WebRTCAdapter(settings(tmp_path, **go2), store, library_loader=lambda: lib)


# -------------------------------------------------------------------- tests
def test_conexion_instala_guardian_suscripciones_y_lidar(tmp_path, store):
    lib = make_lib()
    adapter = adapter_for(tmp_path, store, lib, aes_key=SecretStr(KEY), aes_key_source="file")
    run(adapter.connect())
    conn = lib.instances[0]
    assert adapter.connection_state is ConnectionState.READY_READONLY
    assert conn.method == "STA" and conn.kwargs == {"ip": "192.168.8.181", "aes_128_key": KEY}
    assert isinstance(conn.datachannel.decoder, PassthroughLidarDecoder)
    assert set(conn.datachannel.pub_sub.subscriptions) == set(DEFAULT_READONLY_TOPICS)
    sent = [json.loads(m) for m in conn.datachannel.channel.sent]
    assert {"type": "msg", "topic": LIDAR_SWITCH, "data": "on"} in sent
    assert adapter.descriptor.delivery_mode is DeliveryMode.LIVE
    assert adapter.evidence_class is EvidenceClass.ROBOT_MEASURED
    assert KEY not in json.dumps(adapter.connection_info)
    run(adapter.disconnect())
    assert conn.disconnected and adapter.connection_state is ConnectionState.DISCONNECTED


def test_guardian_bloquea_ordenes_de_movimiento(tmp_path, store):
    lib = make_lib()
    adapter = adapter_for(tmp_path, store, lib)
    run(adapter.connect())
    pub_sub = lib.instances[0].datachannel.pub_sub
    with pytest.raises(ReadOnlyViolation):
        pub_sub.publish_without_callback("rt/api/sport/request", {"header": {"identity": {"api_id": 1008}}}, "req")
    assert adapter.get_status().readonly_guard["blocked_total"] == 1


def test_captura_con_mensajes_inyectados(tmp_path, store):
    lib = make_lib()
    adapter = adapter_for(tmp_path, store, lib)
    frames = generate_frames(3, seed=1)

    async def go():
        await adapter.connect()
        callback = lib.instances[0].datachannel.pub_sub.subscriptions[LIDAR_VOXEL_COMPRESSED]
        lowstate = lib.instances[0].datachannel.pub_sub.subscriptions["rt/lf/lowstate"]

        async def inject():
            await asyncio.sleep(0.05)
            for sf in frames:  # misma forma que entrega la librería con nuestro decoder
                callback({"type": "msg", "topic": LIDAR_VOXEL_COMPRESSED,
                          "data": {**sf.meta, "data": PassthroughLidarDecoder().decode(sf.payload, sf.meta)}})
            lowstate({"type": "msg", "topic": "rt/lf/lowstate", "data": {"bms_state": {"soc": 77}}})

        task = asyncio.create_task(inject())
        meta = await adapter.capture(0.3)
        await task
        status = adapter.get_status()
        await adapter.disconnect()
        return meta, status

    meta, status = run(go())
    union = {tuple(r) for f in frames for r in f.indices.tolist()}
    assert meta.point_count == len(union) and meta.capture.frames_used == 3
    assert meta.delivery_mode is DeliveryMode.LIVE and meta.demo is False
    assert status.telemetry.battery_soc_pct == 77.0
    assert meta.provenance["connection"]["method"] == "LocalSTA"


@pytest.mark.parametrize(
    "error, code",
    [
        (FakeErrors.RobotBusyError("busy"), "robot_busy"),
        (FakeErrors.AesKeyRequiredError("need key"), "aes_key_required"),
        (FakeErrors.LocalSignalingPortError("no ports"), "signaling_unreachable"),
        (FakeErrors.DataChannelTimeoutError("slow"), "datachannel_timeout"),
        (RuntimeError("otra cosa"), "connection_error"),
    ],
)
def test_errores_de_conexion_traducidos(tmp_path, store, error, code):
    lib = make_lib(connect_error=error)
    adapter = adapter_for(tmp_path, store, lib)
    with pytest.raises(ConnectionFailed) as exc:
        run(adapter.connect())
    assert exc.value.code == code and exc.value.hint is not None or code == "connection_error"
    assert adapter.connection_state is ConnectionState.FAILED
    assert lib.instances[0].disconnected  # se libera la conexión a medias


def test_la_clave_nunca_aparece_en_errores(tmp_path, store):
    rejected = make_lib(connect_error=FakeErrors.AesKeyRejectedError(f"key={KEY[:8]}..."))
    adapter = adapter_for(tmp_path, store, rejected, aes_key=SecretStr(KEY), aes_key_source="file")
    with pytest.raises(ConnectionFailed) as exc:
        run(adapter.connect())
    assert KEY[:8] not in str(exc.value) and exc.value.code == "aes_key_rejected"

    leaky = make_lib(connect_error=RuntimeError(f"fallo con {KEY} y {KEY[:8].upper()}"))
    adapter = adapter_for(tmp_path, store, leaky, aes_key=SecretStr(KEY), aes_key_source="file")
    with pytest.raises(ConnectionFailed) as exc:
        run(adapter.connect())
    assert KEY[:8].lower() not in str(exc.value).lower()


def test_timeout_de_conexion(tmp_path, store):
    lib = make_lib(connect_delay=5)
    adapter = adapter_for(tmp_path, store, lib, connect_timeout_s=0.1)
    with pytest.raises(ConnectionFailed) as exc:
        run(adapter.connect())
    assert exc.value.code == "connect_timeout"


def test_perdida_de_conexion_durante_la_captura(tmp_path, store):
    lib = make_lib()
    adapter = adapter_for(tmp_path, store, lib)

    async def go():
        await adapter.connect()
        asyncio.get_running_loop().call_later(0.1, lib.instances[0].pc.fire, "failed")
        with pytest.raises(CaptureError, match="conexión perdida"):
            await adapter.capture(5)

    run(go())
    assert adapter.connection_state is ConnectionState.DISCONNECTED
    assert "perdida" in adapter.last_error


def test_configuracion_invalida(tmp_path, store):
    lib = make_lib()
    with pytest.raises(ConnectionFailed) as exc:
        run(adapter_for(tmp_path, store, lib, ip=None).connect())
    assert exc.value.code == "missing_address" and not lib.instances
    with pytest.raises(ValueError):
        Go2WebRTCAdapter(settings(tmp_path), store, scan_context=ScanContext.SYNTHETIC)
    with pytest.raises(CaptureError):
        run(adapter_for(tmp_path, store, lib)._run_window(None))


@pytest.mark.go2lib
def test_parser_binario_real_de_la_libreria_con_nuestro_decoder(tmp_path, store):
    """Construye el mensaje binario como lo envía el robot y lo pasa por el parser REAL
    de unitree_webrtc_connect (deal_array_buffer) con nuestro decoder passthrough."""
    lib = pytest.importorskip("unitree_webrtc_connect")
    sf = generate_frames(1, seed=4)[0]
    header = json.dumps({"type": "msg", "topic": LIDAR_VOXEL_COMPRESSED, "data": sf.meta}).encode()
    buffer = struct.pack("<HH", 2, 0) + struct.pack("<I", len(header)) + b"\x00" * 4 + header + sf.payload
    dc = lib.WebRTCDataChannel.__new__(lib.WebRTCDataChannel)
    dc.decoder = PassthroughLidarDecoder()
    parsed = dc.deal_array_buffer(buffer)

    adapter = adapter_for(tmp_path, store, make_lib())
    adapter._on_message(LIDAR_VOXEL_COMPRESSED, parsed)
    info = adapter.last_lidar_frame_info
    assert info.decode_error is None
    assert info.point_count == len(sf.indices)
    assert info.frame_id == sf.meta["frame_id"] and info.resolution == sf.meta["resolution"]

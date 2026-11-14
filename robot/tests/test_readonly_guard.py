import json

import pytest

from conftest import run
from terrainx_robot.adapters.readonly_guard import ReadOnlyChannelGuard, ReadOnlyViolation, check_outgoing


class FakeChannel:
    readyState = "open"

    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


def _msg(**kw):
    return json.dumps(kw)


ALLOWED = [
    _msg(type="subscribe", topic="rt/lf/lowstate"),
    _msg(type="unsubscribe", topic="rt/lf/lowstate"),
    _msg(type="heartbeat", topic="", data={"timeInNum": 1}),
    _msg(type="validation", topic="", data="abc"),
    _msg(type="rtc_inner_req", topic="", data={"req_type": "disable_traffic_saving", "instruction": "on"}),
    _msg(type="rtc_inner_req", topic="", data={"req_type": "public_network_status", "uuid": "x"}),
    _msg(type="rtc_inner_req", topic="", data={"req_type": "rtt_probe_send_from_mechine"}),
    _msg(type="msg", topic="rt/utlidar/switch", data="on"),
]

BLOCKED = [
    _msg(type="req", topic="rt/api/sport/request", data={"header": {"identity": {"id": 1, "api_id": 1008}}}),
    _msg(type="req", topic="rt/api/obstacles_avoid/request", data={}),
    _msg(type="msg", topic="rt/lowcmd", data={}),
    _msg(type="msg", topic="rt/wirelesscontroller", data={"lx": 1}),
    _msg(type="msg", topic="rt/utlidar/switch", data="reboot"),
    _msg(type="vid", topic="", data="on"),
    _msg(type="aud", topic="", data="on"),
    _msg(type="rtc_inner_req", topic="", data={"req_type": "push_static_file"}),
    "no es json",
    b"\x00binario",
    json.dumps([1, 2]),
]


@pytest.mark.parametrize("message", ALLOWED)
def test_lista_blanca(message):
    ok, _ = check_outgoing(message)
    assert ok


@pytest.mark.parametrize("message", BLOCKED)
def test_bloqueado_y_no_enviado(message):
    channel = FakeChannel()
    guard = ReadOnlyChannelGuard(channel)
    with pytest.raises(ReadOnlyViolation):
        channel.send(message)
    assert channel.sent == []
    assert guard.counters()["blocked_total"] == 1


def test_permitidos_pasan_y_se_cuentan():
    channel = FakeChannel()
    guard = ReadOnlyChannelGuard(channel)
    for m in ALLOWED:
        channel.send(m)
    assert channel.sent == ALLOWED
    assert guard.counters()["blocked_total"] == 0
    guard.uninstall()
    channel.send("cualquier cosa")  # tras desinstalar vuelve el send original
    assert channel.sent[-1] == "cualquier cosa"


@pytest.mark.go2lib
def test_todas_las_ordenes_sport_de_la_libreria_se_bloquean():
    """Recorre SPORT_CMD de la versión instalada usando el pub/sub REAL de la librería."""
    lib = pytest.importorskip("unitree_webrtc_connect")
    channel = FakeChannel()
    ReadOnlyChannelGuard(channel)
    pub_sub = lib.WebRTCDataChannelPubSub(channel)

    async def go():
        for name, api_id in lib.SPORT_CMD.items():
            with pytest.raises(ReadOnlyViolation):
                await pub_sub.publish_request_new(lib.RTC_TOPIC["SPORT_MOD"], {"api_id": api_id})
        with pytest.raises(ReadOnlyViolation):
            pub_sub.publish_without_callback(lib.RTC_TOPIC["LOW_CMD"], {"x": 1})
        with pytest.raises(ReadOnlyViolation):
            pub_sub.publish_without_callback(lib.RTC_TOPIC["WIRELESS_CONTROLLER"], {"lx": 0.5})
        pub_sub.subscribe(lib.RTC_TOPIC["LOW_STATE"], lambda m: None)  # lectura: permitido

    run(go())
    assert len(channel.sent) == 1 and json.loads(channel.sent[0])["type"] == "subscribe"

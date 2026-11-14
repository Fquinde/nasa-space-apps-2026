"""Línea de comandos del módulo de robótica TERRAIN-X (Fase 1).

Uso (PowerShell, desde la carpeta robot/):
    .\\.venv\\Scripts\\python.exe -m terrainx_robot --help

Comandos
    info            configuración efectiva (sin secretos) y versiones
    check-library   verifica la API de unitree_webrtc_connect instalada
    demo-session    genera una sesión SINTÉTICA para probar sin robot
    probe           sondeo de capacidades (go2 o replay)
    record          graba una sesión cruda del robot para replay posterior
    capture         captura LiDAR -> PLY + metadatos JSON + SHA-256
    list-scans      lista escaneos guardados
    verify-scan     recalcula los SHA-256 de un escaneo
    export-scan     copia un escaneo verificado a otra carpeta
    inspect         estadística descriptiva de un escaneo o PLY
    export-schemas  exporta los JSON Schema de la propuesta de contrato

Códigos de salida: 0 correcto · 1 error · 2 resultado degradado.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .adapters.base import CaptureError, ConnectionFailed, RobotAdapter
from .config import ConfigError, Settings, load_settings
from .models import (
    CapabilityReport,
    EvidenceClass,
    RobotStatus,
    ScanContext,
    ScanMetadata,
    SessionInfo,
)
from .storage.scan_store import ScanStore, ScanStoreError
from .storage.session_log import SessionError
from .util import software_versions, write_json_atomic

log = logging.getLogger("terrainx_robot")


# ------------------------------------------------------------------ utilidades
def _setup_console() -> None:
    # La consola de Windows y las redirecciones pueden no ser UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def _setup_logging(data_dir: Path, verbose: bool) -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.INFO if verbose else logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root.addHandler(console)
    try:
        (data_dir / "logs").mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(data_dir / "logs" / "terrainx_robot.log", encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(file_handler)
    except OSError as exc:
        print(f"Aviso: no se pudo abrir el log en {data_dir}: {exc}", file=sys.stderr)


def _print_json(data) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _latest_session(data_dir: Path) -> Path:
    sessions = data_dir / "sessions"
    candidates = [p for p in sessions.glob("*") if (p / "session.json").is_file()] if sessions.is_dir() else []
    if not candidates:
        raise SessionError(
            f"no hay sesiones en {sessions}. Genere una con: python -m terrainx_robot demo-session"
        )
    return max(candidates, key=lambda p: (p / "session.json").stat().st_mtime)


def _build_adapter(args, settings: Settings, store: ScanStore) -> RobotAdapter:
    if args.source == "go2":
        from .adapters.go2_webrtc import Go2WebRTCAdapter

        return Go2WebRTCAdapter(
            settings,
            store,
            scan_context=ScanContext(getattr(args, "context", "controlled_test")),
            explore=getattr(args, "explore", False),
        )
    from .adapters.replay import ReplayAdapter

    if not args.input:
        raise ValueError("--source replay necesita --input <sesión | archivo.ply | latest>")
    source = _latest_session(settings.data_dir) if args.input == "latest" else Path(args.input)
    evidence = EvidenceClass(args.evidence_class) if getattr(args, "evidence_class", None) else None
    return ReplayAdapter(source, store, speed=args.speed, evidence_class=evidence)


def _add_source_args(parser: argparse.ArgumentParser, *, replay: bool = True) -> None:
    choices = ["go2", "replay"] if replay else ["go2"]
    parser.add_argument("--source", choices=choices, required=True, help="go2 = robot real; replay = offline")
    if replay:
        parser.add_argument("--input", help="replay: carpeta de sesión, archivo .ply o 'latest'")
        parser.add_argument("--speed", type=float, default=0.0, help="replay: 0 = lo más rápido; 1 = tiempo real")
        parser.add_argument(
            "--evidence-class",
            choices=[e.value for e in EvidenceClass if e is not EvidenceClass.ORBITAL_NASA],
            help="replay de un PLY SIN metadatos: origen declarado por el operador",
        )
    parser.add_argument(
        "--context",
        choices=[ScanContext.CONTROLLED_TEST.value, ScanContext.FIELD_CAMPAIGN.value],
        default=ScanContext.CONTROLLED_TEST.value,
        help="go2: contexto de la adquisición (por defecto controlled_test)",
    )
    parser.add_argument("--explore", action="store_true", help="go2: suscribirse también a topics exploratorios")


# ------------------------------------------------------------------- comandos
def cmd_info(args, settings: Settings) -> int:
    _print_json({"terrainx_robot": __version__, "settings": settings.describe(), "software": software_versions()})
    return 0


def cmd_check_library(args, settings: Settings) -> int:
    from .adapters.library_check import run_library_checks

    results = run_library_checks()
    for name, ok, detail in results:
        print(f"[{'OK ' if ok else 'FALLO'}] {name}: {detail}")
    return 0 if all(ok for _, ok, _ in results) else 1


def cmd_demo_session(args, settings: Settings) -> int:
    from .fixtures.synthetic import write_synthetic_session

    info: SessionInfo = write_synthetic_session(settings.data_dir / "sessions", n_frames=args.frames, seed=args.seed)
    print(f"Sesión SINTÉTICA creada (evidence_class=synthetic_test, demo=true): {info.session_id}")
    print(f"  carpeta : {settings.data_dir / 'sessions' / info.session_id}")
    print(f"  mensajes: {info.record_count} ({info.lidar_records} LiDAR, {info.json_records} telemetría)")
    return 0


async def _probe(args, settings: Settings, store: ScanStore) -> CapabilityReport:
    from .probe.capability_probe import run_probe
    from .probe.network import LOCAL_AP_IP, signaling_preflight

    preflight = None
    if args.source == "go2" and not args.skip_preflight:
        ip = settings.go2.ip or (LOCAL_AP_IP if settings.go2.method == "LocalAP" else None)
        preflight = signaling_preflight(ip) if ip else {"skipped": "sin IP configurada (descubrimiento por serie)"}
    adapter = _build_adapter(args, settings, store)
    # go2: 10 s por defecto. replay: sin --window se reproduce la fuente completa (None).
    window = args.window if args.window is not None else (10.0 if args.source == "go2" else None)
    return await run_probe(
        adapter, window_s=window, network_preflight=preflight, record_session=args.record_session
    )


def cmd_probe(args, settings: Settings) -> int:
    store = ScanStore(settings.data_dir)
    report = asyncio.run(_probe(args, settings, store))
    path = settings.data_dir / "probes" / f"{report.report_id}.json"
    write_json_atomic(path, report.model_dump(mode="json"))
    print(f"Sondeo {report.overall_status.upper()} · fuente={args.source} · evidencia={report.evidence_class.value}")
    if report.connection.get("error_code"):
        print(f"  error   : {report.connection['error_code']} - {report.connection.get('error_message')}")
        if report.connection.get("hint"):
            print(f"  sugerencia: {report.connection['hint']}")
    for cap in report.capabilities:
        print(f"  {cap.status.value:<19} {cap.name:<20} {cap.evidence}")
    print(f"Informe: {path}")
    return {"ok": 0, "degraded": 2, "failed": 1}[report.overall_status]


def cmd_record(args, settings: Settings) -> int:
    store = ScanStore(settings.data_dir)
    adapter = _build_adapter(args, settings, store)

    async def run() -> SessionInfo | None:
        await adapter.connect()
        try:
            return await adapter.observe(args.duration, record_session=True, notes=args.notes)
        finally:
            await adapter.disconnect()

    info = asyncio.run(run())
    print(f"Sesión grabada ({info.evidence_class.value}): {info.session_id}")
    print(f"  mensajes: {info.record_count} ({info.lidar_records} LiDAR, {info.json_records} telemetría)")
    print(f"  carpeta : {settings.data_dir / 'sessions' / info.session_id}")
    return 0 if info.lidar_records else 2


def cmd_capture(args, settings: Settings) -> int:
    store = ScanStore(settings.data_dir)
    adapter = _build_adapter(args, settings, store)
    duration = args.duration
    if args.source == "go2" and (duration is None or duration <= 0):
        raise ValueError("--duration (s) es obligatorio con el robot real")

    async def run() -> tuple[ScanMetadata, RobotStatus]:
        await adapter.connect()
        try:
            meta = await adapter.capture(
                duration, mode=args.mode, record_session=args.record_session, binary_ply=not args.ascii
            )
            return meta, adapter.get_status()
        finally:
            await adapter.disconnect()

    meta, status = asyncio.run(run())
    folder = settings.data_dir / "scans" / meta.id
    print(f"Escaneo guardado: {meta.id}")
    print(f"  evidencia : {meta.evidence_class.value} · entrega={meta.delivery_mode.value} · demo={meta.demo}")
    print(f"  puntos    : {meta.point_count} ({meta.geometry.point_type.value}, frame '{meta.frame_id}')")
    print(f"  frames    : {meta.capture.frames_used} usados de {meta.capture.frames_received}"
          + (f" · rechazos {meta.capture.rejection_reasons}" if meta.capture.rejection_reasons else ""))
    print(f"  PLY       : {folder / meta.files['ply'].path}")
    print(f"  metadatos : {folder / (meta.id + '.metadata.json')}")
    print(f"  SHA-256   : {meta.files['ply'].sha256}")
    print(f"  calidad   : {meta.quality_flag}")
    if status.readonly_guard.get("blocked_total"):
        print(f"  AVISO     : el guardián bloqueó {status.readonly_guard['blocked_total']} mensajes salientes")
    return 0


def cmd_list_scans(args, settings: Settings) -> int:
    scans = ScanStore(settings.data_dir).list()
    if args.json:
        _print_json([m.model_dump(mode="json") for m in scans])
        return 0
    if not scans:
        print(f"No hay escaneos en {settings.data_dir / 'scans'}")
    for m in scans:
        print(f"{m.id}  {m.point_count:>8} pts  {m.evidence_class.value:<15} {m.delivery_mode.value:<7} "
              f"{m.scan_context.value:<16} demo={str(m.demo).lower()}")
    return 0


def cmd_verify_scan(args, settings: Settings) -> int:
    result = ScanStore(settings.data_dir).verify(args.scan_id)
    _print_json(result)
    return 0 if result["ok"] else 1


def cmd_export_scan(args, settings: Settings) -> int:
    target = ScanStore(settings.data_dir).export(args.scan_id, Path(args.dest))
    print(f"Exportado (integridad verificada): {target}")
    return 0


def cmd_inspect(args, settings: Settings) -> int:
    from .lidar.describe import describe_points
    from .storage.ply import read_ply

    target = Path(args.target)
    resolution = None
    if target.suffix.lower() == ".ply" and target.is_file():
        points = read_ply(target).points
        sidecar = target.with_name(target.stem + ".metadata.json")
        if sidecar.is_file():
            resolution = ScanMetadata.model_validate_json(sidecar.read_text(encoding="utf-8")).geometry.voxel_resolution_m
    else:
        store = ScanStore(settings.data_dir)
        meta = store.load_metadata(args.target)
        points = store.load_points(args.target)
        resolution = meta.geometry.voxel_resolution_m
    _print_json(describe_points(points, resolution))
    return 0


def cmd_export_schemas(args, settings: Settings) -> int:
    out = Path(args.out)
    for name, model in (
        ("scan_metadata", ScanMetadata),
        ("capability_report", CapabilityReport),
        ("robot_status", RobotStatus),
        ("session_info", SessionInfo),
    ):
        # Modo "serialization": describe el JSON que PRODUCE el módulo (lo que consumen los demás).
        write_json_atomic(out / f"{name}.schema.json", model.model_json_schema(mode="serialization"))
        print(f"  {out / (name + '.schema.json')}")
    return 0


# --------------------------------------------------------------------- parser
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="terrainx_robot",
        description="TERRAIN-X · robótica · Fase 1 (Unitree Go2, solo lectura)",
    )
    parser.add_argument("--data-dir", type=Path, help="carpeta de datos (por defecto robot/runtime)")
    parser.add_argument("--env-file", type=Path, help="archivo .env (por defecto robot/.env)")
    parser.add_argument("-v", "--verbose", action="store_true", help="log detallado en consola")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info", help="configuración efectiva y versiones")
    sub.add_parser("check-library", help="verifica la API de unitree_webrtc_connect instalada")

    p = sub.add_parser("demo-session", help="genera una sesión SINTÉTICA")
    p.add_argument("--frames", type=int, default=8)
    p.add_argument("--seed", type=int, default=7)

    p = sub.add_parser("probe", help="sondeo de capacidades")
    _add_source_args(p)
    p.add_argument("--window", type=float, help="segundos de escucha (go2: 10 por defecto; replay: toda la fuente)")
    p.add_argument("--record-session", action="store_true", help="grabar lo recibido como sesión")
    p.add_argument("--skip-preflight", action="store_true", help="go2: no comprobar puertos 9991/8081")

    p = sub.add_parser("record", help="graba una sesión cruda del robot")
    _add_source_args(p, replay=False)
    p.add_argument("--duration", type=float, required=True)
    p.add_argument("--notes", help="descripción de la escena/ensayo")

    p = sub.add_parser("capture", help="captura LiDAR -> PLY + metadatos")
    _add_source_args(p)
    p.add_argument("--duration", type=float, help="segundos (obligatorio con go2; replay: toda la fuente)")
    p.add_argument("--mode", choices=["accumulate", "last"], default="accumulate")
    p.add_argument("--record-session", action="store_true", help="grabar también los datos crudos")
    p.add_argument("--ascii", action="store_true", help="PLY ascii en vez de binario")

    p = sub.add_parser("list-scans", help="lista escaneos")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("verify-scan", help="verifica SHA-256 de un escaneo")
    p.add_argument("scan_id")
    p = sub.add_parser("export-scan", help="exporta un escaneo verificado")
    p.add_argument("scan_id")
    p.add_argument("--dest", required=True)
    p = sub.add_parser("inspect", help="estadística de un escaneo (id) o archivo .ply")
    p.add_argument("target")
    p = sub.add_parser("export-schemas", help="exporta JSON Schema de los modelos")
    p.add_argument("--out", default="contracts/schemas")
    return parser


COMMANDS = {
    "info": cmd_info,
    "check-library": cmd_check_library,
    "demo-session": cmd_demo_session,
    "probe": cmd_probe,
    "record": cmd_record,
    "capture": cmd_capture,
    "list-scans": cmd_list_scans,
    "verify-scan": cmd_verify_scan,
    "export-scan": cmd_export_scan,
    "inspect": cmd_inspect,
    "export-schemas": cmd_export_schemas,
}


def main(argv: list[str] | None = None) -> int:
    _setup_console()
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(args.env_file, data_dir_override=args.data_dir)
    except ConfigError as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        return 1
    _setup_logging(settings.data_dir, args.verbose)
    try:
        return COMMANDS[args.command](args, settings)
    except ConnectionFailed as exc:
        print(f"Conexión fallida [{exc.code}]: {exc}", file=sys.stderr)
        if exc.hint:
            print(f"Sugerencia: {exc.hint}", file=sys.stderr)
        return 1
    except (CaptureError, ScanStoreError, SessionError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrumpido por el usuario.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

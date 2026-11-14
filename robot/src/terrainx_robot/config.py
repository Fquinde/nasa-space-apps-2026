"""Configuración local del módulo: variables de entorno y archivo .env opcional.

Reglas de seguridad aplicadas aquí (Fase 1):
  - El método Remote (nube de Unitree / servidor TURN) se rechaza: el robot no se
    expone a Internet (dossier §5.4).
  - La clave AES-128 del robot NUNCA se lee de .env ni de un archivo situado
    dentro del repositorio; solo de un archivo externo o de una variable de
    entorno del proceso. Se guarda como SecretStr (no aparece en repr ni logs).
  - Modelo y firmware solo constan si el operador los declara; si no, "unknown".

Errores: ConfigError con un mensaje que nunca incluye la clave.
"""

from __future__ import annotations

import ipaddress
import os
import re
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import BaseModel, SecretStr

from .models import DeliveryMode, RobotDescriptor

# src/terrainx_robot/config.py -> parents[2] = carpeta robot/
ROBOT_ROOT = Path(__file__).resolve().parents[2]
_AES_RE = re.compile(r"^[0-9a-fA-F]{32}$")
_TRUE = {"1", "true", "yes", "si", "sí", "on"}
_FALSE = {"0", "false", "no", "off"}


class ConfigError(ValueError):
    pass


class Go2Settings(BaseModel):
    method: Literal["LocalAP", "LocalSTA"] = "LocalSTA"
    ip: str | None = None
    serial: str | None = None
    aes_key: SecretStr | None = None
    aes_key_source: Literal["none", "file", "environment"] = "none"
    connect_timeout_s: float = 30.0
    enable_lidar: bool = True


class Settings(BaseModel):
    data_dir: Path
    robot_id: str
    model_variant: Literal["AIR", "PRO", "EDU", "unknown"] = "unknown"
    firmware_version: str | None = None
    go2: Go2Settings
    env_file_loaded: str | None = None

    def describe(self) -> dict:
        """Resumen apto para mostrar o registrar: la clave solo como presente/ausente."""
        return {
            "data_dir": str(self.data_dir),
            "robot_id": self.robot_id,
            "model_variant": self.model_variant,
            "firmware_version": self.firmware_version,
            "go2_method": self.go2.method,
            "go2_ip": self.go2.ip,
            "go2_serial_configured": bool(self.go2.serial),
            "go2_aes_key": "configurada" if self.go2.aes_key else "no configurada",
            "go2_aes_key_source": self.go2.aes_key_source,
            "go2_connect_timeout_s": self.go2.connect_timeout_s,
            "go2_enable_lidar": self.go2.enable_lidar,
            "env_file_loaded": self.env_file_loaded,
        }

    def robot_descriptor(self, *, adapter: str, delivery_mode: DeliveryMode) -> RobotDescriptor:
        return RobotDescriptor(
            robot_id=self.robot_id,
            platform="unitree_go2",
            model_variant=self.model_variant,
            model_variant_source="declared_by_operator" if self.model_variant != "unknown" else "unknown",
            firmware_version=self.firmware_version,
            firmware_source="declared_by_operator" if self.firmware_version else "unknown",
            adapter=adapter,
            delivery_mode=delivery_mode,
        )


def find_repo_root(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def _parse_bool(name: str, value: str | None, default: bool) -> bool:
    if value is None:
        return default
    low = value.strip().lower()
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    raise ConfigError(f"{name} debe ser true/false, no {value!r}")


def _load_aes_key(key_file: str | None, key_env: str | None) -> tuple[SecretStr | None, str]:
    if key_file and key_env:
        raise ConfigError(
            "Configure la clave AES por UNA sola vía: TERRAINX_GO2_AES_KEY_FILE o la "
            "variable de entorno TERRAINX_GO2_AES_KEY, no ambas."
        )
    if key_file:
        path = Path(key_file).expanduser().resolve()
        repo = find_repo_root(ROBOT_ROOT)
        if repo is not None and path.is_relative_to(repo.resolve()):
            raise ConfigError(
                "El archivo de la clave AES está dentro del repositorio. Muévalo fuera "
                "(p. ej. a su carpeta de usuario) para que nunca pueda subirse."
            )
        if not path.is_file():
            raise ConfigError(f"No existe el archivo de clave AES indicado: {path}")
        value = path.read_text(encoding="utf-8").strip()
        source = "file"
    elif key_env:
        value = key_env.strip()
        source = "environment"
    else:
        return None, "none"
    if not _AES_RE.fullmatch(value):
        raise ConfigError("La clave AES no tiene el formato esperado (32 caracteres hexadecimales).")
    return SecretStr(value), source


def load_settings(
    env_file: Path | None = None,
    *,
    data_dir_override: Path | None = None,
    environ: dict[str, str] | None = None,
) -> Settings:
    """Lee la configuración. Las variables del proceso tienen prioridad sobre .env."""
    process_env = dict(os.environ) if environ is None else dict(environ)
    env_path = Path(env_file) if env_file else ROBOT_ROOT / ".env"
    file_values: dict[str, str] = {}
    loaded = None
    if env_path.is_file():
        file_values = {k: v for k, v in dotenv_values(env_path).items() if v is not None}
        loaded = str(env_path)
        if "TERRAINX_GO2_AES_KEY" in file_values:
            raise ConfigError(
                f"{env_path} contiene TERRAINX_GO2_AES_KEY. La clave no puede guardarse en "
                ".env: bórrela de ahí y use TERRAINX_GO2_AES_KEY_FILE con una ruta externa."
            )
    merged = {**file_values, **process_env}

    def get(name: str, default: str | None = None) -> str | None:
        value = merged.get(name)
        if value is None or not value.strip():
            return default
        return value.strip()

    method = get("TERRAINX_GO2_METHOD", "LocalSTA")
    if method.lower() == "remote":
        raise ConfigError(
            "El método Remote (nube de Unitree) está deshabilitado por política de "
            "seguridad: use LocalAP o LocalSTA."
        )
    if method not in ("LocalAP", "LocalSTA"):
        raise ConfigError(f"TERRAINX_GO2_METHOD debe ser LocalAP o LocalSTA, no {method!r}")

    ip = get("TERRAINX_GO2_IP")
    if ip:
        try:
            ipaddress.ip_address(ip)
        except ValueError as exc:
            raise ConfigError(f"TERRAINX_GO2_IP no es una IP válida: {ip!r}") from exc

    model = (get("TERRAINX_GO2_MODEL", "unknown") or "unknown").upper()
    if model == "UNKNOWN":
        model = "unknown"
    elif model not in ("AIR", "PRO", "EDU"):
        raise ConfigError(f"TERRAINX_GO2_MODEL debe ser AIR, PRO, EDU o unknown, no {model!r}")

    try:
        timeout = float(get("TERRAINX_GO2_CONNECT_TIMEOUT_S", "30"))
    except ValueError as exc:
        raise ConfigError("TERRAINX_GO2_CONNECT_TIMEOUT_S debe ser numérico") from exc
    if timeout <= 0:
        raise ConfigError("TERRAINX_GO2_CONNECT_TIMEOUT_S debe ser > 0")

    aes_key, aes_source = _load_aes_key(
        get("TERRAINX_GO2_AES_KEY_FILE"),
        (process_env.get("TERRAINX_GO2_AES_KEY") or "").strip() or None,
    )

    if data_dir_override is not None:
        data_dir = Path(data_dir_override).resolve()
    else:
        data_dir = Path(get("TERRAINX_DATA_DIR", "runtime"))
        if not data_dir.is_absolute():
            data_dir = (ROBOT_ROOT / data_dir).resolve()

    return Settings(
        data_dir=data_dir,
        robot_id=get("TERRAINX_ROBOT_ID", "go2-sin-identificar"),
        model_variant=model,
        firmware_version=get("TERRAINX_GO2_FIRMWARE"),
        go2=Go2Settings(
            method=method,
            ip=ip,
            serial=get("TERRAINX_GO2_SERIAL"),
            aes_key=aes_key,
            aes_key_source=aes_source,
            connect_timeout_s=timeout,
            enable_lidar=_parse_bool(
                "TERRAINX_GO2_ENABLE_LIDAR", get("TERRAINX_GO2_ENABLE_LIDAR"), True
            ),
        ),
        env_file_loaded=loaded,
    )

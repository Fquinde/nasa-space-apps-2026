import pytest

import terrainx_robot.config as config
from terrainx_robot.config import ROBOT_ROOT, ConfigError, load_settings

KEY = "0123456789abcdef0123456789abcdef"


def _load(tmp_path, env=None, env_file_text=None):
    env_file = tmp_path / "test.env"
    if env_file_text is not None:
        env_file.write_text(env_file_text, encoding="utf-8")
    return load_settings(env_file, environ=env or {})


def test_valores_por_defecto(tmp_path):
    s = _load(tmp_path)
    assert s.go2.method == "LocalSTA" and s.go2.ip is None and s.go2.aes_key is None
    assert s.model_variant == "unknown" and s.firmware_version is None
    assert s.data_dir == (ROBOT_ROOT / "runtime").resolve()


def test_env_example_se_interpreta_bien():
    """El .env.example (con comentarios en línea) no debe producir valores inventados."""
    s = load_settings(ROBOT_ROOT / ".env.example", environ={})
    assert s.go2.method == "LocalSTA"
    assert s.model_variant == "unknown"
    assert s.firmware_version is None and s.go2.ip is None and s.go2.serial is None
    assert s.go2.aes_key is None and s.go2.enable_lidar is True
    assert s.robot_id == "go2-terrestre-01"


@pytest.mark.parametrize(
    "env",
    [
        {"TERRAINX_GO2_METHOD": "Remote"},
        {"TERRAINX_GO2_METHOD": "Bluetooth"},
        {"TERRAINX_GO2_IP": "999.1.1.1"},
        {"TERRAINX_GO2_MODEL": "X1"},
        {"TERRAINX_GO2_CONNECT_TIMEOUT_S": "-1"},
        {"TERRAINX_GO2_ENABLE_LIDAR": "quizás"},
    ],
)
def test_configuraciones_rechazadas(tmp_path, env):
    with pytest.raises(ConfigError):
        _load(tmp_path, env)


def test_el_proceso_tiene_prioridad_sobre_env(tmp_path):
    s = _load(tmp_path, {"TERRAINX_GO2_IP": "10.0.0.2"}, "TERRAINX_GO2_IP=10.0.0.1\nTERRAINX_GO2_MODEL=edu\n")
    assert s.go2.ip == "10.0.0.2" and s.model_variant == "EDU"
    d = s.robot_descriptor(adapter="x", delivery_mode="live")
    assert d.model_variant_source == "declared_by_operator" and d.firmware_source == "unknown"


def test_clave_en_env_prohibida(tmp_path):
    with pytest.raises(ConfigError, match="no puede guardarse"):
        _load(tmp_path, env_file_text=f"TERRAINX_GO2_AES_KEY={KEY}\n")


def test_clave_desde_archivo_externo_no_se_filtra(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_repo_root", lambda start: tmp_path / "repo")
    key_file = tmp_path / "fuera" / "go2.aes"
    key_file.parent.mkdir()
    key_file.write_text(KEY + "\n", encoding="utf-8")
    s = _load(tmp_path, {"TERRAINX_GO2_AES_KEY_FILE": str(key_file)})
    assert s.go2.aes_key.get_secret_value() == KEY and s.go2.aes_key_source == "file"
    assert KEY not in repr(s) and KEY not in str(s.describe())


def test_clave_dentro_del_repositorio_rechazada(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "find_repo_root", lambda start: tmp_path)
    key_file = tmp_path / "robot" / "go2.aes"
    key_file.parent.mkdir()
    key_file.write_text(KEY, encoding="utf-8")
    with pytest.raises(ConfigError, match="dentro del repositorio"):
        _load(tmp_path, {"TERRAINX_GO2_AES_KEY_FILE": str(key_file)})


def test_clave_con_formato_invalido_no_se_muestra(tmp_path):
    secret = "zz-esto-no-es-hex-pero-es-secreto"
    with pytest.raises(ConfigError) as exc:
        _load(tmp_path, {"TERRAINX_GO2_AES_KEY": secret})
    assert secret not in str(exc.value)


def test_clave_por_dos_vias_rechazada(tmp_path):
    with pytest.raises(ConfigError, match="UNA sola vía"):
        _load(tmp_path, {"TERRAINX_GO2_AES_KEY": KEY, "TERRAINX_GO2_AES_KEY_FILE": "x"})


def test_clave_por_variable_de_entorno(tmp_path):
    s = _load(tmp_path, {"TERRAINX_GO2_AES_KEY": KEY.upper()})
    assert s.go2.aes_key_source == "environment"

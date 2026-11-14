# TERRAIN-X · Módulo de robótica

Software del especialista de robótica de TERRAIN-X (NASA Space Apps Challenge 2026).

**Fase 1:** comunicación de **solo lectura** con el Unitree Go2 físico. Incluye adquisición LiDAR y telemetría, exportación PLY + metadatos JSON con SHA-256 y un modo replay para trabajar sin robot.

> Este módulo **no envía órdenes de movimiento**. Un guardián bloquea en el propio PC cualquier mensaje que no esté en una lista blanca de lectura. No sustituye a la parada de emergencia física del robot.

---

## 1. Estado de la Fase 1

| Componente | Implementado | Probado offline | Pendiente con el robot físico |
|---|---|---|---|
| `RobotAdapter` (interfaz común) | ✅ | ✅ | — |
| `Go2WebRTCAdapter` (LocalAP / LocalSTA) | ✅ | ✅ con librería simulada y con el parser binario real de la librería | Conexión real, comportamiento en Windows con el robot |
| Guardián de solo lectura | ✅ | ✅ (todas las órdenes `SPORT_CMD` de la librería se bloquean) | — |
| `CapabilityProbe` | ✅ | ✅ en replay | Qué topics publica realmente vuestro Go2 y a qué frecuencia |
| Decodificación LiDAR (`voxel_codec`) | ✅ | ✅ idéntica bit a bit al decodificador `native` de la librería | **Unidades, ejes y origen del frame** (ver [docs/VERIFICACION_FISICA.md](docs/VERIFICACION_FISICA.md)) |
| Exportación PLY + JSON + SHA-256 | ✅ | ✅ | — |
| Sesiones crudas + replay | ✅ | ✅ | Grabar la primera sesión real |
| Telemetría (batería, IMU, posición) | ✅ campos de los ejemplos oficiales | ✅ con datos sintéticos | Que los campos existan en vuestro firmware y sus unidades |
| Modelo y firmware | Solo si el operador los declara | ✅ | Leerlos en la app oficial y anotarlos en `.env` |

**Lo que no existe todavía, por diseño:** movimiento, Meta Quest 3, misiones, comunicación planetaria, métricas geométricas (pendiente, suelo, obstáculos) y registro a ENU. Corresponden a las fases 2 a 5.

**Verificado sin robot (14-11-2026):** con una IP no enrutable, la librería real ejecuta en Windows la negociación WebRTC hasta la señalización. El error `LocalSignalingPortError` se traduce a un mensaje comprensible.

---

## 2. Requisitos

- Windows 10/11 con PowerShell.
- Python **3.11 o superior**. Verificado con 3.13.7.
- Para el robot: un PC en la **misma red local** que el Go2 y la app oficial de Unitree **cerrada**. El robot admite un solo cliente WebRTC a la vez.

## 3. Instalación (PowerShell)

Ejecute todo desde la carpeta `robot`. Se llama al Python del entorno virtual directamente, así que no hace falta `Activate.ps1` ni cambiar la política de ejecución.

```powershell
cd C:\Users\Usuario\Desktop\github\nasa-space-apps-2026\robot
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# Opción A (reproducible): versiones exactas verificadas
.\.venv\Scripts\python.exe -m pip install -r requirements\lock-windows-py313.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .

# Opción B: rangos de pyproject.toml (núcleo + Go2 + tests)
.\.venv\Scripts\python.exe -m pip install -e ".[go2,dev]"
```

El núcleo (replay, PLY, tests offline) solo necesita `numpy`, `lz4`, `pydantic` y `python-dotenv`. El extra `[go2]` instala `unitree_webrtc_connect==2.2.0`, la versión cuyo código fuente se ha revisado.

## 4. Prueba rápida SIN robot

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m terrainx_robot demo-session
.\.venv\Scripts\python.exe -m terrainx_robot capture --source replay --input latest
.\.venv\Scripts\python.exe -m terrainx_robot probe --source replay --input latest
.\.venv\Scripts\python.exe -m terrainx_robot list-scans
```

`demo-session` genera una escena **sintética** (suelo, caja de 0,50 m y pared) con el mismo formato binario que publica el robot. Todo lo que sale de ella queda marcado como `evidence_class=synthetic_test` y `demo=true`.

## 5. Uso CON el robot

1. Copie `.env.example` a `.env` y rellene **solo lo que sepa**:
   - `TERRAINX_GO2_IP`.
   - `TERRAINX_GO2_MODEL` y `TERRAINX_GO2_FIRMWARE`, si los ha leído en la app oficial.
2. Si el firmware es **1.1.15 o posterior**, la librería exige la clave AES-128 propia del robot:
   - Guárdela en un archivo **fuera del repositorio**, por ejemplo `C:\Users\<usted>\terrainx-secrets\go2.aes`.
   - Indique esa ruta en `TERRAINX_GO2_AES_KEY_FILE`.
   - El programa rechaza rutas dentro del repositorio y claves escritas en `.env`.
3. Cierre la app oficial de Unitree y ejecute:

```powershell
.\.venv\Scripts\python.exe -m terrainx_robot check-library
.\.venv\Scripts\python.exe -m terrainx_robot probe --source go2 --window 15 --record-session
.\.venv\Scripts\python.exe -m terrainx_robot capture --source go2 --duration 5 --record-session
```

Siga el protocolo de [docs/VERIFICACION_FISICA.md](docs/VERIFICACION_FISICA.md) en la primera sesión con el robot.

## 6. Comandos

| Comando | Qué hace |
|---|---|
| `info` | Configuración efectiva (la clave solo como "configurada" o "no configurada") y versiones |
| `check-library` | Verifica la API real de la librería instalada: versión, topics, gancho del decodificador y equivalencia con `native` |
| `demo-session [--frames N] [--seed S]` | Genera una sesión sintética |
| `probe --source go2\|replay [--window s] [--record-session]` | Sondeo de capacidades. Guarda el JSON en `runtime/probes/` |
| `record --source go2 --duration s [--notes ...]` | Graba datos crudos del robot para reproducirlos después |
| `capture --source go2\|replay [--duration s] [--mode accumulate\|last] [--record-session] [--ascii]` | Genera PLY + metadatos + SHA256SUMS |
| `list-scans [--json]` | Lista los escaneos |
| `verify-scan <id>` | Recalcula los SHA-256 |
| `export-scan <id> --dest <carpeta>` | Copia un escaneo tras verificar su integridad |
| `inspect <id \| archivo.ply>` | Estadística descriptiva para la verificación física |
| `export-schemas [--out carpeta]` | JSON Schema de la propuesta de contrato |

En replay, `--input` acepta una carpeta de sesión, un `.ply` o `latest`. Un PLY sin metadatos exige declarar `--evidence-class`: su origen no se adivina.

Códigos de salida: `0` correcto · `1` error · `2` resultado degradado.

## 7. Estructura

```
robot/
├── pyproject.toml            # paquete, dependencias y extras [go2] y [dev]
├── requirements/             # lock exacto verificado en Windows + Python 3.13
├── .env.example              # plantilla de configuración (sin secretos)
├── contracts/                # PROPUESTA de contrato 1.1-draft para Ciencia y Plataforma
│   ├── README.md             #   qué deben aprobar
│   ├── schemas/              #   JSON Schema generados desde el código
│   └── examples/             #   escaneo e informe SINTÉTICOS de ejemplo
├── docs/
│   ├── VERIFICACION_FISICA.md   # protocolo de la primera sesión con el robot
│   └── NOTAS_LIBRERIA_GO2.md    # qué se comprobó en el código de la librería 2.2.0
├── src/terrainx_robot/
│   ├── cli.py                # línea de comandos
│   ├── config.py             # .env y entorno, con reglas de seguridad
│   ├── models.py             # modelos Pydantic (contrato)
│   ├── adapters/
│   │   ├── base.py           # RobotAdapter + monitor de topics + telemetría
│   │   ├── go2_webrtc.py     # Go2WebRTCAdapter (solo lectura)
│   │   ├── replay.py         # ReplayAdapter (sesiones y PLY)
│   │   ├── readonly_guard.py # lista blanca de mensajes salientes
│   │   ├── go2_topics.py     # topics verificados en la librería 2.2.0
│   │   └── library_check.py  # verificación de la API instalada
│   ├── lidar/                # voxel_codec, frames, validación, acumulación, describe
│   ├── storage/              # PLY, almacén de escaneos, sesiones
│   ├── probe/                # CapabilityProbe y comprobación de red
│   └── fixtures/synthetic.py # generador de escenas sintéticas
├── tests/                    # pytest: ninguno necesita robot ni Internet
└── runtime/                  # datos generados (en .gitignore)
    ├── scans/<id>/           #   <id>.ply · <id>.metadata.json · SHA256SUMS
    ├── sessions/<id>/        #   session.json · messages.jsonl (payload LiDAR original)
    ├── probes/               #   informes de capacidades
    └── logs/
```

## 8. Qué significa cada dato

- **`evidence_class`**: el **origen** del dato.
  - `robot_measured`: medido físicamente por un robot.
  - `synthetic_test`: generado por software para pruebas.
  - Reservados para otros módulos: `orbital_nasa` y `derived`.
- **`delivery_mode`**: la **vía** por la que llegó el dato: `live` o `replay`. Un PLY real reproducido sigue siendo `robot_measured`.
- **`point_type = voxel_occupancy`**: por WebRTC el Go2 no entrega retornos crudos del LiDAR. Entrega un **mapa de vóxeles ocupados**, una rejilla 128 × 128 × N con la resolución que indica el propio mensaje (0,05 en los ejemplos). Cada punto es `origin + índice × resolution`.
- **`units_verification` / `axes_verification = unverified`**: ni el robot ni la librería declaran unidades ni ejes. Se asumen metros hasta completar la verificación física.
- **`registration.status = local_only`**: la nube está en el frame del robot. No se georreferencia sin puntos de control (Fase 2).

## 9. Seguridad

- Solo se usan LocalAP y LocalSTA. El método Remote (nube de Unitree) se rechaza en la configuración.
- La lista blanca de mensajes salientes es:
  - suscripciones;
  - mensajes de protocolo (heartbeat, validation);
  - mantenimiento del enlace;
  - `rt/utlidar/switch` con `on`/`off`.

  Todo lo demás se bloquea antes de salir del PC y queda contado en `readonly_guard`.
- Al desconectar **no** se envía `off` al LiDAR: no alteramos más estado del robot del necesario.
- Las claves y credenciales nunca se escriben en el repositorio, en `.env` ni en los logs. Los mensajes de error de la librería se redactan.
- `runtime/` puede contener datos reales e identificadores del robot. Está en `.gitignore`: revíselo antes de compartirlo.

## 10. Problemas frecuentes

| Síntoma | Causa probable | Solución |
|---|---|---|
| `robot_busy` | Otro cliente WebRTC conectado | Cierre la app oficial de Unitree en el móvil |
| `aes_key_required` | Firmware 1.1.15 o posterior | Configure `TERRAINX_GO2_AES_KEY_FILE` con una ruta externa |
| `signaling_unreachable` | IP incorrecta, otra red o robot apagado | Compruebe la IP. `probe` informa además de los puertos 9991/8081 |
| `datachannel_timeout` | Cortafuegos de Windows bloqueando UDP o Wi-Fi débil | Permita Python en el cortafuegos para redes privadas y acerque el PC |
| `missing_address` | LocalSTA sin IP ni número de serie | Rellene `TERRAINX_GO2_IP` en `.env` |
| Caracteres raros en la consola | Codificación de la consola | La CLI fuerza UTF-8; en consolas antiguas, ejecute `chcp 65001` |

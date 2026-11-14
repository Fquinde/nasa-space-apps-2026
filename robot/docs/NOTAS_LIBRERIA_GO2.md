# Lo que se comprobó en `unitree_webrtc_connect` 2.2.0

Revisión del **código fuente instalado** (`.venv/Lib/site-packages/unitree_webrtc_connect`) y de los ejemplos oficiales del repositorio `legion1581/unitree_webrtc_connect`, rama master, a 14-11-2026. Licencia MIT.

La librería **no es de Unitree**: es un proyecto comunitario que reproduce el protocolo de la app oficial. Unitree no documenta este protocolo.

`python -m terrainx_robot check-library` vuelve a comprobar automáticamente lo esencial de este documento.

## Conexión

| Hecho | Dónde está | Consecuencia |
|---|---|---|
| Métodos `LocalAP` (IP fija `192.168.12.1`), `LocalSTA` (IP o número de serie por multicast) y `Remote` (servidor TURN de Unitree con cuenta) | `webrtc_driver.py` | Solo usamos LocalAP y LocalSTA. Remote se rechaza en `config.py` |
| La señalización LAN prueba el puerto **9991** (`con_notify`: Go2 posterior a 1.1.11) y después el **8081** (`/offer` legado, anterior a 1.1.11) | `unitree_auth.send_sdp_to_local_peer` | `probe` comprueba ambos puertos antes de conectar, como pista de la generación de firmware |
| Go2 con firmware **1.1.15 o posterior** exige `aes_128_key`: 32 hex, propia de cada robot y obtenida de la cuenta Unitree | docstring de `UnitreeWebRTCConnection` | La clave se lee solo de un archivo externo o del entorno del proceso |
| Si el robot responde `sdp == "reject"`, la librería lanza `RobotBusyError`. Según su docstring: "Only one peer at a time" | `webrtc_driver.py`, `unitree_auth.py` | La app oficial y nuestro software no pueden estar conectados a la vez |
| `AesKeyRejectedError` incluye en su mensaje **los 8 primeros caracteres de la clave** | `unitree_auth.py` | El adaptador no usa ese texto y redacta la clave de cualquier error |
| Si se pasan usuario y contraseña al constructor, este inicia sesión en la nube de Unitree | `UnitreeWebRTCConnection.__init__` | Nunca los pasamos |
| La librería imprime su estado por consola con emojis (`print_status`) | `util.py` | La CLI fuerza UTF-8 en la consola |

## Canal de datos

- Todos los mensajes salientes pasan por `datachannel.channel.send(json)`. Los envía `WebRTCDataChannelPubSub`, que también usan el heartbeat (cada 2 s), la validación y el sondeo de estado de red. **Ese es el punto donde se instala nuestro guardián.**
- Tipos de mensaje: `subscribe`, `unsubscribe`, `msg`, `req`, `res`, `heartbeat`, `validation`, `rtc_inner_req`, `vid`, `aud`, `err` y errores.
- Las órdenes de movimiento son mensajes `req` a `rt/api/sport/request` con un `api_id`. Por ejemplo, `Move` = 1008 y `StopMove` = 1003, según `SPORT_CMD`.
- También existen `rt/lowcmd`, `rt/wirelesscontroller` y `rt/api/obstacles_avoid/request`. **Ninguno se usa en Fase 1, y el guardián los bloquea.**
- Los canales de vídeo y audio no envían nada automáticamente al conectar.

## LiDAR

- **Topic:** `rt/utlidar/voxel_map_compressed` (`RTC_TOPIC["ULIDAR_ARRAY"]`).
- **Activación** según el ejemplo oficial: `disableTrafficSaving(True)` y después `"on"` en `rt/utlidar/switch`.
- **Mensaje binario:**
  - cabecera `<HH` = (2, 0);
  - longitud del JSON en `<I`;
  - 4 bytes;
  - JSON de metadatos;
  - payload.

  El parser es `deal_array_buffer_for_lidar`.
- **Metadatos que leen los ejemplos:** `stamp`, `frame_id`, `resolution`, `src_size`, `origin` y `width`. El ejemplo de visualización usa `width = [128, 128, 38]` como valor por defecto.
- **Payload:** bloque LZ4 sin cabecera que, descomprimido, ocupa `src_size` bytes. Es una bitmask de ocupación:
  - 2048 bytes por capa Z;
  - 16 bytes (128 bits) por fila Y;
  - el bit más significativo corresponde a x = 0;
  - cada punto es `origin + índice × resolution`.

  Ver `lidar_decoder_native.py`.
- **Decodificador por defecto:** la librería instala **`libvoxel`**, un WASM extraído de la app que genera una **malla** (`positions`, `uvs`, `indices`), no una nube XYZ. Nosotros lo sustituimos por un decodificador *passthrough* que conserva el payload original y lo decodificamos con `voxel_codec`, que es idéntico al `native`.
- **Lo que no declara la librería:** unidades, convención de ejes ni si el punto es el centro o la esquina del vóxel. Ver [VERIFICACION_FISICA.md](VERIFICACION_FISICA.md).

## Telemetría (nombres de campo de los ejemplos oficiales)

- `rt/lf/lowstate`:
  - `imu_state.rpy`;
  - `motor_state[].{q, temperature, lost}`;
  - `bms_state.{soc, current, cycle, bq_ntc, mcu_ntc, version_high, version_low}`;
  - `foot_force`, `temperature_ntc1`, `power_v`.
- `rt/lf/sportmodestate`:
  - `mode`, `progress`, `gait_type`;
  - `position`, `velocity`, `yaw_speed`;
  - `body_height`, `foot_raise_height`;
  - `range_obstacle`;
  - `foot_force`, `foot_position_body`, `foot_speed_body`;
  - `imu_state.{quaternion, gyroscope, accelerometer, rpy, temperature}`.
- `rt/multiplestate`: llega como **texto JSON**. Campos: `bodyHeight`, `brightness`, `footRaiseHeight`, `obstaclesAvoidSwitch`, `speedLevel`, `uwbSwitch` y `volume`.
- Las unidades **no están documentadas**. Los ejemplos solo imprimen etiquetas: "%" para `soc`, "mA", "V" y "m" para `body_height`. Por eso los campos sin unidad verificada se llaman `*_raw` en `TelemetrySnapshot`.

## Topics que existen en `RTC_TOPIC` pero no sabemos si nuestro robot publica

`rt/utlidar/voxel_map` (sin comprimir), `rt/utlidar/robot_pose`, `rt/uslam/frontend/cloud_world_ds` (nube SLAM submuestreada en frame mundo), `rt/uslam/frontend/odom`, `rt/lio_sam_ros2/mapping/odometry`, etc.

`probe --explore` se suscribe a algunos de ellos (solo lectura) para descubrirlo.

## Compatibilidad con Windows

- `pip install unitree_webrtc_connect==2.2.0` se instala con Python 3.13 en Windows solo con wheels precompiladas: aiortc 1.16.0, av, opencv, PyAudio, wasmtime y lz4.
- Con una IP no enrutable, la negociación llega hasta la recogida ICE completa y falla limpiamente en la señalización.
- **Sin comprobar todavía:** una conexión completa con el robot desde Windows.

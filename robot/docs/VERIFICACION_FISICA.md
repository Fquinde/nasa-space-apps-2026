# Protocolo de la primera sesión con el Go2 físico (Fase 1)

**Objetivo.** Sustituir supuestos por hechos. Al terminar sabremos:

- qué publica realmente nuestro Go2;
- en qué unidades llegan los datos;
- cómo son los ejes y el origen del frame LiDAR;
- qué ocurre si se corta la conexión.

**Alcance.** Todo se hace en **solo lectura**: nuestro software no mueve el robot. Si el robot tiene que desplazarse, lo hace el operador con su mando oficial, nunca este software.

## 0. Antes de empezar

- [ ] Zona despejada y controlada, sin público. Una persona responsable de la parada física del robot.
- [ ] Lea en la app oficial **el modelo** (AIR, PRO o EDU) y **la versión de firmware**. Anótelos en `robot/.env`. Después **cierre la app**: el robot solo admite un cliente WebRTC.
- [ ] El PC está en la misma red que el robot: su Wi-Fi (LocalAP) o el mismo router (LocalSTA).
- [ ] Si el firmware es 1.1.15 o posterior: la clave AES está en un archivo **fuera** del repositorio y `TERRAINX_GO2_AES_KEY_FILE` apunta a él.
- [ ] Cinta métrica y una caja de dimensiones conocidas (por ejemplo, 40 × 30 × 25 cm).

## 1. Comprobaciones de software (2 min)

```powershell
cd C:\Users\Usuario\Desktop\github\nasa-space-apps-2026\robot
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m terrainx_robot check-library
.\.venv\Scripts\python.exe -m terrainx_robot info
```

Todo debe salir `OK`. En `info`, la clave debe aparecer solo como `"configurada"`.

## 2. Sondeo de capacidades (robot quieto, 1 min)

```powershell
.\.venv\Scripts\python.exe -m terrainx_robot probe --source go2 --window 15 --record-session
```

Anote en la tabla de resultados (sección 7):

| Dato | Dónde mirarlo en el informe `runtime/probes/*.json` |
|---|---|
| Puertos de señalización (9991/8081) | `network_preflight` |
| Topics recibidos y frecuencia (Hz) | `topics[].topic`, `topics[].rate_hz` |
| `frame_id`, `resolution`, `width` del LiDAR | `capabilities[lidar_point_data].details` |
| Campos de metadatos desconocidos | `details.extra_metadata_fields` |
| Estructura de lowstate y sportmodestate | `topics[].payload_structure` |
| Mensajes bloqueados por el guardián | `connection.readonly_guard.blocked_total` (debe ser **0**) |

Si el resultado es `failed`, el informe indica `error_code` y una sugerencia (README §10).

## 3. Unidades: distancia a una pared (5 min)

1. Coloque el robot quieto mirando a una **pared plana**. Mida con cinta la distancia horizontal **D** desde el centro del robot hasta la pared.
2. Capture:

   ```powershell
   .\.venv\Scripts\python.exe -m terrainx_robot capture --source go2 --duration 5 --mode last --record-session
   .\.venv\Scripts\python.exe -m terrainx_robot inspect <scan_id>
   ```

3. En `inspect`, busque la pared:
   - `bounds_min` y `bounds_max` del eje horizontal donde aparece;
   - la diferencia de coordenadas entre el suelo bajo el robot y la pared.
4. **Criterio:** si las unidades son metros, la distancia medida en la nube coincide con **D** dentro de ±2 celdas (±0,10 m con resolución 0,05). Una discrepancia de ×10, ×100 o ×1000 indica otra unidad.

## 4. Unidades y altura: la caja (5 min)

1. Ponga la caja a unos 1,5 m del robot. Anote su altura **H** medida con cinta.
2. Capture con el mismo comando y ejecute `inspect`. La diferencia entre el nivel del suelo (`most_populated_z_level`) y la parte alta de la caja debe ser **H** ± 0,10 m.
3. Guarde una foto de la escena junto al `scan_id`.

## 5. Ejes y origen del frame (5 min)

1. Caja **delante** del robot → captura A. Caja a la **izquierda** del robot → captura B.
2. Compare las coordenadas de la caja en A y B:
   - ¿qué eje crece hacia delante?
   - ¿cuál hacia la izquierda?
   - ¿Z apunta hacia arriba?
3. Capture dos veces con el robot quieto y compare `origin` en las sesiones grabadas (`messages.jsonl`). ¿El origen del mapa es fijo o se mueve?
4. (Opcional, solo con el mando oficial y el operador) Desplace el robot 1 m. ¿Cambia el `origin`? ¿Se mueven las paredes en la nube?

   Esto indica si el frame es fijo al mundo (tipo odometría) o al robot.

## 6. Robustez (5 min)

1. **Pérdida de conexión.** Lance `capture --source go2 --duration 20` y desconecte el Wi-Fi del PC a mitad.
   - Resultado esperado: error `conexión perdida` y salida con código 1, sin bloqueo.
   - El robot no se ve afectado: no recibe órdenes.
2. **Robot ocupado.** Abra la app oficial y repita `probe`. Resultado esperado: `robot_busy` con su sugerencia.
3. **Grabación larga.** Ejecute:

   ```powershell
   .\.venv\Scripts\python.exe -m terrainx_robot record --source go2 --duration 60 --notes "pasillo, robot quieto"
   ```

   Compruebe después que la sesión se reproduce:

   ```powershell
   .\.venv\Scripts\python.exe -m terrainx_robot capture --source replay --input latest
   ```

## 7. Tabla de resultados (rellenar y guardar como `docs/RESULTADOS_VERIFICACION_<fecha>.md`)

| Elemento | Valor observado | Evidencia (scan_id / session_id / foto) |
|---|---|---|
| Modelo / firmware (declarados) | | |
| Puerto de señalización abierto | | |
| Frecuencia `voxel_map_compressed` (Hz) | | |
| `frame_id` del LiDAR | | |
| `resolution` / `width` | | |
| Campos extra en metadatos LiDAR | | |
| Formato de `stamp` (¿segundos epoch?) | | |
| Unidades confirmadas (D medida vs nube) | | |
| Altura de la caja (H medida vs nube) | | |
| Eje adelante / izquierda / arriba | | |
| ¿Origen fijo o se mueve con el robot? | | |
| Topics de telemetría disponibles | | |
| Batería (`bms_state.soc`) coherente con la app | | |
| Comportamiento ante pérdida de Wi-Fi | | |

**Siguiente paso (Fase 2):** con esta tabla se crea un **registro de calibración** versionado. Los nuevos escaneos lo citarán y pasarán a `units_verification` / `axes_verification = verified`. Hasta entonces, cada escaneo seguirá marcado como `unverified`.

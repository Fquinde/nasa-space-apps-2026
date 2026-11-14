# Propuesta de contrato del módulo de robótica · versión 1.1-draft

> **Estado: PROPUESTA.** Según la regla del dossier (§6), ningún cambio de contrato es válido hasta que lo aprueben **Ciencia y datos** y **Plataforma**. Hasta entonces este directorio solo vive en `robot/`.

- **Esquemas:** `schemas/*.schema.json`, generados desde el código con:

  ```powershell
  .\.venv\Scripts\python.exe -m terrainx_robot export-schemas
  ```

- **Ejemplos:** `examples/`, producidos por el propio software a partir de una escena **SINTÉTICA** (`evidence_class=synthetic_test`, `demo=true`). No son mediciones.

## 1. Compatibilidad con el contrato 1.0 del dossier

`RobotScan` 1.0 se conserva **con los mismos nombres y significado**:

```
id, scan_context, frame_id, unit="m", timestamp_utc, point_count, file_url, pose_source?, source_record_id?
```

Además, `registration` va anidado como en el ejemplo del dossier (§6.2), con `status = "local_only"`. Quien lea solo los campos 1.0 no nota ningún cambio.

Los estados del dossier (§6.4) se conservan, repartidos en dos máquinas de estados:

- **Conexión:** `disconnected`, `connecting`, `ready_readonly`, `degraded`, `failed`.
- **Captura:** `idle`, `capturing`, `processing`, `complete`, `failed`.

## 2. Campos nuevos que hay que aprobar

| Campo | Valores | Por qué |
|---|---|---|
| `evidence_class` | `robot_measured` · `orbital_nasa` · `derived` · `synthetic_test` | Separa el origen del dato: medición robótica, producto NASA, cálculo o prueba. **Enum compartido con Ciencia**, que produce `orbital_nasa` y `derived` |
| `delivery_mode` | `live` · `replay` · `emulated_link` | La vía de llegada es independiente del origen: un PLY real reproducido sigue siendo `robot_measured` |
| `body` | `earth` · `moon` · `mars` | Dónde se adquirió físicamente el dato. **Regla:** `robot_measured` solo admite `earth` hasta que exista un robot desplegado en otro cuerpo |
| `demo` | bool | Obligatorio y coherente: `synthetic_test` implica `true`; `robot_measured` implica `false` (dossier §6.5) |
| `scan_context` | `controlled_test` · `field_campaign` · `synthetic` | Amplía el valor `controlled_test` del dossier |
| `robot` | `robot_id`, `platform`, `model_variant` (+ fuente), `firmware_version` (+ fuente), `adapter`, `delivery_mode` | Modelo y firmware constan como `declared_by_operator` o `unknown`: nunca se inventan |
| `geometry.point_type` | `voxel_occupancy` · `raw_returns` · `unknown` | **El Go2 por WebRTC entrega vóxeles ocupados (rejilla de 0,05), no retornos crudos.** Importa para la resolución efectiva de cualquier métrica |
| `geometry.units_verification` / `axes_verification` | `unverified` · `verified` | Unidades y ejes pendientes de verificación física |
| `capture.*` | ventana de captura, frames usados y rechazados con sus motivos, hora original de adquisición | Trazabilidad de cómo se formó la nube |
| `files.ply` | `path`, `sha256`, `bytes`, `format` | Integridad (dossier §6.5) |
| `provenance`, `quality_flag`, `caveats[]` | versiones de software, sesión de origen, advertencias legibles | Lo que la interfaz debe mostrar junto a la nube |

## 3. Archivos que produce el módulo

```
scans/<id>/<id>.ply             PLY binary_little_endian, vértices x y z float32,
                                con comentarios de cabecera (frame, unidad, evidencia, demo)
scans/<id>/<id>.metadata.json   ScanMetadata (schemas/scan_metadata.schema.json)
scans/<id>/SHA256SUMS           formato sha256sum: verificable con herramientas estándar
```

`file_url` es una ruta **relativa** a la carpeta de datos del módulo (`scans/<id>/<id>.ply`). Plataforma decide cómo exponerla por HTTP.

Además: `CapabilityReport` (sondeo), `RobotStatus` (estado y telemetría resumida, apto para `GET /api/v1/robot/status`) y `SessionInfo` (sesiones grabadas).

## 4. Qué necesitamos de cada especialista

**Plataforma (C):**

1. ¿Aceptáis `ScanMetadata` 1.1 como respuesta de `GET /api/v1/scans/{id}` y `RobotStatus` como respuesta de `GET /api/v1/robot/status`?
2. ¿Cómo integramos el módulo?
   - **Opción a:** importáis el paquete `terrainx_robot` desde vuestro FastAPI.
   - **Opción b (recomendada):** un proceso "robot gateway" en el PC conectado al robot, que vuestro backend consulta. Así el portátil del robot es el único dueño de la conexión WebRTC.
3. La interfaz debe mostrar siempre:
   - `evidence_class` y `demo`;
   - `point_type`;
   - `units_verification`;
   - `registration.status`;
   - los `caveats`.
4. Para el visor: el PLY es binario float32. ¿Necesitáis un LOD reducido? El tamaño real por escaneo del Go2 aún no se conoce; la escena sintética de ejemplo tiene unos 19 000 puntos (~225 KB).

**Ciencia y datos (B):**

1. Aprobar el enum `evidence_class` como **compartido**: vosotros producís `orbital_nasa` y `derived`.
2. Para la Fase 2 (métricas): ¿cómo definís cada métrica?
   - pendiente: ¿sobre qué distancia base?
   - rugosidad: ¿RMS de residuos a un plano? ¿con qué ventana?
   - obstáculo: ¿con qué umbral de altura?

   Las calcularemos con vuestra definición para que sean comparables con los DEM.
3. Confirmar que una nube `voxel_occupancy` con celda de 0,05 m es útil para vuestro perfil de misión.

## 5. Fuera de esta versión (fases siguientes)

- `Observation` (métricas con unidad, escala `scale_m`, método e incertidumbre): Fase 2.
- `Registration` real a ENU con puntos de control y RMSE: Fase 2.
- Comandos, confirmaciones, sesión de teleoperación y misiones: Fases 4 y 5. **Requiere aprobar el cambio de la regla del dossier que excluye el control del robot desde XR.**

## 6. Checklist de aprobación

- [ ] Ciencia aprueba `evidence_class`, `body`, `demo` y `point_type`
- [ ] Plataforma aprueba `ScanMetadata` 1.1 y `RobotStatus`
- [ ] Plataforma decide la integración: paquete o gateway
- [ ] Se mueve la versión aprobada a `packages/contracts` (o al lugar que acordemos)

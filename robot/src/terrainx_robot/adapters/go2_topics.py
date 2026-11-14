"""Topics del Go2 usados en Fase 1, verificados en unitree_webrtc_connect 2.2.0.

Qué hace
    Fija los nombres de topic que usamos (todos de LECTURA salvo el interruptor
    del LiDAR) y permite comprobar en tiempo de ejecución que la versión
    instalada de la librería sigue usando los mismos valores (check_against_library).
Fuente
    constants.RTC_TOPIC de unitree_webrtc_connect 2.2.0 y los ejemplos oficiales
    examples/go2/data_channel/{lidar,lowstate,sportmodestate,multiplestate}.
"""

from __future__ import annotations

VERIFIED_LIBRARY_VERSION = "2.2.0"

# Clave en RTC_TOPIC -> valor verificado
LIDAR_VOXEL_COMPRESSED = "rt/utlidar/voxel_map_compressed"  # "ULIDAR_ARRAY"
LIDAR_SWITCH = "rt/utlidar/switch"  # "ULIDAR_SWITCH" (activa el flujo LiDAR; no mueve el robot)
LIDAR_STATE = "rt/utlidar/lidar_state"  # "ULIDAR_STATE"
ROBOT_POSE = "rt/utlidar/robot_pose"  # "ROBOTODOM"
LOW_STATE = "rt/lf/lowstate"  # "LOW_STATE" (IMU, motores, batería)
SPORT_MODE_STATE = "rt/lf/sportmodestate"  # "LF_SPORT_MOD_STATE" (posición, velocidad, IMU)
MULTIPLE_STATE = "rt/multiplestate"  # "MULTIPLE_STATE" (configuración: altura, velocidad...)

# Exploratorios (solo con --explore): existen en RTC_TOPIC pero no sabemos si
# nuestro robot/firmware los publica ni en qué formato.
LIDAR_VOXEL_UNCOMPRESSED = "rt/utlidar/voxel_map"  # "ULIDAR"
SLAM_CLOUD_WORLD_DS = "rt/uslam/frontend/cloud_world_ds"  # "LIDAR_MAPPING_CLOUD_POINT"
SLAM_ODOM = "rt/uslam/frontend/odom"  # "LIDAR_MAPPING_ODOM"

LIBRARY_KEYS: dict[str, str] = {
    "ULIDAR_ARRAY": LIDAR_VOXEL_COMPRESSED,
    "ULIDAR_SWITCH": LIDAR_SWITCH,
    "ULIDAR_STATE": LIDAR_STATE,
    "ROBOTODOM": ROBOT_POSE,
    "LOW_STATE": LOW_STATE,
    "LF_SPORT_MOD_STATE": SPORT_MODE_STATE,
    "MULTIPLE_STATE": MULTIPLE_STATE,
    "ULIDAR": LIDAR_VOXEL_UNCOMPRESSED,
    "LIDAR_MAPPING_CLOUD_POINT": SLAM_CLOUD_WORLD_DS,
    "LIDAR_MAPPING_ODOM": SLAM_ODOM,
}

DEFAULT_READONLY_TOPICS: tuple[str, ...] = (
    LIDAR_VOXEL_COMPRESSED,
    LIDAR_STATE,
    ROBOT_POSE,
    LOW_STATE,
    SPORT_MODE_STATE,
    MULTIPLE_STATE,
)
EXPLORATORY_TOPICS: tuple[str, ...] = (
    LIDAR_VOXEL_UNCOMPRESSED,
    SLAM_CLOUD_WORLD_DS,
    SLAM_ODOM,
)

TOPIC_PURPOSE: dict[str, str] = {
    LIDAR_VOXEL_COMPRESSED: "mapa de vóxeles LiDAR comprimido",
    LIDAR_STATE: "estado del LiDAR",
    ROBOT_POSE: "pose/odometría estimada por el robot",
    LOW_STATE: "estado de bajo nivel (IMU, motores, batería)",
    SPORT_MODE_STATE: "estado de locomoción (posición, velocidad, IMU)",
    MULTIPLE_STATE: "configuración (altura, velocidad, evitación de obstáculos)",
    LIDAR_VOXEL_UNCOMPRESSED: "mapa de vóxeles sin comprimir (exploratorio)",
    SLAM_CLOUD_WORLD_DS: "nube SLAM en frame mundo, submuestreada (exploratorio)",
    SLAM_ODOM: "odometría SLAM (exploratorio)",
}


def check_against_library() -> list[str]:
    """Compara nuestros topics con RTC_TOPIC de la librería instalada.

    Devuelve la lista de discrepancias (vacía si todo coincide).
    Lanza ImportError si la librería no está instalada.
    """
    from unitree_webrtc_connect.constants import RTC_TOPIC  # import diferido: pila pesada

    problems = []
    for key, expected in LIBRARY_KEYS.items():
        actual = RTC_TOPIC.get(key)
        if actual != expected:
            problems.append(f"RTC_TOPIC[{key!r}] = {actual!r}, esperado {expected!r}")
    return problems

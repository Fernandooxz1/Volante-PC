"""
Transmisor UDP optimizado de telemetría hacia ESP32 por WiFi para Volante-PC.

Envía paquetes binarios ultraligeros (9 bytes) en broadcast UDP hacia la red local
para alimentar paneles de instrumentos (DDU), pantallas LCD (16x2/20x4) o displays OLED
conectados a una ESP32 con MicroPython.

Estructura del paquete ESP32 (9 bytes):
- 2 bytes de sincronización: 0xAA 0x55
- 2 bytes uint16: RPM (0..20000)
- 1 byte int8: Marcha (-1: R, 0: N, 1..8)
- 2 bytes uint16: Velocidad en km/h
- 1 byte uint8: Porcentaje de Shift Lights (0..100)
- 1 byte uint8: Estado de DRS (0: apagado, 1: activo)
"""

import logging
import socket
import struct
import threading
import time
from typing import Optional, Tuple

logger = logging.getLogger("VolantePC.ESP32Bridge")

ESP32_SYNC_BYTE_1 = 0xAA
ESP32_SYNC_BYTE_2 = 0x55
ESP32_PACKET_FORMAT = "<BBHbHBB"
ESP32_PACKET_LEN = 9

DEFAULT_ESP32_BROADCAST_HOST = "255.255.255.255"
DEFAULT_ESP32_UDP_PORT = 20778
DEFAULT_ESP32_RATE_LIMIT_HZ = 30.0


def encode_esp32_telemetry(
    rpm: int,
    gear: int,
    speed: int,
    rev_lights_percent: int = 0,
    drs: int = 0,
) -> bytes:
    """Codifica los datos esenciales de telemetría en un paquete binario de 9 bytes."""
    clamped_rpm = max(0, min(65535, int(rpm)))
    clamped_gear = max(-1, min(127, int(gear)))
    clamped_speed = max(0, min(65535, int(speed)))
    clamped_revs = max(0, min(100, int(rev_lights_percent)))
    clamped_drs = 1 if drs else 0

    return struct.pack(
        ESP32_PACKET_FORMAT,
        ESP32_SYNC_BYTE_1,
        ESP32_SYNC_BYTE_2,
        clamped_rpm,
        clamped_gear,
        clamped_speed,
        clamped_revs,
        clamped_drs,
    )


def decode_esp32_telemetry(data: bytes) -> Optional[Tuple[int, int, int, int, int]]:
    """
    Desempaqueta un paquete de telemetría de ESP32 (9 bytes o fallback de 5 bytes).
    Retorna (rpm, gear, speed, rev_lights_percent, drs) o None si no es válido.
    """
    if len(data) >= ESP32_PACKET_LEN:
        sync1, sync2, rpm, gear, speed, revs, drs = struct.unpack_from(ESP32_PACKET_FORMAT, data, 0)
        if sync1 == ESP32_SYNC_BYTE_1 and sync2 == ESP32_SYNC_BYTE_2:
            return (rpm, gear, speed, revs, drs)

    # Fallback de compatibilidad con paquetes simplificados <HbH (5 bytes)
    if len(data) == 5:
        try:
            rpm, gear, speed = struct.unpack_from("<HbH", data, 0)
            return (rpm, gear, speed, 0, 0)
        except Exception:
            return None

    return None


class ESP32Bridge:
    """
    Transmisor de telemetría UDP no bloqueante hacia ESP32 por WiFi.
    Permite broadcast en la red local o envío a una IP específica.
    """

    def __init__(
        self,
        host: str = DEFAULT_ESP32_BROADCAST_HOST,
        port: int = DEFAULT_ESP32_UDP_PORT,
        rate_limit_hz: float = DEFAULT_ESP32_RATE_LIMIT_HZ,
        enabled: bool = True,
    ):
        self.host = host
        self.port = port
        self.rate_limit_hz = rate_limit_hz
        self.enabled = enabled

        self._min_interval = 1.0 / rate_limit_hz if rate_limit_hz > 0 else 0.0
        self._last_send_time = 0.0
        self._socket: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._packets_sent = 0
        self._running = False

    @property
    def packets_sent(self) -> int:
        with self._lock:
            return self._packets_sent

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        """Inicializa el socket de transmisión UDP con soporte de broadcast."""
        if not self.enabled:
            return False

        if self._running and self._socket:
            return True

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setblocking(False)
            self._socket = sock
            self._running = True
            logger.info("Puente ESP32 UDP activo transmitiendo hacia %s:%d", self.host, self.port)
            return True
        except Exception as e:
            logger.warning("No se pudo iniciar el socket UDP de ESP32: %s", e)
            self._socket = None
            self._running = False
            return False

    def stop(self) -> None:
        """Cierra el socket de transmisión UDP."""
        self._running = False
        with self._lock:
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None
        logger.info("Puente ESP32 UDP detenido.")

    def send_telemetry(
        self,
        rpm: int,
        gear: int,
        speed: int,
        rev_lights_percent: int = 0,
        drs: int = 0,
    ) -> bool:
        """
        Envía un paquete de telemetría hacia la ESP32 respetando el límite de frecuencia.
        Retorna True si el paquete fue emitido.
        """
        if not self.enabled or not self._running:
            return False

        now = time.time()
        if (now - self._last_send_time) < self._min_interval:
            return False

        payload = encode_esp32_telemetry(
            rpm=rpm,
            gear=gear,
            speed=speed,
            rev_lights_percent=rev_lights_percent,
            drs=drs,
        )

        sock = self._socket
        if not sock:
            return False

        try:
            sock.sendto(payload, (self.host, self.port))
            self._last_send_time = now
            with self._lock:
                self._packets_sent += 1
            return True
        except Exception as e:
            logger.debug("Error enviando paquete UDP a ESP32: %s", e)
            return False

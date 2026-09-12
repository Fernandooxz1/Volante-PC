"""
Receptor de telemetría UDP para juegos de F1 (F1 2020, F1 2021, F1 22, F1 23, F1 24).
Captura paquetes de telemetría (Packet ID 6: PacketCarTelemetryData) enviados por el juego a 127.0.0.1:20777
para controlar la iluminación dinámica del LED RGB como Shift Light (luces de cambio).

Secuencia de iluminación Shift Light:
- 0% rev lights: None (mantiene el color base del preset configurado)
- 1% - 40%: Verde
- 41% - 70%: Amarillo
- 71% - 90%: Rojo
- 91% - 100%: Azul (¡Punto óptimo de cambio!)
"""

import logging
import select
import socket
import struct
import threading
import time
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("VolantePC.F1Telemetry")

DEFAULT_F1_UDP_PORT = 20777
PACKET_ID_CAR_TELEMETRY = 6
LIVENESS_TIMEOUT_SEC = 2.0


class F1TelemetryReceiver:
    """
    Receptor UDP thread-safe para telemetría de Fórmula 1.
    Escucha en segundo plano y extrae RPM, marcha actual, velocidad y porcentaje de luces de cambio.
    """

    def __init__(self, port: int = DEFAULT_F1_UDP_PORT, host: str = "0.0.0.0"):
        self.port = port
        self.host = host

        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._socket: Optional[socket.socket] = None

        # Estado de telemetría
        self._last_packet_time: float = 0.0
        self._packet_format: int = 0
        self._speed: int = 0
        self._gear: int = 0
        self._engine_rpm: int = 0
        self._rev_lights_percent: int = 0
        self._drs: int = 0
        self._player_car_index: int = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_active(self) -> bool:
        """Indica si se han recibido paquetes válidos en los últimos 2 segundos."""
        with self._lock:
            return (time.time() - self._last_packet_time) < LIVENESS_TIMEOUT_SEC

    def get_telemetry_data(self) -> Dict[str, Any]:
        """Retorna una instantánea atómica de los datos del coche del jugador."""
        with self._lock:
            active = (time.time() - self._last_packet_time) < LIVENESS_TIMEOUT_SEC
            return {
                "active": active,
                "packet_format": self._packet_format,
                "speed": self._speed,
                "gear": self._gear,
                "rpm": self._engine_rpm,
                "rev_lights_percent": self._rev_lights_percent,
                "drs": self._drs,
                "last_packet_time": self._last_packet_time,
            }

    def get_shift_led_color(
        self,
        green_thresh: int = 1,
        yellow_thresh: int = 40,
        red_thresh: int = 70,
        blue_thresh: int = 90,
    ) -> Optional[str]:
        """
        Determina el color que debe adoptar el LED RGB según el porcentaje de revoluciones.
        Retorna None si la telemetría está inactiva o las RPM están por debajo del umbral inicial.
        """
        with self._lock:
            if (time.time() - self._last_packet_time) >= LIVENESS_TIMEOUT_SEC:
                return None

            pct = self._rev_lights_percent

            if pct < green_thresh:
                return None
            elif pct >= blue_thresh:
                return "Azul"
            elif pct >= red_thresh:
                return "Rojo"
            elif pct >= yellow_thresh:
                return "Amarillo"
            else:
                return "Verde"

    def process_packet(self, data: bytes) -> bool:
        """
        Decodifica un paquete binario de telemetría de F1.
        Retorna True si fue un paquete de telemetría del coche válido y procesado.
        """
        if len(data) < 24:
            return False

        try:
            # Cabecera estándar (24 bytes mínimos para F1 2020/2021/2022)
            m_packet_format = struct.unpack_from("<H", data, 0)[0]
            m_packet_id = data[5]

            # Solo nos interesa el paquete ID 6 (Car Telemetry)
            if m_packet_id != PACKET_ID_CAR_TELEMETRY:
                return False

            # Desplazamiento de cabecera y posición del índice de jugador
            if m_packet_format >= 2023:
                # F1 23 / F1 24 añade campos extra en la cabecera (29 bytes)
                header_size = 29
                player_car_index = data[27] if len(data) > 27 else 0
            else:
                # F1 2020 / F1 2021 / F1 2022 (24 bytes)
                header_size = 24
                player_car_index = data[22] if len(data) > 22 else 0

            # Tamaño de CarTelemetryData por coche (60 bytes en F1 2021/2022/2023)
            car_entry_size = 60
            player_offset = header_size + (player_car_index * car_entry_size)

            if len(data) < player_offset + 22:
                return False

            # Campos dentro de CarTelemetryData:
            # +0: speed (uint16)
            # +14: clutch (uint8)
            # +15: gear (int8)
            # +16: engineRPM (uint16)
            # +18: drs (uint8)
            # +19: revLightsPercent (uint8)
            speed = struct.unpack_from("<H", data, player_offset + 0)[0]
            gear = struct.unpack_from("<b", data, player_offset + 15)[0]
            rpm = struct.unpack_from("<H", data, player_offset + 16)[0]
            drs = data[player_offset + 18]
            rev_pct = data[player_offset + 19]

            with self._lock:
                self._packet_format = m_packet_format
                self._player_car_index = player_car_index
                self._speed = speed
                self._gear = gear
                self._engine_rpm = rpm
                self._drs = drs
                self._rev_lights_percent = min(100, max(0, rev_pct))
                self._last_packet_time = time.time()

            return True

        except Exception as e:
            logger.debug("Error procesando paquete F1 UDP: %s", e)
            return False

    def start(self) -> bool:
        """Inicia el socket UDP y el hilo de escucha en segundo plano."""
        if self._running:
            return True

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # SO_REUSEPORT si está disponible (Linux / BSD)
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except OSError:
                    pass

            sock.bind((self.host, self.port))
            sock.setblocking(False)
            self._socket = sock
        except Exception as e:
            logger.warning("No se pudo enlazar el puerto UDP %d de F1: %s", self.port, e)
            return False

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="F1TelemetryUDP")
        self._thread.start()
        logger.info("Receptor de telemetría F1 UDP activo en %s:%d", self.host, self.port)
        return True

    def stop(self) -> None:
        """Detiene el hilo de escucha y cierra el socket UDP."""
        self._running = False
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.5)
        self._thread = None
        logger.info("Receptor de telemetría F1 UDP detenido.")

    def _listen_loop(self) -> None:
        """Bucle de recepción de paquetes UDP no bloqueante con select."""
        sock = self._socket
        if not sock:
            return

        while self._running:
            try:
                readable, _, _ = select.select([sock], [], [], 0.2)
                if not readable:
                    continue

                while self._running:
                    try:
                        data, _ = sock.recvfrom(2048)
                        if data:
                            self.process_packet(data)
                    except (BlockingIOError, socket.error):
                        break
            except Exception as e:
                if self._running:
                    logger.debug("Excepción en bucle UDP F1: %s", e)
                    time.sleep(0.05)

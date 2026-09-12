"""
Motor central de baja latencia para Volante-PC.

Ejecuta un bucle en tiempo real a 100 Hz (intervalo estricto de 10 ms con time.perf_counter()),
gestionando:
1. Comunicación serie binaria con Arduino UNO (115200 baud, 8N1, reconexión automática).
2. Filtrado DSP anti-jitter (Slew Rate Limiter + EMA) mediante SteeringFilter.
3. Modelado matemático de respuesta (Steering Expo, anti-deadzone, rest-deadzone, pedales).
4. Abstracción multiplataforma de Gamepad Virtual (Xbox 360 vía vgamepad / uinput / ViGEmBus).
5. Buffer de estado de telemetría atómico y thread-safe (TelemetrySnapshot).
6. Bus reactivo de eventos de entrada (Press-to-Map wizard).
7. Modos de operación: "Conducción" vs "Crucetas / D-Pad".
8. Transmisión periódica y reactiva de comandos LED RGB (0xBB 0x66 <código>).
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import serial
import serial.tools.list_ports

from core.calibration import calculate_pedal, calculate_steering
from core.config_manager import ConfigManager
from core.dsp import SteeringFilter
from core.gamepad import BUTTON_MAPPING_TABLE, VirtualGamepadManager
from core.protocol import (
    CONFIG_BUTTON_KEYS,
    LED_COLORS,
    PIN_NAMES,
    StreamParser,
    encode_led_command,
    unpack_payload,
)

logger = logging.getLogger("VolantePC.Engine")

# Constantes del motor
TARGET_INTERVAL: float = 0.010  # 10 ms = 100 Hz
DEFAULT_BAUD_RATE: int = 115200
DEFAULT_AXIS_THRESHOLD: int = 50  # ~5% de cambio en ADC 0..1023 para disparar evento reactivo
HEARTBEAT_INTERVAL: float = 2.0  # Segundos entre latidos LED para mantener conectado el Arduino

# Modos de operación
MODE_CONDUCCION: str = "Conducción"
MODE_CRUCETAS: str = "Crucetas / D-Pad"
AVAILABLE_MODES: Tuple[str, ...] = (MODE_CONDUCCION, MODE_CRUCETAS)

# Mapeo de pines a claves de configuración y nombres legibles
PIN_TO_CONFIG_KEY: Dict[str, str] = dict(zip(PIN_NAMES, CONFIG_BUTTON_KEYS))
CONFIG_KEY_TO_PIN: Dict[str, str] = {v: k for k, v in PIN_TO_CONFIG_KEY.items()}

# Tipo para listeners del bus de eventos: (source_type, source_id, value)
# source_type: "button" | "axis"
# source_id: pin ("D2", "A3", etc.) o eje ("steer", "accel", "brake")
# value: int (1 para botón presionado, 0..1023 para valor de eje)
InputEventListener = Callable[[str, str, int], None]


def find_available_ports() -> List[str]:
    """
    Retorna la lista de puertos serie activos en el sistema,
    descartando puertos UART nativos de placa madre en Linux y ordenando
    los puertos con adaptadores USB/Arduino al principio.
    """
    ports = serial.tools.list_ports.comports()
    filtered: List[str] = []
    for p in ports:
        if sys.platform.startswith("linux") and p.device.startswith("/dev/ttyS") and (p.hwid == "n/a" or not p.hwid):
            continue
        filtered.append(p.device)

    filtered.sort(
        key=lambda x: (
            not any(k in x.upper() for k in ["USB", "ACM", "ARDUINO", "CH340", "FTDI"]),
            x,
        )
    )
    return filtered


def auto_detect_arduino_port() -> Optional[str]:
    """Detecta automáticamente el primer puerto que coincida con Arduino o USB Serial."""
    ports = serial.tools.list_ports.comports()
    for p in ports:
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()
        mfg = (p.manufacturer or "").lower()
        if any(k in desc or k in hwid or k in mfg for k in ["arduino", "ch340", "ftdi", "cp210", "usb serial"]):
            return p.device

    for p in ports:
        if p.device.startswith("/dev/ttyACM") or p.device.startswith("/dev/ttyUSB"):
            return p.device

    avail = find_available_ports()
    return avail[0] if avail else None


def pin_to_label(pin: str) -> str:
    """Convierte un identificador de pin ('D2') al formato UI ('Pin D2')."""
    return f"Pin {pin}" if not pin.startswith("Pin ") else pin


def label_to_pin(label: str) -> str:
    """Convierte una etiqueta UI ('Pin D2') al pin normalizado ('D2')."""
    label_clean = label.strip()
    if label_clean.startswith("Pin "):
        return label_clean[4:]
    return label_clean


@dataclass(frozen=True)
class TelemetrySnapshot:
    """
    Instantánea inmutable y thread-safe del estado completo del motor a 100 Hz.
    Permite lecturas atómicas de alta frecuencia sin bloqueos para interfaces gráficas.
    """
    timestamp: float
    status: str  # "connected", "connecting", "reconnecting", "disconnected", "stopped"
    active_port: Optional[str]
    mode: str  # "Conducción" | "Crucetas / D-Pad"
    preset: str
    led_color: str

    # Lecturas de hardware crudas (0..1023)
    raw_steer: int
    raw_accel: int
    raw_brake: int
    raw_buttons: Tuple[int, ...]

    # Valores filtrados y calibrados mapeados para indicadores de UI (0..1023)
    mapped_steer: int
    mapped_accel: int
    mapped_brake: int
    mapped_buttons: Tuple[int, ...]

    # Valores matemáticos de telemetría de carrera
    steer_angle: float  # -90.0° a +90.0°
    steer_phys_norm: float  # -1.0 a 1.0 (posición física relativa a centro real)
    steer_out_norm: float  # -1.0 a 1.0 (posición pos-curva exponencial y anti-deadzone)
    throttle_pct: float  # 0.0% a 100.0%
    brake_pct: float  # 0.0% a 100.0%

    # Salidas enviadas al driver del gamepad virtual
    gamepad_steer: int  # -32768 a 32767
    gamepad_accel: int  # 0 a 255
    gamepad_brake: int  # 0 a 255
    active_gamepad_buttons: Tuple[str, ...]

    # Métricas de rendimiento
    loop_hz: float
    gamepad_connected: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convierte la telemetría a formato compatible con JSON y APIs de UI."""
        return {
            "timestamp": self.timestamp,
            "status": self.status,
            "active_port": self.active_port,
            "mode": self.mode,
            "preset": self.preset,
            "led_color": self.led_color,
            "raw": {
                "steer": self.raw_steer,
                "accel": self.raw_accel,
                "brake": self.raw_brake,
                "buttons": list(self.raw_buttons),
            },
            "mapped": {
                "steer": self.mapped_steer,
                "accel": self.mapped_accel,
                "brake": self.mapped_brake,
                "buttons": list(self.mapped_buttons),
            },
            "steer_angle": self.steer_angle,
            "steer_phys_norm": self.steer_phys_norm,
            "steer_out_norm": self.steer_out_norm,
            "throttle_pct": self.throttle_pct,
            "brake_pct": self.brake_pct,
            "gamepad": {
                "steer": self.gamepad_steer,
                "accel": self.gamepad_accel,
                "brake": self.gamepad_brake,
                "active_buttons": list(self.active_gamepad_buttons),
            },
            "loop_hz": self.loop_hz,
            "gamepad_connected": self.gamepad_connected,
            "error_message": self.error_message,
        }


class Engine:
    """
    Motor en tiempo real a 100 Hz para Volante-PC.
    
    Controla el hilo de comunicación de baja latencia, deserialización binaria,
    procesamiento de señales, gamepad virtual y bus de eventos.
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        gamepad_manager: Optional[VirtualGamepadManager] = None,
        port: Optional[str] = None,
        baud_rate: int = DEFAULT_BAUD_RATE,
        auto_reconnect: bool = True,
        axis_threshold: int = DEFAULT_AXIS_THRESHOLD,
        serial_instance: Optional[serial.Serial] = None,
    ):
        self.config_manager: ConfigManager = config_manager or ConfigManager()
        self.gamepad_manager: VirtualGamepadManager = gamepad_manager or VirtualGamepadManager()
        self.target_port: Optional[str] = port
        self.baud_rate: int = baud_rate
        self.auto_reconnect: bool = auto_reconnect
        self.axis_threshold: int = axis_threshold

        # Subsistemas de protocolo y DSP
        self._parser = StreamParser()
        self._steer_filter = SteeringFilter()

        # Conexión serie
        self._serial: Optional[serial.Serial] = serial_instance
        self._active_port: Optional[str] = port
        self._last_reconnect_attempt: float = 0.0
        self._reconnect_interval: float = 1.0

        # Estado del motor y sincronización
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._status: str = "disconnected"
        self._last_error: Optional[str] = None

        # Modo de operación
        self._mode: str = MODE_CONDUCCION

        # D-Pad en modo Crucetas
        self._dpad_from_axes: bool = True
        self._dpad_suppress_axes: bool = True

        # LED RGB
        self._current_led_color: str = str(self.config_manager.get("led_color", "Azul"))
        self._pending_led_command: Optional[bytes] = None
        self._last_led_send_time: float = 0.0

        # Estado previo de hardware para detección de eventos y flancos
        self._prev_raw_buttons: List[int] = [0] * len(PIN_NAMES)
        self._prev_event_axis_values: Dict[str, int] = {"steer": 512, "accel": 0, "brake": 0}
        self._last_raw_axes: Dict[str, int] = {"steer": 512, "accel": 0, "brake": 0}
        self._last_btn_cycle_state: int = 0

        # Bus de eventos de entrada (Press-to-Map)
        self._listener_lock = threading.Lock()
        self._input_listeners: List[InputEventListener] = []

        # Métricas de rendimiento de bucle a 100 Hz
        self._loop_hz: float = 0.0
        self._tick_count: int = 0
        self._hz_timer: float = time.perf_counter()

        # Buffer atómico de telemetría protegido
        self._telemetry_lock = threading.Lock()
        self._telemetry_snapshot: TelemetrySnapshot = self._create_initial_snapshot()

    def _create_initial_snapshot(self) -> TelemetrySnapshot:
        """Crea una instantánea inicial neutra."""
        return TelemetrySnapshot(
            timestamp=time.time(),
            status=self._status,
            active_port=self._active_port,
            mode=self._mode,
            preset=str(self.config_manager.get("active_preset", "Personalizado")),
            led_color=self._current_led_color,
            raw_steer=512,
            raw_accel=0,
            raw_brake=0,
            raw_buttons=tuple([0] * len(PIN_NAMES)),
            mapped_steer=512,
            mapped_accel=0,
            mapped_brake=0,
            mapped_buttons=tuple([0] * len(PIN_NAMES)),
            steer_angle=0.0,
            steer_phys_norm=0.0,
            steer_out_norm=0.0,
            throttle_pct=0.0,
            brake_pct=0.0,
            gamepad_steer=0,
            gamepad_accel=0,
            gamepad_brake=0,
            active_gamepad_buttons=(),
            loop_hz=0.0,
            gamepad_connected=self.gamepad_manager.is_connected,
            error_message=self._last_error,
        )

    # =========================================================================
    # Ciclo de Vida y Control del Hilo
    # =========================================================================

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def status(self) -> str:
        return self._status

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def active_port(self) -> Optional[str]:
        return self._active_port

    def start(self) -> bool:
        """Inicia el bucle de emulación a 100 Hz en un hilo dedicado."""
        if self._running:
            logger.warning("El motor ya se encuentra en ejecución.")
            return True

        # 1. Inicializar Gamepad Virtual
        if not self.gamepad_manager.is_connected:
            ok, msg = self.gamepad_manager.initialize()
            if not ok:
                logger.warning("Gamepad virtual no disponible: %s", msg)
                self._last_error = msg
            else:
                logger.info("Gamepad virtual inicializado con éxito.")

        # 2. Inicializar color de LED según preset activo
        self._update_led_color_from_config()

        # 3. Arrancar hilo
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, name="VolantePC-100Hz", daemon=True)
        self._thread.start()
        logger.info("Hilo del motor iniciado a 100 Hz.")
        return True

    def stop(self) -> None:
        """Detiene de forma segura el hilo del motor y libera recursos."""
        if not self._running:
            return

        logger.info("Deteniendo motor Volante-PC...")
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None

        # Cerrar puerto serie
        self._close_serial()

        # Resetear gamepad virtual a centro neutro
        if self.gamepad_manager.is_connected:
            self.gamepad_manager.reset()

        self._status = "stopped"
        with self._telemetry_lock:
            self._telemetry_snapshot = self._create_initial_snapshot()
        logger.info("Motor detenido correctamente.")

    def __enter__(self) -> Engine:
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    # =========================================================================
    # Manejo de Conexión Serie y Reconexión Automática
    # =========================================================================

    def connect(self, port: Optional[str] = None) -> bool:
        """Conecta o cambia el puerto serie objetivo."""
        if port is not None:
            self.target_port = port

        self._close_serial()
        return self._attempt_connection()

    def disconnect(self) -> None:
        """Desconecta el puerto serie manualmente."""
        self._close_serial()
        self._status = "disconnected"
        if self.gamepad_manager.is_connected:
            self.gamepad_manager.reset()

    def _close_serial(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception as e:
                logger.debug("Error cerrando puerto serie: %s", e)
            self._serial = None
        self._active_port = None

    def _attempt_connection(self) -> bool:
        """Intenta abrir la conexión serie con timeout de bajo retardo."""
        port = self.target_port or auto_detect_arduino_port()
        if not port:
            self._status = "disconnected"
            self._last_error = "No se detectó ningún puerto Arduino disponible."
            return False

        try:
            self._status = "connecting"
            logger.info("Intentando conectar con Arduino en %s (%d baud)...", port, self.baud_rate)
            ser = serial.Serial(
                port=port,
                baudrate=self.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.005,  # 5 ms timeout no bloqueante
            )
            ser.reset_input_buffer()
            self._serial = ser
            self._active_port = port
            self._status = "connected"
            self._last_error = None
            self._parser.reset()
            self._steer_filter.reset()

            # Enviar color de LED inmediatamente tras conectar
            self.send_led_color(self._current_led_color)
            logger.info("Conexión serie establecida con éxito en %s.", port)
            return True

        except (serial.SerialException, OSError) as e:
            self._close_serial()
            self._status = "reconnecting" if self.auto_reconnect else "error"
            self._last_error = f"Error conectando en {port}: {e}"
            logger.warning("Fallo al conectar en %s: %s", port, e)
            return False

    def _handle_disconnect(self, reason: str) -> None:
        """Maneja la desconexión sobrevenida (ej. cable USB desenchufado)."""
        logger.warning("Desconexión detectada: %s", reason)
        self._close_serial()
        if self.gamepad_manager.is_connected:
            self.gamepad_manager.reset()

        self._status = "reconnecting" if self.auto_reconnect else "disconnected"
        self._last_error = reason

    # =========================================================================
    # Modos de Operación y Presets
    # =========================================================================

    def set_mode(self, mode: str) -> None:
        """Cambia el modo de operación ('Conducción' vs 'Crucetas / D-Pad')."""
        if mode not in AVAILABLE_MODES:
            raise ValueError(f"Modo inválido '{mode}'. Opciones disponibles: {AVAILABLE_MODES}")

        if self._mode == mode:
            return

        self._mode = mode
        logger.info("Modo cambiado a: %s", mode)

        # Transmitir color de LED según el modo seleccionado
        if mode == MODE_CRUCETAS:
            # Color Naranja (código 7) característico para modo D-Pad
            self.send_led_color("Naranja")
        else:
            self._update_led_color_from_config()
            self.send_led_color(self._current_led_color)

    def toggle_mode(self) -> str:
        """Alterna entre 'Conducción' y 'Crucetas / D-Pad' y retorna el nuevo modo."""
        new_mode = MODE_CRUCETAS if self._mode == MODE_CONDUCCION else MODE_CONDUCCION
        self.set_mode(new_mode)
        return new_mode

    def load_preset(self, preset_name: str) -> bool:
        """Carga un preset en la configuración y actualiza el LED correspondiente."""
        success = self.config_manager.load_preset(preset_name)
        if success:
            logger.info("Preset cargado: %s", preset_name)
            # Sincronizar modo si el preset es de crucetas
            if "CRUCETA" in preset_name.upper():
                self._mode = MODE_CRUCETAS
            else:
                self._mode = MODE_CONDUCCION

            self._update_led_color_from_config()
            self.send_led_color(self._current_led_color)
        return success

    def cycle_presets(self) -> str:
        """
        Alterna de forma rápida entre presets guardados (ej. F1 RACING <-> F1 RACING CRUCETAS).
        """
        current_preset = self.config_manager.get("active_preset", "Personalizado")
        prev_preset = self.config_manager.get("previous_preset", "Personalizado")
        presets = self.config_manager.get_presets_list()

        if prev_preset == current_preset or prev_preset not in presets:
            others = [p for p in presets if p != current_preset]
            next_preset = others[0] if others else "Personalizado"
        else:
            next_preset = prev_preset

        self.load_preset(next_preset)
        self.config_manager.save()
        return next_preset

    # =========================================================================
    # Control de LED RGB
    # =========================================================================

    def _update_led_color_from_config(self) -> None:
        """Determina el color LED correspondiente según preset o configuración activa."""
        active_preset = self.config_manager.get("active_preset", "Personalizado")
        custom_presets = self.config_manager.get("custom_presets", {})
        color = None

        if active_preset in custom_presets:
            color = custom_presets[active_preset].get("led_color")

        if not color:
            color = self.config_manager.get("led_color", "Azul")

        self._current_led_color = str(color)

    def set_led_color(self, color: str | int) -> None:
        """Actualiza el color del LED en la configuración y lo envía al Arduino."""
        if isinstance(color, int):
            # Buscar nombre de color por código inverso
            inv = {v: k for k, v in LED_COLORS.items()}
            color_name = inv.get(color, "Apagado").capitalize()
        else:
            color_name = color.strip().capitalize()

        self._current_led_color = color_name
        self.config_manager.set("led_color", color_name)
        self.send_led_color(color)

    def send_led_color(self, color: str | int) -> None:
        """Encola la transmisión de un comando de color LED (0xBB 0x66 <código>)."""
        packet = encode_led_command(color)
        self._pending_led_command = packet

    # =========================================================================
    # Bus Reactivo de Eventos de Entrada (Press-to-Map Wizard)
    # =========================================================================

    def set_input_listener(self, listener: Optional[InputEventListener]) -> None:
        """
        Registra el listener principal para el asistente de mapeo Press-to-Map.
        Al registrarse, actualiza la línea base para ignorar valores estáticos de potenciómetros.
        """
        with self._listener_lock:
            self._input_listeners.clear()
            if listener is not None:
                self._input_listeners.append(listener)
                self._prev_event_axis_values = dict(self._last_raw_axes)

    def add_input_listener(self, listener: InputEventListener) -> None:
        """Añade un callback reactivo al bus de eventos de entrada."""
        with self._listener_lock:
            if listener not in self._input_listeners:
                self._input_listeners.append(listener)
                self._prev_event_axis_values = dict(self._last_raw_axes)

    def remove_input_listener(self, listener: InputEventListener) -> None:
        """Elimina un callback del bus de eventos."""
        with self._listener_lock:
            if listener in self._input_listeners:
                self._input_listeners.remove(listener)

    def set_axis_threshold(self, threshold: int) -> None:
        """Establece el umbral de detección de movimiento de ejes analógicos."""
        self.axis_threshold = max(10, min(500, threshold))

    def _emit_input_event(self, source_type: str, source_id: str, value: int) -> None:
        """Emite un evento de entrada de forma segura sin bloquear el bucle de 100 Hz."""
        with self._listener_lock:
            listeners = list(self._input_listeners)

        for listener in listeners:
            try:
                listener(source_type, source_id, value)
            except Exception as e:
                logger.error("Error en callback de evento de entrada (%s, %s): %s", source_type, source_id, e)

    # =========================================================================
    # Telemetría Thread-Safe y Pulso de Cruceta Virtual
    # =========================================================================

    def get_telemetry(self) -> TelemetrySnapshot:
        """Obtiene una copia atómica e inmutable de la última telemetría calculada."""
        with self._telemetry_lock:
            return self._telemetry_snapshot

    def get_telemetry_dict(self) -> Dict[str, Any]:
        """Obtiene la telemetría en formato diccionario compatible con frontend."""
        return self.get_telemetry().to_dict()

    def trigger_virtual_dpad(self, direction: str, duration_ms: int = 200) -> None:
        """Emite una pulsación temporal de cruceta virtual para mapeo en menús de juegos."""
        if self.gamepad_manager.is_connected:
            self.gamepad_manager.trigger_button_pulse(direction, duration_ms)

    # =========================================================================
    # Bucle de Ejecución a 100 Hz (time.perf_counter() para Zero-Jitter)
    # =========================================================================

    def _run_loop(self) -> None:
        """Bucle principal de ejecución a 100 Hz con reloj monotónico estricto."""
        next_tick = time.perf_counter()

        while self._running:
            loop_start = time.perf_counter()

            # 1. Ejecutar un tick de emulación y procesamiento
            try:
                self._tick()
            except Exception as e:
                logger.error("Excepción no controlada en tick de motor: %s", e, exc_info=True)

            # 2. Control de frecuencia y compensación de deriva temporal (Zero-Jitter)
            next_tick += TARGET_INTERVAL
            now = time.perf_counter()
            sleep_time = next_tick - now

            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                # Si nos retrasamos más de 2 ciclos (ej. pausa de depuración o sobrecarga extrema),
                # reiniciar next_tick para evitar bucles acelerados de recuperación.
                if now - next_tick > TARGET_INTERVAL * 2:
                    next_tick = now

            # 3. Medición de Hz reales
            self._tick_count += 1
            if now - self._hz_timer >= 1.0:
                self._loop_hz = round(self._tick_count / (now - self._hz_timer), 1)
                self._tick_count = 0
                self._hz_timer = now

    def _tick(self) -> None:
        """Ejecuta una iteración completa del motor."""
        now = time.perf_counter()

        # 1. Gestionar reconexión automática si no hay conexión serie
        if self._serial is None or not self._serial.is_open:
            if self.auto_reconnect and (now - self._last_reconnect_attempt >= self._reconnect_interval):
                self._last_reconnect_attempt = now
                self._attempt_connection()
            return

        # 2. Transmisión de comandos LED RGB (inmediato si hay cambio o latido cada 2s)
        self._manage_led_transmission(now)

        # 3. Lectura de bytes entrantes del puerto serie
        chunk = b""
        try:
            in_waiting = self._serial.in_waiting
            if in_waiting > 0:
                chunk = self._serial.read(in_waiting)
            else:
                # Lectura breve con timeout de 5ms para alinearse con el paquete de Arduino
                chunk = self._serial.read(1)
                if chunk and self._serial.in_waiting > 0:
                    chunk += self._serial.read(self._serial.in_waiting)
        except (serial.SerialException, OSError) as e:
            self._handle_disconnect(str(e))
            return

        # 4. Parsear paquetes binarios (0xAA 0x55)
        if chunk:
            packets = self._parser.parse_bytes(chunk)
            for packet in packets:
                steer_raw, accel_raw, brake_raw, buttons = packet
                self.process_packet(steer_raw, accel_raw, brake_raw, buttons)

    def _manage_led_transmission(self, now: float) -> None:
        """Envía comandos de LED o el latido de presencia cada 2 segundos."""
        if not self._serial or not self._serial.is_open:
            return

        cmd_to_send: Optional[bytes] = None
        if self._pending_led_command is not None:
            cmd_to_send = self._pending_led_command
            self._pending_led_command = None
            self._last_led_send_time = now
        elif now - self._last_led_send_time >= HEARTBEAT_INTERVAL:
            # Latido periódico para que Arduino mantenga pcConnected = true
            color_to_keep = "Naranja" if self._mode == MODE_CRUCETAS else self._current_led_color
            cmd_to_send = encode_led_command(color_to_keep)
            self._last_led_send_time = now

        if cmd_to_send:
            try:
                self._serial.write(cmd_to_send)
                self._serial.flush()
            except (serial.SerialException, OSError) as e:
                self._handle_disconnect(f"Error transmitiendo LED: {e}")

    # =========================================================================
    # Procesamiento de Paquetes: DSP + Calibración + Gamepad + Eventos
    # =========================================================================

    def process_bytes(self, chunk: bytes) -> List[Tuple[int, int, int, List[int]]]:
        """Inyecta y procesa bytes crudos directamente (ideal para pruebas y simulación)."""
        packets = self._parser.parse_bytes(chunk)
        for packet in packets:
            self.process_packet(*packet)
        return packets

    def process_packet(self, steer_raw: int, accel_raw: int, brake_raw: int, buttons: List[int]) -> None:
        """
        Procesa un paquete de datos completo recibido de Arduino:
        aplica inversión, DSP, calibración exponencial, mapeo de botones,
        detecta eventos reactivos y actualiza el gamepad virtual y la telemetría.
        """
        # Asegurar longitud correcta de botones
        if len(buttons) < len(PIN_NAMES):
            buttons = list(buttons) + [0] * (len(PIN_NAMES) - len(buttons))
        else:
            buttons = buttons[: len(PIN_NAMES)]

        # Guardar lecturas crudas del hardware
        self._last_raw_axes = {"steer": steer_raw, "accel": accel_raw, "brake": brake_raw}

        # ---------------------------------------------------------------------
        # 1. Bus Reactivo de Eventos de Entrada (Press-to-Map)
        # ---------------------------------------------------------------------
        # Botones: Detectar flanco de subida (0 -> 1)
        for i, pin in enumerate(PIN_NAMES):
            curr_state = buttons[i]
            prev_state = self._prev_raw_buttons[i]
            if curr_state == 1 and prev_state == 0:
                self._emit_input_event("button", pin, 1)
            self._prev_raw_buttons[i] = curr_state

        # Ejes: Detectar cambio acumulado superior al umbral
        for axis_name, curr_val in self._last_raw_axes.items():
            prev_val = self._prev_event_axis_values.get(axis_name, curr_val)
            if abs(curr_val - prev_val) >= self.axis_threshold:
                self._prev_event_axis_values[axis_name] = curr_val
                self._emit_input_event("axis", axis_name, curr_val)

        # ---------------------------------------------------------------------
        # 2. Detección del Botón Físico de Ciclo de Presets
        # ---------------------------------------------------------------------
        cycle_btn_configured = str(self.config_manager.get("preset_cycle_btn", "Ninguno"))
        current_cycle_state = self._get_configured_pin_state(cycle_btn_configured, buttons)
        if current_cycle_state == 1 and self._last_btn_cycle_state == 0:
            self.cycle_presets()
        self._last_btn_cycle_state = current_cycle_state

        # ---------------------------------------------------------------------
        # 3. Aplicar Inversión de Ejes Configurada
        # ---------------------------------------------------------------------
        invert_steer = bool(self.config_manager.get("invert_steer", False))
        invert_accel = bool(self.config_manager.get("invert_accel", False))
        invert_brake = bool(self.config_manager.get("invert_brake", False))

        steer_calc = 1023 - steer_raw if invert_steer else steer_raw
        accel_calc = 1023 - accel_raw if invert_accel else accel_raw
        brake_calc = 1023 - brake_raw if invert_brake else brake_raw

        # Clamping de seguridad
        steer_calc = max(0, min(1023, steer_calc))
        accel_calc = max(0, min(1023, accel_calc))
        brake_calc = max(0, min(1023, brake_calc))

        # ---------------------------------------------------------------------
        # 4. Filtro DSP Anti-Jitter (SteeringFilter)
        # ---------------------------------------------------------------------
        filter_strength = float(self.config_manager.get("filter", 0.0))
        steer_filtered = self._steer_filter.process(steer_calc, filter_strength)

        # ---------------------------------------------------------------------
        # 5. Modelado Matemático de Calibración
        # ---------------------------------------------------------------------
        # Dirección
        val_steer, steer_phys_norm, steer_out_norm = calculate_steering(
            steer=steer_filtered,
            steer_min=int(self.config_manager.get("steer_min", 0)),
            steer_center=int(self.config_manager.get("steer_center", 512)),
            steer_max=int(self.config_manager.get("steer_max", 1023)),
            slope=float(self.config_manager.get("slope", 1.85)),
            sensitivity=float(self.config_manager.get("sensitivity", 1.0)),
            anti_deadzone=float(self.config_manager.get("anti_deadzone", 0.0)),
            rest_deadzone=float(self.config_manager.get("rest_deadzone", 0.01)),
        )

        # Pedales (acelerador y freno)
        deadzone = float(self.config_manager.get("deadzone", 0.13))

        accel_val_trigger, accel_norm = calculate_pedal(
            raw_val=accel_calc,
            val_min=int(self.config_manager.get("accel_min", 0)),
            val_max=int(self.config_manager.get("accel_max", 1023)),
            deadzone=deadzone,
            max_output=255,
        )

        brake_val_trigger, brake_norm = calculate_pedal(
            raw_val=brake_calc,
            val_min=int(self.config_manager.get("brake_min", 0)),
            val_max=int(self.config_manager.get("brake_max", 1023)),
            deadzone=deadzone,
            max_output=255,
        )

        # Indicadores mapeados para interfaz (0..1023)
        gui_steer = max(0, min(1023, int(round(((steer_out_norm + 1.0) / 2.0) * 1023))))
        gui_accel = max(0, min(1023, int(round(accel_norm * 1023))))
        gui_brake = max(0, min(1023, int(round(brake_norm * 1023))))

        # Ángulo visual del volante (-90° a +90°)
        steer_angle = round(steer_out_norm * 90.0, 1)
        throttle_pct = round(accel_norm * 100.0, 1)
        brake_pct = round(brake_norm * 100.0, 1)

        # ---------------------------------------------------------------------
        # 6. Mapeo de Botones Activos y Modo Crucetas
        # ---------------------------------------------------------------------
        active_buttons: Set[str] = set()

        for i, pin in enumerate(PIN_NAMES):
            if buttons[i] == 1:
                cfg_key = PIN_TO_CONFIG_KEY.get(pin)
                if cfg_key:
                    target_action = str(self.config_manager.get(cfg_key, "Ninguno"))
                    if target_action and target_action != "Ninguno":
                        active_buttons.add(target_action)

        # Lógica de Crucetas / D-Pad
        final_steer = val_steer
        final_accel = accel_val_trigger
        final_brake = brake_val_trigger

        if self._mode == MODE_CRUCETAS and self._dpad_from_axes:
            # Traducir ejes analógicos a pulsaciones virtuales del D-Pad
            if steer_out_norm < -0.35:
                active_buttons.add("D-Pad LEFT")
            elif steer_out_norm > 0.35:
                active_buttons.add("D-Pad RIGHT")

            if accel_norm > 0.25:
                active_buttons.add("D-Pad UP")
            if brake_norm > 0.25:
                active_buttons.add("D-Pad DOWN")

            # Suprimir ejes analógicos para no pelear con la selección de menús en juegos
            if self._dpad_suppress_axes:
                final_steer = 0
                final_accel = 0
                final_brake = 0

        # ---------------------------------------------------------------------
        # 7. Actualización del Gamepad Virtual
        # ---------------------------------------------------------------------
        steer_target = str(self.config_manager.get("steer_target", "Left Stick X"))
        accel_target = str(self.config_manager.get("accel_target", "Right Trigger (RT)"))
        brake_target = str(self.config_manager.get("brake_target", "Left Trigger (LT)"))

        if self.gamepad_manager.is_connected:
            self.gamepad_manager.apply_inputs(
                steer_target=steer_target,
                steer_val=final_steer,
                accel_target=accel_target,
                accel_val=final_accel,
                brake_target=brake_target,
                brake_val=final_brake,
                active_buttons=active_buttons,
            )

        # ---------------------------------------------------------------------
        # 8. Creación de Instantánea Atómica de Telemetría
        # ---------------------------------------------------------------------
        snapshot = TelemetrySnapshot(
            timestamp=time.time(),
            status=self._status,
            active_port=self._active_port,
            mode=self._mode,
            preset=str(self.config_manager.get("active_preset", "Personalizado")),
            led_color=self._current_led_color,
            raw_steer=steer_raw,
            raw_accel=accel_raw,
            raw_brake=brake_raw,
            raw_buttons=tuple(buttons),
            mapped_steer=gui_steer,
            mapped_accel=gui_accel,
            mapped_brake=gui_brake,
            mapped_buttons=tuple(buttons),
            steer_angle=steer_angle,
            steer_phys_norm=round(steer_phys_norm, 4),
            steer_out_norm=round(steer_out_norm, 4),
            throttle_pct=throttle_pct,
            brake_pct=brake_pct,
            gamepad_steer=final_steer,
            gamepad_accel=final_accel,
            gamepad_brake=final_brake,
            active_gamepad_buttons=tuple(sorted(active_buttons)),
            loop_hz=self._loop_hz,
            gamepad_connected=self.gamepad_manager.is_connected,
            error_message=self._last_error,
        )

        with self._telemetry_lock:
            self._telemetry_snapshot = snapshot

    def _get_configured_pin_state(self, configured_name: str, btn_states: List[int]) -> int:
        """Devuelve el estado (0 o 1) del pin configurado como disparador."""
        if not configured_name or configured_name in ("Ninguno", "None"):
            return 0

        clean = configured_name.strip()
        pin = label_to_pin(clean)

        if pin in PIN_NAMES:
            idx = PIN_NAMES.index(pin)
            if idx < len(btn_states):
                return btn_states[idx]

        return 0

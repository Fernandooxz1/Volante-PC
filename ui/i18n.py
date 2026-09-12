"""
Módulo de Internacionalización (i18n) para Volante-PC.
Soporte bilingüe completo para Español (ES) e Inglés (EN).
Terminología técnica de ingeniería y simracing sin emojis.
Implementa el patrón Observer y señal Qt para suscripción reactiva de componentes de interfaz.
"""

import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

# Verificación condicional de Qt para soporte opcional de señales PyQt / PySide
try:
    from PyQt6.QtCore import QObject, pyqtSignal

    class _QtSignalEmitter(QObject):
        language_changed = pyqtSignal(str)

    _qt_emitter: Optional[_QtSignalEmitter] = _QtSignalEmitter()
except Exception:
    try:
        from PySide6.QtCore import QObject, Signal as pyqtSignal

        class _QtSignalEmitter(QObject):
            language_changed = pyqtSignal(str)

        _qt_emitter = _QtSignalEmitter()
    except Exception:
        _qt_emitter = None

# Lista de idiomas disponibles y códigos
SUPPORTED_LANGUAGES = ("es", "en")
DEFAULT_LANGUAGE = "es"

LANGUAGE_METADATA = {
    "es": {
        "code": "es",
        "name": "Español",
        "native_name": "Español",
        "flag_code": "ES"
    },
    "en": {
        "code": "en",
        "name": "English",
        "native_name": "English",
        "flag_code": "US"
    }
}

# Diccionario completo de traducciones sin emojis
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "es": {
        # General y Encabezados
        "app.title": "Volante-PC Simracing Controller",
        "app.subtitle": "Panel de Control, Telemetría y Emulación de Hardware",
        "app.version": "Versión",

        # Estado y Conexión
        "status.connected": "Conectado",
        "status.disconnected": "Desconectado",
        "status.connecting": "Conectando...",
        "status.port": "Puerto Serie",
        "status.baudrate": "Velocidad de Transmisión",
        "status.emulating": "Emulando",
        "status.stopped": "Detenido",
        "status.virtual_gamepad": "Gamepad Virtual",
        "status.virtual_gamepad_active": "Gamepad Virtual Activo",
        "status.virtual_gamepad_inactive": "Gamepad Virtual Inactivo",
        "status.device_ready": "Dispositivo Preparado",
        "status.device_error": "Fallo de Dispositivo",
        "status.communication_error": "Error de Comunicación Serie",
        "status.packet_rate": "Tasa de Paquetes",
        "status.packets_per_sec": "{rate} Hz",
        "status.sync_lost": "Sincronización Perdida",
        "status.firmware_ok": "Firmware Sincronizado",
        "status.scanning_ports": "Escaneando puertos serie disponibles...",
        "status.no_ports_found": "No se detectaron puertos serie válidos",
        "status.auto_detecting": "Autodetectando Arduino...",
        "status.connect": "Conectar",
        "status.disconnect": "Desconectar",
        "status.start_emulation": "Iniciar Emulación",
        "status.stop_emulation": "Detener Emulación",
        "status.refresh_ports": "Actualizar Puertos",

        # Telemetría y Ejes
        "telemetry.title": "Telemetría en Vivo",
        "telemetry.steering": "DIRECCIÓN",
        "telemetry.throttle": "ACELERADOR",
        "telemetry.brake": "FRENO",
        "telemetry.clutch": "EMBRAGUE",
        "telemetry.degrees": "GRADOS",
        "telemetry.raw": "RAW",
        "telemetry.mapped": "MAPEO",
        "telemetry.gear": "MARCHA",
        "telemetry.mode": "MODO",
        "telemetry.calibrated": "CALIBRADO",
        "telemetry.input": "ENTRADA",
        "telemetry.output": "SALIDA",
        "telemetry.axis": "EJE",
        "telemetry.percentage": "PORCENTAJE",
        "telemetry.response_curve": "CURVA DE RESPUESTA",
        "telemetry.deadzone_active": "ZONA MUERTA ACTIVA",
        "telemetry.clipping": "SATURACIÓN (CLIPPING)",

        # Deslizadores y Parámetros de Sintonía
        "sliders.title": "Ajuste Dinámico y Filtros",
        "sliders.sensitivity": "Sensibilidad",
        "sliders.sensitivity_desc": "Multiplicador de respuesta general del volante. Valores altos aumentan la rapidez de respuesta ante pequeños giros.",
        "sliders.slope": "Pendiente de Linealidad",
        "sliders.slope_desc": "Curvatura de respuesta exponencial: valores menores a 1.0 ofrecen respuesta progresiva, 1.0 es lineal pura, mayores a 1.0 otorgan máxima precisión en el centro.",
        "sliders.anti_deadzone": "Anti-Zona Muerta",
        "sliders.anti_deadzone_desc": "Compensa el umbral de zona muerta interna del juego simulador, suprimiendo el recorrido neutro inicial del volante.",
        "sliders.deadzone": "Zona Muerta de Pedales",
        "sliders.deadzone_desc": "Umbral de recorrido de reposo en pedales para eliminar activaciones involuntarias o ruido residual de potenciómetros.",
        "sliders.filter": "Filtro Anti-Ruido",
        "sliders.filter_desc": "Filtro de media móvil exponencial para eliminar oscilaciones, jitter y ruido analógico de la señal.",
        "sliders.throttle_deadzone": "Zona Muerta de Acelerador",
        "sliders.throttle_deadzone_desc": "Umbral de reposo para el acelerador para ignorar presión involuntaria del pie.",
        "sliders.brake_deadzone": "Zona Muerta de Freno",
        "sliders.brake_deadzone_desc": "Umbral de reposo para el freno para evitar frenadas accidentales sin pulsar.",
        "sliders.steering_deadzone": "Zona Muerta Central de Dirección",
        "sliders.steering_deadzone_desc": "Tolerancia neutra en el centro para evitar desvíos al rodar en línea recta.",

        # Presets
        "presets.title": "Gestor de Presets",
        "presets.save": "Guardar",
        "presets.save_preset": "Guardar Preset",
        "presets.load": "Cargar",
        "presets.load_preset": "Cargar Preset",
        "presets.delete": "Eliminar",
        "presets.delete_preset": "Eliminar Preset",
        "presets.name": "Nombre",
        "presets.preset_name": "Nombre del Preset",
        "presets.active_preset": "Preset Activo",
        "presets.previous_preset": "Preset Anterior",
        "presets.custom_presets": "Presets Personalizados",
        "presets.factory_presets": "Presets de Fábrica",
        "presets.enter_name": "Ingrese el nombre del nuevo preset...",
        "presets.save_success": "Preset '{name}' guardado correctamente.",
        "presets.load_success": "Preset '{name}' aplicado con éxito.",
        "presets.delete_success": "Preset '{name}' eliminado.",
        "presets.confirm_delete_title": "Confirmar Eliminación",
        "presets.confirm_delete_msg": "¿Está seguro de eliminar permanentemente el preset '{name}'?",
        "presets.overwrite_title": "Confirmar Sobrescritura",
        "presets.overwrite_msg": "El preset '{name}' ya existe. ¿Desea sobrescribir su configuración?",
        "presets.cannot_delete_default": "Los presets de fábrica no pueden ser eliminados.",
        "presets.invalid_name": "El nombre del preset no puede estar vacío ni contener caracteres reservados.",

        # Mapeo de Acciones y Botones Xbox
        "mapping.title": "Asignación de Pines y Gamepad",
        "mapping.steer_target": "Asignación Eje Dirección",
        "mapping.accel_target": "Asignación Eje Acelerador",
        "mapping.brake_target": "Asignación Eje Freno",
        "mapping.invert_steer": "Invertir Eje de Dirección",
        "mapping.invert_accel": "Invertir Eje de Acelerador",
        "mapping.invert_brake": "Invertir Eje de Freno",
        "mapping.preset_cycle_btn": "Botón Cambio de Preset",
        "mapping.led_color": "Color de LED Indicador",
        "mapping.digital_pins": "Pulsadores Digitales",
        "mapping.unassigned": "Ninguno",
        "mapping.btn_a": "Button A",
        "mapping.btn_b": "Button B",
        "mapping.btn_x": "Button X",
        "mapping.btn_y": "Button Y",
        "mapping.btn_lb": "Button LB (Left Shoulder)",
        "mapping.btn_rb": "Button RB (Right Shoulder)",
        "mapping.btn_start": "Button Start",
        "mapping.btn_back": "Button Back",
        "mapping.btn_l3": "Button L3 (Left Click)",
        "mapping.btn_r3": "Button R3 (Right Click)",
        "mapping.dpad_up": "D-Pad UP",
        "mapping.dpad_down": "D-Pad DOWN",
        "mapping.dpad_left": "D-Pad LEFT",
        "mapping.dpad_right": "D-Pad RIGHT",
        "mapping.stick_lx": "Left Stick X",
        "mapping.stick_ly": "Left Stick Y",
        "mapping.stick_rx": "Right Stick X",
        "mapping.stick_ry": "Right Stick Y",
        "mapping.trigger_lt": "Left Trigger (LT)",
        "mapping.trigger_rt": "Right Trigger (RT)",

        # Pines Físicos Arduino
        "pins.d2": "Pin D2",
        "pins.d3": "Pin D3",
        "pins.d4": "Pin D4",
        "pins.d5": "Pin D5",
        "pins.d6": "Pin D6",
        "pins.d7": "Pin D7",
        "pins.d8": "Pin D8",
        "pins.pa3": "Pin A3",
        "pins.pa5": "Pin A5",
        "pins.pa4": "Pin A4",
        "pins.p12": "Pin D12",

        # Colores LED RGB
        "led.off": "Apagado",
        "led.red": "Rojo",
        "led.green": "Verde",
        "led.blue": "Azul",
        "led.yellow": "Amarillo",
        "led.violet": "Violeta",
        "led.cyan": "Cian",
        "led.orange": "Naranja",

        # Asistentes de Calibración (Wizards)
        "wizards.title": "Asistente de Calibración de Hardware",
        "wizards.steer_title": "Calibración del Volante",
        "wizards.pedals_title": "Calibración de Pedales",
        "wizards.buttons_title": "Asistente de Detección de Botones",
        "wizards.press_button": "Presione el pulsador físico",
        "wizards.press_button_instruction": "Presione cualquier pulsador físico en el volante o pedalera para detectar su pin correspondiente...",
        "wizards.turn_max_left": "Girar al tope máximo izquierdo",
        "wizards.turn_max_left_instruction": "Gire el volante completamente hacia el tope izquierdo y manténgalo allí...",
        "wizards.center": "Centrar el volante",
        "wizards.center_instruction": "Sitúe el volante en la posición neutra central (0 grados) y suéltelo...",
        "wizards.turn_max_right": "Girar al tope máximo derecho",
        "wizards.turn_max_right_instruction": "Gire el volante completamente hacia el tope derecho y manténgalo allí...",
        "wizards.pedals_release": "Soltar todos los pedales",
        "wizards.pedals_release_instruction": "Suelte completamente los pedales de acelerador y freno para calibrar el reposo...",
        "wizards.pedals_press": "Presionar pedal a fondo",
        "wizards.pedals_press_instruction": "Presione el pedal indicado a fondo de su recorrido físico y manténgalo...",
        "wizards.throttle_release": "Soltar acelerador",
        "wizards.throttle_press": "Pisar acelerador a fondo",
        "wizards.brake_release": "Soltar freno",
        "wizards.brake_press": "Pisar freno a fondo",
        "wizards.waiting_input": "Esperando señal física de hardware...",
        "wizards.detected_pin": "Pin detectado: {pin}",
        "wizards.step_indicator": "Paso {current} de {total}",
        "wizards.next": "Siguiente",
        "wizards.back": "Anterior",
        "wizards.cancel": "Cancelar",
        "wizards.finish": "Finalizar Calibración",
        "wizards.success": "Calibración completada y almacenada satisfactoriamente.",
        "wizards.timeout": "Tiempo de espera agotado sin detectar señal.",

        # Nombres de Temas Visuales
        "themes.title": "Tema Visual y Acento",
        "themes.accent_color": "Color de Acento",
        "themes.oled_black": "OLED Black",
        "themes.cyan_neon": "Cyan Neon",
        "themes.racing_red": "Racing Red",
        "themes.acid_green": "Porsche Acid Green",
        "themes.mclaren_orange": "McLaren Orange",
        "themes.tokyo_violet": "Tokyo Night Violet",
        "themes.custom_hex": "Color Personalizado (Hex)",
        "themes.custom_color_picker": "Seleccionar Color Personalizado",
        "themes.invalid_hex": "Código de color hexadecimal no válido. Formato requerido: #RRGGBB",
        "themes.language": "Idioma de Interfaz",

        # Términos Comunes y Botones
        "common.ok": "Aceptar",
        "common.cancel": "Cancelar",
        "common.apply": "Aplicar",
        "common.save": "Guardar",
        "common.reset": "Restablecer",
        "common.close": "Cerrar",
        "common.delete": "Eliminar",
        "common.edit": "Editar",
        "common.refresh": "Actualizar",
        "common.warning": "Advertencia",
        "common.error": "Error",
        "common.success": "Éxito",
        "common.settings": "Configuración",
        "common.controls": "Controles",
        "common.calibration": "Calibración",
        "common.telemetry": "Telemetría",
        "common.general": "General",
        "common.hardware": "Hardware",
        "common.profiles": "Perfiles",
        "common.system": "Sistema",
        "common.status": "Estado",
    },

    "en": {
        # General & Headers
        "app.title": "Volante-PC Simracing Controller",
        "app.subtitle": "Hardware Emulation, Telemetry and Tuning Dashboard",
        "app.version": "Version",

        # Status & Connection
        "status.connected": "Connected",
        "status.disconnected": "Disconnected",
        "status.connecting": "Connecting...",
        "status.port": "Serial Port",
        "status.baudrate": "Baud Rate",
        "status.emulating": "Emulating",
        "status.stopped": "Stopped",
        "status.virtual_gamepad": "Virtual Gamepad",
        "status.virtual_gamepad_active": "Virtual Gamepad Active",
        "status.virtual_gamepad_inactive": "Virtual Gamepad Inactive",
        "status.device_ready": "Device Ready",
        "status.device_error": "Device Fault",
        "status.communication_error": "Serial Communication Error",
        "status.packet_rate": "Packet Rate",
        "status.packets_per_sec": "{rate} Hz",
        "status.sync_lost": "Synchronization Lost",
        "status.firmware_ok": "Firmware Synchronized",
        "status.scanning_ports": "Scanning available serial ports...",
        "status.no_ports_found": "No valid serial ports detected",
        "status.auto_detecting": "Auto-detecting Arduino...",
        "status.connect": "Connect",
        "status.disconnect": "Disconnect",
        "status.start_emulation": "Start Emulation",
        "status.stop_emulation": "Stop Emulation",
        "status.refresh_ports": "Refresh Ports",

        # Telemetry & Axes
        "telemetry.title": "Live Telemetry",
        "telemetry.steering": "STEERING",
        "telemetry.throttle": "THROTTLE",
        "telemetry.brake": "BRAKE",
        "telemetry.clutch": "CLUTCH",
        "telemetry.degrees": "DEGREES",
        "telemetry.raw": "RAW",
        "telemetry.mapped": "MAPPED",
        "telemetry.gear": "GEAR",
        "telemetry.mode": "MODE",
        "telemetry.calibrated": "CALIBRATED",
        "telemetry.input": "INPUT",
        "telemetry.output": "OUTPUT",
        "telemetry.axis": "AXIS",
        "telemetry.percentage": "PERCENTAGE",
        "telemetry.response_curve": "RESPONSE CURVE",
        "telemetry.deadzone_active": "DEADZONE ACTIVE",
        "telemetry.clipping": "CLIPPING",

        # Sliders & Tuning Parameters
        "sliders.title": "Response Dynamics and Filtering",
        "sliders.sensitivity": "Sensitivity",
        "sliders.sensitivity_desc": "Overall steering response multiplier. Higher values increase steering responsiveness to wheel movement.",
        "sliders.slope": "Linearity Slope",
        "sliders.slope_desc": "Exponential curve: values below 1.0 give progressive response, 1.0 is strictly linear, above 1.0 grants surgical center precision.",
        "sliders.anti_deadzone": "Anti-Deadzone",
        "sliders.anti_deadzone_desc": "Compensates for game simulator internal controller deadzone by bypassing the initial dead movement.",
        "sliders.deadzone": "Pedal Deadzone",
        "sliders.deadzone_desc": "Resting pedal threshold to eliminate unintended activations and potentiometer signal noise.",
        "sliders.filter": "Anti-Jitter Filter",
        "sliders.filter_desc": "Exponential moving average filter that dampens potentiometer noise, oscillations and jitter.",
        "sliders.throttle_deadzone": "Throttle Deadzone",
        "sliders.throttle_deadzone_desc": "Rest threshold for the accelerator pedal to prevent unintended inputs.",
        "sliders.brake_deadzone": "Brake Deadzone",
        "sliders.brake_deadzone_desc": "Rest threshold for the brake pedal to eliminate accidental foot drag.",
        "sliders.steering_deadzone": "Steering Rest Deadzone",
        "sliders.steering_deadzone_desc": "Center deadband tolerance to prevent drift when traveling in a straight line.",

        # Presets
        "presets.title": "Configuration Presets",
        "presets.save": "Save",
        "presets.save_preset": "Save Preset",
        "presets.load": "Load",
        "presets.load_preset": "Load Preset",
        "presets.delete": "Delete",
        "presets.delete_preset": "Delete Preset",
        "presets.name": "Name",
        "presets.preset_name": "Preset Name",
        "presets.active_preset": "Active Preset",
        "presets.previous_preset": "Previous Preset",
        "presets.custom_presets": "Custom Presets",
        "presets.factory_presets": "Factory Presets",
        "presets.enter_name": "Enter new preset name...",
        "presets.save_success": "Preset '{name}' saved successfully.",
        "presets.load_success": "Preset '{name}' loaded successfully.",
        "presets.delete_success": "Preset '{name}' deleted.",
        "presets.confirm_delete_title": "Confirm Deletion",
        "presets.confirm_delete_msg": "Are you sure you want to permanently delete preset '{name}'?",
        "presets.overwrite_title": "Confirm Overwrite",
        "presets.overwrite_msg": "Preset '{name}' already exists. Do you want to overwrite it?",
        "presets.cannot_delete_default": "Factory presets cannot be deleted.",
        "presets.invalid_name": "Preset name cannot be empty or contain reserved characters.",

        # Mapping Actions & Xbox Buttons
        "mapping.title": "Pin Assignment and Gamepad Mapping",
        "mapping.steer_target": "Steering Axis Assignment",
        "mapping.accel_target": "Throttle Axis Assignment",
        "mapping.brake_target": "Brake Axis Assignment",
        "mapping.invert_steer": "Invert Steering Axis",
        "mapping.invert_accel": "Invert Throttle Axis",
        "mapping.invert_brake": "Invert Brake Axis",
        "mapping.preset_cycle_btn": "Preset Cycle Button",
        "mapping.led_color": "RGB LED Indicator Color",
        "mapping.digital_pins": "Digital Button Inputs",
        "mapping.unassigned": "None",
        "mapping.btn_a": "Button A",
        "mapping.btn_b": "Button B",
        "mapping.btn_x": "Button X",
        "mapping.btn_y": "Button Y",
        "mapping.btn_lb": "Button LB (Left Shoulder)",
        "mapping.btn_rb": "Button RB (Right Shoulder)",
        "mapping.btn_start": "Button Start",
        "mapping.btn_back": "Button Back",
        "mapping.btn_l3": "Button L3 (Left Click)",
        "mapping.btn_r3": "Button R3 (Right Click)",
        "mapping.dpad_up": "D-Pad UP",
        "mapping.dpad_down": "D-Pad DOWN",
        "mapping.dpad_left": "D-Pad LEFT",
        "mapping.dpad_right": "D-Pad RIGHT",
        "mapping.stick_lx": "Left Stick X",
        "mapping.stick_ly": "Left Stick Y",
        "mapping.stick_rx": "Right Stick X",
        "mapping.stick_ry": "Right Stick Y",
        "mapping.trigger_lt": "Left Trigger (LT)",
        "mapping.trigger_rt": "Right Trigger (RT)",

        # Arduino Physical Pins
        "pins.d2": "Pin D2",
        "pins.d3": "Pin D3",
        "pins.d4": "Pin D4",
        "pins.d5": "Pin D5",
        "pins.d6": "Pin D6",
        "pins.d7": "Pin D7",
        "pins.d8": "Pin D8",
        "pins.pa3": "Pin A3",
        "pins.pa5": "Pin A5",
        "pins.pa4": "Pin A4",
        "pins.p12": "Pin D12",

        # RGB LED Colors
        "led.off": "Off",
        "led.red": "Red",
        "led.green": "Green",
        "led.blue": "Blue",
        "led.yellow": "Yellow",
        "led.violet": "Violet",
        "led.cyan": "Cyan",
        "led.orange": "Orange",

        # Calibration Wizards
        "wizards.title": "Hardware Calibration Wizard",
        "wizards.steer_title": "Steering Wheel Range Calibration",
        "wizards.pedals_title": "Pedal Travel Calibration",
        "wizards.buttons_title": "Button Detection and Mapping Wizard",
        "wizards.press_button": "Press physical button",
        "wizards.press_button_instruction": "Press any physical button on your wheel or pedal box to detect its input pin...",
        "wizards.turn_max_left": "Turn max left",
        "wizards.turn_max_left_instruction": "Turn the steering wheel to maximum left lock and hold it...",
        "wizards.center": "Center steering wheel",
        "wizards.center_instruction": "Position the steering wheel at neutral center (0 degrees) and release...",
        "wizards.turn_max_right": "Turn max right",
        "wizards.turn_max_right_instruction": "Turn the steering wheel to maximum right lock and hold it...",
        "wizards.pedals_release": "Release all pedals",
        "wizards.pedals_release_instruction": "Release throttle and brake pedals completely to calibrate rest position...",
        "wizards.pedals_press": "Depress pedal to maximum",
        "wizards.pedals_press_instruction": "Depress the indicated pedal to maximum physical travel and hold...",
        "wizards.throttle_release": "Release throttle",
        "wizards.throttle_press": "Depress throttle to 100%",
        "wizards.brake_release": "Release brake",
        "wizards.brake_press": "Depress brake to 100%",
        "wizards.waiting_input": "Waiting for physical hardware input...",
        "wizards.detected_pin": "Detected pin: {pin}",
        "wizards.step_indicator": "Step {current} of {total}",
        "wizards.next": "Next",
        "wizards.back": "Back",
        "wizards.cancel": "Cancel",
        "wizards.finish": "Finish Calibration",
        "wizards.success": "Calibration successfully completed and saved.",
        "wizards.timeout": "Calibration timed out without input signal.",

        # Visual Theme Names
        "themes.title": "Visual Theme and Accent",
        "themes.accent_color": "Accent Color",
        "themes.oled_black": "OLED Black",
        "themes.cyan_neon": "Cyan Neon",
        "themes.racing_red": "Racing Red",
        "themes.acid_green": "Porsche Acid Green",
        "themes.mclaren_orange": "McLaren Orange",
        "themes.tokyo_violet": "Tokyo Night Violet",
        "themes.custom_hex": "Custom Color (Hex)",
        "themes.custom_color_picker": "Select Custom Accent Color",
        "themes.invalid_hex": "Invalid hexadecimal color code. Expected format: #RRGGBB",
        "themes.language": "Interface Language",

        # Common Terms & Buttons
        "common.ok": "OK",
        "common.cancel": "Cancel",
        "common.apply": "Apply",
        "common.save": "Save",
        "common.reset": "Reset",
        "common.close": "Close",
        "common.delete": "Delete",
        "common.edit": "Edit",
        "common.refresh": "Refresh",
        "common.warning": "Warning",
        "common.error": "Error",
        "common.success": "Success",
        "common.settings": "Settings",
        "common.controls": "Controls",
        "common.calibration": "Calibration",
        "common.telemetry": "Telemetry",
        "common.general": "General",
        "common.hardware": "Hardware",
        "common.profiles": "Profiles",
        "common.system": "System",
        "common.status": "Status",
    }
}

# Diccionario de alias directos para lookup plano común
_ALIASES: Dict[str, str] = {
    # Status
    "connected": "status.connected",
    "disconnected": "status.disconnected",
    "connecting": "status.connecting",
    "port": "status.port",
    "baudrate": "status.baudrate",
    "baud rate": "status.baudrate",
    "emulating": "status.emulating",
    "stopped": "status.stopped",
    "virtual gamepad": "status.virtual_gamepad",
    "connect": "status.connect",
    "disconnect": "status.disconnect",

    # Telemetry
    "steering": "telemetry.steering",
    "throttle": "telemetry.throttle",
    "brake": "telemetry.brake",
    "clutch": "telemetry.clutch",
    "degrees": "telemetry.degrees",
    "raw": "telemetry.raw",
    "mapped": "telemetry.mapped",
    "gear": "telemetry.gear",
    "mode": "telemetry.mode",
    "calibrated": "telemetry.calibrated",
    "input": "telemetry.input",
    "output": "telemetry.output",
    "axis": "telemetry.axis",
    "percentage": "telemetry.percentage",

    # Sliders
    "sensitivity": "sliders.sensitivity",
    "linearity slope": "sliders.slope",
    "slope": "sliders.slope",
    "anti-deadzone": "sliders.anti_deadzone",
    "antideadzone": "sliders.anti_deadzone",
    "pedal deadzone": "sliders.deadzone",
    "deadzone": "sliders.deadzone",
    "anti-jitter filter": "sliders.filter",
    "filter": "sliders.filter",

    # Presets
    "save": "presets.save",
    "load": "presets.load",
    "delete": "presets.delete",
    "name": "presets.name",
    "save preset": "presets.save_preset",
    "load preset": "presets.load_preset",
    "delete preset": "presets.delete_preset",
    "preset name": "presets.preset_name",
    "active preset": "presets.active_preset",

    # Actions
    "button a": "mapping.btn_a",
    "button b": "mapping.btn_b",
    "button x": "mapping.btn_x",
    "button y": "mapping.btn_y",
    "button lb (left shoulder)": "mapping.btn_lb",
    "button rb (right shoulder)": "mapping.btn_rb",
    "button start": "mapping.btn_start",
    "button back": "mapping.btn_back",
    "button l3 (left click)": "mapping.btn_l3",
    "button r3 (right click)": "mapping.btn_r3",
    "d-pad up": "mapping.dpad_up",
    "d-pad down": "mapping.dpad_down",
    "d-pad left": "mapping.dpad_left",
    "d-pad right": "mapping.dpad_right",
    "left stick x": "mapping.stick_lx",
    "left stick y": "mapping.stick_ly",
    "right stick x": "mapping.stick_rx",
    "right stick y": "mapping.stick_ry",
    "left trigger (lt)": "mapping.trigger_lt",
    "right trigger (rt)": "mapping.trigger_rt",
    "none": "mapping.unassigned",
    "ninguno": "mapping.unassigned",

    # Wizards
    "press physical button": "wizards.press_button",
    "turn max left": "wizards.turn_max_left",
    "center": "wizards.center",
    "turn max right": "wizards.turn_max_right",
    "pedals release": "wizards.pedals_release",
    "pedals press": "wizards.pedals_press",

    # Themes
    "oled black": "themes.oled_black",
    "cyan neon": "themes.cyan_neon",
    "racing red": "themes.racing_red",
    "porsche acid green": "themes.acid_green",
    "acid green": "themes.acid_green",
    "mclaren orange": "themes.mclaren_orange",
    "tokyo night violet": "themes.tokyo_violet",
    "tokyo violet": "themes.tokyo_violet",
}


class I18nManager:
    """
    Gestor global de internacionalización thread-safe.
    Implementa suscripciones sincrónicas (Observer) y compatibilidad con señales Qt.
    """

    def __init__(self, initial_language: str = DEFAULT_LANGUAGE):
        self._lock = threading.RLock()
        self._current_language = initial_language if initial_language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        self._listeners: List[Callable[[str], None]] = []

    @property
    def current_language(self) -> str:
        with self._lock:
            return self._current_language

    def set_language(self, lang: str, force: bool = False) -> None:
        """Cambia el idioma activo y notifica a todos los observadores registrados."""
        normalized = lang.strip().lower()
        if normalized not in SUPPORTED_LANGUAGES:
            normalized = DEFAULT_LANGUAGE

        with self._lock:
            if self._current_language == normalized and not force:
                return
            self._current_language = normalized
            listeners_snapshot = list(self._listeners)

        # Emitir señal Qt si está disponible
        if _qt_emitter is not None:
            try:
                _qt_emitter.language_changed.emit(normalized)
            except Exception:
                pass

        # Notificar observadores estándar
        for callback in listeners_snapshot:
            try:
                callback(normalized)
            except Exception as e:
                print(f"[i18n] Error ejecutando callback de cambio de idioma: {e}")

    def get_language(self) -> str:
        with self._lock:
            return self._current_language

    def subscribe(self, callback: Callable[[str], None], notify_immediate: bool = False) -> Callable[[], None]:
        """
        Suscribe una función callback para ser notificada al cambiar el idioma.
        Si notify_immediate es True, ejecuta el callback inmediatamente con el idioma actual.
        Retorna una función para cancelar la suscripción.
        """
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)
            current = self._current_language

        if notify_immediate:
            try:
                callback(current)
            except Exception as e:
                print(f"[i18n] Error en notificación inmediata: {e}")

        def unsubscribe():
            self.unsubscribe(callback)

        return unsubscribe

    def unsubscribe(self, callback: Callable[[str], None]) -> None:
        """Elimina una función callback previamente registrada."""
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def translate(self, key: str, **kwargs: Any) -> str:
        """
        Traduce una clave al idioma actual, con soporte para interpolación segura de formato.
        Si la clave no existe, intenta el idioma alternativo o devuelve la clave original.
        """
        if not key:
            return ""

        with self._lock:
            lang = self._current_language

        # 1. Búsqueda exacta directa
        text = TRANSLATIONS.get(lang, {}).get(key)

        # 2. Búsqueda mediante tabla de alias
        if text is None:
            alias_key = _ALIASES.get(key.strip().lower())
            if alias_key:
                text = TRANSLATIONS.get(lang, {}).get(alias_key)

        # 3. Fallback al idioma alternativo (EN si ES, o ES si EN)
        if text is None:
            fallback_lang = "en" if lang == "es" else "es"
            text = TRANSLATIONS.get(fallback_lang, {}).get(key)
            if text is None and alias_key:
                text = TRANSLATIONS.get(fallback_lang, {}).get(alias_key)

        # 4. Fallback final: devolver la clave
        if text is None:
            text = key

        # Interpolación segura de kwargs
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text

        return text

    def get_qt_signal(self):
        """Retorna la señal pyqtSignal / Signal para integración nativa en componentes PyQt/PySide."""
        if _qt_emitter is not None:
            return _qt_emitter.language_changed
        return None


# Instancia singleton del gestor
_manager = I18nManager()


# Funciones de conveniencia globales
def tr(key: str, **kwargs: Any) -> str:
    """Función global de traducción."""
    return _manager.translate(key, **kwargs)


def set_language(lang: str, force: bool = False) -> None:
    """Establece el idioma activo global ('es' o 'en')."""
    _manager.set_language(lang, force=force)


def get_language() -> str:
    """Obtiene el código del idioma activo global ('es' o 'en')."""
    return _manager.get_language()


def subscribe(callback: Callable[[str], None], notify_immediate: bool = False) -> Callable[[], None]:
    """Suscribe un componente a eventos de cambio de idioma."""
    return _manager.subscribe(callback, notify_immediate=notify_immediate)


def unsubscribe(callback: Callable[[str], None]) -> None:
    """Cancela la suscripción a eventos de cambio de idioma."""
    _manager.unsubscribe(callback)


def get_signal():
    """Retorna la señal Qt si está disponible."""
    return _manager.get_qt_signal()


def get_available_languages() -> List[Tuple[str, str]]:
    """Retorna la lista de idiomas disponibles como tuplas (código, nombre nativo)."""
    return [(k, v["native_name"]) for k, v in LANGUAGE_METADATA.items()]

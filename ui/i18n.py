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

        # Calibrador de Hardware (Calibration Wizard)
        "calib.window_title": "ASISTENTE DE CALIBRACIÓN // LÍMITES DE HARDWARE",
        "calib.header_title": "CALIBRACIÓN DEL SISTEMA // ASISTENTE DE LÍMITES",
        "calib.step_header": "PASO {current:02d} DE {total:02d}",
        "calib.completed": "COMPLETADO",

        # Ejes y Barras de Sensores
        "calib.axis_steer": "Eje del Volante",
        "calib.axis_throttle": "Pedal de Acelerador",
        "calib.axis_brake": "Pedal de Freno",
        "calib.marker_min": "MÍN",
        "calib.marker_ctr": "CTR",
        "calib.marker_max": "MÁX",

        # Pasos del Asistente
        "calib.step1_title": "PASO 1: VOLANTE - LÍMITE IZQUIERDO",
        "calib.step1_instructions": "Gire el volante completamente hacia el tope IZQUIERDO y manténgalo firme. Observe la lectura del sensor y presione 'Guardar Límite Izquierdo'.",
        "calib.btn_save_left": "Guardar Límite Izquierdo",
        "calib.step1_feedback": "Gire el volante al tope izquierdo y presione 'Guardar Límite Izquierdo'.",
        "calib.feedback_left_saved": "Límite Izquierdo del Volante: {val}",

        "calib.step2_title": "PASO 2: VOLANTE - POSICIÓN CENTRAL",
        "calib.step2_instructions": "Suelte el volante en su posición física CENTRAL neutra. Asegúrese de que esté alineado al centro y presione 'Guardar Centro'.",
        "calib.btn_save_center": "Guardar Posición Central",
        "calib.step2_feedback": "Centre el volante y presione 'Guardar Posición Central'.",
        "calib.feedback_center_saved": "Posición Central del Volante: {val}",

        "calib.step3_title": "PASO 3: VOLANTE - LÍMITE DERECHO",
        "calib.step3_instructions": "Gire el volante completamente hacia el tope DERECHO y manténgalo firme. Observe la lectura del sensor y presione 'Guardar Límite Derecho'.",
        "calib.btn_save_right": "Guardar Límite Derecho",
        "calib.step3_feedback": "Gire el volante al tope derecho y presione 'Guardar Límite Derecho'.",
        "calib.feedback_right_saved": "Límite Derecho del Volante: {val}",

        "calib.step4_title": "PASO 4: PEDALES - LÍMITES DE ACELERADOR Y FRENO",
        "calib.step4_instructions": "1. Suelte ambos pedales por completo -> Haga clic en 'Guardar Límites de Reposo'.\n2. Pise el Acelerador a fondo -> Haga clic en 'Guardar Acelerador Máx'.\n3. Pise el Freno a fondo -> Haga clic en 'Guardar Freno Máx'.\nO active 'Autodetección de Recorrido' y accione ambos pedales a fondo.",
        "calib.btn_save_rest": "Guardar Límites de Reposo (Mín)",
        "calib.btn_save_throttle_max": "Guardar Acelerador Máx",
        "calib.btn_save_brake_max": "Guardar Freno Máx",
        "calib.btn_auto_detect_on": "Autodetección de Recorrido: ACTIVADO",
        "calib.btn_auto_detect_off": "Autodetección de Recorrido: DESACTIVADO",
        "calib.step4_feedback": "Calibre el reposo y los límites de recorrido completo de los pedales.",
        "calib.feedback_rest_saved": "Límites de Reposo -> Acelerador: {accel} | Freno: {brake}",
        "calib.feedback_throttle_saved": "Límite Máximo de Acelerador: {val}",
        "calib.feedback_brake_saved": "Límite Máximo de Freno: {val}",
        "calib.feedback_pump_pedals": "Accione ambos pedales a fondo para registrar el rango de recorrido.",
        "calib.feedback_envelope_captured": "Rango capturado -> Acelerador: [{a_min}..{a_max}], Freno: [{b_min}..{b_max}]",
        "calib.feedback_tracking": "[SEGUIMIENTO] Acelerador: {a_min}..{a_max} | Freno: {b_min}..{b_max}",

        # Resumen y Navegación
        "calib.summary_title": "CALIBRACIÓN COMPLETADA // RESUMEN DE LÍMITES DE SENSORES",
        "calib.summary_instructions": "Verifique los límites calibrados abajo. Haga clic en 'Aplicar y Guardar Calibración' para registrar los cambios en la configuración.",
        "calib.summary_steer_axis": "EJE DE DIRECCIÓN (VOLANTE):",
        "calib.summary_left_lock": "Tope Físico Izquierdo:",
        "calib.summary_center": "Centro Físico:",
        "calib.summary_right_lock": "Tope Físico Derecho:",
        "calib.summary_calibrated_range": "Rango Calibrado:",
        "calib.summary_span": "Amplitud",
        "calib.summary_travel": "Recorrido",
        "calib.summary_counts": "cuentas",
        "calib.summary_axis_inversion": "Inversión de Eje:",
        "calib.summary_inverted_auto": "INVERTIDO (Autocorregido)",
        "calib.summary_normal": "NORMAL",
        "calib.summary_inverted": "INVERTIDO",
        "calib.summary_throttle_pedal": "PEDAL DE ACELERADOR:",
        "calib.summary_brake_pedal": "PEDAL DE FRENO:",
        "calib.summary_rest_to_full": "Reposo (Mín) -> Fondo:",
        "calib.summary_invert_throttle": "Invertir Acelerador:",
        "calib.summary_invert_brake": "Invertir Freno:",

        "calib.btn_prev": "Paso Anterior",
        "calib.btn_next": "Paso Siguiente",
        "calib.btn_apply_save": "Aplicar y Guardar Calibración",
        "calib.tag_saved": "GUARDADO",
        "calib.tag_error": "ERROR",
        "calib.error_steer_span": "Rango de dirección demasiado estrecho (mín. 50 cuentas)",
        "calib.error_accel_span": "Recorrido de acelerador demasiado estrecho (mín. 20 cuentas)",
        "calib.error_brake_span": "Recorrido de freno demasiado estrecho (mín. 20 cuentas)",
        "calib.initial_feedback": "Telemetría de sensores activa en tiempo real. Siga las instrucciones superiores.",
        "calib.config_saved_success": "Calibración escrita correctamente en config_volante.json.",

        # Asistente de Mapeo de Entradas (Mapping Wizard)
        "mapping_wizard.window_title": "ASISTENTE DE ASIGNACIÓN DE ENTRADAS",
        "mapping_wizard.header_title": "CONFIGURACIÓN DEL SISTEMA // ASISTENTE DE ASIGNACIÓN",
        "mapping_wizard.step_counter": "PASO {current:02d} DE {total:02d}",
        "mapping_wizard.completed": "COMPLETADO",

        # Insignias de Tipo de Entrada
        "mapping_wizard.badge_analog_steer": "[EJE ANALÓGICO DE DIRECCIÓN]",
        "mapping_wizard.badge_analog_pedal": "[GATILLO / PEDAL ANALÓGICO]",
        "mapping_wizard.badge_digital_button": "[PULSADOR DIGITAL DEL VOLANTE]",
        "mapping_wizard.badge_preset": "[TECLA RÁPIDA DE PRESET]",
        "mapping_wizard.badge_clutch": "[PEDALERA // D12]",
        "mapping_wizard.badge_led": "[ARDUINO // ILUMINACIÓN LED]",

        # Descripciones de Controles
        "mapping_wizard.desc_brake": "Entrada analógica de freno. Pise firmemente el pedal de freno o presione el pulsador designado.",
        "mapping_wizard.desc_throttle": "Entrada analógica de acelerador. Pise firmemente el pedal de acelerador o presione el pulsador designado.",
        "mapping_wizard.desc_steer": "Eje principal de dirección. Gire el volante al menos un 25% hacia cualquier lado.",
        "mapping_wizard.desc_btn_a": "Acción principal / Aceptar / Reducción secundaria. Presione el pulsador en el volante.",
        "mapping_wizard.desc_btn_b": "Acción secundaria / Cancelar / Marcha atrás. Presione el pulsador en el volante.",
        "mapping_wizard.desc_btn_x": "Botón de acción / Embrague / Freno de mano. Presione el pulsador en el volante.",
        "mapping_wizard.desc_btn_y": "Botón de acción / Mirar atrás / DRS. Presione el pulsador en el volante.",
        "mapping_wizard.desc_btn_lb": "Leva izquierda / Reducción de marcha. Accione la leva izquierda o presione el pulsador.",
        "mapping_wizard.desc_btn_rb": "Leva derecha / Subida de marcha. Accione la leva derecha o presione el pulsador.",
        "mapping_wizard.desc_btn_l3": "Botón L3 (Click stick izquierdo). Presione el pulsador en el volante.",
        "mapping_wizard.desc_btn_r3": "Botón R3 (Click stick derecho). Presione el pulsador en el volante.",
        "mapping_wizard.desc_btn_start": "Pausa / Menú del juego / Encendido. Presione el pulsador en el volante.",
        "mapping_wizard.desc_btn_back": "Telemetría / Cambiar vista / Limitador de pit. Presione el pulsador en el volante.",
        "mapping_wizard.desc_dpad_up": "Cruceta Arriba / Reparto de frenada delantero / Navegación MFD. Presione el selector direccional.",
        "mapping_wizard.desc_dpad_down": "Cruceta Abajo / Reparto de frenada trasero / Navegación MFD. Presione el selector direccional.",
        "mapping_wizard.desc_dpad_left": "Cruceta Izquierda / Mezcla pobre de combustible / Selección MFD. Presione el selector direccional.",
        "mapping_wizard.desc_dpad_right": "Cruceta Derecha / Mezcla rica de combustible / Selección MFD. Presione el selector direccional.",
        "mapping_wizard.desc_preset": "Pulse el botón que alternará rápidamente entre el preset actual y el anterior (estilo Q en CS).",
        "mapping_wizard.desc_clutch": "Pulse el pedal de embrague (generalmente conectado al pin D12).",
        "mapping_wizard.desc_led_color": "Seleccione el color de iluminación del LED RGB para este preset.",
        "mapping_wizard.desc_default": "Presione el pulsador físico o accione el pedal para vincular.",

        # Estados y Monitor de Hardware
        "mapping_wizard.awaiting_input": "Esperando señal física de hardware... Presione un botón o pedal",
        "mapping_wizard.tag_mapped": "ASIGNADO",
        "mapping_wizard.live_monitor": "HARDWARE EN VIVO: Dirección: {steer:4d} | Acelerador: {accel:4d} | Freno: {brake:4d} | Activo: {pins}",
        "mapping_wizard.none": "Ninguno",

        # Asignaciones Detectadas
        "mapping_wizard.assigned_steer": "Eje de Dirección (Left Stick X)",
        "mapping_wizard.assigned_throttle": "Pedal de Acelerador (Right Trigger)",
        "mapping_wizard.assigned_brake": "Pedal de Freno (Left Trigger)",
        "mapping_wizard.assigned_axis": "Eje {axis}",
        "mapping_wizard.assigned_pin": "Pin {pin}",

        # Botones de Navegación del Asistente
        "mapping_wizard.btn_back": "Control Anterior",
        "mapping_wizard.btn_skip": "Omitir Control",
        "mapping_wizard.btn_cancel": "Cancelar y Salir",
        "mapping_wizard.btn_finish": "Guardar y Finalizar",

        # Resumen Final de Asignación
        "mapping_wizard.summary_title": "ASIGNACIÓN COMPLETADA // RESUMEN DE HARDWARE",
        "mapping_wizard.col_target": "CONTROL OBJETIVO",
        "mapping_wizard.col_assigned": "HARDWARE ASIGNADO",
        "mapping_wizard.col_status": "ESTADO",
        "mapping_wizard.status_active": "[OK] ACTIVO",
        "mapping_wizard.val_preserved": "Conservado / Omitido",
        "mapping_wizard.val_existing": "Existente",

        # Asignador Rápido de Botón Individual (SingleButtonMapperDialog)
        "mapping_wizard.quick_bind_window": "ASIGNACIÓN RÁPIDA // {target}",
        "mapping_wizard.quick_bind_header": "ASIGNACIÓN RÁPIDA DE BOTÓN INDIVIDUAL",
        "mapping_wizard.quick_bind_target": "DESTINO: {target}",
        "mapping_wizard.quick_bind_awaiting": "Esperando señal física de hardware... Presione un botón en el volante",

        # Diálogo de Temas y Localización (Theme Dialog)
        "themes.dialog_title": "PREFERENCIAS DEL SISTEMA // TEMA Y LOCALIZACIÓN",
        "themes.subtitle": "SELECCIONAR COLOR DE ACENTO DEL COCKPIT E IDIOMA",
        "themes.color_presets_title": "PRESETS DE COLOR DE ACENTO",
        "themes.custom_color_btn": "Color Personalizado...",
        "themes.custom_color_dialog": "Seleccionar Color de Acento Motorsport",
        "themes.live_preview_title": "VISTA PREVIA DE INTERFAZ Y TELEMETRÍA",
        "themes.preview_badge": "DDU TELEMETRÍA",
        "themes.preview_status": "EN LÍNEA // 100 HZ",
        "themes.preview_btn": "ACCIÓN PRINCIPAL",
        "themes.preview_slider_lbl": "INDICADOR TELEMETRÍA // 78%",
        "themes.language_title": "IDIOMA DE LA INTERFAZ",
        "themes.lang_en": "[EN] English",
        "themes.lang_es": "[ES] Español",
        "themes.active_tag": "[ACTIVO]",
        "themes.custom_tag": "[PERSONALIZADO]",
        "themes.btn_apply": "Aplicar",
        "themes.btn_save": "Guardar y Cerrar",
        "themes.btn_cancel": "Cancelar",

        # Términos Comunes y Botones
        "common.ok": "Aceptar",
        "common.cancel": "Cancelar",
        "common.apply": "Aplicar",
        "common.save": "Guardar",
        "common.save_and_close": "Guardar y Cerrar",
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

        # Hardware Calibration Wizard
        "calib.window_title": "CALIBRATION WIZARD // HARDWARE LIMITS",
        "calib.header_title": "SYSTEM CALIBRATION // SENSOR LIMITS WIZARD",
        "calib.step_header": "STEP {current:02d} OF {total:02d}",
        "calib.completed": "COMPLETED",

        # Axes & Sensor Bars
        "calib.axis_steer": "Steering Wheel Axis",
        "calib.axis_throttle": "Throttle Pedal",
        "calib.axis_brake": "Brake Pedal",
        "calib.marker_min": "MIN",
        "calib.marker_ctr": "CTR",
        "calib.marker_max": "MAX",

        # Wizard Steps
        "calib.step1_title": "STEP 1: STEERING WHEEL - LEFT LIMIT",
        "calib.step1_instructions": "Turn the steering wheel fully to the MAXIMUM LEFT lock position and hold it firmly. Observe the live sensor reading below, then click 'Save Left Limit'.",
        "calib.btn_save_left": "Save Left Limit",
        "calib.step1_feedback": "Turn wheel fully left, then click 'Save Left Limit'.",
        "calib.feedback_left_saved": "Steering Left Limit: {val}",

        "calib.step2_title": "STEP 2: STEERING WHEEL - CENTER POSITION",
        "calib.step2_instructions": "Release the steering wheel completely to its physical CENTER neutral position. Ensure the wheel is straight, then click 'Save Center'.",
        "calib.btn_save_center": "Save Center Position",
        "calib.step2_feedback": "Center the wheel, then click 'Save Center Position'.",
        "calib.feedback_center_saved": "Steering Center Position: {val}",

        "calib.step3_title": "STEP 3: STEERING WHEEL - RIGHT LIMIT",
        "calib.step3_instructions": "Turn the steering wheel fully to the MAXIMUM RIGHT lock position and hold it firmly. Observe the live sensor reading below, then click 'Save Right Limit'.",
        "calib.btn_save_right": "Save Right Limit",
        "calib.step3_feedback": "Turn wheel fully right, then click 'Save Right Limit'.",
        "calib.feedback_right_saved": "Steering Right Limit: {val}",

        "calib.step4_title": "STEP 4: PEDALS - THROTTLE & BRAKE LIMITS",
        "calib.step4_instructions": "1. Release both pedals completely -> Click 'Save Rest Limits'.\n2. Press Throttle fully -> Click 'Save Throttle Max'.\n3. Press Brake fully -> Click 'Save Brake Max'.\nOr toggle 'Auto-Detect Travel' and pump both pedals through full stroke.",
        "calib.btn_save_rest": "Save Rest Limits (Min)",
        "calib.btn_save_throttle_max": "Save Throttle Max",
        "calib.btn_save_brake_max": "Save Brake Max",
        "calib.btn_auto_detect_on": "Auto-Detect Travel: ON",
        "calib.btn_auto_detect_off": "Auto-Detect Travel: OFF",
        "calib.step4_feedback": "Calibrate pedal rest and full travel limits.",
        "calib.feedback_rest_saved": "Rest Limits -> Throttle: {accel} | Brake: {brake}",
        "calib.feedback_throttle_saved": "Throttle Max Limit: {val}",
        "calib.feedback_brake_saved": "Brake Max Limit: {val}",
        "calib.feedback_pump_pedals": "Pump both pedals fully to register travel envelope.",
        "calib.feedback_envelope_captured": "Envelope captured -> Throttle: [{a_min}..{a_max}], Brake: [{b_min}..{b_max}]",
        "calib.feedback_tracking": "[TRACKING] Accel: {a_min}..{a_max} | Brake: {b_min}..{b_max}",

        # Summary & Navigation
        "calib.summary_title": "CALIBRATION COMPLETE // SENSOR LIMITS SUMMARY",
        "calib.summary_instructions": "Verify the calibrated limits below. Click 'Apply & Save Calibration' to commit changes to system configuration.",
        "calib.summary_steer_axis": "STEERING WHEEL AXIS:",
        "calib.summary_left_lock": "Physical Left Lock:",
        "calib.summary_center": "Physical Center:",
        "calib.summary_right_lock": "Physical Right Lock:",
        "calib.summary_calibrated_range": "Calibrated Min/Max:",
        "calib.summary_span": "Span",
        "calib.summary_travel": "Travel",
        "calib.summary_counts": "counts",
        "calib.summary_axis_inversion": "Axis Inversion:",
        "calib.summary_inverted_auto": "INVERTED (Auto-corrected)",
        "calib.summary_normal": "NORMAL",
        "calib.summary_inverted": "INVERTED",
        "calib.summary_throttle_pedal": "THROTTLE PEDAL:",
        "calib.summary_brake_pedal": "BRAKE PEDAL:",
        "calib.summary_rest_to_full": "Rest (Min) -> Full:",
        "calib.summary_invert_throttle": "Invert Throttle:",
        "calib.summary_invert_brake": "Invert Brake:",

        "calib.btn_prev": "Previous Step",
        "calib.btn_next": "Next Step",
        "calib.btn_apply_save": "Apply & Save Calibration",
        "calib.tag_saved": "SAVED",
        "calib.tag_error": "ERROR",
        "calib.error_steer_span": "Steering range too narrow (min 50 counts)",
        "calib.error_accel_span": "Throttle travel too narrow (min 20 counts)",
        "calib.error_brake_span": "Brake travel too narrow (min 20 counts)",
        "calib.initial_feedback": "Real-time sensor feedback active. Follow instruction above.",
        "calib.config_saved_success": "Calibration successfully written to config_volante.json.",

        # Input Mapping Wizard
        "mapping_wizard.window_title": "INPUT MAPPING WIZARD",
        "mapping_wizard.header_title": "SYSTEM CONFIGURATION // INPUT MAPPING WIZARD",
        "mapping_wizard.step_counter": "STEP {current:02d} OF {total:02d}",
        "mapping_wizard.completed": "COMPLETED",

        # Input Type Badges
        "mapping_wizard.badge_analog_steer": "[ANALOG STEERING AXIS]",
        "mapping_wizard.badge_analog_pedal": "[ANALOG TRIGGER / PEDAL]",
        "mapping_wizard.badge_digital_button": "[DIGITAL WHEEL BUTTON]",
        "mapping_wizard.badge_preset": "[QUICK PRESET TOGGLE]",
        "mapping_wizard.badge_clutch": "[PEDALS // D12 CLUTCH]",
        "mapping_wizard.badge_led": "[ARDUINO // RGB LED COLOR]",

        # Control Descriptions
        "mapping_wizard.desc_brake": "Analog brake input. Depress brake pedal firmly or press designated button.",
        "mapping_wizard.desc_throttle": "Analog throttle input. Depress throttle pedal firmly or press designated button.",
        "mapping_wizard.desc_steer": "Primary steering axis. Rotate steering wheel at least 25% in either direction.",
        "mapping_wizard.desc_btn_a": "Primary action / accept / downshift secondary. Press physical wheel button.",
        "mapping_wizard.desc_btn_b": "Secondary action / cancel / reverse. Press physical wheel button.",
        "mapping_wizard.desc_btn_x": "Action button / clutch / handbrake. Press physical wheel button.",
        "mapping_wizard.desc_btn_y": "Action button / look back / DRS. Press physical wheel button.",
        "mapping_wizard.desc_btn_lb": "Left paddle shifter / downshift. Pull left paddle or press button.",
        "mapping_wizard.desc_btn_rb": "Right paddle shifter / upshift. Pull right paddle or press button.",
        "mapping_wizard.desc_btn_l3": "Button L3 (Left thumbstick click). Press physical wheel button.",
        "mapping_wizard.desc_btn_r3": "Button R3 (Right thumbstick click). Press physical wheel button.",
        "mapping_wizard.desc_btn_start": "Pause / Game menu / Ignition. Press physical button.",
        "mapping_wizard.desc_btn_back": "Telemetry overlay / Change view / Pit limiter. Press physical button.",
        "mapping_wizard.desc_dpad_up": "Directional up / Brake bias forward / MFD nav. Press directional switch.",
        "mapping_wizard.desc_dpad_down": "Directional down / Brake bias rearward / MFD nav. Press directional switch.",
        "mapping_wizard.desc_dpad_left": "Directional left / Fuel mix lean / MFD select. Press directional switch.",
        "mapping_wizard.desc_dpad_right": "Directional right / Fuel mix rich / MFD select. Press directional switch.",
        "mapping_wizard.desc_preset": "Press the button that will toggle quickly between this preset and previous (CS 'Q' style).",
        "mapping_wizard.desc_clutch": "Press the clutch pedal (typically wired to pin D12).",
        "mapping_wizard.desc_led_color": "Select RGB LED lighting color on Arduino for this preset.",
        "mapping_wizard.desc_default": "Press physical button or move pedal to bind.",

        # Status & Hardware Monitor
        "mapping_wizard.awaiting_input": "Awaiting hardware input... Press button on wheel or pedal",
        "mapping_wizard.tag_mapped": "MAPPED",
        "mapping_wizard.live_monitor": "LIVE HARDWARE: Steer: {steer:4d} | Accel: {accel:4d} | Brake: {brake:4d} | Active: {pins}",
        "mapping_wizard.none": "None",

        # Detected Bindings
        "mapping_wizard.assigned_steer": "Steering Axis (Left Stick X)",
        "mapping_wizard.assigned_throttle": "Throttle Pedal (Right Trigger)",
        "mapping_wizard.assigned_brake": "Brake Pedal (Left Trigger)",
        "mapping_wizard.assigned_axis": "Axis {axis}",
        "mapping_wizard.assigned_pin": "Pin {pin}",

        # Navigation Buttons
        "mapping_wizard.btn_back": "Previous Control",
        "mapping_wizard.btn_skip": "Skip Control",
        "mapping_wizard.btn_cancel": "Cancel & Exit",
        "mapping_wizard.btn_finish": "Save & Finish",

        # Summary View
        "mapping_wizard.summary_title": "MAPPING COMPLETE // HARDWARE ASSIGNMENT SUMMARY",
        "mapping_wizard.col_target": "TARGET CONTROL",
        "mapping_wizard.col_assigned": "ASSIGNED HARDWARE",
        "mapping_wizard.col_status": "STATUS",
        "mapping_wizard.status_active": "[OK] ACTIVE",
        "mapping_wizard.val_preserved": "Preserved / Skipped",
        "mapping_wizard.val_existing": "Existing",

        # Single Button Mapper Dialog
        "mapping_wizard.quick_bind_window": "QUICK BIND // {target}",
        "mapping_wizard.quick_bind_header": "SINGLE BUTTON QUICK BIND",
        "mapping_wizard.quick_bind_target": "TARGET: {target}",
        "mapping_wizard.quick_bind_awaiting": "Awaiting hardware input... Press button on wheel",

        # Theme & Localization Dialog
        "themes.dialog_title": "SYSTEM PREFERENCES // THEME & LOCALIZATION",
        "themes.subtitle": "SELECT COCKPIT DISPLAY ACCENT AND INTERFACE LANGUAGE",
        "themes.color_presets_title": "ACCENT COLOR PRESETS",
        "themes.custom_color_btn": "Custom Color...",
        "themes.custom_color_dialog": "Select Custom Motorsport Accent Color",
        "themes.live_preview_title": "LIVE HUD & TELEMETRY PREVIEW",
        "themes.preview_badge": "TELEMETRY DDU",
        "themes.preview_status": "ONLINE // 100 HZ",
        "themes.preview_btn": "PRIMARY ACTION",
        "themes.preview_slider_lbl": "TELEMETRY GAUGE // 78%",
        "themes.language_title": "INTERFACE LANGUAGE",
        "themes.lang_en": "[EN] English",
        "themes.lang_es": "[ES] Español",
        "themes.active_tag": "[ACTIVE]",
        "themes.custom_tag": "[CUSTOM]",
        "themes.btn_apply": "Apply",
        "themes.btn_save": "Save & Close",
        "themes.btn_cancel": "Cancel",

        # Common Terms & Buttons
        "common.ok": "OK",
        "common.cancel": "Cancel",
        "common.apply": "Apply",
        "common.save": "Save",
        "common.save_and_close": "Save & Close",
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

    # Axes & Sensor Bars
    "steering wheel axis": "calib.axis_steer",
    "throttle pedal": "calib.axis_throttle",
    "brake pedal": "calib.axis_brake",
    "save and close": "common.save_and_close",
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

    def translate(self, key: str, lang: Optional[str] = None, **kwargs: Any) -> str:
        """
        Traduce una clave al idioma actual o especificado, con soporte para interpolación segura de formato.
        Si la clave no existe, intenta el idioma alternativo o devuelve la clave original.
        """
        if not key:
            return ""

        with self._lock:
            active_lang = lang if (lang and lang in SUPPORTED_LANGUAGES) else self._current_language

        # 1. Búsqueda exacta directa
        text = TRANSLATIONS.get(active_lang, {}).get(key)

        # 2. Búsqueda mediante tabla de alias
        if text is None:
            alias_key = _ALIASES.get(key.strip().lower())
            if alias_key:
                text = TRANSLATIONS.get(active_lang, {}).get(alias_key)

        # 3. Fallback al idioma alternativo (EN si ES, o ES si EN)
        if text is None:
            fallback_lang = "en" if active_lang == "es" else "es"
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
i18n = _manager


def get_i18n_manager() -> I18nManager:
    """Retorna la instancia singleton de I18nManager."""
    return _manager


# Funciones de conveniencia globales
def tr(key: str, lang: Optional[str] = None, **kwargs: Any) -> str:
    """Función global de traducción."""
    return _manager.translate(key, lang=lang, **kwargs)


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

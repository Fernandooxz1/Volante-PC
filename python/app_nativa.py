#!/usr/bin/env python3
# ==========================================================================
# app_nativa.py — Versión nativa del emulador Volante-PC con PyWebView
#
# Reemplaza la arquitectura HTTP + WebSocket de gui_web.py por una ventana
# nativa GTK+WebKit que carga directamente web/index.html.
# La lógica de emulación (lectura serie, vgamepad, calibración) es idéntica.
#
# La comunicación con el frontend se realiza a través de la clase EmuladorAPI
# expuesta como window.pywebview.api en JavaScript.
# ==========================================================================

import os
import sys
import time
import json
import threading
import serial
import serial.tools.list_ports
import vgamepad as vg
import webview

# ==========================================================================
# RESOLUCIÓN DE RUTAS (COMPATIBILIDAD CON PYINSTALLER / FROZEN)
# ==========================================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_config_path():
    """Retorna la ruta del archivo de configuración en el directorio del usuario y lo inicializa si es necesario."""
    if os.name == 'nt':
        appdata = os.getenv('APPDATA')
        config_dir = os.path.join(appdata, 'VolantePC') if appdata else os.path.expanduser('~')
    else:
        config_dir = os.path.join(os.path.expanduser('~'), '.config', 'volante_pc')
    
    user_config_path = os.path.join(config_dir, 'config_volante.json')
    
    if os.path.exists(user_config_path):
        return user_config_path
        
    # Buscar el de origen
    if getattr(sys, 'frozen', False):
        default_config_path = os.path.join(sys._MEIPASS, 'config_volante.json')
        if not os.path.exists(default_config_path):
            default_config_path = os.path.join(os.path.dirname(sys.executable), 'config_volante.json')
    else:
        default_config_path = os.path.join(BASE_DIR, 'config_volante.json')
        
    if os.path.exists(default_config_path):
        try:
            os.makedirs(config_dir, exist_ok=True)
            import shutil
            shutil.copy2(default_config_path, user_config_path)
            print(f"Configuración por defecto copiada a: {user_config_path}")
            return user_config_path
        except Exception as e:
            print(f"Error copiando configuración inicial: {e}")
            
    return default_config_path

CONFIG_FILE_PATH = get_config_path()

# ==========================================================================
# MAPEO DE BOTONES DE GAMEPAD (XBOX 360)
# ==========================================================================
BUTTON_MAP = {
    "Button Start": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    "Button Back": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    "Button A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "Button B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "Button X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "Button Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "Button LB (Left Shoulder)": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "Button RB (Right Shoulder)": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    "Button L3 (Left Click)": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    "Button R3 (Right Click)": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    "D-Pad UP": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    "D-Pad DOWN": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    "D-Pad LEFT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    "D-Pad RIGHT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    "Ninguno": None
}

# ==========================================================================
# ESTADO GLOBAL COMPARTIDO (THREAD-SAFE)
# ==========================================================================
state_lock = threading.Lock()

# Variables de Emulación
is_emulating = False
selected_port = None
emulation_thread = None
serial_conn = None
virtual_gamepad = None

# Estado de botones virtuales del D-pad para mapeo
virtual_btn_states = {
    "D-Pad UP": 0,
    "D-Pad DOWN": 0,
    "D-Pad LEFT": 0,
    "D-Pad RIGHT": 0
}

# Ajustes de calibración activos
calib_config = {
    "sensitivity": 0.25,
    "slope": 0.65,
    "anti_deadzone": 0.0,
    "deadzone": 0.23,
    "filter": 0.55,
    "steer_target": "Left Stick X",
    "accel_target": "Right Trigger (RT)",
    "brake_target": "Left Trigger (LT)",
    "btn_d2_target": "Ninguno",  # Mantenido por compatibilidad
    "steer_min": 0,
    "steer_center": 512,
    "steer_max": 1023,
    # Mapeo de botones individuales (Pines 2 al 11)
    "btn_map_p2": "Ninguno",
    "btn_map_p3": "Ninguno",
    "btn_map_p4": "Ninguno",
    "btn_map_p5": "Ninguno",
    "btn_map_p6": "Ninguno",
    "btn_map_p7": "Ninguno",
    "btn_map_p8": "Ninguno",
    "btn_map_p9": "Ninguno",
    "btn_map_p10": "Ninguno",
    "btn_map_p11": "Ninguno",
    "preset_cycle_btn": "Ninguno",
    "active_preset": "Personalizado",
    "previous_preset": "Personalizado",
    "custom_presets": {}
}

# Última lectura de dirección para filtro EMA
last_filtered_steer = 512

# ==========================================================================
# BUFFERS DE TELEMETRÍA Y LOGS PARA POLLING DESDE JAVASCRIPT
# ==========================================================================
_telemetry_buffer = None   # Último dict de telemetría, None si ya fue leído
_log_buffer = []           # Lista de dicts {"text": str, "level": str}

# ==========================================================================
# PERSISTENCIA DE CONFIGURACIÓN
# ==========================================================================
def save_config_to_json():
    """Guarda la configuración activa en config_volante.json de forma segura."""
    with state_lock:
        config_copy = calib_config.copy()
        # Copiar custom_presets por separado para evitar referencia mutable
        if "custom_presets" in calib_config:
            config_copy["custom_presets"] = dict(calib_config["custom_presets"])
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_copy, f, indent=4)
        log_to_buffer(f"Configuración guardada en: {CONFIG_FILE_PATH}", "success")
    except Exception as e:
        print(f"Error guardando configuración JSON: {e}")
        log_to_buffer(f"Error guardando configuración: {e}", "error")


def load_config_from_json():
    """Carga la configuración desde config_volante.json si existe."""
    global calib_config
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                with state_lock:
                    for k, v in saved.items():
                        if k in calib_config:
                            if k == "custom_presets":
                                calib_config[k] = dict(v)
                            else:
                                calib_config[k] = v
            print(f"Configuración cargada con éxito desde: {CONFIG_FILE_PATH}")
            log_to_buffer(f"Configuración cargada desde: {CONFIG_FILE_PATH}", "success")
        except Exception as e:
            print(f"Error cargando configuración JSON: {e}")
            log_to_buffer(f"Error cargando configuración JSON: {e}", "error")

# ==========================================================================
# LOGS Y NOTIFICACIONES (BUFFER EN VEZ DE WEBSOCKET)
# ==========================================================================
def log_to_buffer(text, level="info"):
    """Imprime en terminal Y almacena en el buffer para polling del frontend."""
    color_map = {
        "success": "\033[92m",
        "warn": "\033[93m",
        "error": "\033[91m",
        "info": "\033[94m"
    }
    reset_color = "\033[0m"

    # Imprimir localmente en terminal
    print(f"{color_map.get(level, '')}[LOG - {level.upper()}] {text}{reset_color}")

    # Almacenar en buffer para que JS lo recoja por polling
    with state_lock:
        _log_buffer.append({"text": text, "level": level})

# ==========================================================================
# LÓGICA DE DETECCIÓN Y EMULACIÓN DE HARDWARE (SERIE & GAMEPAD)
# ==========================================================================
def get_available_ports():
    """Retorna una lista de puertos serie activos en el sistema."""
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]


def init_virtual_gamepad():
    """Inicializa la instancia de vgamepad (mando Xbox 360 virtual)."""
    global virtual_gamepad
    try:
        virtual_gamepad = vg.VX360Gamepad()
        log_to_buffer("Gamepad virtual Xbox 360 inicializado correctamente.", "success")
        return True
    except Exception as e:
        log_to_buffer(f"Error fatal inicializando gamepad: {e}", "error")
        if os.name == 'nt':
            log_to_buffer("En Windows asegúrate de tener instalado el driver ViGEmBus.", "warn")
        else:
            log_to_buffer("En Linux asegúrate de tener permisos en /dev/uinput (revisa README.md).", "warn")
        virtual_gamepad = None
        return False


def cycle_presets_native():
    """Alterna entre presets guardados (idéntico a cycle_presets_web de gui_web.py)."""
    global calib_config
    with state_lock:
        current_preset = calib_config.get("active_preset", "Personalizado")
        prev_preset = calib_config.get("previous_preset", "Personalizado")

        # Obtener lista de presets disponibles de forma dinámica
        presets_list = []
        if "custom_presets" in calib_config and calib_config["custom_presets"]:
            presets_list.extend(calib_config["custom_presets"].keys())
        presets_list.append("Personalizado")

        # Si el preset anterior no es válido o es igual al actual, buscar uno diferente al actual
        if prev_preset == current_preset or prev_preset not in presets_list:
            other_presets = [p for p in presets_list if p != current_preset]
            if other_presets:
                prev_preset = other_presets[0]
            else:
                prev_preset = "Personalizado"

        next_preset = prev_preset
        calib_config["previous_preset"] = current_preset
        calib_config["active_preset"] = next_preset

        # Cargar todos los valores del preset seleccionado (ejes y botones)
        if next_preset in calib_config.get("custom_presets", {}):
            p_values = calib_config["custom_presets"][next_preset]
            for k, v in p_values.items():
                if k != "custom_presets" and k in calib_config:
                    calib_config[k] = v

    log_to_buffer(f"Alternando preset de {current_preset} a {next_preset}", "success")

    # Guardar la configuración en disco
    save_config_to_json()


def get_pin_state(pin_name, btn_states):
    """Devuelve el estado de un pin digital dado su nombre ('Pin D2'...'Pin D11')."""
    if pin_name and pin_name.startswith("Pin D"):
        try:
            pin_num = int(pin_name[5:])
            idx = pin_num - 2
            if 0 <= idx < len(btn_states):
                return btn_states[idx]
        except ValueError:
            pass
    return 0

# ==========================================================================
# BUCLE DE EMULACIÓN DE BAJA LATENCIA (CORRE EN HILO DE FONDO)
# ==========================================================================
def emulation_loop(port):
    """Bucle principal de lectura serie + emulación de gamepad.
    Idéntico a gui_web.py pero almacena telemetría en buffer compartido."""
    global is_emulating, serial_conn, last_filtered_steer, virtual_gamepad
    global _telemetry_buffer

    log_to_buffer(f"Abriendo puerto serie {port} a 115200 baudios...", "info")
    try:
        serial_conn = serial.Serial(port, 115200, timeout=1.0)
        serial_conn.reset_input_buffer()
        log_to_buffer(f"Conectado a Arduino en {port} con éxito.", "success")
    except Exception as e:
        log_to_buffer(f"Error abriendo puerto {port}: {e}", "error")
        with state_lock:
            is_emulating = False
        return

    # Iniciar ciclo de lectura binaria
    pressed_buttons = set()
    last_send_time = 0.0
    last_btn_cycle_state = 0

    while True:
        with state_lock:
            if not is_emulating:
                break

        try:
            # Buscar cabecera de sincronización (0xAA, 0x55)
            b1 = serial_conn.read(1)
            if b1 == b'\xaa':
                b2 = serial_conn.read(1)
                if b2 == b'\x55':
                    # Leer datos: 6 bytes (4 de ejes + 2 de botones)
                    data_bytes = serial_conn.read(6)
                    if len(data_bytes) == 6:
                        axes_val = int.from_bytes(data_bytes[0:4], byteorder='little')
                        buttons_val = int.from_bytes(data_bytes[4:6], byteorder='little')

                        # Extraer campos de 10 bits
                        steer_raw = axes_val & 0x3FF
                        accel_raw = (axes_val >> 10) & 0x3FF
                        brake_raw = (axes_val >> 20) & 0x3FF

                        # Extraer los 10 botones individuales (bits 0 a 9)
                        btn_states = []
                        for i in range(10):
                            btn_states.append((buttons_val >> i) & 0x01)

                        # Detectar flanco de subida del botón de alternar preset
                        with state_lock:
                            cycle_btn_name = calib_config.get("preset_cycle_btn", "Ninguno")

                        current_cycle_state = get_pin_state(cycle_btn_name, btn_states)
                        if current_cycle_state == 1 and last_btn_cycle_state == 0:
                            cycle_presets_native()
                        last_btn_cycle_state = current_cycle_state

                        # Clamp de seguridad
                        steer = max(0, min(1023, steer_raw))
                        accel = max(0, min(1023, accel_raw))
                        brake = max(0, min(1023, brake_raw))

                        # Copiar variables de calibración locales de manera segura
                        with state_lock:
                            sensitivity = calib_config["sensitivity"]
                            slope = calib_config["slope"]
                            anti_deadzone = calib_config["anti_deadzone"]
                            deadzone = calib_config["deadzone"]
                            filter_strength = calib_config["filter"]
                            steer_target = calib_config["steer_target"]
                            accel_target = calib_config["accel_target"]
                            brake_target = calib_config["brake_target"]
                            steer_min = calib_config["steer_min"]
                            steer_center = calib_config["steer_center"]
                            steer_max = calib_config["steer_max"]

                            # Botones mapeados individuales
                            btn_map_p2 = calib_config["btn_map_p2"]
                            btn_map_p3 = calib_config["btn_map_p3"]
                            btn_map_p4 = calib_config["btn_map_p4"]
                            btn_map_p5 = calib_config["btn_map_p5"]
                            btn_map_p6 = calib_config["btn_map_p6"]
                            btn_map_p7 = calib_config["btn_map_p7"]
                            btn_map_p8 = calib_config["btn_map_p8"]
                            btn_map_p9 = calib_config["btn_map_p9"]
                            btn_map_p10 = calib_config["btn_map_p10"]
                            btn_map_p11 = calib_config["btn_map_p11"]

                        # 1. Filtro DSP Anti-Ruido (EMA)
                        if filter_strength > 0:
                            max_change = int(15 + (1.0 - filter_strength) * 35)
                            diff = steer - last_filtered_steer
                            if abs(diff) > max_change:
                                steer_step = max_change if diff > 0 else -max_change
                                steer_filtered = last_filtered_steer + steer_step
                            else:
                                steer_filtered = steer

                            alpha = 1.0 - filter_strength
                            steer_smoothed = int(alpha * steer_filtered + (1.0 - alpha) * last_filtered_steer)
                            last_filtered_steer = steer_smoothed
                            steer = steer_smoothed
                        else:
                            last_filtered_steer = steer

                        # 2. Procesar Dirección (Normalizar [-1, 1] usando límites calibrados,
                        #    aplicar Exponencial y Anti-Zona Muerta)
                        if steer < steer_center:
                            denom = steer_center - steer_min
                            x = (steer - steer_center) / float(denom) if denom > 0 else 0.0
                            x = max(-1.0, min(0.0, x))
                        else:
                            denom = steer_max - steer_center
                            x = (steer - steer_center) / float(denom) if denom > 0 else 0.0
                            x = max(0.0, min(1.0, x))

                        # Exponencial: x_expo = sign(x) * (|x| ^ slope)
                        abs_x_raw = abs(x)
                        sign_x_raw = 1.0 if x >= 0 else -1.0
                        x_expo = sign_x_raw * (abs_x_raw ** slope) if abs_x_raw > 0 else 0.0

                        x_sloped = x_expo * sensitivity
                        x_sloped = max(-1.0, min(1.0, x_sloped))

                        abs_x = abs(x_sloped)
                        sign_x = 1.0 if x_sloped >= 0 else -1.0
                        REST_DEADZONE = 0.01

                        if abs_x <= REST_DEADZONE:
                            x_final = 0.0
                        else:
                            scaled = (abs_x - REST_DEADZONE) / (1.0 - REST_DEADZONE)
                            x_final_magnitude = anti_deadzone + (1.0 - anti_deadzone) * scaled
                            x_final = sign_x * x_final_magnitude

                        x_final = max(-1.0, min(1.0, x_final))
                        val_steer_mapped = int(x_final * 32767)

                        # 3. Auxiliar para procesar pedales
                        def get_pedal_val(pedal_in, max_val):
                            deadzone_limit = int(deadzone * 1023)
                            if pedal_in <= deadzone_limit:
                                return 0
                            else:
                                val_scaled = (pedal_in - deadzone_limit) / (1023.0 - deadzone_limit)
                                return int(val_scaled * max_val)

                        # 4. Mapear Salidas
                        left_stick_x = 0
                        left_stick_y = 0
                        right_stick_x = 0
                        right_stick_y = 0
                        left_trigger_val = 0
                        right_trigger_val = 0

                        # Dirección
                        if steer_target == "Left Stick X":
                            left_stick_x = val_steer_mapped
                        elif steer_target == "Right Stick X":
                            right_stick_x = val_steer_mapped
                        elif steer_target == "Left Stick Y":
                            left_stick_y = val_steer_mapped
                        elif steer_target == "Right Stick Y":
                            right_stick_y = val_steer_mapped

                        # Pedales — Acelerador
                        a_val_trigger = get_pedal_val(accel, 255)
                        a_val_stick = get_pedal_val(accel, 32767)

                        if accel_target == "Right Trigger (RT)":
                            right_trigger_val = a_val_trigger
                        elif accel_target == "Left Trigger (LT)":
                            left_trigger_val = a_val_trigger
                        elif accel_target == "Right Stick Y+ (UP)":
                            right_stick_y -= get_pedal_val(accel, 32768)  # Negativo = UP en driver Xbox
                        elif accel_target == "Right Stick Y- (DOWN)":
                            right_stick_y += a_val_stick
                        elif accel_target == "Left Stick Y+ (UP)":
                            left_stick_y -= get_pedal_val(accel, 32768)
                        elif accel_target == "Left Stick Y- (DOWN)":
                            left_stick_y += a_val_stick

                        # Pedales — Freno
                        b_val_trigger = get_pedal_val(brake, 255)
                        b_val_stick = get_pedal_val(brake, 32767)

                        if brake_target == "Left Trigger (LT)":
                            left_trigger_val = b_val_trigger
                        elif brake_target == "Right Trigger (RT)":
                            right_trigger_val = b_val_trigger
                        elif brake_target == "Right Stick Y- (DOWN)":
                            right_stick_y += b_val_stick
                        elif brake_target == "Right Stick Y+ (UP)":
                            right_stick_y -= get_pedal_val(brake, 32768)
                        elif brake_target == "Left Stick Y- (DOWN)":
                            left_stick_y += b_val_stick
                        elif brake_target == "Left Stick Y+ (UP)":
                            left_stick_y -= get_pedal_val(brake, 32768)

                        # Enviar a vgamepad (si inicializado con éxito)
                        if virtual_gamepad:
                            virtual_gamepad.left_joystick(x_value=left_stick_x, y_value=left_stick_y)
                            virtual_gamepad.right_joystick(x_value=right_stick_x, y_value=right_stick_y)
                            virtual_gamepad.left_trigger(value=left_trigger_val)
                            virtual_gamepad.right_trigger(value=right_trigger_val)

                            # Mapear los 10 botones digitales de forma dinámica
                            btn_mappings = [
                                btn_map_p2, btn_map_p3, btn_map_p4, btn_map_p5, btn_map_p6,
                                btn_map_p7, btn_map_p8, btn_map_p9, btn_map_p10, btn_map_p11
                            ]
                            active_buttons = set()
                            for i in range(10):
                                if btn_states[i] == 1:
                                    target = btn_mappings[i]
                                    if target in BUTTON_MAP and BUTTON_MAP[target] is not None:
                                        active_buttons.add(BUTTON_MAP[target])

                            # Agregar botones virtuales del D-pad para mapeo
                            with state_lock:
                                for v_btn, state in virtual_btn_states.items():
                                    if state == 1:
                                        target_button = BUTTON_MAP.get(v_btn)
                                        if target_button is not None:
                                            active_buttons.add(target_button)

                            # Liberar viejos
                            to_release = [b for b in pressed_buttons if b not in active_buttons]
                            for b in to_release:
                                if b is not None:
                                    virtual_gamepad.release_button(button=b)
                                    pressed_buttons.remove(b)

                            # Presionar nuevos
                            for b in active_buttons:
                                if b not in pressed_buttons:
                                    virtual_gamepad.press_button(button=b)
                                    pressed_buttons.add(b)

                            virtual_gamepad.update()

                        # 5. Enviar telemetría al buffer a un máximo de ~60Hz (16ms)
                        now = time.time()
                        if now - last_send_time >= 0.016:
                            last_send_time = now

                            # Valores mapeados escalados a 0-1023 para las barras del front
                            gui_steer = int(((x_final + 1.0) / 2.0) * 1023)
                            gui_accel = get_pedal_val(accel, 1023)
                            gui_brake = get_pedal_val(brake, 1023)

                            telemetry_data = {
                                "raw": {
                                    "steer": steer_raw,
                                    "accel": accel_raw,
                                    "brake": brake_raw,
                                    "buttons": btn_states
                                },
                                "mapped": {
                                    "steer": gui_steer,
                                    "accel": gui_accel,
                                    "brake": gui_brake,
                                    "buttons": btn_states
                                }
                            }

                            with state_lock:
                                _telemetry_buffer = telemetry_data

        except Exception as e:
            log_to_buffer(f"Error procesando datos en loop de hardware: {e}", "error")
            time.sleep(0.1)

    # Limpieza al terminar
    log_to_buffer("Cerrando puerto serie...", "info")
    try:
        # Soltar botones digitales presionados
        if virtual_gamepad:
            for b in pressed_buttons:
                try:
                    virtual_gamepad.release_button(button=b)
                except:
                    pass
            virtual_gamepad.update()

        if serial_conn and serial_conn.is_open:
            serial_conn.close()
    except Exception as e:
        log_to_buffer(f"Error en limpieza del puerto: {e}", "warn")

    log_to_buffer("Emulación detenida con éxito.", "success")

# ==========================================================================
# CLASE API EXPUESTA A JAVASCRIPT VÍA window.pywebview.api
# ==========================================================================
class EmuladorAPI:
    """API nativa que el frontend (app.js) invoca a través de window.pywebview.api.
    Todos los métodos que retornan datos devuelven cadenas JSON."""

    def get_status(self) -> str:
        """Retorna el estado completo actual: emulación, puerto, lista de puertos y config."""
        with state_lock:
            msg = {
                "type": "status",
                "data": {
                    "emulating": is_emulating,
                    "current_port": selected_port,
                    "ports": get_available_ports(),
                    "config": calib_config.copy()
                }
            }
        return json.dumps(msg)

    def refresh_ports(self) -> str:
        """Escanea puertos serie disponibles y retorna la lista."""
        ports = get_available_ports()
        log_to_buffer(f"Buscando puertos serie. Encontrados: {ports}", "info")
        msg = {
            "type": "ports",
            "data": {
                "ports": ports,
                "current_port": selected_port
            }
        }
        return json.dumps(msg)

    def select_port(self, port: str) -> None:
        """Establece el puerto serie seleccionado por el usuario."""
        global selected_port
        with state_lock:
            selected_port = port
        log_to_buffer(f"Puerto seleccionado por el usuario: {selected_port}", "info")

    def start_emulation(self, port: str) -> str:
        """Inicia la emulación en el puerto indicado. Lanza hilo en background."""
        global is_emulating, selected_port, emulation_thread

        if not port:
            port = selected_port
        if not port:
            log_to_buffer("No se puede iniciar: Puerto serie no especificado.", "error")
            return self.get_status()

        with state_lock:
            if is_emulating:
                log_to_buffer("La emulación ya está corriendo.", "warn")
                return self.get_status()
            is_emulating = True
            selected_port = port

        # Lanzar hilo en background
        emulation_thread = threading.Thread(target=emulation_loop, args=(port,), daemon=True)
        emulation_thread.start()
        log_to_buffer("Hilo de emulación de hardware iniciado.", "info")
        return self.get_status()

    def stop_emulation(self) -> str:
        """Detiene la emulación de forma segura."""
        global is_emulating
        with state_lock:
            if not is_emulating:
                log_to_buffer("La emulación ya está detenida.", "warn")
                return self.get_status()
            is_emulating = False
        # El hilo detectará is_emulating=False y terminará limpio
        log_to_buffer("Deteniendo bucle de emulación...", "info")
        return self.get_status()

    def update_config(self, config_json: str) -> str:
        """Actualiza la configuración de calibración desde un string JSON y la guarda a disco."""
        try:
            new_config = json.loads(config_json) if isinstance(config_json, str) else config_json
            with state_lock:
                for k, v in new_config.items():
                    if k in calib_config:
                        calib_config[k] = v
            # Guardar en disco en hilo separado para no bloquear
            threading.Thread(target=save_config_to_json, daemon=True).start()
        except Exception as e:
            log_to_buffer(f"Error actualizando configuración: {e}", "error")
        return self.get_status()

    def trigger_dpad(self, direction: str) -> None:
        """Activa un botón virtual del D-pad y lo libera tras 500ms.
        direction: 'D-Pad UP', 'D-Pad DOWN', 'D-Pad LEFT', 'D-Pad RIGHT'"""
        with state_lock:
            virtual_btn_states[direction] = 1

        # Función para liberar después de 500ms
        def release_later():
            time.sleep(0.5)
            with state_lock:
                virtual_btn_states[direction] = 0
        threading.Thread(target=release_later, daemon=True).start()

    def get_telemetry(self) -> str:
        """Retorna la última telemetría disponible como JSON, o cadena vacía si no hay nueva."""
        global _telemetry_buffer
        with state_lock:
            data = _telemetry_buffer
            _telemetry_buffer = None  # Marcar como leído
        if data is not None:
            return json.dumps(data)
        return ""

    def get_logs(self) -> str:
        """Retorna los mensajes de log acumulados como array JSON y vacía el buffer."""
        with state_lock:
            if not _log_buffer:
                return "[]"
            logs_copy = list(_log_buffer)
            _log_buffer.clear()
        return json.dumps(logs_copy)

# ==========================================================================
# INICIO Y LIMPIEZA PRINCIPAL
# ==========================================================================
def main():
    global is_emulating, virtual_gamepad

    # 1. Limpiar pantalla de consola y mostrar banner
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\033[96m=================================================================\033[0m")
    print("\033[96m     EMULADOR DE VOLANTE Y PEDALES - APLICACIÓN NATIVA (PyWebView)\033[0m")
    print("\033[96m=================================================================\033[0m")

    # 2. Cargar configuración guardada
    load_config_from_json()

    # 3. Inicializar Gamepad virtual
    if not init_virtual_gamepad():
        print("\033[91mNo se pudo inicializar el gamepad virtual. Deteniendo.\033[0m")
        if os.name == 'nt':
            print("\n=======================================================")
            print("ERROR: Falta el driver de mando virtual ViGEmBus.")
            print("Para usar este emulador en Windows, debes instalar ViGEmBus.")
            print("Descarga e instala la última versión desde el siguiente enlace:")
            print("https://github.com/nefarius/ViGEmBus/releases")
            print("=======================================================\n")
        else:
            print("\nEn Linux, asegúrate de tener permisos en /dev/uinput (revisa el README.md).\n")
        # Mostrar diálogo de error nativo y salir
        try:
            webview.create_window(
                'Error - Volante PC',
                html='<html><body style="font-family:sans-serif;padding:40px;background:#1a1a2e;color:#e94560;">'
                     '<h2>Error Fatal</h2>'
                     '<p>No se pudo inicializar el gamepad virtual.</p>'
                     '<p>En Linux, asegúrate de tener permisos en /dev/uinput.</p>'
                     '<p>En Windows, instala el driver ViGEmBus.</p>'
                     '</body></html>',
                width=500, height=300
            )
            webview.start()
        except Exception:
            pass
        sys.exit(1)

    # 4. Determinar ruta del directorio web (manejar modo frozen con sys._MEIPASS)
    web_dir = os.path.join(BASE_DIR, 'web')
    if not os.path.isdir(web_dir):
        print(f"\033[91mError: No se encontró el directorio web en: {web_dir}\033[0m")
        sys.exit(1)

    index_path = os.path.join(web_dir, 'index.html')
    if not os.path.isfile(index_path):
        print(f"\033[91mError: No se encontró index.html en: {index_path}\033[0m")
        sys.exit(1)

    print(f"\033[92mCargando interfaz desde: {index_path}\033[0m")

    # 5. Crear instancia de la API
    api = EmuladorAPI()

    # 6. Crear ventana nativa con PyWebView
    webview.create_window(
        'Volante PC - Racing Dashboard Pro',
        url=index_path,
        js_api=api,
        width=1280,
        height=700,
        min_size=(960, 580),
        confirm_close=True
    )

    # 7. Arrancar PyWebView (bloquea hasta que la ventana se cierre)
    webview.start(debug=False, http_server=True)

    # 8. Limpieza al cerrar la ventana
    print("\n\033[93mCerrando aplicación...\033[0m")
    with state_lock:
        is_emulating = False

    # Esperar a que el hilo de emulación termine
    if emulation_thread and emulation_thread.is_alive():
        emulation_thread.join(timeout=2.0)

    # Liberar gamepad virtual
    if virtual_gamepad:
        try:
            virtual_gamepad.reset()
            virtual_gamepad.update()
        except Exception:
            pass
        virtual_gamepad = None

    print("Aplicación cerrada. ¡Hasta luego!")
    os._exit(0)


if __name__ == "__main__":
    main()

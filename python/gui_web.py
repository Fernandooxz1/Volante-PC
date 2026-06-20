#!/usr/bin/env python3
import os
import sys
import time
import json
import socket
import asyncio
import threading
import webbrowser
import http.server
import serial
import serial.tools.list_ports
import vgamepad as vg

# ==========================================================================
# CONFIGURACIÓN DE PUERTOS POR DEFECTO
# ==========================================================================
DEFAULT_HTTP_PORT = 8000
DEFAULT_WS_PORT = 8765

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
connected_websockets = set()
async_loop = None

# Variables de Emulación
is_emulating = False
selected_port = None
emulation_thread = None
serial_conn = None
virtual_gamepad = None
gamepad_ok = True

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
    "invert_steer": False,
    "invert_accel": False,
    "invert_brake": False,
    "accel_min": 0,
    "accel_max": 1023,
    "brake_min": 0,
    "brake_max": 1023,
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

# Archivo de persistencia de configuración
if getattr(sys, 'frozen', False):
    CONFIG_FILE_PATH = os.path.join(os.path.dirname(sys.executable), 'config_volante.json')
else:
    CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config_volante.json')

def save_config_to_json():
    """Guarda la configuración activa en config_volante.json de forma segura."""
    # No usamos state_lock aquí porque este método se llama ya sea desde hilos bloqueados
    # o de forma asíncrona, pero para evitar interbloqueos, hacemos una copia rápida
    with state_lock:
        config_copy = calib_config.copy()
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_copy, f, indent=4)
    except Exception as e:
        print(f"Error guardando configuración JSON: {e}")

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
                            calib_config[k] = v
            print("Configuración cargada con éxito desde config_volante.json.")
        except Exception as e:
            print(f"Error cargando configuración JSON: {e}")

# Última lectura de dirección para filtro EMA
last_filtered_steer = 512

# ==========================================================================
# LOGS Y NOTIFICACIONES
# ==========================================================================
def log_to_gui(text, level="info"):
    """Imprime en terminal y envía un mensaje de log al WebSocket del cliente."""
    color_map = {
        "success": "\033[92m",
        "warn": "\033[93m",
        "error": "\033[91m",
        "info": "\033[94m"
    }
    reset_color = "\033[0m"
    
    # Imprimir localmente en terminal
    print(f"{color_map.get(level, '')}[LOG - {level.upper()}] {text}{reset_color}")
    
    # Emitir via websocket si el event loop está corriendo
    if async_loop and connected_websockets:
        msg = {
            "type": "log",
            "data": {
                "text": text,
                "level": level
            }
        }
        asyncio.run_coroutine_threadsafe(broadcast_message(msg), async_loop)

# ==========================================================================
# REDIRECCIONAMIENTO DEL SERVIDOR HTTP
# ==========================================================================
class WebDashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Manejador HTTP que sirve exclusivamente la carpeta 'web'."""
    def __init__(self, *args, **kwargs):
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
        super().__init__(*args, directory=web_dir, **kwargs)

    def log_message(self, format, *args):
        # Desactivar logs de peticiones HTTP en consola para no ensuciar la telemetría
        pass

def run_http_server(port):
    """Arranca el servidor HTTP en un puerto específico."""
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, WebDashboardRequestHandler)
    log_to_gui(f"Servidor HTTP corriendo en http://localhost:{port}", "success")
    httpd.serve_forever()

# ==========================================================================
# AUXILIARES DE RED
# ==========================================================================
def find_free_port(start_port):
    """Busca un puerto libre a partir de start_port."""
    port = start_port
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except socket.error:
                port += 1

# ==========================================================================
# LÓGICA DE DETECCIÓN Y EMULACIÓN DE HARDWARE (SERIE & GAMEPAD)
# ==========================================================================
def get_available_ports():
    """Retorna una lista de puertos serie activos en el sistema."""
    ports = serial.tools.list_ports.comports()
    return [p.device for p in ports]

def init_virtual_gamepad():
    """Inicializa la instancia de vgamepad (mando Xbox 360 virtual)."""
    global virtual_gamepad, gamepad_ok
    try:
        virtual_gamepad = vg.VX360Gamepad()
        log_to_gui("Gamepad virtual Xbox 360 inicializado correctamente.", "success")
        gamepad_ok = True
        return True
    except Exception as e:
        log_to_gui(f"Error fatal inicializando gamepad: {e}", "error")
        if os.name == 'nt':
            log_to_gui("En Windows asegúrate de tener instalado el driver ViGEmBus.", "warn")
        else:
            log_to_gui("En Linux asegúrate de tener permisos en /dev/uinput (revisa README.md).", "warn")
        virtual_gamepad = None
        gamepad_ok = False
        return False

def cycle_presets_web():
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
            
        log_to_gui(f"Alternando preset de {current_preset} a {next_preset}", "success")
        
    # Guardar la configuración y notificar a los websockets
    save_config_to_json()
    broadcast_status()

def get_pin_state(pin_name, btn_states):
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
# BUCLE DE EMULACIÓN DE BAJA LATENCIA (RUNS IN BACKGROUND THREAD)
# ==========================================================================
def emulation_loop(port):
    global is_emulating, serial_conn, last_filtered_steer, virtual_gamepad
    
    log_to_gui(f"Abriendo puerto serie {port} a 115200 baudios...", "info")
    try:
        serial_conn = serial.Serial(port, 115200, timeout=1.0)
        serial_conn.reset_input_buffer()
        log_to_gui(f"Conectado a Arduino en {port} con éxito.", "success")
    except Exception as e:
        log_to_gui(f"Error abriendo puerto {port}: {e}", "error")
        with state_lock:
            is_emulating = False
        broadcast_status()
        return

    # Iniciar ciclo de lectura binaria
    pressed_buttons = set()
    last_ws_send_time = 0.0
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
                        
                        # Aplicar inversión de ejes si está configurada
                        with state_lock:
                            invert_steer = calib_config.get("invert_steer", False)
                            invert_accel = calib_config.get("invert_accel", False)
                            invert_brake = calib_config.get("invert_brake", False)
                            
                        if invert_steer:
                            steer_raw = 1023 - steer_raw
                        if invert_accel:
                            accel_raw = 1023 - accel_raw
                        if invert_brake:
                            brake_raw = 1023 - brake_raw
                        
                        # Extraer los 10 botones individuales (bits 0 a 9)
                        btn_states = []
                        for i in range(10):
                            btn_states.append((buttons_val >> i) & 0x01)
                        
                        # Detectar flanco de subida del botón de alternar preset
                        with state_lock:
                            cycle_btn_name = calib_config.get("preset_cycle_btn", "Ninguno")
                        
                        current_cycle_state = get_pin_state(cycle_btn_name, btn_states)
                        if current_cycle_state == 1 and last_btn_cycle_state == 0:
                            cycle_presets_web()
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
                            accel_min = calib_config.get("accel_min", 0)
                            accel_max = calib_config.get("accel_max", 1023)
                            brake_min = calib_config.get("brake_min", 0)
                            brake_max = calib_config.get("brake_max", 1023)
                            
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

                        # 2. Procesar Dirección (Normalizar [-1, 1] usando límites calibrados, aplicar Exponencial y Anti-Zona Muerta)
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

                        # 3. Auxiliar para procesar pedales con calibración de límites
                        def get_pedal_val(pedal_in, pedal_min, pedal_max, max_val):
                            if pedal_max > pedal_min:
                                val_norm = (pedal_in - pedal_min) / float(pedal_max - pedal_min)
                                val_norm = max(0.0, min(1.0, val_norm))
                            else:
                                val_norm = 0.0
                                
                            if val_norm <= deadzone:
                                return 0
                            else:
                                val_scaled = (val_norm - deadzone) / (1.0 - deadzone)
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

                        # Pedales
                        a_val_trigger = get_pedal_val(accel, accel_min, accel_max, 255)
                        a_val_stick = get_pedal_val(accel, accel_min, accel_max, 32767)
                        
                        if accel_target == "Right Trigger (RT)":
                            right_trigger_val = a_val_trigger
                        elif accel_target == "Left Trigger (LT)":
                            left_trigger_val = a_val_trigger
                        elif accel_target == "Right Stick Y+ (UP)":
                            right_stick_y -= get_pedal_val(accel, accel_min, accel_max, 32768)  # Negativo = UP en driver Xbox
                        elif accel_target == "Right Stick Y- (DOWN)":
                            right_stick_y += a_val_stick
                        elif accel_target == "Left Stick Y+ (UP)":
                            left_stick_y -= get_pedal_val(accel, accel_min, accel_max, 32768)
                        elif accel_target == "Left Stick Y- (DOWN)":
                            left_stick_y += a_val_stick

                        b_val_trigger = get_pedal_val(brake, brake_min, brake_max, 255)
                        b_val_stick = get_pedal_val(brake, brake_min, brake_max, 32767)

                        if brake_target == "Left Trigger (LT)":
                            left_trigger_val = b_val_trigger
                        elif brake_target == "Right Trigger (RT)":
                            right_trigger_val = b_val_trigger
                        elif brake_target == "Right Stick Y- (DOWN)":
                            right_stick_y += b_val_stick
                        elif brake_target == "Right Stick Y+ (UP)":
                            right_stick_y -= get_pedal_val(brake, brake_min, brake_max, 32768)
                        elif brake_target == "Left Stick Y- (DOWN)":
                            left_stick_y += b_val_stick
                        elif brake_target == "Left Stick Y+ (UP)":
                            left_stick_y -= get_pedal_val(brake, brake_min, brake_max, 32768)

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

                        # 5. Enviar telemetría a los clientes web a un máximo de 60Hz
                        now = time.time()
                        if now - last_ws_send_time >= 0.016:  # 60 FPS
                            last_ws_send_time = now
                            
                            # Valores mapeados escalados a 0-1023 para las barras de progreso del front
                            gui_steer = int(((x_final + 1.0) / 2.0) * 1023)
                            gui_accel = get_pedal_val(accel, accel_min, accel_max, 1023)
                            gui_brake = get_pedal_val(brake, brake_min, brake_max, 1023)
                            
                            telemetry_msg = {
                                "type": "telemetry",
                                "data": {
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
                            }
                            
                            # Ejecutar envío asíncrono
                            if async_loop and connected_websockets:
                                asyncio.run_coroutine_threadsafe(
                                    broadcast_message(telemetry_msg), 
                                    async_loop
                                )
                                
        except Exception as e:
            log_to_gui(f"Error procesando datos en loop de hardware: {e}", "error")
            time.sleep(0.1)

    # Limpieza al terminar
    log_to_gui("Cerrando puerto serie...", "info")
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
        log_to_gui(f"Error en limpieza del puerto: {e}", "warn")
        
    log_to_gui("Emulación detenida con éxito.", "success")
    broadcast_status()

# ==========================================================================
# SERVIDOR WEBSOCKETS (MANEJO DE COMUNICACIÓN CON FRONTEND)
# ==========================================================================
async def register(websocket):
    with state_lock:
        connected_websockets.add(websocket)
    log_to_gui("Cliente web dashboard conectado.", "success")
    
    # Enviar estado actual
    await send_status_to(websocket)

async def unregister(websocket):
    with state_lock:
        connected_websockets.remove(websocket)
    log_to_gui("Cliente web dashboard desconectado.", "info")

async def broadcast_message(message_dict):
    """Envía un diccionario JSON a todos los clientes conectados."""
    if not connected_websockets:
        return
    message_str = json.dumps(message_dict)
    # Hacer una copia para evitar iterar sobre set mutable durante el envío
    targets = list(connected_websockets)
    await asyncio.gather(*[ws.send(message_str) for ws in targets], return_exceptions=True)

async def send_status_to(websocket):
    """Envía el estado actual al cliente seleccionado."""
    with state_lock:
        msg = {
            "type": "status",
            "data": {
                "emulating": is_emulating,
                "gamepad_ok": gamepad_ok,
                "current_port": selected_port,
                "ports": get_available_ports(),
                "config": calib_config
            }
        }
    await websocket.send(json.dumps(msg))

def broadcast_status():
    """Envía el estado general a todos los clientes."""
    if async_loop:
        asyncio.run_coroutine_threadsafe(broadcast_status_async(), async_loop)

async def broadcast_status_async():
    with state_lock:
        msg = {
            "type": "status",
            "data": {
                "emulating": is_emulating,
                "gamepad_ok": gamepad_ok,
                "current_port": selected_port,
                "ports": get_available_ports(),
                "config": calib_config
            }
        }
    await broadcast_message(msg)

async def handle_websocket_message(websocket, message_str):
    global is_emulating, selected_port, emulation_thread
    
    try:
        msg = json.loads(message_str)
        msg_type = msg.get("type")
        msg_data = msg.get("data")
        msg_value = msg.get("value")
        
        if msg_type == "command":
            if msg_data == "get_status":
                await send_status_to(websocket)
                
            elif msg_data == "install_driver":
                try:
                    if getattr(sys, 'frozen', False):
                        base_dir = sys._MEIPASS
                    else:
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                    installer_path = os.path.join(base_dir, 'web', 'drivers', 'ViGEmBus_Setup.exe')
                    if os.path.exists(installer_path):
                        if os.name == 'nt':
                            os.startfile(installer_path)
                            log_to_gui("Ejecutando instalador de ViGEmBus...", "info")
                        else:
                            log_to_gui("El driver solo es necesario en Windows.", "warn")
                    else:
                        log_to_gui(f"Instalador no encontrado en: {installer_path}", "error")
                except Exception as e:
                    log_to_gui(f"Error al ejecutar instalador: {e}", "error")
                
            elif msg_data == "refresh_ports":
                ports = get_available_ports()
                log_to_gui(f"Buscando puertos serie. Encontrados: {ports}", "info")
                await broadcast_message({
                    "type": "ports",
                    "data": {
                        "ports": ports,
                        "current_port": selected_port
                    }
                })
                
            elif msg_data == "select_port":
                with state_lock:
                    selected_port = msg_value
                log_to_gui(f"Puerto seleccionado por el usuario: {selected_port}", "info")
                
            elif msg_data == "start":
                port = msg_value if msg_value else selected_port
                if not port:
                    log_to_gui("No se puede iniciar: Puerto serie no especificado.", "error")
                    return
                
                with state_lock:
                    if is_emulating:
                        log_to_gui("La emulación ya está corriendo.", "warn")
                        return
                    is_emulating = True
                    selected_port = port
                
                # Lanzar hilo en background
                emulation_thread = threading.Thread(target=emulation_loop, args=(port,), daemon=True)
                emulation_thread.start()
                log_to_gui("Hilo de emulación de hardware iniciado.", "info")
                await broadcast_status_async()
                
            elif msg_data == "stop":
                with state_lock:
                    if not is_emulating:
                        log_to_gui("La emulación ya está detenida.", "warn")
                        return
                    is_emulating = False
                # El hilo detectará is_emulating=False y terminará limpio
                log_to_gui("Deteniendo bucle de emulación...", "info")
                                
            elif msg_data == "trigger_dpad":
                direction = msg_value  # "D-Pad UP", "D-Pad DOWN", etc.
                with state_lock:
                    virtual_btn_states[direction] = 1
                
                # Función para liberar después de 500ms
                def release_later():
                    time.sleep(0.5)
                    with state_lock:
                        virtual_btn_states[direction] = 0
                threading.Thread(target=release_later, daemon=True).start()
                
        elif msg_type == "config":
            # Actualizar configuración thread-safe
            with state_lock:
                for k, v in msg_data.items():
                    if k in calib_config:
                        calib_config[k] = v
            # Guardar la configuración en disco en background y difundir cambios
            def save_and_broadcast():
                save_config_to_json()
                broadcast_status()
            threading.Thread(target=save_and_broadcast, daemon=True).start()
            
    except Exception as e:
        log_to_gui(f"Error procesando mensaje websocket: {e}", "error")

async def ws_handler(websocket, path=None):
    # En python websockets>=10.0, path no siempre se pasa
    await register(websocket)
    try:
        async for message in websocket:
            await handle_websocket_message(websocket, message)
    except Exception as e:
        # Manejar desconexiones abruptas sin petar
        pass
    finally:
        await unregister(websocket)

# ==========================================================================
# INICIO Y LIMPIEZA PRINCIPAL
# ==========================================================================
def main():
    global async_loop
    
    # 1. Limpiar pantalla de consola y mostrar banner
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\033[96m=================================================================\033[0m")
    print("\033[96m       EMULADOR DE VOLANTE Y PEDALES - PANEL DE CONTROL WEB      \033[0m")
    print("\033[96m=================================================================\033[0m")
    
    # 1.5 Cargar configuración guardada
    load_config_from_json()
    
    # 2. InicializarGamepad virtual
    if not init_virtual_gamepad():
        print("\033[93mAVISO: No se pudo inicializar el gamepad virtual. El dashboard se iniciará en modo de configuración/solo lectura.\033[0m")
        
    # 3. Encontrar puertos libres para HTTP y WS
    http_port = find_free_port(DEFAULT_HTTP_PORT)
    ws_port = find_free_port(DEFAULT_WS_PORT)
    
    # 4. Arrancar servidor HTTP de estáticos en un hilo secundario
    http_thread = threading.Thread(target=run_http_server, args=(http_port,), daemon=True)
    http_thread.start()
    
    # 5. Guardar loop para tareas asíncronas
    try:
        async_loop = asyncio.get_event_loop()
    except RuntimeError:
        async_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(async_loop)
    
    # 6. Crear servidor WebSocket en el loop principal
    import websockets.server
    start_ws = websockets.server.serve(ws_handler, "127.0.0.1", ws_port)
    async_loop.run_until_complete(start_ws)
    log_to_gui(f"Servidor WebSockets iniciado en ws://127.0.0.1:{ws_port}", "success")
    
    # 7. Abrir interfaz en el navegador automáticamente
    url = f"http://localhost:{http_port}/?ws_port={ws_port}"
    log_to_gui(f"Abriendo interfaz gráfica en: {url}", "info")
    webbrowser.open(url)
    
    # 8. Correr bucle de asyncio para siempre (mantiene vivo el socket)
    try:
        async_loop.run_forever()
    except KeyboardInterrupt:
        print("\n\033[93mApagando servidores por petición del usuario...\033[0m")
    finally:
        # Limpieza
        global is_emulating
        with state_lock:
            is_emulating = False
        if emulation_thread and emulation_thread.is_alive():
            emulation_thread.join(timeout=1.0)
        print("Servidores web detenidos. ¡Hasta luego!")

if __name__ == "__main__":
    main()

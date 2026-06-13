#!/usr/bin/env python3
import sys
import time
import threading
import serial
import serial.tools.list_ports
import vgamepad as vg
import customtkinter as ctk

# Configuración inicial de la estética visual (Dark theme moderno)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")  # Tema azul/violeta premium

# Presets por defecto para diferentes juegos
PRESETS = {
    "F1 Series (F1 23/24) / Modern Racing": {
        "steer_target": "Left Stick X",
        "accel_target": "Right Trigger (RT)",
        "brake_target": "Left Trigger (LT)",
        "btn_d2_target": "Button Start",
    },
    "Gran Turismo 4 (PS2 / PCSX2)": {
        "steer_target": "Left Stick X",
        "accel_target": "Right Stick Y+ (UP)",
        "brake_target": "Right Stick Y- (DOWN)",
        "btn_d2_target": "Button Start",
    },
    "Need for Speed Underground / PS2 Classic": {
        "steer_target": "Left Stick X",
        "accel_target": "Right Stick Y+ (UP)",
        "brake_target": "Left Stick Y- (DOWN)",
        "btn_d2_target": "Button Start",
    },
    "Personalizado": {
        "steer_target": "Left Stick X",
        "accel_target": "Right Trigger (RT)",
        "brake_target": "Right Trigger (RT)",
        "btn_d2_target": "Button Start",
    }
}

# Mapeo de botones de vgamepad para el pin digital D2
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

class VolanteGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de ventana (Aumentamos altura para dar espacio a los 5 sliders)
        self.title("Volante PC - Emulador & Mapeador Premium")
        self.geometry("680x740")
        self.resizable(False, False)

        # Variables de estado y sincronización (Thread-safe)
        self.running = False
        self.thread = None
        self.serial_conn = None
        self.lock = threading.Lock()
        
        # Ajustes de mapeo y calibración compartidos (Lineal con Anti-Zona Muerta)
        self.steer_target = "Left Stick X"
        self.accel_target = "Right Trigger (RT)"
        self.brake_target = "Right Trigger (RT)"
        self.btn_d2_target = "Button Start"
        self.sensitivity_val = 0.25
        self.slope_val = 0.65
        self.anti_deadzone_val = 0.0
        self.deadzone_val = 0.23
        self.filter_val = 0.55
        self.last_filtered_steer = 512
        
        # Últimos valores leídos de entrada (Raw)
        self.current_steer = 512
        self.current_accel = 0
        self.current_brake = 0
        self.current_btn_d2 = 0
        
        # Últimos valores calculados de salida (Mapeados y escalados)
        self.mapped_steer = 512
        self.mapped_accel = 0
        self.mapped_brake = 0
        self.mapped_btn_d2 = 0
        
        # Inicializar el gamepad virtual una única vez al arrancar para evitar duplicados
        try:
            self.gamepad = vg.VX360Gamepad()
            self.gamepad_ok = True
        except Exception as e:
            self.gamepad = None
            self.gamepad_ok = False
            print(f"Error al crear el gamepad virtual: {e}")

        # Construir UI
        self.create_widgets()
        self.load_ports()
        self.select_preset("Personalizado")

        # Vincular cierre de la ventana para limpiar el gamepad correctamente
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # Título principal
        title_label = ctk.CTkLabel(
            self, 
            text="CONTROLADOR DE VOLANTE & PEDALERA PC", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=12)

        # Contenedor de conexión
        conn_frame = ctk.CTkFrame(self)
        conn_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(conn_frame, text="Puerto Serie:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.port_combo = ctk.CTkComboBox(conn_frame, values=["Buscando..."], width=180)
        self.port_combo.grid(row=0, column=1, padx=10, pady=10)

        self.refresh_btn = ctk.CTkButton(conn_frame, text="Refrescar", width=80, command=self.load_ports)
        self.refresh_btn.grid(row=0, column=2, padx=5, pady=10)

        self.connect_btn = ctk.CTkButton(
            conn_frame, 
            text="Iniciar Emulación", 
            fg_color="#2b7a4b", 
            hover_color="#1e5734",
            command=self.toggle_emulation
        )
        self.connect_btn.grid(row=0, column=3, padx=15, pady=10)

        # Contenedor de Configuración de Mapeo
        config_frame = ctk.CTkFrame(self)
        config_frame.pack(fill="both", expand=True, padx=20, pady=5)

        # Fila Preset
        ctk.CTkLabel(config_frame, text="Preset de Juego:", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        self.preset_combo = ctk.CTkComboBox(
            config_frame, 
            values=list(PRESETS.keys()), 
            width=300, 
            command=self.select_preset
        )
        self.preset_combo.grid(row=0, column=1, columnspan=2, padx=15, pady=10, sticky="w")

        # Separador visual
        separator = ctk.CTkFrame(config_frame, height=2, fg_color="gray30")
        separator.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)

        # Configuración de Ejes Individuales
        ctk.CTkLabel(config_frame, text="Dirección (A0):", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=15, pady=8, sticky="w")
        self.steer_combo = ctk.CTkComboBox(
            config_frame, 
            values=["Left Stick X", "Right Stick X", "Left Stick Y", "Right Stick Y"],
            command=self.mark_custom
        )
        self.steer_combo.grid(row=2, column=1, padx=15, pady=8, sticky="w")

        ctk.CTkLabel(config_frame, text="Acelerador (A1):", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, padx=15, pady=8, sticky="w")
        self.accel_combo = ctk.CTkComboBox(
            config_frame, 
            values=["Right Trigger (RT)", "Right Stick Y+ (UP)", "Right Stick Y- (DOWN)", "Left Stick Y+ (UP)", "Left Stick Y- (DOWN)", "Left Trigger (LT)"],
            command=self.mark_custom
        )
        self.accel_combo.grid(row=3, column=1, padx=15, pady=8, sticky="w")

        ctk.CTkLabel(config_frame, text="Freno (A2):", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=15, pady=8, sticky="w")
        self.brake_combo = ctk.CTkComboBox(
            config_frame, 
            values=["Left Trigger (LT)", "Right Stick Y- (DOWN)", "Right Stick Y+ (UP)", "Left Stick Y- (DOWN)", "Left Stick Y+ (UP)", "Right Trigger (RT)"],
            command=self.mark_custom
        )
        self.brake_combo.grid(row=4, column=1, padx=15, pady=8, sticky="w")

        ctk.CTkLabel(config_frame, text="Botón D2 (Start):", font=ctk.CTkFont(weight="bold")).grid(row=5, column=0, padx=15, pady=8, sticky="w")
        self.btn_d2_combo = ctk.CTkComboBox(
            config_frame, 
            values=list(BUTTON_MAP.keys()),
            command=self.mark_custom
        )
        self.btn_d2_combo.grid(row=5, column=1, padx=15, pady=8, sticky="w")

        # Separador visual 2
        separator2 = ctk.CTkFrame(config_frame, height=2, fg_color="gray30")
        separator2.grid(row=6, column=0, columnspan=3, sticky="ew", pady=5)

        # Ajustes de Sensibilidad de Volante (Software)
        sens_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        sens_frame.grid(row=7, column=0, columnspan=3, sticky="ew", pady=5, padx=10)
        config_frame.grid_rowconfigure(7, weight=1)
        sens_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(sens_frame, text="Sensibilidad Volante:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", pady=4, padx=5)
        self.sens_slider = ctk.CTkSlider(sens_frame, from_=0.1, to=1.0, number_of_steps=18, command=self.update_sens_lbl)
        self.sens_slider.grid(row=0, column=1, padx=10, pady=4, sticky="ew")
        self.sens_slider.set(0.25)  # Por defecto al 25%
        self.sens_lbl = ctk.CTkLabel(sens_frame, text="25%", width=40)
        self.sens_lbl.grid(row=0, column=2, pady=4, padx=5)

        ctk.CTkLabel(sens_frame, text="Pendiente del Eje:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", pady=4, padx=5)
        self.slope_slider = ctk.CTkSlider(sens_frame, from_=0.25, to=2.0, number_of_steps=35, command=self.update_slope_lbl)
        self.slope_slider.grid(row=1, column=1, padx=10, pady=4, sticky="ew")
        self.slope_slider.set(0.65)  # Por defecto pendiente 0.65x
        self.slope_lbl = ctk.CTkLabel(sens_frame, text="0.65x", width=40)
        self.slope_lbl.grid(row=1, column=2, pady=4, padx=5)

        ctk.CTkLabel(sens_frame, text="Anti-Zona Muerta:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", pady=4, padx=5)
        self.anti_deadzone_slider = ctk.CTkSlider(sens_frame, from_=0.0, to=0.5, number_of_steps=50, command=self.update_anti_deadzone_lbl)
        self.anti_deadzone_slider.grid(row=2, column=1, padx=10, pady=4, sticky="ew")
        self.anti_deadzone_slider.set(0.0)  # Por defecto 0%
        self.anti_deadzone_lbl = ctk.CTkLabel(sens_frame, text="0%", width=40)
        self.anti_deadzone_lbl.grid(row=2, column=2, pady=4, padx=5)

        ctk.CTkLabel(sens_frame, text="Zona Muerta Pedales:", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, sticky="w", pady=4, padx=5)
        self.deadzone_slider = ctk.CTkSlider(sens_frame, from_=0.0, to=0.5, number_of_steps=50, command=self.update_deadzone_lbl)
        self.deadzone_slider.grid(row=3, column=1, padx=10, pady=4, sticky="ew")
        self.deadzone_slider.set(0.23)  # Por defecto al 23%
        self.deadzone_lbl = ctk.CTkLabel(sens_frame, text="23%", width=40)
        self.deadzone_lbl.grid(row=3, column=2, pady=4, padx=5)

        ctk.CTkLabel(sens_frame, text="Filtro Anti-Ruido (Jitter):", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, sticky="w", pady=4, padx=5)
        self.filter_slider = ctk.CTkSlider(sens_frame, from_=0.0, to=0.9, number_of_steps=18, command=self.update_filter_lbl)
        self.filter_slider.grid(row=4, column=1, padx=10, pady=4, sticky="ew")
        self.filter_slider.set(0.55)  # Por defecto al 55%
        self.filter_lbl = ctk.CTkLabel(sens_frame, text="55%", width=40)
        self.filter_lbl.grid(row=4, column=2, pady=4, padx=5)

        # Contenedor de Monitoreo Analógico (Visualización)
        monitor_frame = ctk.CTkFrame(self)
        monitor_frame.pack(fill="x", padx=20, pady=5)

        self.monitor_title = ctk.CTkLabel(monitor_frame, text="MONITOR DE SALIDAS (VIRTUAL)", font=ctk.CTkFont(size=11, weight="bold"))
        self.monitor_title.pack(pady=4)

        # Volante
        steer_box = ctk.CTkFrame(monitor_frame, fg_color="transparent")
        steer_box.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(steer_box, text="Volante:  ", width=80, anchor="w").pack(side="left")
        self.steer_bar = ctk.CTkProgressBar(steer_box)
        self.steer_bar.pack(side="left", fill="x", expand=True, padx=5)
        self.steer_val_lbl = ctk.CTkLabel(steer_box, text="512", width=40)
        self.steer_val_lbl.pack(side="left", padx=5)

        # Acelerador
        accel_box = ctk.CTkFrame(monitor_frame, fg_color="transparent")
        accel_box.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(accel_box, text="Acelerador:", width=80, anchor="w").pack(side="left")
        self.accel_bar = ctk.CTkProgressBar(accel_box, progress_color="green")
        self.accel_bar.pack(side="left", fill="x", expand=True, padx=5)
        self.accel_val_lbl = ctk.CTkLabel(accel_box, text="0%", width=40)
        self.accel_val_lbl.pack(side="left", padx=5)

        # Freno
        brake_box = ctk.CTkFrame(monitor_frame, fg_color="transparent")
        brake_box.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(brake_box, text="Freno:     ", width=80, anchor="w").pack(side="left")
        self.brake_bar = ctk.CTkProgressBar(brake_box, progress_color="red")
        self.brake_bar.pack(side="left", fill="x", expand=True, padx=5)
        self.brake_val_lbl = ctk.CTkLabel(brake_box, text="0%", width=40)
        self.brake_val_lbl.pack(side="left", padx=5)

        # Botón D2
        btn_box = ctk.CTkFrame(monitor_frame, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(btn_box, text="Botón D2:  ", width=80, anchor="w").pack(side="left")
        self.btn_indicator = ctk.CTkLabel(btn_box, text="SUELTO", text_color="gray", font=ctk.CTkFont(weight="bold"))
        self.btn_indicator.pack(side="left", padx=5)

        # Barra de Estado Inferior
        self.status_lbl = ctk.CTkLabel(
            self, 
            text="Listo para conectar", 
            text_color="gray", 
            font=ctk.CTkFont(slant="italic")
        )
        self.status_lbl.pack(pady=8)

        # Bucle de actualización de UI
        self.update_gui_meters()

    def update_sens_lbl(self, val):
        self.sens_lbl.configure(text=f"{int(val * 100)}%")
        with self.lock:
            self.sensitivity_val = float(val)

    def update_slope_lbl(self, val):
        self.slope_lbl.configure(text=f"{val:.2f}x")
        with self.lock:
            self.slope_val = float(val)

    def update_anti_deadzone_lbl(self, val):
        self.anti_deadzone_lbl.configure(text=f"{int(val * 100)}%")
        with self.lock:
            self.anti_deadzone_val = float(val)

    def update_deadzone_lbl(self, val):
        self.deadzone_lbl.configure(text=f"{int(val * 100)}%")
        with self.lock:
            self.deadzone_val = float(val)

    def update_filter_lbl(self, val):
        self.filter_lbl.configure(text=f"{int(val * 100)}%")
        with self.lock:
            self.filter_val = float(val)

    def load_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if ports:
            self.port_combo.configure(values=ports)
            
            # Auto-seleccionar puerto que sea USB o ACM (Arduino típico)
            default_port = ports[0]
            for port in ports:
                p_low = port.lower()
                if "usb" in p_low or "acm" in p_low:
                    default_port = port
                    break
            self.port_combo.set(default_port)
            self.status_lbl.configure(text="Puertos cargados con éxito", text_color="gray")
        else:
            self.port_combo.configure(values=["No se hallaron puertos"])
            self.port_combo.set("No se hallaron puertos")
            self.status_lbl.configure(text="Conecta el Arduino para empezar", text_color="orange")

    def select_preset(self, preset_name):
        if preset_name in PRESETS:
            config = PRESETS[preset_name]
            self.steer_combo.set(config["steer_target"])
            self.accel_combo.set(config["accel_target"])
            self.brake_combo.set(config["brake_target"])
            
            # Asignar botón D2 del preset o "Button Start"
            btn_val = config.get("btn_d2_target", "Button Start")
            self.btn_d2_combo.set(btn_val)
            
            self.update_mappings()
            if preset_name != "Personalizado":
                self.preset_combo.set(preset_name)

    def mark_custom(self, *args):
        self.preset_combo.set("Personalizado")
        self.update_mappings()

    def update_mappings(self):
        # Guardar mapeos de forma segura para lectura del thread
        with self.lock:
            self.steer_target = self.steer_combo.get()
            self.accel_target = self.accel_combo.get()
            self.brake_target = self.brake_combo.get()
            self.btn_d2_target = self.btn_d2_combo.get()

    def toggle_emulation(self):
        if not self.running:
            self.start_emulation()
        else:
            self.stop_emulation()

    def start_emulation(self):
        if not self.gamepad_ok:
            self.status_lbl.configure(text="Error: Gamepad virtual no disponible", text_color="red")
            return

        port = self.port_combo.get()
        if port in ["No se hallaron puertos", "Buscando..."]:
            self.status_lbl.configure(text="Error: Selecciona un puerto serie válido", text_color="red")
            return

        # Conectar al puerto serie
        try:
            self.serial_conn = serial.Serial(port, 115200, timeout=1.0)
            self.serial_conn.reset_input_buffer()
        except Exception as e:
            self.status_lbl.configure(text=f"Error serie: {e}", text_color="red")
            print(f"Error de conexión serie: {e}")
            return

        # Sincronizar mapeos iniciales
        self.update_mappings()

        # Arrancar hilo de lectura
        self.running = True
        self.thread = threading.Thread(target=self.emulation_loop, daemon=True)
        self.thread.start()

        # Actualizar UI
        self.connect_btn.configure(text="Detener Emulación", fg_color="#a83232", hover_color="#822525")
        self.port_combo.configure(state="disabled")
        self.refresh_btn.configure(state="disabled")
        self.status_lbl.configure(text="Emulación activa y corriendo", text_color="green")
        self.monitor_title.configure(text="MONITOR DE SALIDAS (FILTRADO Y CONFIGURADO)")

    def stop_emulation(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.2)
        
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            
        self.serial_conn = None
        
        # Restablecer UI
        self.connect_btn.configure(text="Iniciar Emulación", fg_color="#2b7a4b", hover_color="#1e5734")
        self.port_combo.configure(state="normal")
        self.refresh_btn.configure(state="normal")
        self.status_lbl.configure(text="Emulación detenida", text_color="gray")
        self.monitor_title.configure(text="MONITOR DE ENTRADAS (ESTADO RAW)")

    def emulation_loop(self):
        pressed_buttons = set()  # Para controlar botones virtuales presionados y evitar que queden pegados
        while self.running:
            try:
                # Buscar encabezado de sincronización de 2 bytes (0xAA, 0x55)
                b1 = self.serial_conn.read(1)
                if b1 == b'\xaa':
                    b2 = self.serial_conn.read(1)
                    if b2 == b'\x55':
                        # Leer los 6 bytes de datos empaquetados (4 de ejes + 2 de botones)
                        data_bytes = self.serial_conn.read(6)
                        if len(data_bytes) == 6:
                            val = int.from_bytes(data_bytes[0:4], byteorder='little')
                            buttons_val = int.from_bytes(data_bytes[4:6], byteorder='little')
                            
                            # Extraer campos de 10 bits y el botón D2 (que corresponde al pin digital 2)
                            steer = val & 0x3FF
                            accel = (val >> 10) & 0x3FF
                            brake = (val >> 20) & 0x3FF
                            btn_d2 = buttons_val & 0x01

                            # Limitar rangos analógicos
                            steer = max(0, min(1023, steer))
                            accel = max(0, min(1023, accel))
                            brake = max(0, min(1023, brake))

                            # Leer variables de configuración de forma segura
                            with self.lock:
                                sensitivity = self.sensitivity_val
                                slope = self.slope_val
                                anti_deadzone = self.anti_deadzone_val
                                deadzone = self.deadzone_val
                                filter_strength = self.filter_val
                                steer_target = self.steer_target
                                accel_target = self.accel_target
                                brake_target = self.brake_target
                                btn_d2_target = self.btn_d2_target

                            # --- FILTRADO AVANZADO ANTI-RUIDO (DSP) ---
                            if filter_strength > 0:
                                # A mayor filtro, más estricto es el limitador de saltos de cambio
                                max_change = int(15 + (1.0 - filter_strength) * 35)
                                diff = steer - self.last_filtered_steer
                                if abs(diff) > max_change:
                                    steer_step = max_change if diff > 0 else -max_change
                                    steer_filtered = self.last_filtered_steer + steer_step
                                else:
                                    steer_filtered = steer
                                
                                # Filtro Promedio Móvil Exponencial (EMA)
                                alpha_steer = 1.0 - filter_strength
                                steer_smoothed = int(alpha_steer * steer_filtered + (1.0 - alpha_steer) * self.last_filtered_steer)
                                self.last_filtered_steer = steer_smoothed
                                steer = steer_smoothed
                            else:
                                self.last_filtered_steer = steer

                            # --- PROCESAR DIRECCIÓN CON ANTI-ZONA MUERTA Y PENDIENTE ---
                            # 1. Normalizar dirección de 0-1023 a rango (-1.0 a 1.0)
                            x = (steer - 512) / 512.0

                            # 2. Aplicar multiplicador de pendiente (slope) y factor de sensibilidad
                            x_sloped = x * slope * sensitivity
                            x_sloped = max(-1.0, min(1.0, x_sloped))

                            # 3. Aplicar compensación de Anti-Zona Muerta (Anti-Deadzone)
                            abs_x = abs(x_sloped)
                            sign_x = 1.0 if x_sloped >= 0 else -1.0
                            
                            # Pequeña zona muerta física en el absoluto centro para evitar vibraciones (1%)
                            REST_DEADZONE = 0.01
                            
                            if abs_x <= REST_DEADZONE:
                                x_final = 0.0
                            else:
                                # Rescalar rango activo aplicando el salto inicial (offset) de la anti-zona muerta
                                scaled = (abs_x - REST_DEADZONE) / (1.0 - REST_DEADZONE)
                                x_final_magnitude = anti_deadzone + (1.0 - anti_deadzone) * scaled
                                x_final = sign_x * x_final_magnitude

                            # Acotar valor final a rango (-1.0 a 1.0)
                            x_final = max(-1.0, min(1.0, x_final))

                            # Convertir a rango de Xbox (-32768 a 32767)
                            val_steer_mapped = int(x_final * 32767)
                            val_steer_mapped = max(-32768, min(32767, val_steer_mapped))

                            # --- APLICAR MAPEOS CONFIGURADOS ---
                            left_stick_x = 0
                            left_stick_y = 0
                            right_stick_x = 0
                            right_stick_y = 0
                            left_trigger_val = 0
                            right_trigger_val = 0

                            # Asignar Dirección
                            if steer_target == "Left Stick X":
                                left_stick_x = val_steer_mapped
                            elif steer_target == "Right Stick X":
                                right_stick_x = val_steer_mapped
                            elif steer_target == "Left Stick Y":
                                left_stick_y = val_steer_mapped
                            elif steer_target == "Right Stick Y":
                                right_stick_y = val_steer_mapped

                            # Funciones de mapeo de pedales con Zona Muerta (Deadzone) rescalada
                            def get_pedal_val(pedal_in, max_val):
                                deadzone_limit = int(deadzone * 1023)
                                if pedal_in <= deadzone_limit:
                                    return 0
                                else:
                                    # Rescalar rango activo (deadzone_limit .. 1023) a (0 .. max_val)
                                    val_scaled = (pedal_in - deadzone_limit) / (1023.0 - deadzone_limit)
                                    return int(val_scaled * max_val)

                            # En los joysticks analógicos de Xbox/ViGEm, el eje Y está invertido en el driver:
                            # Negativo (-32768) es hacia ARRIBA (UP)
                            # Positivo (32767) es hacia ABAJO (DOWN)

                            # Procesar Acelerador (A1)
                            a_val_trigger = get_pedal_val(accel, 255)
                            a_val_stick = get_pedal_val(accel, 32767)

                            if accel_target == "Right Trigger (RT)":
                                right_trigger_val = a_val_trigger
                            elif accel_target == "Left Trigger (LT)":
                                left_trigger_val = a_val_trigger
                            elif accel_target == "Right Stick Y+ (UP)":
                                right_stick_y -= get_pedal_val(accel, 32768)  # Negativo = UP
                            elif accel_target == "Right Stick Y- (DOWN)":
                                right_stick_y += a_val_stick                  # Positivo = DOWN
                            elif accel_target == "Left Stick Y+ (UP)":
                                left_stick_y -= get_pedal_val(accel, 32768)   # Negativo = UP
                            elif accel_target == "Left Stick Y- (DOWN)":
                                left_stick_y += a_val_stick                   # Positivo = DOWN

                            # Procesar Freno (A2)
                            b_val_trigger = get_pedal_val(brake, 255)
                            b_val_stick = get_pedal_val(brake, 32767)

                            if brake_target == "Left Trigger (LT)":
                                left_trigger_val = b_val_trigger
                            elif brake_target == "Right Trigger (RT)":
                                right_trigger_val = b_val_trigger
                            elif brake_target == "Right Stick Y- (DOWN)":
                                right_stick_y += b_val_stick                  # Positivo = DOWN
                            elif brake_target == "Right Stick Y+ (UP)":
                                right_stick_y -= get_pedal_val(brake, 32768)  # Negativo = UP
                            elif brake_target == "Left Stick Y- (DOWN)":
                                left_stick_y += b_val_stick                   # Positivo = DOWN
                            elif brake_target == "Left Stick Y+ (UP)":
                                left_stick_y -= get_pedal_val(brake, 32768)   # Negativo = UP

                            # Acotar variables finales
                            left_stick_x = max(-32768, min(32767, left_stick_x))
                            left_stick_y = max(-32768, min(32767, left_stick_y))
                            right_stick_x = max(-32768, min(32767, right_stick_x))
                            right_stick_y = max(-32768, min(32767, right_stick_y))
                            left_trigger_val = max(0, min(255, left_trigger_val))
                            right_trigger_val = max(0, min(255, right_trigger_val))

                            # --- PROCESAR BOTÓN D2 (START) ---
                            active_button = None
                            if btn_d2 == 1 and btn_d2_target in BUTTON_MAP:
                                active_button = BUTTON_MAP[btn_d2_target]

                            # Liberar botones que ya no deben estar presionados
                            to_release = [b for b in pressed_buttons if b != active_button]
                            for b in to_release:
                                if b is not None:
                                    self.gamepad.release_button(button=b)
                                    pressed_buttons.remove(b)

                            # Presionar el botón activo si no lo está ya
                            if active_button is not None and active_button not in pressed_buttons:
                                self.gamepad.press_button(button=active_button)
                                pressed_buttons.add(active_button)

                            # Guardar variables calculadas finales de forma segura para la visualización gráfica en UI
                            with self.lock:
                                self.current_steer = steer
                                self.current_accel = accel
                                self.current_brake = brake
                                self.current_btn_d2 = btn_d2
                                
                                # Convertir valores calculados finales a escala 0-1023 para la UI
                                self.mapped_steer = int(((val_steer_mapped + 32768) / 65535.0) * 1023)
                                
                                # Para los pedales, mostramos la entrada analógica procesada con la zona muerta
                                # para que se refleje visualmente la corrección en las barras.
                                self.mapped_accel = get_pedal_val(accel, 1023)
                                self.mapped_brake = get_pedal_val(brake, 1023)
                                self.mapped_btn_d2 = btn_d2

                            # Enviar valores actualizados al Gamepad virtual
                            self.gamepad.left_joystick(x_value=left_stick_x, y_value=left_stick_y)
                            self.gamepad.right_joystick(x_value=right_stick_x, y_value=right_stick_y)
                            self.gamepad.left_trigger(value=left_trigger_val)
                            self.gamepad.right_trigger(value=right_trigger_val)
                            self.gamepad.update()

            except Exception as e:
                print(f"Error procesando datos en loop: {e}")
                self.running = False
                break
        
        # Al detener la emulación, liberar todos los botones presionados
        for b in pressed_buttons:
            try:
                self.gamepad.release_button(button=b)
            except:
                pass
        pressed_buttons.clear()
        
        # Detener emulación en el hilo principal
        self.after(10, self.on_emulation_error)

    def on_emulation_error(self):
        self.stop_emulation()
        self.status_lbl.configure(text="Error de conexión o puerto desconectado", text_color="red")

    def update_gui_meters(self):
        # Obtener valores de forma segura
        with self.lock:
            if self.running:
                # Mostrar los valores finales procesados que se envían al mando virtual
                steer = self.mapped_steer
                accel = self.mapped_accel
                brake = self.mapped_brake
                btn_pressed = (self.mapped_btn_d2 == 1)
            else:
                # Mostrar los valores raw/analógicos del potenciómetro
                steer = self.current_steer
                accel = self.current_accel
                brake = self.current_brake
                btn_pressed = (self.current_btn_d2 == 1)

        # Actualizar Barras de progreso (de 0.0 a 1.0)
        self.steer_bar.set(steer / 1023.0)
        self.accel_bar.set(accel / 1023.0)
        self.brake_bar.set(brake / 1023.0)

        # Actualizar indicador de botón
        if btn_pressed:
            self.btn_indicator.configure(text="PRESIONADO", text_color="#2b7a4b")
        else:
            self.btn_indicator.configure(text="SUELTO", text_color="gray")

        # Actualizar etiquetas de texto
        self.steer_val_lbl.configure(text=f"{steer}")
        self.accel_val_lbl.configure(text=f"{int((accel / 1023.0) * 100)}%")
        self.brake_val_lbl.configure(text=f"{int((brake / 1023.0) * 100)}%")

        # Repetir cada 50ms (20fps es más que suficiente para visualización fluida)
        self.after(50, self.update_gui_meters)

    def on_closing(self):
        # Detener hilos y cerrar conexiones
        self.stop_emulation()
        if self.gamepad:
            del self.gamepad
        self.destroy()

if __name__ == "__main__":
    app = VolanteGUI()
    app.mainloop()

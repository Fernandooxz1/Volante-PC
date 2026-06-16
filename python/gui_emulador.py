#!/usr/bin/env python3
import sys
import os
import json
import time
import threading
import serial
import serial.tools.list_ports
import vgamepad as vg
import customtkinter as ctk

# Archivo de persistencia de configuración
if getattr(sys, 'frozen', False):
    CONFIG_FILE_PATH = os.path.join(os.path.dirname(sys.executable), 'config_volante.json')
else:
    CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config_volante.json')

# Configuración inicial de la estética visual (Dark theme moderno)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")  # Tema azul/violeta premium

# Presets por defecto para diferentes juegos
PRESETS = {
    "Personalizado": {
        "steer_target": "Left Stick X",
        "accel_target": "Right Trigger (RT)",
        "brake_target": "Left Trigger (LT)",
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
        self.geometry("680x780")
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
        
        # Mapeos por defecto de los 10 botones (Pines 2 al 11)
        self.btn_d2_target = "Ninguno"
        self.btn_d3_target = "Ninguno"
        self.btn_d4_target = "Ninguno"
        self.btn_d5_target = "Ninguno"
        self.btn_d6_target = "Ninguno"
        self.btn_d7_target = "Ninguno"
        self.btn_d8_target = "Ninguno"
        self.btn_d9_target = "Ninguno"
        self.btn_d10_target = "Ninguno"
        self.btn_d11_target = "Ninguno"
        
        self.preset_cycle_btn = "Ninguno"
        self.last_btn_cycle_state = 0
        
        self.sensitivity_val = 0.25
        self.slope_val = 0.65
        self.anti_deadzone_val = 0.0
        self.deadzone_val = 0.23
        self.filter_val = 0.55
        self.last_filtered_steer = 512
        self.last_btn_d9_state = 0
        
        # Últimos valores leídos de entrada (Raw) y salida (Mapeados)
        self.current_steer = 512
        self.current_accel = 0
        self.current_brake = 0
        self.current_btn_states = [0] * 10
        
        self.mapped_steer = 512
        self.mapped_accel = 0
        self.mapped_brake = 0
        self.mapped_btn_states = [0] * 10
        
        # Estado de botones virtuales del D-pad para mapeo
        self.virtual_btn_states = {
            "D-Pad UP": 0,
            "D-Pad DOWN": 0,
            "D-Pad LEFT": 0,
            "D-Pad RIGHT": 0
        }
        
        # Inicializar el gamepad virtual una única vez al arrancar para evitar duplicados
        try:
            self.gamepad = vg.VX360Gamepad()
            self.gamepad_ok = True
        except Exception as e:
            self.gamepad = None
            self.gamepad_ok = False
            print(f"Error al crear el gamepad virtual: {e}")

        # Inicializar variables de presets dinámicos
        self.custom_presets = {}
        self.active_preset = "Personalizado"
        self.previous_preset = "Personalizado"

        # Construir UI
        self.create_widgets()
        self.load_ports()
        self.load_config_from_json()

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
        ctk.CTkLabel(config_frame, text="Preset de Juego:", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=8, sticky="w")
        self.preset_combo = ctk.CTkComboBox(
            config_frame, 
            values=list(PRESETS.keys()), 
            width=300, 
            command=self.select_preset
        )
        self.preset_combo.grid(row=0, column=1, columnspan=2, padx=15, pady=8, sticky="w")

        # Fila Botón de Alternar Preset
        ctk.CTkLabel(config_frame, text="Alternar Presets:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, padx=15, pady=5, sticky="w")
        cycle_options = ["Ninguno", "Pin D2", "Pin D3", "Pin D4", "Pin D5", "Pin D6", "Pin D7", "Pin D8", "Pin D9", "Pin D10", "Pin D11"]
        self.preset_cycle_combo = ctk.CTkComboBox(
            config_frame,
            values=cycle_options,
            command=self.mark_custom,
            width=300
        )
        self.preset_cycle_combo.grid(row=1, column=1, columnspan=2, padx=15, pady=5, sticky="w")
        self.preset_cycle_combo.set("Ninguno")

        # Separador visual
        separator = ctk.CTkFrame(config_frame, height=2, fg_color="gray30")
        separator.grid(row=2, column=0, columnspan=4, sticky="ew", pady=5)

        # Configuración de Ejes Individuales
        ctk.CTkLabel(config_frame, text="Dirección (A0):", font=ctk.CTkFont(weight="bold")).grid(row=3, column=0, padx=15, pady=8, sticky="w")
        self.steer_combo = ctk.CTkComboBox(
            config_frame, 
            values=["Left Stick X", "Right Stick X", "Left Stick Y", "Right Stick Y"],
            command=self.mark_custom,
            width=140
        )
        self.steer_combo.grid(row=3, column=1, padx=15, pady=8, sticky="w")

        ctk.CTkLabel(config_frame, text="Acelerador (A1):", font=ctk.CTkFont(weight="bold")).grid(row=3, column=2, padx=15, pady=8, sticky="w")
        self.accel_combo = ctk.CTkComboBox(
            config_frame, 
            values=["Right Trigger (RT)", "Right Stick Y+ (UP)", "Right Stick Y- (DOWN)", "Left Stick Y+ (UP)", "Left Stick Y- (DOWN)", "Left Trigger (LT)"],
            command=self.mark_custom,
            width=140
        )
        self.accel_combo.grid(row=3, column=3, padx=15, pady=8, sticky="w")

        ctk.CTkLabel(config_frame, text="Freno (A2):", font=ctk.CTkFont(weight="bold")).grid(row=4, column=0, padx=15, pady=8, sticky="w")
        self.brake_combo = ctk.CTkComboBox(
            config_frame, 
            values=["Left Trigger (LT)", "Right Stick Y- (DOWN)", "Right Stick Y+ (UP)", "Left Stick Y- (DOWN)", "Left Stick Y+ (UP)", "Right Trigger (RT)"],
            command=self.mark_custom,
            width=140
        )
        self.brake_combo.grid(row=4, column=1, padx=15, pady=8, sticky="w")

        # Separador visual entre ejes y botones
        separator_mid = ctk.CTkFrame(config_frame, height=2, fg_color="gray30")
        separator_mid.grid(row=5, column=0, columnspan=4, sticky="ew", pady=5)

        # Row 6: D2 & D7
        ctk.CTkLabel(config_frame, text="Botón D2 (Start):", font=ctk.CTkFont(weight="bold")).grid(row=6, column=0, padx=15, pady=5, sticky="w")
        self.btn_d2_combo = ctk.CTkComboBox(config_frame, values=list(BUTTON_MAP.keys()), command=self.mark_custom, width=140)
        self.btn_d2_combo.grid(row=6, column=1, padx=15, pady=5, sticky="w")
        
        ctk.CTkLabel(config_frame, text="Botón D7 (LB):", font=ctk.CTkFont(weight="bold")).grid(row=6, column=2, padx=15, pady=5, sticky="w")
        self.btn_d7_combo = ctk.CTkComboBox(config_frame, values=list(BUTTON_MAP.keys()), command=self.mark_custom, width=140)
        self.btn_d7_combo.grid(row=6, column=3, padx=15, pady=5, sticky="w")

        # Row 7: D3 & D8
        ctk.CTkLabel(config_frame, text="Botón D3 (A):", font=ctk.CTkFont(weight="bold")).grid(row=7, column=0, padx=15, pady=5, sticky="w")
        self.btn_d3_combo = ctk.CTkComboBox(config_frame, values=list(BUTTON_MAP.keys()), command=self.mark_custom, width=140)
        self.btn_d3_combo.grid(row=7, column=1, padx=15, pady=5, sticky="w")
        
        ctk.CTkLabel(config_frame, text="Botón D8 (RB):", font=ctk.CTkFont(weight="bold")).grid(row=7, column=2, padx=15, pady=5, sticky="w")
        self.btn_d8_combo = ctk.CTkComboBox(config_frame, values=list(BUTTON_MAP.keys()), command=self.mark_custom, width=140)
        self.btn_d8_combo.grid(row=7, column=3, padx=15, pady=5, sticky="w")

        # Row 8: D4 & D9
        ctk.CTkLabel(config_frame, text="Botón D4 (B):", font=ctk.CTkFont(weight="bold")).grid(row=8, column=0, padx=15, pady=5, sticky="w")
        self.btn_d4_combo = ctk.CTkComboBox(config_frame, values=list(BUTTON_MAP.keys()), command=self.mark_custom, width=140)
        self.btn_d4_combo.grid(row=8, column=1, padx=15, pady=5, sticky="w")
        
        ctk.CTkLabel(config_frame, text="Botón D9 (Preset Cycle):", font=ctk.CTkFont(weight="bold")).grid(row=8, column=2, padx=15, pady=5, sticky="w")
        self.btn_d9_combo = ctk.CTkComboBox(config_frame, values=list(BUTTON_MAP.keys()), command=self.mark_custom, width=140)
        self.btn_d9_combo.grid(row=8, column=3, padx=15, pady=5, sticky="w")

        # Row 9: D5 & D10
        ctk.CTkLabel(config_frame, text="Botón D5 (X):", font=ctk.CTkFont(weight="bold")).grid(row=9, column=0, padx=15, pady=5, sticky="w")
        self.btn_d5_combo = ctk.CTkComboBox(config_frame, values=list(BUTTON_MAP.keys()), command=self.mark_custom, width=140)
        self.btn_d5_combo.grid(row=9, column=1, padx=15, pady=5, sticky="w")
        
        ctk.CTkLabel(config_frame, text="Botón D10 (L3):", font=ctk.CTkFont(weight="bold")).grid(row=9, column=2, padx=15, pady=5, sticky="w")
        self.btn_d10_combo = ctk.CTkComboBox(config_frame, values=list(BUTTON_MAP.keys()), command=self.mark_custom, width=140)
        self.btn_d10_combo.grid(row=9, column=3, padx=15, pady=5, sticky="w")

        # Row 10: D6 & D11
        ctk.CTkLabel(config_frame, text="Botón D6 (Y):", font=ctk.CTkFont(weight="bold")).grid(row=10, column=0, padx=15, pady=5, sticky="w")
        self.btn_d6_combo = ctk.CTkComboBox(config_frame, values=list(BUTTON_MAP.keys()), command=self.mark_custom, width=140)
        self.btn_d6_combo.grid(row=10, column=1, padx=15, pady=5, sticky="w")
        
        ctk.CTkLabel(config_frame, text="Botón D11 (R3):", font=ctk.CTkFont(weight="bold")).grid(row=10, column=2, padx=15, pady=5, sticky="w")
        self.btn_d11_combo = ctk.CTkComboBox(config_frame, values=list(BUTTON_MAP.keys()), command=self.mark_custom, width=140)
        self.btn_d11_combo.grid(row=10, column=3, padx=15, pady=5, sticky="w")

        # Separador visual 2
        separator2 = ctk.CTkFrame(config_frame, height=2, fg_color="gray30")
        separator2.grid(row=11, column=0, columnspan=4, sticky="ew", pady=5)

        # Ajustes de Sensibilidad de Volante (Software)
        sens_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        sens_frame.grid(row=12, column=0, columnspan=4, sticky="ew", pady=5, padx=10)
        config_frame.grid_rowconfigure(12, weight=1)
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

        # Botones de estado (D2 a D11) como leds horizontales
        btn_box = ctk.CTkFrame(monitor_frame, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(btn_box, text="Botones:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(5, 10))
        self.btn_indicators = []
        for i in range(10):
            pin = i + 2
            lbl = ctk.CTkLabel(
                btn_box, 
                text=f"D{pin}", 
                fg_color="gray25", 
                text_color="gray70", 
                corner_radius=4,
                width=42,
                height=22,
                font=ctk.CTkFont(size=10, weight="bold")
            )
            lbl.pack(side="left", padx=3)
            self.btn_indicators.append(lbl)

        # Mapeador de Cruceta Virtual (Mapeo)
        dpad_frame = ctk.CTkFrame(monitor_frame, fg_color="transparent")
        dpad_frame.pack(pady=10)
        
        ctk.CTkLabel(dpad_frame, text="Cruceta Virtual (Mapear):", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, columnspan=3, pady=(0, 4))
        
        self.btn_up = ctk.CTkButton(dpad_frame, text="▲", width=34, height=28, command=lambda: self.trigger_virtual_dpad("D-Pad UP"))
        self.btn_up.grid(row=1, column=1, padx=2, pady=2)
        
        self.btn_left = ctk.CTkButton(dpad_frame, text="◀", width=34, height=28, command=lambda: self.trigger_virtual_dpad("D-Pad LEFT"))
        self.btn_left.grid(row=2, column=0, padx=2, pady=2)
        
        self.btn_down = ctk.CTkButton(dpad_frame, text="▼", width=34, height=28, command=lambda: self.trigger_virtual_dpad("D-Pad DOWN"))
        self.btn_down.grid(row=2, column=1, padx=2, pady=2)
        
        self.btn_right = ctk.CTkButton(dpad_frame, text="▶", width=34, height=28, command=lambda: self.trigger_virtual_dpad("D-Pad RIGHT"))
        self.btn_right.grid(row=2, column=2, padx=2, pady=2)

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
        self.mark_custom()

    def update_slope_lbl(self, val):
        self.slope_lbl.configure(text=f"{val:.2f}x")
        with self.lock:
            self.slope_val = float(val)
        self.mark_custom()

    def update_anti_deadzone_lbl(self, val):
        self.anti_deadzone_lbl.configure(text=f"{int(val * 100)}%")
        with self.lock:
            self.anti_deadzone_val = float(val)
        self.mark_custom()

    def update_deadzone_lbl(self, val):
        self.deadzone_lbl.configure(text=f"{int(val * 100)}%")
        with self.lock:
            self.deadzone_val = float(val)
        self.mark_custom()

    def update_filter_lbl(self, val):
        self.filter_lbl.configure(text=f"{int(val * 100)}%")
        with self.lock:
            self.filter_val = float(val)
        self.mark_custom()

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

    def load_config_from_json(self):
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                
                # Cargar presets personalizados
                self.custom_presets = saved.get("custom_presets", {})
                
                # Cargar ajustes individuales
                self.sensitivity_val = saved.get("sensitivity", 0.25)
                self.slope_val = saved.get("slope", 0.65)
                self.anti_deadzone_val = saved.get("anti_deadzone", 0.0)
                self.deadzone_val = saved.get("deadzone", 0.23)
                self.filter_val = saved.get("filter", 0.55)
                
                self.steer_target = saved.get("steer_target", "Left Stick X")
                self.accel_target = saved.get("accel_target", "Right Trigger (RT)")
                self.brake_target = saved.get("brake_target", "Left Trigger (LT)")
                
                self.btn_d2_target = saved.get("btn_map_p2", "Ninguno")
                self.btn_d3_target = saved.get("btn_map_p3", "Ninguno")
                self.btn_d4_target = saved.get("btn_map_p4", "Ninguno")
                self.btn_d5_target = saved.get("btn_map_p5", "Ninguno")
                self.btn_d6_target = saved.get("btn_map_p6", "Ninguno")
                self.btn_d7_target = saved.get("btn_map_p7", "Ninguno")
                self.btn_d8_target = saved.get("btn_map_p8", "Ninguno")
                self.btn_d9_target = saved.get("btn_map_p9", "Ninguno")
                self.btn_d10_target = saved.get("btn_map_p10", "Ninguno")
                self.btn_d11_target = saved.get("btn_map_p11", "Ninguno")
                
                self.preset_cycle_btn = saved.get("preset_cycle_btn", "Ninguno")
                self.active_preset = saved.get("active_preset", "Personalizado")
                self.previous_preset = saved.get("previous_preset", "Personalizado")
                
                # Actualizar valores de widgets de calibración si ya existen
                if hasattr(self, 'sens_slider'):
                    self.sens_slider.set(self.sensitivity_val)
                    self.sens_lbl.configure(text=f"{int(self.sensitivity_val * 100)}%")
                if hasattr(self, 'slope_slider'):
                    self.slope_slider.set(self.slope_val)
                    self.slope_lbl.configure(text=f"{self.slope_val:.2f}x")
                if hasattr(self, 'anti_deadzone_slider'):
                    self.anti_deadzone_slider.set(self.anti_deadzone_val)
                    self.anti_deadzone_lbl.configure(text=f"{int(self.anti_deadzone_val * 100)}%")
                if hasattr(self, 'deadzone_slider'):
                    self.deadzone_slider.set(self.deadzone_val)
                    self.deadzone_lbl.configure(text=f"{int(self.deadzone_val * 100)}%")
                if hasattr(self, 'filter_slider'):
                    self.filter_slider.set(self.filter_val)
                    self.filter_lbl.configure(text=f"{int(self.filter_val * 100)}%")
                
                # Ejes
                if hasattr(self, 'steer_combo'):
                    self.steer_combo.set(self.steer_target)
                if hasattr(self, 'accel_combo'):
                    self.accel_combo.set(self.accel_target)
                if hasattr(self, 'brake_combo'):
                    self.brake_combo.set(self.brake_target)
                    
                # Botones
                if hasattr(self, 'btn_d2_combo'):
                    self.btn_d2_combo.set(self.btn_d2_target)
                if hasattr(self, 'btn_d3_combo'):
                    self.btn_d3_combo.set(self.btn_d3_target)
                if hasattr(self, 'btn_d4_combo'):
                    self.btn_d4_combo.set(self.btn_d4_target)
                if hasattr(self, 'btn_d5_combo'):
                    self.btn_d5_combo.set(self.btn_d5_target)
                if hasattr(self, 'btn_d6_combo'):
                    self.btn_d6_combo.set(self.btn_d6_target)
                if hasattr(self, 'btn_d7_combo'):
                    self.btn_d7_combo.set(self.btn_d7_target)
                if hasattr(self, 'btn_d8_combo'):
                    self.btn_d8_combo.set(self.btn_d8_target)
                if hasattr(self, 'btn_d9_combo'):
                    self.btn_d9_combo.set(self.btn_d9_target)
                if hasattr(self, 'btn_d10_combo'):
                    self.btn_d10_combo.set(self.btn_d10_target)
                if hasattr(self, 'btn_d11_combo'):
                    self.btn_d11_combo.set(self.btn_d11_target)
                    
                # Ciclo
                if hasattr(self, 'preset_cycle_combo'):
                    self.preset_cycle_combo.set(self.preset_cycle_btn)
                    
                # Preset combo values
                if hasattr(self, 'preset_combo'):
                    presets_list = list(self.custom_presets.keys()) + ["Personalizado"]
                    self.preset_combo.configure(values=presets_list)
                    self.preset_combo.set(self.active_preset)
                    
            except Exception as e:
                print(f"Error cargando configuración JSON en GUI: {e}")

    def save_config_to_json(self):
        saved = {}
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
            except Exception:
                pass
                
        saved["sensitivity"] = self.sensitivity_val
        saved["slope"] = self.slope_val
        saved["anti_deadzone"] = self.anti_deadzone_val
        saved["deadzone"] = self.deadzone_val
        saved["filter"] = self.filter_val
        
        saved["steer_target"] = self.steer_target
        saved["accel_target"] = self.accel_target
        saved["brake_target"] = self.brake_target
        
        saved["btn_map_p2"] = self.btn_d2_target
        saved["btn_map_p3"] = self.btn_d3_target
        saved["btn_map_p4"] = self.btn_d4_target
        saved["btn_map_p5"] = self.btn_d5_target
        saved["btn_map_p6"] = self.btn_d6_target
        saved["btn_map_p7"] = self.btn_d7_target
        saved["btn_map_p8"] = self.btn_d8_target
        saved["btn_map_p9"] = self.btn_d9_target
        saved["btn_map_p10"] = self.btn_d10_target
        saved["btn_map_p11"] = self.btn_d11_target
        
        saved["preset_cycle_btn"] = self.preset_cycle_btn
        if hasattr(self, 'preset_combo'):
            saved["active_preset"] = self.preset_combo.get()
        else:
            saved["active_preset"] = self.active_preset
        saved["previous_preset"] = self.previous_preset
        saved["custom_presets"] = self.custom_presets
        
        try:
            with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(saved, f, indent=4)
        except Exception as e:
            print(f"Error guardando configuración JSON en GUI: {e}")

    def select_preset(self, preset_name):
        current_active = getattr(self, 'active_preset', 'Personalizado')
        if preset_name != current_active:
            self.previous_preset = current_active
            
        if preset_name == "Personalizado":
            with self.lock:
                self.active_preset = "Personalizado"
            if hasattr(self, 'preset_combo'):
                self.preset_combo.set("Personalizado")
            self.save_config_to_json()
            return
            
        preset = self.custom_presets.get(preset_name)
        if preset:
            # Copiar valores a los sliders y combos
            self.sensitivity_val = preset.get("sensitivity", 0.25)
            self.slope_val = preset.get("slope", 0.65)
            self.anti_deadzone_val = preset.get("anti_deadzone", 0.0)
            self.deadzone_val = preset.get("deadzone", 0.23)
            self.filter_val = preset.get("filter", 0.55)
            
            self.steer_target = preset.get("steer_target", "Left Stick X")
            self.accel_target = preset.get("accel_target", "Right Trigger (RT)")
            self.brake_target = preset.get("brake_target", "Left Trigger (LT)")
            
            self.btn_d2_target = preset.get("btn_map_p2", "Ninguno")
            self.btn_d3_target = preset.get("btn_map_p3", "Ninguno")
            self.btn_d4_target = preset.get("btn_map_p4", "Ninguno")
            self.btn_d5_target = preset.get("btn_map_p5", "Ninguno")
            self.btn_d6_target = preset.get("btn_map_p6", "Ninguno")
            self.btn_d7_target = preset.get("btn_map_p7", "Ninguno")
            self.btn_d8_target = preset.get("btn_map_p8", "Ninguno")
            self.btn_d9_target = preset.get("btn_map_p9", "Ninguno")
            self.btn_d10_target = preset.get("btn_map_p10", "Ninguno")
            self.btn_d11_target = preset.get("btn_map_p11", "Ninguno")
            self.preset_cycle_btn = preset.get("preset_cycle_btn", "Ninguno")
            
            # Actualizar widgets
            if hasattr(self, 'sens_slider'):
                self.sens_slider.set(self.sensitivity_val)
                self.sens_lbl.configure(text=f"{int(self.sensitivity_val * 100)}%")
            if hasattr(self, 'slope_slider'):
                self.slope_slider.set(self.slope_val)
                self.slope_lbl.configure(text=f"{self.slope_val:.2f}x")
            if hasattr(self, 'anti_deadzone_slider'):
                self.anti_deadzone_slider.set(self.anti_deadzone_val)
                self.anti_deadzone_lbl.configure(text=f"{int(self.anti_deadzone_val * 100)}%")
            if hasattr(self, 'deadzone_slider'):
                self.deadzone_slider.set(self.deadzone_val)
                self.deadzone_lbl.configure(text=f"{int(self.deadzone_val * 100)}%")
            if hasattr(self, 'filter_slider'):
                self.filter_slider.set(self.filter_val)
                self.filter_lbl.configure(text=f"{int(self.filter_val * 100)}%")
            
            if hasattr(self, 'steer_combo'):
                self.steer_combo.set(self.steer_target)
            if hasattr(self, 'accel_combo'):
                self.accel_combo.set(self.accel_target)
            if hasattr(self, 'brake_combo'):
                self.brake_combo.set(self.brake_target)
                
            if hasattr(self, 'btn_d2_combo'):
                self.btn_d2_combo.set(self.btn_d2_target)
            if hasattr(self, 'btn_d3_combo'):
                self.btn_d3_combo.set(self.btn_d3_target)
            if hasattr(self, 'btn_d4_combo'):
                self.btn_d4_combo.set(self.btn_d4_target)
            if hasattr(self, 'btn_d5_combo'):
                self.btn_d5_combo.set(self.btn_d5_target)
            if hasattr(self, 'btn_d6_combo'):
                self.btn_d6_combo.set(self.btn_d6_target)
            if hasattr(self, 'btn_d7_combo'):
                self.btn_d7_combo.set(self.btn_d7_target)
            if hasattr(self, 'btn_d8_combo'):
                self.btn_d8_combo.set(self.btn_d8_target)
            if hasattr(self, 'btn_d9_combo'):
                self.btn_d9_combo.set(self.btn_d9_target)
            if hasattr(self, 'btn_d10_combo'):
                self.btn_d10_combo.set(self.btn_d10_target)
            if hasattr(self, 'btn_d11_combo'):
                self.btn_d11_combo.set(self.btn_d11_target)
                
            if hasattr(self, 'preset_cycle_combo'):
                self.preset_cycle_combo.set(self.preset_cycle_btn)
                
            if hasattr(self, 'preset_combo'):
                self.preset_combo.set(preset_name)
                
            with self.lock:
                self.active_preset = preset_name
                
            self.save_config_to_json()

    def mark_custom(self, *args):
        current_active = getattr(self, 'active_preset', 'Personalizado')
        if current_active != "Personalizado":
            self.previous_preset = current_active
            
        if hasattr(self, 'preset_combo'):
            self.preset_combo.set("Personalizado")
        self.update_mappings()
        self.save_config_to_json()

    def update_mappings(self):
        # Guardar mapeos de forma segura para lectura del thread
        with self.lock:
            self.steer_target = self.steer_combo.get() if hasattr(self, 'steer_combo') else self.steer_target
            self.accel_target = self.accel_combo.get() if hasattr(self, 'accel_combo') else self.accel_target
            self.brake_target = self.brake_combo.get() if hasattr(self, 'brake_combo') else self.brake_target
            self.btn_d2_target = self.btn_d2_combo.get() if hasattr(self, 'btn_d2_combo') else self.btn_d2_target
            self.btn_d3_target = self.btn_d3_combo.get() if hasattr(self, 'btn_d3_combo') else self.btn_d3_target
            self.btn_d4_target = self.btn_d4_combo.get() if hasattr(self, 'btn_d4_combo') else self.btn_d4_target
            self.btn_d5_target = self.btn_d5_combo.get() if hasattr(self, 'btn_d5_combo') else self.btn_d5_target
            self.btn_d6_target = self.btn_d6_combo.get() if hasattr(self, 'btn_d6_combo') else self.btn_d6_target
            self.btn_d7_target = self.btn_d7_combo.get() if hasattr(self, 'btn_d7_combo') else self.btn_d7_target
            self.btn_d8_target = self.btn_d8_combo.get() if hasattr(self, 'btn_d8_combo') else self.btn_d8_target
            self.btn_d9_target = self.btn_d9_combo.get() if hasattr(self, 'btn_d9_combo') else self.btn_d9_target
            self.btn_d10_target = self.btn_d10_combo.get() if hasattr(self, 'btn_d10_combo') else self.btn_d10_target
            self.btn_d11_target = self.btn_d11_combo.get() if hasattr(self, 'btn_d11_combo') else self.btn_d11_target
            self.preset_cycle_btn = self.preset_cycle_combo.get() if hasattr(self, 'preset_cycle_combo') else self.preset_cycle_btn

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
                            
                            # Extraer campos de 10 bits y los botones
                            steer = val & 0x3FF
                            accel = (val >> 10) & 0x3FF
                            brake = (val >> 20) & 0x3FF
                            
                            # Extraer los 10 botones individuales (bits 0 a 9)
                            btn_states = []
                            for i in range(10):
                                btn_states.append((buttons_val >> i) & 0x01)

                            # Detectar flanco de subida del botón de alternar preset
                            with self.lock:
                                cycle_btn_name = self.preset_cycle_btn
                                
                            current_cycle_state = 0
                            if cycle_btn_name.startswith("Pin D"):
                                try:
                                    pin_num = int(cycle_btn_name[5:])
                                    idx = pin_num - 2
                                    if 0 <= idx < len(btn_states):
                                        current_cycle_state = btn_states[idx]
                                except ValueError:
                                    pass
                                    
                            if current_cycle_state == 1 and self.last_btn_cycle_state == 0:
                                self.after(0, self.cycle_presets_desktop)
                            self.last_btn_cycle_state = current_cycle_state

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
                                btn_mappings = [
                                    self.btn_d2_target, self.btn_d3_target, self.btn_d4_target,
                                    self.btn_d5_target, self.btn_d6_target, self.btn_d7_target,
                                    self.btn_d8_target, self.btn_d9_target, self.btn_d10_target,
                                    self.btn_d11_target
                                ]

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

                            # --- PROCESAR BOTONES (D2 a D11) ---
                            active_buttons = set()
                            for i in range(10):
                                if btn_states[i] == 1:
                                    target = btn_mappings[i]
                                    if target in BUTTON_MAP and BUTTON_MAP[target] is not None:
                                        active_buttons.add(BUTTON_MAP[target])

                            # Agregar botones virtuales del D-pad para mapeo
                            with self.lock:
                                for v_btn, state in self.virtual_btn_states.items():
                                    if state == 1:
                                        target_button = BUTTON_MAP.get(v_btn)
                                        if target_button is not None:
                                            active_buttons.add(target_button)

                            # Liberar botones que ya no deben estar presionados
                            to_release = [b for b in pressed_buttons if b not in active_buttons]
                            for b in to_release:
                                if b is not None:
                                    self.gamepad.release_button(button=b)
                                    pressed_buttons.remove(b)

                            # Presionar los botones activos si no lo están ya
                            for b in active_buttons:
                                if b not in pressed_buttons:
                                    self.gamepad.press_button(button=b)
                                    pressed_buttons.add(b)

                            # Guardar variables calculadas finales de forma segura para la visualización gráfica en UI
                            with self.lock:
                                self.current_steer = steer
                                self.current_accel = accel
                                self.current_brake = brake
                                self.current_btn_states = btn_states.copy()
                                
                                # Convertir valores calculados finales a escala 0-1023 para la UI
                                self.mapped_steer = int(((val_steer_mapped + 32768) / 65535.0) * 1023)
                                
                                # Para los pedales, mostramos la entrada analógica procesada con la zona muerta
                                self.mapped_accel = get_pedal_val(accel, 1023)
                                self.mapped_brake = get_pedal_val(brake, 1023)
                                self.mapped_btn_states = btn_states.copy()

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
                steer = self.mapped_steer
                accel = self.mapped_accel
                brake = self.mapped_brake
                btn_states = self.mapped_btn_states.copy()
            else:
                steer = self.current_steer
                accel = self.current_accel
                brake = self.current_brake
                btn_states = self.current_btn_states.copy()

        # Actualizar Barras de progreso (de 0.0 a 1.0)
        self.steer_bar.set(steer / 1023.0)
        self.accel_bar.set(accel / 1023.0)
        self.brake_bar.set(brake / 1023.0)

        # Actualizar indicadores de botones
        for i in range(10):
            if i < len(btn_states) and btn_states[i] == 1:
                self.btn_indicators[i].configure(fg_color="#2b7a4b", text_color="white")
            else:
                self.btn_indicators[i].configure(fg_color="gray25", text_color="gray70")

        # Actualizar etiquetas de texto
        self.steer_val_lbl.configure(text=f"{steer}")
        self.accel_val_lbl.configure(text=f"{int((accel / 1023.0) * 100)}%")
        self.brake_val_lbl.configure(text=f"{int((brake / 1023.0) * 100)}%")

        # Repetir cada 50ms
        self.after(50, self.update_gui_meters)

    def trigger_virtual_dpad(self, direction):
        with self.lock:
            self.virtual_btn_states[direction] = 1
        # Programar la liberación del botón virtual tras 500ms
        self.after(500, lambda: self.release_virtual_dpad(direction))

    def release_virtual_dpad(self, direction):
        with self.lock:
            self.virtual_btn_states[direction] = 0

    def cycle_presets_desktop(self):
        presets_list = list(self.custom_presets.keys()) + ["Personalizado"]
        current_preset = self.preset_combo.get()
        if current_preset in presets_list:
            current_idx = presets_list.index(current_preset)
            next_idx = (current_idx + 1) % len(presets_list)
        else:
            next_idx = 0
            
        next_preset = presets_list[next_idx]
        if hasattr(self, 'preset_combo'):
            self.preset_combo.set(next_preset)
        self.select_preset(next_preset)

    def on_closing(self):
        # Detener hilos y cerrar conexiones
        self.stop_emulation()
        if self.gamepad:
            del self.gamepad
        self.destroy()

if __name__ == "__main__":
    app = VolanteGUI()
    app.mainloop()

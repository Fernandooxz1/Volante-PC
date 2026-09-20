"""
Manejo de configuración, persistencia y presets para Volante-PC.
Multiplataforma: almacena en ~/.config/volante_pc/ en Linux y %APPDATA%/VolantePC/ en Windows.
Escritura atómica para evitar corrupción de datos.
"""

import json
import os
import shutil
import sys
import threading
from typing import Any, Dict, List, Optional

from core.protocol import CONFIG_BUTTON_KEYS

DEFAULT_CONFIG: Dict[str, Any] = {
    "language": "es",
    "theme_accent": "#00F2FE",
    "sensitivity": 1.0,
    "slope": 1.0,
    "anti_deadzone": 0.0,
    "deadzone": 0.13,
    "filter": 0.0,
    "steer_target": "Left Stick X",
    "accel_target": "Right Trigger (RT)",
    "brake_target": "Left Trigger (LT)",
    "clutch_target": "Right Stick Y- (DOWN)",
    "steer_min": 0,
    "steer_center": 512,
    "steer_max": 1023,
    "steer_lock_deg": 360,
    "invert_steer": False,
    "invert_accel": False,
    "invert_brake": False,
    "invert_clutch": False,
    "accel_min": 0,
    "accel_max": 1023,
    "brake_min": 0,
    "brake_max": 1023,
    "clutch_min": 0,
    "clutch_max": 1023,
    "btn_map_p2": "Ninguno",
    "btn_map_p3": "Button Start",
    "btn_map_p4": "Button B",
    "btn_map_p5": "Button X",
    "btn_map_p6": "Button A",
    "btn_map_p7": "Button Y",
    "btn_map_p8": "D-Pad RIGHT",
    "btn_map_pa3": "D-Pad LEFT",
    "btn_map_pa5": "D-Pad DOWN",
    "btn_map_pa4": "D-Pad UP",
    "btn_map_p12": "Ninguno",
    "preset_cycle_btn": "Pin D2",
    "mode": "Conducción",
    "active_preset": "Personalizado",
    "previous_preset": "F1 RACING CRUCETAS",
    "led_color": "Azul",
    "f1_telemetry_enabled": True,
    "f1_telemetry_port": 20777,
    "esp32_broadcast_enabled": True,
    "esp32_broadcast_host": "255.255.255.255",
    "esp32_broadcast_port": 20778,
    "custom_presets": {
        "F1 RACING": {
            "mode": "Conducción",
            "preset_cycle_btn": "Pin D2",
            "f1_telemetry": True,
            "steer_lock_deg": 360,
            "sensitivity": 1.0,
            "slope": 1.0,
            "anti_deadzone": 0.0,
            "deadzone": 0.08,
            "filter": 0.2,
            "steer_target": "Left Stick X",
            "accel_target": "Right Trigger (RT)",
            "brake_target": "Left Trigger (LT)",
            "clutch_target": "Right Stick Y- (DOWN)",
            "led_color": "Verde",
            "btn_map_p2": "Ninguno",
            "btn_map_p3": "Button Start",
            "btn_map_p4": "Button B",
            "btn_map_p5": "Button X",
            "btn_map_p6": "Button A",
            "btn_map_p7": "Button Y",
            "btn_map_p8": "D-Pad RIGHT",
            "btn_map_pa3": "D-Pad LEFT",
            "btn_map_pa5": "D-Pad DOWN",
            "btn_map_pa4": "D-Pad UP",
            "btn_map_p12": "Ninguno"
        },
        "F1 RACING CRUCETAS": {
            "mode": "Crucetas / D-Pad",
            "preset_cycle_btn": "Pin D2",
            "f1_telemetry": False,
            "steer_lock_deg": 360,
            "sensitivity": 1.0,
            "slope": 1.0,
            "anti_deadzone": 0.0,
            "deadzone": 0.13,
            "filter": 0.0,
            "steer_target": "Left Stick X",
            "accel_target": "Right Trigger (RT)",
            "brake_target": "Left Trigger (LT)",
            "clutch_target": "Right Stick Y- (DOWN)",
            "led_color": "Naranja",
            "btn_map_p2": "Ninguno",
            "btn_map_p3": "Button Start",
            "btn_map_p4": "Button B",
            "btn_map_p5": "Button X",
            "btn_map_p6": "Button A",
            "btn_map_p7": "Button Y",
            "btn_map_p8": "D-Pad RIGHT",
            "btn_map_pa3": "D-Pad LEFT",
            "btn_map_pa5": "D-Pad DOWN",
            "btn_map_pa4": "D-Pad UP",
            "btn_map_p12": "Ninguno"
        },
        "RALLY / DRIFT": {
            "steer_lock_deg": 540,
            "sensitivity": 1.0,
            "slope": 1.0,
            "anti_deadzone": 0.02,
            "deadzone": 0.05,
            "filter": 0.1,
            "steer_target": "Left Stick X",
            "accel_target": "Right Trigger (RT)",
            "brake_target": "Left Trigger (LT)",
            "clutch_target": "Right Stick Y- (DOWN)",
            "led_color": "Amarillo"
        },
        "SIMULADOR CAMIONES": {
            "steer_lock_deg": 900,
            "sensitivity": 1.0,
            "slope": 1.0,
            "anti_deadzone": 0.0,
            "deadzone": 0.15,
            "filter": 0.4,
            "steer_target": "Left Stick X",
            "accel_target": "Right Trigger (RT)",
            "brake_target": "Left Trigger (LT)",
            "clutch_target": "Right Stick Y- (DOWN)",
            "led_color": "Verde"
        }
    }
}

ALLOWED_STEER_LOCKS = (360, 540, 900)


def snap_steer_lock(degrees: int | float) -> int:
    """Ajusta cualquier ángulo continuo a los tres estándares de simracing (360°, 540°, 900°)."""
    deg = float(degrees)
    if deg <= 450:
        return 360
    elif deg <= 720:
        return 540
    return 900


def get_config_dir() -> str:
    """Devuelve la ruta al directorio de configuración según el sistema operativo."""
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
        config_dir = os.path.join(base, 'VolantePC')
    else:
        base = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        config_dir = os.path.join(base, 'volante_pc')
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def get_config_file_path() -> str:
    """Devuelve la ruta absoluta al archivo config_volante.json."""
    return os.path.join(get_config_dir(), 'config_volante.json')


class ConfigManager:
    """Gestor de configuración thread-safe con persistencia atómica."""

    def __init__(self, custom_path: Optional[str] = None):
        self._lock = threading.RLock()
        self.file_path = custom_path or get_config_file_path()
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Carga la configuración desde disco o genera la predeterminada."""
        with self._lock:
            loaded_data = {}
            if os.path.exists(self.file_path):
                try:
                    with open(self.file_path, 'r', encoding='utf-8') as f:
                        loaded_data = json.load(f)
                except Exception as e:
                    print(f"[ConfigManager] Error leyendo {self.file_path}: {e}")

            # Si hay datos previos guardados en disco, respetar exactamente los presets del usuario
            if loaded_data:
                merged = dict(DEFAULT_CONFIG)
                for k, v in loaded_data.items():
                    if k == "custom_presets" and isinstance(v, dict):
                        merged["custom_presets"] = dict(v)
                    else:
                        merged[k] = v
            else:
                merged = dict(DEFAULT_CONFIG)
                merged["custom_presets"] = dict(DEFAULT_CONFIG.get("custom_presets", {}))

            self.config = merged
            return dict(self.config)

    def save(self) -> bool:
        """Guarda atómicamente la configuración actual en disco."""
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
                temp_path = self.file_path + ".tmp"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4, ensure_ascii=False)
                # Reemplazo atómico en POSIX y Windows
                os.replace(temp_path, self.file_path)
                return True
            except Exception as e:
                print(f"[ConfigManager] Error guardando configuración: {e}")
                return False

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self.config[key] = value

    def update(self, updates: Dict[str, Any], auto_save: bool = True) -> None:
        with self._lock:
            self.config.update(updates)
        if auto_save:
            self.save()

    def get_language(self) -> str:
        with self._lock:
            return str(self.config.get("language", "es"))

    def set_language(self, lang: str, auto_save: bool = True) -> None:
        with self._lock:
            self.config["language"] = lang
        if auto_save:
            self.save()

    def get_theme_accent(self) -> str:
        with self._lock:
            return str(self.config.get("theme_accent", "#00F2FE"))

    def set_theme_accent(self, color_hex: str, auto_save: bool = True) -> None:
        with self._lock:
            self.config["theme_accent"] = color_hex
        if auto_save:
            self.save()

    def get_presets_list(self) -> List[str]:
        with self._lock:
            presets = list(self.config.get("custom_presets", {}).keys())
            if "Personalizado" not in presets:
                presets.append("Personalizado")
            return sorted(presets)

    def load_preset(self, preset_name: str) -> bool:
        """Carga los valores de un preset en la configuración activa."""
        with self._lock:
            custom_presets = self.config.get("custom_presets", {})
            if preset_name in custom_presets:
                preset_data = custom_presets[preset_name]
                for k, v in preset_data.items():
                    if k not in ("steer_min", "steer_center", "steer_max",
                                "accel_min", "accel_max", "brake_min", "brake_max",
                                "invert_steer", "invert_accel", "invert_brake"):
                        self.config[k] = v
                has_button_mapping = any(k.startswith("btn_map_") for k in preset_data)
                if has_button_mapping:
                    for btn_key in CONFIG_BUTTON_KEYS:
                        self.config[btn_key] = preset_data.get(btn_key, "Ninguno")
                if "mode" not in preset_data:
                    self.config["mode"] = "Crucetas / D-Pad" if "CRUCETA" in preset_name.upper() else "Conducción"
                if "steer_lock_deg" not in preset_data:
                    upper_name = preset_name.upper()
                    if "TRUCK" in upper_name or "CAMION" in upper_name:
                        self.config["steer_lock_deg"] = 900
                    elif "RALLY" in upper_name or "DIRT" in upper_name or "GT" in upper_name:
                        self.config["steer_lock_deg"] = 540
                    else:
                        self.config["steer_lock_deg"] = 360
                else:
                    self.config["steer_lock_deg"] = snap_steer_lock(preset_data["steer_lock_deg"])
                self.config["previous_preset"] = self.config.get("active_preset", "Personalizado")
                self.config["active_preset"] = preset_name
                return True
            elif preset_name == "Personalizado":
                self.config["previous_preset"] = self.config.get("active_preset", "Personalizado")
                self.config["active_preset"] = "Personalizado"
                return True
            return False

    def get_preset_counterpart(self, preset_name: str) -> Optional[str]:
        """
        Retorna el nombre exacto del preset contraparte/gemelo si existe registrado, o None.
        - Si el preset termina en ' CRUCETAS' (insensible a mayúsculas), su contraparte es el nombre base.
        - Si no termina en ' CRUCETAS', su contraparte es f'{preset_name} CRUCETAS'.
        """
        clean_name = preset_name.strip()
        if not clean_name:
            return None

        suffix = " CRUCETAS"
        if clean_name.upper().endswith(suffix):
            target = clean_name[:-len(suffix)].strip()
        else:
            target = f"{clean_name} CRUCETAS"

        if not target:
            return None

        target_upper = target.upper()
        with self._lock:
            custom_presets = self.config.get("custom_presets")
            if isinstance(custom_presets, dict):
                for key in custom_presets:
                    if key.strip().upper() == target_upper:
                        return key
        return None

    def save_current_as_preset(self, preset_name: str, sync_counterpart: bool = True) -> bool:
        """Guarda la configuración actual de sintonía, botones y modo como un preset nombrado."""
        clean_name = preset_name.strip()
        if not clean_name or clean_name == "Personalizado":
            return False

        with self._lock:
            if "custom_presets" not in self.config or not isinstance(self.config["custom_presets"], dict):
                self.config["custom_presets"] = {}

            existing_target = self.config["custom_presets"].get(clean_name, {})

            # Determinar modo para clean_name
            if "CRUCETA" in clean_name.upper():
                preset_mode = "Crucetas / D-Pad"
            elif existing_target.get("mode"):
                preset_mode = existing_target["mode"]
            else:
                preset_mode = self.config.get("mode", "Conducción")

            # Determinar led_color para clean_name
            if self.config.get("active_preset") == clean_name:
                preset_led = self.config.get("led_color", existing_target.get("led_color", "Azul"))
            elif existing_target.get("led_color"):
                preset_led = existing_target["led_color"]
            elif "CRUCETA" in clean_name.upper():
                preset_led = "Naranja"
            else:
                preset_led = self.config.get("led_color", "Azul")

            # Determinar f1_telemetry para clean_name
            if "CRUCETA" in clean_name.upper():
                preset_f1 = False
            elif "f1_telemetry" in existing_target:
                preset_f1 = existing_target["f1_telemetry"]
            else:
                preset_f1 = True if "F1" in clean_name.upper() and preset_mode == "Conducción" else False

            preset_dict: Dict[str, Any] = {
                "mode": preset_mode,
                "preset_cycle_btn": self.config.get("preset_cycle_btn", "Pin D2"),
                "sensitivity": self.config.get("sensitivity", 1.0),
                "slope": self.config.get("slope", 1.0),
                "anti_deadzone": self.config.get("anti_deadzone", 0.0),
                "deadzone": self.config.get("deadzone", 0.13),
                "filter": self.config.get("filter", 0.0),
                "steer_lock_deg": self.config.get("steer_lock_deg", 360),
                "steer_target": self.config.get("steer_target", "Left Stick X"),
                "accel_target": self.config.get("accel_target", "Right Trigger (RT)"),
                "brake_target": self.config.get("brake_target", "Left Trigger (LT)"),
                "clutch_target": self.config.get("clutch_target", "Right Stick Y- (DOWN)"),
                "invert_steer": self.config.get("invert_steer", False),
                "invert_accel": self.config.get("invert_accel", False),
                "invert_brake": self.config.get("invert_brake", False),
                "invert_clutch": self.config.get("invert_clutch", False),
                "led_color": preset_led,
                "f1_telemetry": preset_f1,
            }
            # Guardar botones
            for btn_key in CONFIG_BUTTON_KEYS:
                preset_dict[btn_key] = self.config.get(btn_key, "Ninguno")
            for key in self.config:
                if key.startswith("btn_map_"):
                    preset_dict[key] = self.config[key]

            self.config["custom_presets"][clean_name] = preset_dict
            self.config["active_preset"] = clean_name

            if sync_counterpart:
                counterpart_name = self.get_preset_counterpart(clean_name)
                if counterpart_name and counterpart_name in self.config["custom_presets"]:
                    counterpart_data = self.config["custom_presets"][counterpart_name]
                    # Preservar estrictamente modo, led_color y f1_telemetry de la contraparte
                    if "mode" not in counterpart_data:
                        counterpart_data["mode"] = "Crucetas / D-Pad" if "CRUCETA" in counterpart_name.upper() else "Conducción"
                    if "led_color" not in counterpart_data:
                        counterpart_data["led_color"] = "Naranja" if counterpart_data["mode"] == "Crucetas / D-Pad" else "Verde"
                    if "f1_telemetry" not in counterpart_data:
                        counterpart_data["f1_telemetry"] = True if "F1" in counterpart_name.upper() and counterpart_data["mode"] == "Conducción" else False

                    # Propagar configuraciones compartidas de hardware, pedales y dirección.
                    # IMPORTANTE: NO propagar mapeos de botones (btn_map_*), ya que el modo crucetas
                    # usa flechas direccionales y el modo conducción usa botones de acción (LB, RB, etc.).
                    shared_keys = (
                        "steer_lock_deg",
                        "deadzone",
                        "anti_deadzone",
                        "filter",
                        "sensitivity",
                        "slope",
                        "accel_target",
                        "brake_target",
                        "clutch_target",
                        "steer_target",
                        "invert_steer",
                        "invert_accel",
                        "invert_brake",
                        "invert_clutch",
                        "preset_cycle_btn",
                    )
                    for k in shared_keys:
                        if k in preset_dict:
                            counterpart_data[k] = preset_dict[k]

        self.save()
        return True

    def delete_preset(self, preset_name: str) -> bool:
        """Elimina un preset personalizado."""
        should_save = False
        with self._lock:
            custom_presets = self.config.get("custom_presets", {})
            if preset_name in custom_presets:
                del custom_presets[preset_name]
                if self.config.get("active_preset") == preset_name:
                    self.config["active_preset"] = "Personalizado"
                should_save = True
        if should_save:
            self.save()
            return True
        return False

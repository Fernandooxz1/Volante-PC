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

DEFAULT_CONFIG: Dict[str, Any] = {
    "language": "es",
    "theme_accent": "#00F2FE",
    "sensitivity": 1.0,
    "slope": 1.85,
    "anti_deadzone": 0.0,
    "deadzone": 0.13,
    "filter": 0.0,
    "steer_target": "Left Stick X",
    "accel_target": "Right Trigger (RT)",
    "brake_target": "Left Trigger (LT)",
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
    "custom_presets": {
        "F1 RACING": {
            "mode": "Conducción",
            "preset_cycle_btn": "Pin D2",
            "f1_telemetry": True,
            "sensitivity": 1.0,
            "slope": 2.2,
            "anti_deadzone": 0.0,
            "deadzone": 0.08,
            "filter": 0.2,
            "steer_target": "Left Stick X",
            "accel_target": "Right Trigger (RT)",
            "brake_target": "Left Trigger (LT)",
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
            "sensitivity": 1.0,
            "slope": 1.85,
            "anti_deadzone": 0.0,
            "deadzone": 0.13,
            "filter": 0.0,
            "steer_target": "Left Stick X",
            "accel_target": "Right Trigger (RT)",
            "brake_target": "Left Trigger (LT)",
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
            "sensitivity": 1.0,
            "slope": 1.0,
            "anti_deadzone": 0.02,
            "deadzone": 0.05,
            "filter": 0.1,
            "steer_target": "Left Stick X",
            "accel_target": "Right Trigger (RT)",
            "brake_target": "Left Trigger (LT)",
            "led_color": "Amarillo"
        },
        "SIMULADOR CAMIONES": {
            "sensitivity": 0.7,
            "slope": 1.4,
            "anti_deadzone": 0.0,
            "deadzone": 0.15,
            "filter": 0.4,
            "steer_target": "Left Stick X",
            "accel_target": "Right Trigger (RT)",
            "brake_target": "Left Trigger (LT)",
            "led_color": "Verde"
        }
    }
}


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
                if "mode" not in preset_data:
                    self.config["mode"] = "Crucetas / D-Pad" if "CRUCETA" in preset_name.upper() else "Conducción"
                self.config["previous_preset"] = self.config.get("active_preset", "Personalizado")
                self.config["active_preset"] = preset_name
                return True
            elif preset_name == "Personalizado":
                self.config["previous_preset"] = self.config.get("active_preset", "Personalizado")
                self.config["active_preset"] = "Personalizado"
                return True
            return False

    def save_current_as_preset(self, preset_name: str) -> bool:
        """Guarda la configuración actual de sintonía, botones y modo como un preset nombrado."""
        clean_name = preset_name.strip()
        if not clean_name or clean_name == "Personalizado":
            return False

        with self._lock:
            if "custom_presets" not in self.config:
                self.config["custom_presets"] = {}

            preset_dict: Dict[str, Any] = {
                "mode": self.config.get("mode", "Conducción"),
                "preset_cycle_btn": self.config.get("preset_cycle_btn", "Pin D2"),
                "sensitivity": self.config.get("sensitivity", 1.0),
                "slope": self.config.get("slope", 1.85),
                "anti_deadzone": self.config.get("anti_deadzone", 0.0),
                "deadzone": self.config.get("deadzone", 0.13),
                "filter": self.config.get("filter", 0.0),
                "steer_target": self.config.get("steer_target", "Left Stick X"),
                "accel_target": self.config.get("accel_target", "Right Trigger (RT)"),
                "brake_target": self.config.get("brake_target", "Left Trigger (LT)"),
                "led_color": self.config.get("led_color", "Azul"),
                "f1_telemetry": self.config.get("f1_telemetry", True if "F1" in clean_name.upper() and self.config.get("mode") == "Conducción" else False)
            }
            # Guardar botones
            for key in self.config:
                if key.startswith("btn_map_"):
                    preset_dict[key] = self.config[key]

            self.config["custom_presets"][clean_name] = preset_dict
            self.config["active_preset"] = clean_name
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

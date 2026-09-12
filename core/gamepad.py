"""
Abstracción multiplataforma de Gamepad Virtual (Xbox 360).
Maneja la creación y actualización del dispositivo virtual con vgamepad.
En Linux se comunica con el subsistema kernel uinput (/dev/uinput).
En Windows se comunica con el driver ViGEmBus.
"""

import os
import sys
from typing import Dict, Optional, Set, Tuple

import vgamepad as vg

BUTTON_MAPPING_TABLE: Dict[str, Optional[vg.XUSB_BUTTON]] = {
    "Button A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "Button B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "Button X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "Button Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "Button LB (Left Shoulder)": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "Button RB (Right Shoulder)": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    "Button Start": vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    "Button Back": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    "Button L3 (Left Click)": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    "Button R3 (Right Click)": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    "D-Pad UP": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    "D-Pad DOWN": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    "D-Pad LEFT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    "D-Pad RIGHT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    "Ninguno": None,
    "None": None,
}

AVAILABLE_TARGET_ACTIONS = list(BUTTON_MAPPING_TABLE.keys())


def check_gamepad_prerequisites() -> Tuple[bool, str]:
    """Verifica si el sistema tiene los requisitos para crear el gamepad virtual."""
    if sys.platform.startswith('linux'):
        uinput_path = '/dev/uinput'
        if not os.path.exists(uinput_path):
            return False, "El módulo 'uinput' del kernel no está cargado. Ejecuta: sudo modprobe uinput"
        if not os.access(uinput_path, os.W_OK):
            return False, (
                "Permiso denegado en /dev/uinput.\n"
                "Asegúrate de ejecutar ./install.sh o agregar tu usuario al grupo input:\n"
                "  sudo usermod -aG input,dialout $USER (luego reinicia sesión)."
            )
        return True, "Permisos de uinput correctos."
    elif sys.platform == 'win32':
        system_root = os.environ.get('SystemRoot', r'C:\Windows')
        possible_paths = [
            os.path.join(system_root, 'System32', 'drivers', 'ViGEmBus.sys'),
            os.path.join(system_root, 'Sysnative', 'drivers', 'ViGEmBus.sys'),
        ]
        driver_found = any(os.path.exists(p) for p in possible_paths)
        if not driver_found:
            return False, (
                "Controlador ViGEmBus no detectado en el sistema.\n"
                "Para emular el mando virtual de Xbox 360 en Windows, instala ViGEmBus:\n"
                "Ejecuta 'windows/drivers/ViGEmBus_Setup.exe' o el instalador del proyecto."
            )
        return True, "Driver ViGEmBus detectado en Windows."
    else:
        return True, "Plataforma no linux/windows."


class VirtualGamepadManager:
    """Manejador del gamepad virtual Xbox 360 con reconciliación por diferencias."""

    def __init__(self):
        self.gamepad: Optional[vg.VX360Gamepad] = None
        self.is_connected: bool = False
        self.error_message: Optional[str] = None
        self._pressed_buttons: Set[vg.XUSB_BUTTON] = set()

    def initialize(self) -> Tuple[bool, str]:
        """Inicializa el gamepad virtual de Xbox 360."""
        can_init, msg = check_gamepad_prerequisites()
        if not can_init:
            # En Windows intentamos crear VX360Gamepad por si el driver está cargado en otra ruta
            if sys.platform == 'win32':
                try:
                    self.gamepad = vg.VX360Gamepad()
                    self.is_connected = True
                    self.error_message = None
                    self._pressed_buttons.clear()
                    return True, "Gamepad virtual Xbox 360 inicializado correctamente."
                except Exception:
                    self.error_message = msg
                    self.is_connected = False
                    return False, msg
            else:
                self.error_message = msg
                self.is_connected = False
                return False, msg

        try:
            self.gamepad = vg.VX360Gamepad()
            self.is_connected = True
            self.error_message = None
            self._pressed_buttons.clear()
            return True, "Gamepad virtual Xbox 360 inicializado correctamente."
        except Exception as e:
            self.is_connected = False
            if sys.platform == 'win32':
                self.error_message = (
                    f"Error inicializando vgamepad: {e}.\n"
                    "Asegúrate de tener instalado el controlador ViGEmBus."
                )
            else:
                self.error_message = f"Error inicializando vgamepad: {e}"
            return False, self.error_message

    def apply_inputs(
        self,
        steer_target: str,
        steer_val: int,
        accel_target: str,
        accel_val: int,
        brake_target: str,
        brake_val: int,
        active_buttons: Set[str]
    ) -> None:
        """
        Aplica los ejes, gatillos y botones al gamepad virtual en un único lote atómico.
        """
        if not self.is_connected or not self.gamepad:
            return

        # 1. Aplicar Dirección
        self._apply_axis(steer_target, steer_val)

        # 2. Aplicar Acelerador
        self._apply_pedal(accel_target, accel_val)

        # 3. Aplicar Freno
        self._apply_pedal(brake_target, brake_val)

        # 4. Reconciliación de botones
        target_buttons: Set[vg.XUSB_BUTTON] = set()
        for btn_name in active_buttons:
            mapped_btn = BUTTON_MAPPING_TABLE.get(btn_name)
            if mapped_btn:
                target_buttons.add(mapped_btn)

        to_release = self._pressed_buttons - target_buttons
        to_press = target_buttons - self._pressed_buttons

        for btn in to_release:
            self.gamepad.release_button(btn)

        for btn in to_press:
            self.gamepad.press_button(btn)

        self._pressed_buttons = target_buttons

        # 5. Enviar actualización al driver del SO
        self.gamepad.update()

    def _apply_axis(self, target: str, value: int) -> None:
        if not self.gamepad:
            return
        # value: -32768 a 32767
        if target == "Left Stick X":
            self.gamepad.left_joystick(x_value=value, y_value=self._get_current_ly())
        elif target == "Right Stick X":
            self.gamepad.right_joystick(x_value=value, y_value=self._get_current_ry())
        elif target == "Left Stick Y":
            self.gamepad.left_joystick(x_value=self._get_current_lx(), y_value=-value)
        elif target == "Right Stick Y":
            self.gamepad.right_joystick(x_value=self._get_current_rx(), y_value=-value)

    def _apply_pedal(self, target: str, value: int) -> None:
        if not self.gamepad:
            return
        if target == "Right Trigger (RT)":
            self.gamepad.right_trigger(min(255, max(0, value)))
        elif target == "Left Trigger (LT)":
            self.gamepad.left_trigger(min(255, max(0, value)))
        elif target == "Right Stick Y+ (UP)":
            self.gamepad.right_joystick(x_value=self._get_current_rx(), y_value=-int(value * 128.5))
        elif target == "Right Stick Y- (DOWN)":
            self.gamepad.right_joystick(x_value=self._get_current_rx(), y_value=int(value * 128.5))
        elif target == "Left Stick Y+ (UP)":
            self.gamepad.left_joystick(x_value=self._get_current_lx(), y_value=-int(value * 128.5))
        elif target == "Left Stick Y- (DOWN)":
            self.gamepad.left_joystick(x_value=self._get_current_lx(), y_value=int(value * 128.5))

    def _get_current_lx(self) -> int:
        return 0

    def _get_current_ly(self) -> int:
        return 0

    def _get_current_rx(self) -> int:
        return 0

    def _get_current_ry(self) -> int:
        return 0

    def trigger_button_pulse(self, button_name: str, duration_ms: int = 200) -> None:
        """Pulsa temporalmente un botón virtual (ej. D-Pad) para mapeo en juegos."""
        import threading
        import time

        btn = BUTTON_MAPPING_TABLE.get(button_name)
        if not btn or not self.gamepad:
            return

        def pulse():
            if self.gamepad:
                self.gamepad.press_button(btn)
                self.gamepad.update()
                time.sleep(duration_ms / 1000.0)
                self.gamepad.release_button(btn)
                self.gamepad.update()

        threading.Thread(target=pulse, daemon=True).start()

    def reset(self) -> None:
        """Centra todos los controles y libera todos los botones."""
        if not self.is_connected or not self.gamepad:
            return
        try:
            for btn in self._pressed_buttons:
                self.gamepad.release_button(btn)
            self._pressed_buttons.clear()
            self.gamepad.left_joystick(0, 0)
            self.gamepad.right_joystick(0, 0)
            self.gamepad.left_trigger(0)
            self.gamepad.right_trigger(0)
            self.gamepad.update()
        except Exception:
            pass

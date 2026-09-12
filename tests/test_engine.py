"""Pruebas unitarias para core/engine.py."""

import os
import tempfile
import time
import unittest
from typing import List, Tuple

from core.config_manager import ConfigManager
from core.engine import (
    DEFAULT_AXIS_THRESHOLD,
    MODE_CONDUCCION,
    MODE_CRUCETAS,
    Engine,
    TelemetrySnapshot,
    label_to_pin,
    pin_to_label,
)
from core.protocol import PIN_NAMES


class MockGamepadManager:
    """Mock para pruebas de Engine sin dependencias de kernel uinput."""

    def __init__(self):
        self.is_connected = True
        self.error_message = None
        self.last_inputs = None
        self.reset_called = False
        self.pulses = []

    def initialize(self):
        self.is_connected = True
        return True, "Mock OK"

    def apply_inputs(self, steer_target, steer_val, accel_target, accel_val, brake_target, brake_val, active_buttons):
        self.last_inputs = {
            "steer_target": steer_target,
            "steer_val": steer_val,
            "accel_target": accel_target,
            "accel_val": accel_val,
            "brake_target": brake_target,
            "brake_val": brake_val,
            "active_buttons": set(active_buttons),
        }

    def trigger_button_pulse(self, button_name, duration_ms=200):
        self.pulses.append((button_name, duration_ms))

    def reset(self):
        self.reset_called = True


def make_raw_packet(steer: int, accel: int, brake: int, buttons: List[int]) -> bytes:
    """Construye un paquete binario válido de 8 bytes de Arduino (0xAA 0x55 + 6 payload)."""
    axes_val = (steer & 0x3FF) | ((accel & 0x3FF) << 10) | ((brake & 0x3FF) << 20)
    btn_val = 0
    for i, b in enumerate(buttons[:11]):
        if b:
            btn_val |= (1 << i)

    payload = axes_val.to_bytes(4, byteorder="little") + btn_val.to_bytes(2, byteorder="little")
    return bytes([0xAA, 0x55]) + payload


class TestEngine(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.config_manager = ConfigManager(custom_path=self.temp_file.name)
        self.mock_gamepad = MockGamepadManager()
        self.engine = Engine(
            config_manager=self.config_manager,
            gamepad_manager=self.mock_gamepad,
            auto_reconnect=False,
        )

    def tearDown(self):
        self.engine.stop()
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_initial_telemetry_snapshot(self):
        telemetry = self.engine.get_telemetry()
        self.assertIsInstance(telemetry, TelemetrySnapshot)
        self.assertEqual(telemetry.raw_steer, 512)
        self.assertEqual(telemetry.raw_accel, 0)
        self.assertEqual(telemetry.raw_brake, 0)
        self.assertEqual(len(telemetry.raw_buttons), 11)
        self.assertEqual(telemetry.mode, MODE_CONDUCCION)

        data = self.engine.get_telemetry_dict()
        self.assertIn("raw", data)
        self.assertIn("mapped", data)
        self.assertIn("gamepad", data)
        self.assertIn("steer_angle", data)

    def test_process_packet_math_and_gamepad(self):
        # Envía volante al centro (512), acelerador a 512, freno 0, botón 1 (D3 -> Button Start)
        buttons = [0] * 11
        buttons[1] = 1  # D3

        packet = make_raw_packet(steer=512, accel=512, brake=0, buttons=buttons)
        self.engine.process_bytes(packet)

        telemetry = self.engine.get_telemetry()
        self.assertEqual(telemetry.raw_steer, 512)
        self.assertEqual(telemetry.raw_accel, 512)
        self.assertEqual(telemetry.raw_brake, 0)
        self.assertEqual(telemetry.raw_buttons[1], 1)

        # Mapeo a gamepad virtual
        self.assertIsNotNone(self.mock_gamepad.last_inputs)
        # Volante centrado -> 0
        self.assertEqual(self.mock_gamepad.last_inputs["steer_val"], 0)
        # Botón D3 mapeado a Button Start según default config
        self.assertIn("Button Start", self.mock_gamepad.last_inputs["active_buttons"])

    def test_axis_inversion(self):
        self.config_manager.set("invert_steer", True)
        self.config_manager.set("invert_accel", True)

        # Si hardware lee 0 en steer con invert=True, cálculo lo toma como 1023 (full right)
        buttons = [0] * 11
        packet = make_raw_packet(steer=0, accel=0, brake=0, buttons=buttons)
        self.engine.process_bytes(packet)

        self.assertGreater(self.mock_gamepad.last_inputs["steer_val"], 30000)
        # Acelerador hardware 0 invertido a 1023 -> full trigger (255)
        self.assertEqual(self.mock_gamepad.last_inputs["accel_val"], 255)

    def test_reactive_input_event_bus_buttons(self):
        events = []

        def on_event(source_type: str, source_id: str, value: int):
            events.append((source_type, source_id, value))

        self.engine.set_input_listener(on_event)

        # Tick 1: Pulsar botón D2 (índice 0) -> Flanco de subida
        btn_pressed = [0] * 11
        btn_pressed[0] = 1
        self.engine.process_packet(512, 0, 0, btn_pressed)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], ("button", "D2", 1))

        # Tick 2: Mantener presionado -> NO debe generar evento duplicado
        events.clear()
        self.engine.process_packet(512, 0, 0, btn_pressed)
        self.assertEqual(len(events), 0)

        # Tick 3: Soltar botón -> Flanco de bajada (NO genera evento en rising edge)
        btn_released = [0] * 11
        self.engine.process_packet(512, 0, 0, btn_released)
        self.assertEqual(len(events), 0)

        # Tick 4: Volver a presionar D4 (índice 2) -> Nuevo evento
        btn_pressed2 = [0] * 11
        btn_pressed2[2] = 1
        self.engine.process_packet(512, 0, 0, btn_pressed2)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], ("button", "D4", 1))

    def test_reactive_input_event_bus_axes(self):
        events = []

        def on_event(source_type: str, source_id: str, value: int):
            events.append((source_type, source_id, value))

        # Inicializar línea base con 512
        self.engine.process_packet(512, 0, 0, [0] * 11)
        self.engine.set_input_listener(on_event)
        self.engine.set_axis_threshold(50)

        # Pequeño jitter (cambio de 10 unidades < umbral de 50) -> NO dispara evento
        self.engine.process_packet(522, 0, 0, [0] * 11)
        self.assertEqual(len(events), 0)

        # Movimiento intencional (512 a 600 -> delta = 88 >= 50) -> Dispara evento
        self.engine.process_packet(600, 0, 0, [0] * 11)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], ("axis", "steer", 600))

        # Mover pedal de freno de 0 a 120 -> Dispara evento
        events.clear()
        self.engine.process_packet(600, 0, 120, [0] * 11)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0], ("axis", "brake", 120))

    def test_modes_switching_and_dpad_emulation(self):
        self.assertEqual(self.engine.mode, MODE_CONDUCCION)

        # Cambiar a Crucetas / D-Pad
        new_mode = self.engine.toggle_mode()
        self.assertEqual(new_mode, MODE_CRUCETAS)
        self.assertEqual(self.engine.mode, MODE_CRUCETAS)

        # Giro fuerte a la izquierda (< -0.35) en modo Crucetas
        # Hardware steer = 0 -> normalized -1.0
        self.engine.process_packet(0, 0, 0, [0] * 11)
        self.assertIn("D-Pad LEFT", self.mock_gamepad.last_inputs["active_buttons"])
        # Ejes analógicos deben ser suprimidos a 0 para no interferir en menús
        self.assertEqual(self.mock_gamepad.last_inputs["steer_val"], 0)

        # Giro fuerte a la derecha (> 0.35)
        self.engine.process_packet(1023, 0, 0, [0] * 11)
        self.assertIn("D-Pad RIGHT", self.mock_gamepad.last_inputs["active_buttons"])
        self.assertNotIn("D-Pad LEFT", self.mock_gamepad.last_inputs["active_buttons"])

        # Presión de acelerador (> 0.25) -> D-Pad UP
        self.engine.process_packet(512, 800, 0, [0] * 11)
        self.assertIn("D-Pad UP", self.mock_gamepad.last_inputs["active_buttons"])

        # Presión de freno (> 0.25) -> D-Pad DOWN
        self.engine.process_packet(512, 0, 800, [0] * 11)
        self.assertIn("D-Pad DOWN", self.mock_gamepad.last_inputs["active_buttons"])

        # Volver a modo Conducción
        self.engine.set_mode(MODE_CONDUCCION)
        self.assertEqual(self.engine.mode, MODE_CONDUCCION)

        # Conducción normal: girar no activa D-Pad y los ejes analógicos se transmiten
        self.engine.process_packet(0, 0, 0, [0] * 11)
        self.assertNotIn("D-Pad LEFT", self.mock_gamepad.last_inputs["active_buttons"])
        self.assertLess(self.mock_gamepad.last_inputs["steer_val"], -30000)

    def test_preset_cycle_and_physical_button(self):
        # Configurar D2 como botón de alternar preset
        self.config_manager.set("preset_cycle_btn", "Pin D2")
        self.config_manager.set("active_preset", "F1 RACING")
        self.config_manager.set("previous_preset", "F1 RACING CRUCETAS")

        # Pulsar D2 (índice 0)
        btn_cycle = [0] * 11
        btn_cycle[0] = 1
        self.engine.process_packet(512, 0, 0, btn_cycle)

        # Debe haber alternado a F1 RACING CRUCETAS
        self.assertEqual(self.config_manager.get("active_preset"), "F1 RACING CRUCETAS")
        self.assertEqual(self.engine.mode, MODE_CRUCETAS)

        # Soltar D2 (flanco de bajada)
        self.engine.process_packet(512, 0, 0, [0] * 11)

        # Pulsar D2 nuevamente (estilo tecla Q de Counter-Strike)
        self.engine.process_packet(512, 0, 0, btn_cycle)

        # Debe volver a F1 RACING y Modo Conducción
        self.assertEqual(self.config_manager.get("active_preset"), "F1 RACING")
        self.assertEqual(self.engine.mode, MODE_CONDUCCION)

    def test_preset_cycle_suppressed_during_mapping(self):
        self.config_manager.set("preset_cycle_btn", "Pin D2")
        self.config_manager.set("active_preset", "F1 RACING")
        self.config_manager.set("previous_preset", "F1 RACING CRUCETAS")

        btn_cycle = [0] * 11
        btn_cycle[0] = 1

        # Caso 1: Asistente escuchando mediante listener
        self.engine.set_input_listener(lambda s, i, v: None)
        self.assertTrue(self.engine.is_mapping_active)

        # Pulsar D2 mientras el asistente está activo
        self.engine.process_packet(512, 0, 0, btn_cycle)
        # NO debe alternar preset
        self.assertEqual(self.config_manager.get("active_preset"), "F1 RACING")

        # Soltar D2 y cerrar listener
        self.engine.process_packet(512, 0, 0, [0] * 11)
        self.engine.set_input_listener(None)
        self.assertFalse(self.engine.is_mapping_active)

        # Caso 2: Modo mapeo explícito
        self.engine.set_mapping_mode(True)
        self.assertTrue(self.engine.is_mapping_active)
        self.engine.process_packet(512, 0, 0, btn_cycle)
        self.assertEqual(self.config_manager.get("active_preset"), "F1 RACING")

        # Desactivar modo mapeo
        self.engine.process_packet(512, 0, 0, [0] * 11)
        self.engine.set_mapping_mode(False)
        self.assertFalse(self.engine.is_mapping_active)

        # Ahora sí debe alternar normalmente al pulsar D2
        self.engine.process_packet(512, 0, 0, btn_cycle)
        self.assertEqual(self.config_manager.get("active_preset"), "F1 RACING CRUCETAS")

    def test_led_color_in_crucetas_mode_not_forced_to_naranja(self):
        class MockSerial:
            def __init__(self):
                self.is_open = True
                self.written = []

            def write(self, data):
                self.written.append(data)

            def flush(self):
                pass

        mock_ser = MockSerial()
        self.engine._serial = mock_ser

        # Cambiar a modo Crucetas
        self.engine.set_mode(MODE_CRUCETAS)
        self.assertEqual(self.engine.mode, MODE_CRUCETAS)

        # Establecer color Rojo
        self.engine.send_led_color("Rojo")
        self.assertEqual(self.engine._current_led_color, "Rojo")

        # Ejecutar transmisión inmediata
        now = time.time()
        self.engine._manage_led_transmission(now)
        self.assertIn(bytes([0xBB, 0x66, 1]), mock_ser.written)  # 1 = Rojo

        # Simular latido periódico pasados 3 segundos
        mock_ser.written.clear()
        self.engine._manage_led_transmission(now + 3.0)
        # El latido en modo crucetas debe mantener Rojo y NO sobreescribir a Naranja
        self.assertEqual(len(mock_ser.written), 1)
        self.assertEqual(mock_ser.written[0], bytes([0xBB, 0x66, 1]))  # Debe ser Rojo (1), NO Naranja (7)

    def test_led_command_queued(self):
        self.engine.set_led_color("Rojo")
        self.assertIsNotNone(self.engine._pending_led_command)
        self.assertEqual(self.engine._pending_led_command, bytes([0xBB, 0x66, 1]))

    def test_pin_helpers(self):
        self.assertEqual(pin_to_label("D2"), "Pin D2")
        self.assertEqual(pin_to_label("Pin D2"), "Pin D2")
        self.assertEqual(label_to_pin("Pin D2"), "D2")
        self.assertEqual(label_to_pin("D2"), "D2")

    def test_engine_lifecycle_thread(self):
        self.assertFalse(self.engine.is_running)
        started = self.engine.start()
        self.assertTrue(started)
        self.assertTrue(self.engine.is_running)

        # Dejar correr brevemente
        time.sleep(0.05)

        self.engine.stop()
        self.assertFalse(self.engine.is_running)
        self.assertTrue(self.mock_gamepad.reset_called)

    def test_disconnect_and_reconnect_thread_safety(self):
        """Verifica que disconnect() es seguro contra colisiones de hilos y actualiza la telemetría."""
        self.engine.start()
        self.assertTrue(self.engine.is_running)

        # Desconectar manualmente
        self.engine.disconnect()
        self.assertEqual(self.engine.status, "disconnected")
        self.assertTrue(self.engine._manual_disconnect)
        snap = self.engine.get_telemetry()
        self.assertEqual(snap.status, "disconnected")

        # Dejar iterar el bucle a 100 Hz mientras está desconectado
        time.sleep(0.05)

        # No debe haber reconectado automáticamente si fue manual
        self.assertEqual(self.engine.status, "disconnected")

        self.engine.stop()


if __name__ == "__main__":
    unittest.main()

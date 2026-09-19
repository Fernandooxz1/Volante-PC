"""
Pruebas de integración para ui/main_window.py:
Verifica el deslizador steer_lock_deg, la sincronización con WheelGauge,
la carga de presets con diferentes grados de giro y la telemetría.
"""

import os
import tempfile
import pytest
from PyQt6.QtWidgets import QApplication

from core.config_manager import ConfigManager
from core.engine import Engine, TelemetrySnapshot
from ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        app = QApplication([])
    return app


@pytest.fixture
def temp_config_file():
    temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
    temp_file.write("{}")
    temp_file.close()
    yield temp_file.name
    try:
        os.remove(temp_file.name)
    except OSError:
        pass


@pytest.fixture
def config_manager(temp_config_file):
    return ConfigManager(custom_path=temp_config_file)


@pytest.fixture
def engine(config_manager):
    return Engine(config_manager=config_manager, auto_reconnect=False)


def test_main_window_steer_lock_initialization(qapp, engine, config_manager):
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        assert hasattr(win, "slider_degrees")
        assert win.slider_degrees.minimum() == 360
        assert win.slider_degrees.maximum() == 900
        assert win.slider_degrees.value() == 360
        assert win.val_degrees.text() == "360°"
        assert win.wheel_gauge._max_angle == 180.0
    finally:
        win.close()


def test_main_window_slider_steer_lock_change(qapp, engine, config_manager):
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        # Cambiar a 900 grados (Camiones)
        win.slider_degrees.setValue(900)
        assert config_manager.get("steer_lock_deg") == 900
        assert win.val_degrees.text() == "900°"
        assert win.wheel_gauge._max_angle == 450.0

        # Cambiar a 540 grados (Rally)
        win.slider_degrees.setValue(540)
        assert config_manager.get("steer_lock_deg") == 540
        assert win.val_degrees.text() == "540°"
        assert win.wheel_gauge._max_angle == 270.0

        # Cambiar mediante click directo en el botón de 360 grados (F1)
        win.steer_lock_selector.btn_360.click()
        assert config_manager.get("steer_lock_deg") == 360
        assert win.val_degrees.text() == "360°"
        assert win.wheel_gauge._max_angle == 180.0
    finally:
        win.close()


def test_main_window_preset_loading_applies_steer_lock(qapp, engine, config_manager):
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        # Seleccionar preset RALLY / DRIFT (540°)
        win._on_preset_selected("RALLY / DRIFT")
        assert config_manager.get("steer_lock_deg") == 540
        assert win.slider_degrees.value() == 540
        assert win.wheel_gauge._max_angle == 270.0

        # Seleccionar preset SIMULADOR CAMIONES (900°)
        win._on_preset_selected("SIMULADOR CAMIONES")
        assert config_manager.get("steer_lock_deg") == 900
        assert win.slider_degrees.value() == 900
        assert win.wheel_gauge._max_angle == 450.0

        # Seleccionar preset F1 RACING (360°)
        win._on_preset_selected("F1 RACING")
        assert config_manager.get("steer_lock_deg") == 360
        assert win.slider_degrees.value() == 360
        assert win.wheel_gauge._max_angle == 180.0
    finally:
        win.close()


def test_main_window_telemetry_snapshot_updates_wheel_gauge(qapp, engine, config_manager):
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        win.slider_degrees.setValue(900)  # max_angle = 450.0
        base_snap = engine.get_telemetry()
        snapshot = TelemetrySnapshot(
            timestamp=base_snap.timestamp,
            status="connected",
            active_port=base_snap.active_port,
            mode=base_snap.mode,
            preset=base_snap.preset,
            led_color=base_snap.led_color,
            raw_steer=800,
            raw_accel=512,
            raw_brake=0,
            raw_buttons=base_snap.raw_buttons,
            mapped_steer=base_snap.mapped_steer,
            mapped_accel=base_snap.mapped_accel,
            mapped_brake=base_snap.mapped_brake,
            mapped_buttons=base_snap.mapped_buttons,
            steer_angle=320.5,
            steer_phys_norm=0.71,
            steer_out_norm=0.71,
            throttle_pct=50.0,
            brake_pct=0.0,
            gamepad_steer=base_snap.gamepad_steer,
            gamepad_accel=base_snap.gamepad_accel,
            gamepad_brake=base_snap.gamepad_brake,
            active_gamepad_buttons=base_snap.active_gamepad_buttons,
            loop_hz=60.0,
            gamepad_connected=True,
        )
        win._on_telemetry_snapshot(snapshot)
        assert abs(win.wheel_gauge.get_angle() - 320.5) < 0.01
        assert win.wheel_gauge._raw_value == 800
    finally:
        win.close()


def test_main_window_quick_center_button(qapp, engine, config_manager):
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        assert hasattr(win, "btn_quick_center")
        # Simular volante en raw 600
        engine.process_packet(600, 0, 0, [0] * 11)
        win.btn_quick_center.click()
        assert config_manager.get("steer_center") == 600
    finally:
        win.close()


def test_main_window_clutch_pedal_telemetry_and_behavior(qapp, engine, config_manager):
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        assert hasattr(win, "pedal_clutch")
        assert win.pedal_clutch._pedal_type == "clutch"
        assert win.pedal_clutch._bar_color.name() == "#00e5ff"

        # Simular snapshot con embrague
        base_snap = engine.get_telemetry()
        snapshot = TelemetrySnapshot(
            timestamp=base_snap.timestamp,
            status="connected",
            active_port=base_snap.active_port,
            mode=base_snap.mode,
            preset=base_snap.preset,
            led_color=base_snap.led_color,
            raw_steer=512,
            raw_accel=0,
            raw_brake=0,
            raw_buttons=base_snap.raw_buttons,
            mapped_steer=0.0,
            mapped_accel=0.0,
            mapped_brake=0.0,
            mapped_buttons=base_snap.mapped_buttons,
            steer_angle=0.0,
            steer_phys_norm=0.0,
            steer_out_norm=0.0,
            throttle_pct=0.0,
            brake_pct=0.0,
            gamepad_steer=0,
            gamepad_accel=0,
            gamepad_brake=0,
            active_gamepad_buttons=base_snap.active_gamepad_buttons,
            loop_hz=60.0,
            gamepad_connected=True,
            clutch_pct=75.0,
            raw_clutch=768,
        )
        win._update_telemetry(snapshot)
        assert abs(win.pedal_clutch.get_value() - 0.75) < 0.01
        assert win.pedal_clutch.get_raw_adc() == 768

        # Test deadzone
        win._on_deadzone_changed(0.18)
        assert abs(win.pedal_clutch.get_deadzone() - 0.18) < 0.001

        # Test preset settings
        win._apply_preset_settings({"steer_lock_deg": 540, "deadzone": 0.12})
        assert abs(win.pedal_clutch.get_deadzone() - 0.12) < 0.001

        # Test retranslation
        from ui.i18n import set_language
        set_language("en")
        assert win.pedal_clutch._label == "CLUTCH"
        set_language("es")
        assert win.pedal_clutch._label == "EMBRAGUE"
    finally:
        win.close()


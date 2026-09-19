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
from core.protocol import CONFIG_BUTTON_KEYS, PIN_NAMES
from ui.i18n import set_language
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
        assert abs(win.pedal_throttle.get_value() - 0.50) < 0.01
        assert win.pedal_throttle.get_raw_adc() == 512
        assert abs(win.pedal_brake.get_value() - 0.0) < 0.01
        assert win.pedal_brake.get_raw_adc() == 0
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


def test_main_window_all_pedals_and_wheel_full_telemetry_cycle(qapp, engine, config_manager):
    """
    Verifica que el WheelGauge y las tres barras de pedales (acelerador, freno, embrague)
    funcionen conjuntamente de forma robusta a lo largo de un ciclo completo de telemetría,
    cambio de presets y propagación de zona muerta.
    """
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        # 1. Verificar existencia y configuración inicial de los widgets DDU
        assert hasattr(win, "wheel_gauge")
        assert hasattr(win, "pedal_throttle")
        assert hasattr(win, "pedal_brake")
        assert hasattr(win, "pedal_clutch")

        assert win.pedal_throttle._pedal_type == "throttle"
        assert win.pedal_brake._pedal_type == "brake"
        assert win.pedal_clutch._pedal_type == "clutch"

        assert win.pedal_throttle.get_value() == 0.0
        assert win.pedal_brake.get_value() == 0.0
        assert win.pedal_clutch.get_value() == 0.0
        assert win.wheel_gauge.get_angle() == 0.0

        base_snap = engine.get_telemetry()

        # 2. Telemetría Escenario 1: Aceleración a fondo + dirección a la derecha
        snap1 = TelemetrySnapshot(
            timestamp=base_snap.timestamp,
            status="connected",
            active_port="COM3",
            mode="DRIVE MODE",
            preset="F1 RACING",
            led_color="#00e5ff",
            raw_steer=720,
            raw_accel=1023,
            raw_brake=0,
            raw_buttons=base_snap.raw_buttons,
            mapped_steer=0.5,
            mapped_accel=1.0,
            mapped_brake=0.0,
            mapped_buttons=base_snap.mapped_buttons,
            steer_angle=90.0,
            steer_phys_norm=0.5,
            steer_out_norm=0.5,
            throttle_pct=100.0,
            brake_pct=0.0,
            gamepad_steer=16384,
            gamepad_accel=32767,
            gamepad_brake=0,
            active_gamepad_buttons=[],
            loop_hz=100.0,
            gamepad_connected=True,
            clutch_pct=15.0,
            raw_clutch=154,
        )
        win._on_telemetry_snapshot(snap1)
        assert abs(win.wheel_gauge.get_angle() - 90.0) < 0.01
        assert win.wheel_gauge._raw_value == 720
        assert abs(win.pedal_throttle.get_value() - 1.00) < 0.01
        assert win.pedal_throttle.get_raw_adc() == 1023
        assert abs(win.pedal_brake.get_value() - 0.0) < 0.01
        assert win.pedal_brake.get_raw_adc() == 0
        assert abs(win.pedal_clutch.get_value() - 0.15) < 0.01
        assert win.pedal_clutch.get_raw_adc() == 154

        # 3. Telemetría Escenario 2: Frenada fuerte + embrague a fondo + dirección a la izquierda (-270°)
        win.slider_degrees.setValue(900)  # Max angle = 450°
        snap2 = TelemetrySnapshot(
            timestamp=base_snap.timestamp,
            status="connected",
            active_port="COM3",
            mode="DRIVE MODE",
            preset="SIMULADOR CAMIONES",
            led_color="#00e5ff",
            raw_steer=120,
            raw_accel=0,
            raw_brake=1023,
            raw_buttons=base_snap.raw_buttons,
            mapped_steer=-0.6,
            mapped_accel=0.0,
            mapped_brake=1.0,
            mapped_buttons=base_snap.mapped_buttons,
            steer_angle=-270.0,
            steer_phys_norm=-0.6,
            steer_out_norm=-0.6,
            throttle_pct=0.0,
            brake_pct=100.0,
            gamepad_steer=-19660,
            gamepad_accel=0,
            gamepad_brake=32767,
            active_gamepad_buttons=[],
            loop_hz=100.0,
            gamepad_connected=True,
            clutch_pct=100.0,
            raw_clutch=1023,
        )
        win._on_telemetry_snapshot(snap2)
        assert abs(win.wheel_gauge.get_angle() - (-270.0)) < 0.01
        assert win.wheel_gauge._raw_value == 120
        assert abs(win.pedal_throttle.get_value() - 0.0) < 0.01
        assert win.pedal_throttle.get_raw_adc() == 0
        assert abs(win.pedal_brake.get_value() - 1.00) < 0.01
        assert win.pedal_brake.get_raw_adc() == 1023
        assert abs(win.pedal_clutch.get_value() - 1.00) < 0.01
        assert win.pedal_clutch.get_raw_adc() == 1023

        # 4. Propagación de zona muerta a los tres pedales simultáneamente
        win._on_deadzone_changed(0.16)
        assert abs(win.pedal_throttle.get_deadzone() - 0.16) < 0.001
        assert abs(win.pedal_brake.get_deadzone() - 0.16) < 0.001
        assert abs(win.pedal_clutch.get_deadzone() - 0.16) < 0.001

        # 5. Internacionalización de etiquetas en los tres pedales
        from ui.i18n import set_language
        set_language("en")
        assert win.pedal_throttle._label == "THROTTLE"
        assert win.pedal_brake._label == "BRAKE"
        assert win.pedal_clutch._label == "CLUTCH"

        set_language("es")
        assert win.pedal_throttle._label == "ACELERADOR"
        assert win.pedal_brake._label == "FRENO"
        assert win.pedal_clutch._label == "EMBRAGUE"
    finally:
        win.close()


def test_main_window_pedals_and_wheel_resilient_without_curve_canvas(qapp, engine, config_manager):
    """
    Verifica que MainWindow y sus componentes críticos (WheelGauge, PedalBars)
    no fallen ni dependan de curve_canvas, slider_sens o slider_slope.
    """
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        # Asegurar que los componentes vitales de hardware existen
        assert hasattr(win, "wheel_gauge")
        assert hasattr(win, "pedal_throttle")
        assert hasattr(win, "pedal_brake")
        assert hasattr(win, "pedal_clutch")

        # Verificar que el volante y los pedales reciben telemetría independientemente
        base_snap = engine.get_telemetry()
        snapshot = TelemetrySnapshot(
            timestamp=base_snap.timestamp,
            status="connected",
            active_port="COM3",
            mode="DRIVE MODE",
            preset="F1 RACING",
            led_color="#00e5ff",
            raw_steer=512,
            raw_accel=512,
            raw_brake=512,
            raw_buttons=base_snap.raw_buttons,
            mapped_steer=0.0,
            mapped_accel=0.5,
            mapped_brake=0.5,
            mapped_buttons=base_snap.mapped_buttons,
            steer_angle=0.0,
            steer_phys_norm=0.0,
            steer_out_norm=0.0,
            throttle_pct=50.0,
            brake_pct=50.0,
            gamepad_steer=0,
            gamepad_accel=16384,
            gamepad_brake=16384,
            active_gamepad_buttons=[],
            loop_hz=100.0,
            gamepad_connected=True,
            clutch_pct=50.0,
            raw_clutch=512,
        )
        win._on_telemetry_snapshot(snapshot)
        assert abs(win.pedal_throttle.get_value() - 0.50) < 0.01
        assert abs(win.pedal_brake.get_value() - 0.50) < 0.01
        assert abs(win.pedal_clutch.get_value() - 0.50) < 0.01
        assert win.wheel_gauge.get_angle() - 0.0 < 0.01
    finally:
        win.close()


def test_main_window_curve_canvas_and_sliders_cleaned(qapp, engine, config_manager):
    """
    Verifica que la curva gráfica y los sliders de sensibilidad/pendiente hayan sido
    removidos de la interfaz principal de forma limpia, manteniendo la compatibilidad
    hacia atrás (dummy None attributes) y asegurando que WheelGauge y las 3 barras de
    pedales sigan funcionando al 100% sin roturas.
    """
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        # 1. CurveCanvas y Sliders de sensibilidad/pendiente ya no deben estar activos
        assert win.curve_canvas is None
        assert win.slider_sens is None
        assert win.slider_slope is None

        # 2. Los widgets de telemetría DDU deben seguir existiendo e intactos
        assert win.wheel_gauge is not None
        assert win.pedal_clutch is not None
        assert win.pedal_brake is not None
        assert win.pedal_throttle is not None

        # 3. Invocar sincronización de configuración no debe lanzar excepción
        win._sync_sliders_from_config()

        # 4. Cambios de tema no deben lanzar excepción
        win._on_theme_changed("#ff5722", "es")
        assert win.wheel_gauge._accent_color.name() == "#ff5722"

        # 5. Telemetría debe actualizar wheel_gauge y las barras de pedales sin errores
        base_snap = engine.get_telemetry()
        snapshot = TelemetrySnapshot(
            timestamp=base_snap.timestamp,
            status="connected",
            active_port="COM3",
            mode="DRIVE MODE",
            preset="F1 RACING",
            led_color="#00e5ff",
            raw_steer=650,
            raw_accel=800,
            raw_brake=400,
            raw_buttons=base_snap.raw_buttons,
            mapped_steer=0.25,
            mapped_accel=0.8,
            mapped_brake=0.4,
            mapped_buttons=base_snap.mapped_buttons,
            steer_angle=45.0,
            steer_phys_norm=0.25,
            steer_out_norm=0.25,
            throttle_pct=80.0,
            brake_pct=40.0,
            gamepad_steer=8192,
            gamepad_accel=26000,
            gamepad_brake=13000,
            active_gamepad_buttons=[],
            loop_hz=100.0,
            gamepad_connected=True,
            clutch_pct=60.0,
            raw_clutch=600,
        )
        win._on_telemetry_snapshot(snapshot)
        assert abs(win.wheel_gauge.get_angle() - 45.0) < 0.01
        assert abs(win.pedal_throttle.get_value() - 0.80) < 0.01
        assert abs(win.pedal_brake.get_value() - 0.40) < 0.01
        assert abs(win.pedal_clutch.get_value() - 0.60) < 0.01
    finally:
        win.close()


def test_main_window_button_indicators_initialization(qapp, engine, config_manager):
    """Verifica que los 11 indicadores muestren las acciones de Xbox asignadas y no los nombres de pines."""
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        assert hasattr(win, "buttons_box")
        assert win.buttons_box.title() == "Botones Xbox"
        assert len(win._btn_indicators) == 11

        # Verificar etiquetas de botones con la configuración por defecto
        # D2 -> Ninguno -> "-"
        assert win._btn_indicators["D2"].text() == "-"
        assert "D2" in win._btn_indicators["D2"].toolTip()

        # D3 -> Button Start -> "START"
        assert win._btn_indicators["D3"].text() == "START"

        # D4 -> Button B -> "BTN B"
        assert win._btn_indicators["D4"].text() == "BTN B"

        # D5 -> Button X -> "BTN X"
        assert win._btn_indicators["D5"].text() == "BTN X"

        # D6 -> Button A -> "BTN A"
        assert win._btn_indicators["D6"].text() == "BTN A"

        # D7 -> Button Y -> "BTN Y"
        assert win._btn_indicators["D7"].text() == "BTN Y"

        # D8 -> D-Pad RIGHT -> "DPAD RT"
        assert win._btn_indicators["D8"].text() == "DPAD RT"

        # A3 -> D-Pad LEFT -> "DPAD LF"
        assert win._btn_indicators["A3"].text() == "DPAD LF"

        # A5 -> D-Pad DOWN -> "DPAD DN"
        assert win._btn_indicators["A5"].text() == "DPAD DN"

        # A4 -> D-Pad UP -> "DPAD UP"
        assert win._btn_indicators["A4"].text() == "DPAD UP"

        # D12 -> Ninguno -> "-"
        assert win._btn_indicators["D12"].text() == "-"
    finally:
        win.close()


def test_main_window_button_indicators_telemetry_press_and_release(qapp, engine, config_manager):
    """Verifica que al pulsar un botón físicamente, la pastilla se ilumine manteniendo el texto del botón Xbox asignado."""
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        base_snap = engine.get_telemetry()
        accent = config_manager.get_theme_accent() if hasattr(config_manager, "get_theme_accent") else "#00e5ff"

        # Simular pulsación de D6 (índice 4 en PIN_NAMES) -> "BTN A"
        raw_pressed = [0] * 11
        raw_pressed[4] = 1  # D6 = 1

        snap_pressed = TelemetrySnapshot(
            timestamp=base_snap.timestamp,
            status="connected",
            active_port=base_snap.active_port,
            mode=base_snap.mode,
            preset=base_snap.preset,
            led_color=base_snap.led_color,
            raw_steer=512,
            raw_accel=0,
            raw_brake=0,
            raw_buttons=raw_pressed,
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
        )
        win._on_telemetry_snapshot(snap_pressed)

        lbl_d6 = win._btn_indicators["D6"]
        # El texto DEBE ser "BTN A", NUNCA "D6"
        assert lbl_d6.text() == "BTN A"
        # Debe iluminarse con el color de acento y resaltar
        assert accent in lbl_d6.styleSheet()
        assert "#0a0c10" in lbl_d6.styleSheet()

        # D3 no presionado debe mantener estilo en reposo
        lbl_d3 = win._btn_indicators["D3"]
        assert lbl_d3.text() == "START"
        assert "#161c24" in lbl_d3.styleSheet()

        # Simular liberación del botón
        raw_released = [0] * 11
        snap_released = TelemetrySnapshot(
            timestamp=base_snap.timestamp,
            status="connected",
            active_port=base_snap.active_port,
            mode=base_snap.mode,
            preset=base_snap.preset,
            led_color=base_snap.led_color,
            raw_steer=512,
            raw_accel=0,
            raw_brake=0,
            raw_buttons=raw_released,
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
        )
        win._on_telemetry_snapshot(snap_released)

        # Regresa a reposo pero conserva el texto "BTN A"
        assert lbl_d6.text() == "BTN A"
        assert "#161c24" in lbl_d6.styleSheet()
    finally:
        win.close()


def test_main_window_button_indicators_dynamic_mapping_and_preset_update(qapp, engine, config_manager):
    """Verifica que al cambiar asignaciones o cargar presets, los textos se actualicen dinámicamente."""
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        # Modificar mapeo de D2 a LB
        config_manager.set("btn_map_p2", "Button LB (Left Shoulder)")
        win._update_button_labels()
        assert win._btn_indicators["D2"].text() == "LB"
        assert "Button LB" in win._btn_indicators["D2"].toolTip()

        # Modificar mapeo de D12 a RB
        config_manager.set("btn_map_p12", "Button RB (Right Shoulder)")
        win._update_button_labels()
        assert win._btn_indicators["D12"].text() == "RB"

        # Probar re-asignar a Ninguno
        config_manager.set("btn_map_p2", "Ninguno")
        win._update_button_labels()
        assert win._btn_indicators["D2"].text() == "-"

        # Probar cambio de preset
        win._on_preset_selected("F1 RACING")
        assert win._btn_indicators["D6"].text() == "BTN A"
        assert win._btn_indicators["D3"].text() == "START"
    finally:
        win.close()


def test_main_window_button_box_retranslation(qapp, engine, config_manager):
    """Verifica la traducción del contenedor de botones entre español e inglés."""
    win = MainWindow(engine=engine, config_manager=config_manager)
    try:
        set_language("en")
        assert win.buttons_box.title() == "Xbox Buttons"

        set_language("es")
        assert win.buttons_box.title() == "Botones Xbox"
    finally:
        set_language("es")
        win.close()


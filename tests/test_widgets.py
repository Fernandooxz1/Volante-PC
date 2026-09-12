"""
Pruebas unitarias y de renderizado para los widgets Motorsport PyQt6 en ui/widgets/.
Verifica creación, setters, renderizado vectorial offscreen y ausencia total de emojis.
"""

import os
import glob
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication

from ui.widgets import (
    ButtonGrid,
    ButtonPill,
    CurveCanvas,
    LedIndicator,
    PedalBar,
    WheelGauge,
)
from core.protocol import PIN_NAMES


@pytest.fixture(scope="session")
def qapp():
    """Crea una instancia de QApplication para pruebas de widgets de interfaz."""
    app = QApplication.instance()
    if app is None:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        app = QApplication([])
    return app


# =============================================================================
# 1. Pruebas de WheelGauge
# =============================================================================

def test_wheel_gauge_initialization(qapp):
    gauge = WheelGauge(max_angle=90.0)
    assert gauge.get_angle() == 0.0
    assert gauge.minimumSize().width() >= 180
    assert gauge.minimumSize().height() >= 180


def test_wheel_gauge_set_angle(qapp):
    gauge = WheelGauge(max_angle=90.0)
    gauge.set_angle(-45.2)
    assert abs(gauge.get_angle() - (-45.2)) < 0.01

    # Clamping
    gauge.set_angle(120.0)
    assert gauge.get_angle() == 90.0
    gauge.set_angle(-120.0)
    assert gauge.get_angle() == -90.0


def test_wheel_gauge_normalized_and_raw(qapp):
    gauge = WheelGauge(max_angle=90.0)
    gauge.set_normalized_value(0.5)
    assert abs(gauge.get_angle() - 45.0) < 0.01

    gauge.set_raw_value(512, steer_min=0, steer_center=512, steer_max=1023)
    assert abs(gauge.get_angle() - 0.0) < 0.01

    gauge.set_raw_value(0, steer_min=0, steer_center=512, steer_max=1023)
    assert gauge.get_angle() == -90.0


def test_wheel_gauge_render(qapp):
    gauge = WheelGauge()
    gauge.resize(260, 260)
    for test_angle in [-90.0, -45.0, 0.0, 45.0, 90.0]:
        gauge.set_angle(test_angle)
        pix = gauge.grab()
        assert not pix.isNull()
        assert pix.width() == 260
        assert pix.height() == 260


# =============================================================================
# 2. Pruebas de PedalBar
# =============================================================================

def test_pedal_bar_initialization(qapp):
    throttle = PedalBar(label="THROTTLE", pedal_type="throttle")
    assert throttle.get_value() == 0.0
    assert throttle.get_raw_adc() == 0

    brake = PedalBar(label="BRAKE", pedal_type="brake")
    assert brake._pedal_type == "brake"


def test_pedal_bar_values_and_deadzone(qapp):
    bar = PedalBar(label="THROTTLE", pedal_type="throttle")
    bar.set_value(0.85, raw_adc=870)
    assert abs(bar.get_value() - 0.85) < 0.001
    assert bar.get_raw_adc() == 870

    # Test auto-scaling if percentage (0..100) is passed
    bar.set_value(65.0, raw_adc=660)
    assert abs(bar.get_value() - 0.65) < 0.001

    bar.set_deadzone(0.12)
    assert abs(bar.get_deadzone() - 0.12) < 0.001


def test_pedal_bar_render(qapp):
    bar = PedalBar(label="THROTTLE", pedal_type="throttle")
    bar.resize(95, 240)
    for level in [0.0, 0.25, 0.50, 0.85, 1.0]:
        bar.set_value(level, raw_adc=int(level * 1023))
        pix = bar.grab()
        assert not pix.isNull()
        assert pix.width() == 95


# =============================================================================
# 3. Pruebas de CurveCanvas
# =============================================================================

def test_curve_canvas_initialization(qapp):
    canvas = CurveCanvas(slope=1.85, sensitivity=1.0, anti_deadzone=0.0, rest_deadzone=0.02)
    assert canvas._slope == 1.85
    assert canvas._sensitivity == 1.0


def test_curve_canvas_follower_and_params(qapp):
    canvas = CurveCanvas()
    canvas.set_parameters(slope=2.2, sensitivity=1.0, anti_deadzone=0.05, rest_deadzone=0.01)
    assert canvas._slope == 2.2
    assert canvas._anti_deadzone == 0.05

    canvas.set_follower(0.5)
    assert abs(canvas._input_x - 0.5) < 0.01
    assert canvas._output_y > 0.0


def test_curve_canvas_render(qapp):
    canvas = CurveCanvas()
    canvas.resize(320, 240)
    for fx in [-1.0, -0.5, 0.0, 0.5, 1.0]:
        canvas.set_follower(fx)
        pix = canvas.grab()
        assert not pix.isNull()
        assert pix.width() == 320


# =============================================================================
# 4. Pruebas de ButtonGrid
# =============================================================================

def test_button_grid_initialization(qapp):
    grid = ButtonGrid(columns=4)
    assert len(grid._pills) == 11
    for pin in PIN_NAMES:
        assert pin in grid._pills


def test_button_grid_states_and_mapping(qapp):
    grid = ButtonGrid(columns=4)
    grid.set_mapping({"D2": "Button Start", "D3": "Button B", "D12": "D-Pad UP"})
    assert grid._pills["D2"]._action_label == "START"
    assert grid._pills["D3"]._action_label == "BTN B"
    assert grid._pills["D12"]._action_label == "DPAD UP"

    grid.set_button_states([1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0])
    assert grid.get_button_state("D2") is True
    assert grid.get_button_state("D3") is False
    assert grid.get_button_state("D4") is True

    grid.set_button_state("D12", True)
    assert grid.get_button_state("D12") is True


def test_button_grid_render(qapp):
    grid = ButtonGrid(columns=4)
    grid.resize(400, 160)
    grid.set_button_states([1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1])
    pix = grid.grab()
    assert not pix.isNull()
    assert pix.width() == 400


# =============================================================================
# 5. Pruebas de LedIndicator
# =============================================================================

def test_led_indicator_initialization(qapp):
    led = LedIndicator(mode="DRIVE MODE", led_color="azul")
    assert led.get_mode() == "DRIVE MODE"
    assert not led.is_alert_mode()


def test_led_indicator_mode_switch(qapp):
    led = LedIndicator()
    led.set_mode("DRIVE MODE")
    assert not led.is_alert_mode()

    led.set_mode("D-PAD / CRUCETAS")
    assert led.is_alert_mode()

    led.set_led_color("rojo")
    assert led.get_led_color() == QColor("#ff2238")


def test_led_indicator_render(qapp):
    led = LedIndicator()
    led.resize(340, 42)

    # Modo Drive
    led.set_mode("DRIVE MODE")
    pix = led.grab()
    assert not pix.isNull()

    # Modo D-Pad Alert
    led.set_mode("D-PAD / CRUCETAS")
    pix2 = led.grab()
    assert not pix2.isNull()

    # Modo Shift Light RPM
    led.set_rpm_ratio(0.85)
    pix3 = led.grab()
    assert not pix3.isNull()


# =============================================================================
# 6. Verificación de cero emojis en todos los widgets
# =============================================================================

def test_no_emojis_in_widgets():
    widget_dir = os.path.join(os.path.dirname(__file__), "..", "ui", "widgets")
    py_files = glob.glob(os.path.join(widget_dir, "**", "*.py"), recursive=True)
    assert len(py_files) >= 6

    emojis_found = []
    for fpath in py_files:
        with open(fpath, "r", encoding="utf-8") as fp:
            for line_no, line in enumerate(fp, start=1):
                for ch in line:
                    code = ord(ch)
                    if (
                        0x1F600 <= code <= 0x1F64F
                        or 0x1F300 <= code <= 0x1F5FF
                        or 0x1F680 <= code <= 0x1F6FF
                        or 0x1F700 <= code <= 0x1F77F
                        or 0x1F780 <= code <= 0x1F7FF
                        or 0x1F800 <= code <= 0x1F8FF
                        or 0x1F900 <= code <= 0x1F9FF
                        or 0x1FA00 <= code <= 0x1FA6F
                        or 0x1FA70 <= code <= 0x1FAFF
                        or 0x2600 <= code <= 0x26FF
                        or 0x2700 <= code <= 0x27BF
                    ):
                        emojis_found.append((fpath, line_no, ch, hex(code)))

    assert len(emojis_found) == 0, f"Emojis detectados en código: {emojis_found}"

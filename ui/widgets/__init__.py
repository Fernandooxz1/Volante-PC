"""
Volante-PC Motorsport PyQt6 Custom Widgets.
Componentes de instrumentación de carreras de alto rendimiento y estética DDU.
"""

from ui.widgets.button_grid import ButtonGrid, ButtonPill
from ui.widgets.curve_canvas import CurveCanvas
from ui.widgets.led_indicator import LedIndicator
from ui.widgets.pedal_bar import PedalBar
from ui.widgets.theme import (
    ARDUINO_LED_COLORS,
    COLOR_ACCENT_CYAN,
    COLOR_ALERT_ORANGE,
    COLOR_BG_CARD,
    COLOR_BG_DEEP,
    COLOR_BG_HOVER,
    COLOR_BG_SURFACE,
    COLOR_BORDER_ACTIVE,
    COLOR_BORDER_HIGHLIGHT,
    COLOR_BORDER_SUBTLE,
    COLOR_BRAKE_RED,
    COLOR_TEXT_DARK,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_THROTTLE_GREEN,
    COLOR_VIOLET,
    COLOR_WARNING_YELLOW,
    parse_color,
)
from ui.widgets.wheel_gauge import WheelGauge

__all__ = [
    "WheelGauge",
    "PedalBar",
    "CurveCanvas",
    "ButtonGrid",
    "ButtonPill",
    "LedIndicator",
    # Constantes y utilidades de tema
    "COLOR_BG_DEEP",
    "COLOR_BG_CARD",
    "COLOR_BG_SURFACE",
    "COLOR_BG_HOVER",
    "COLOR_BORDER_SUBTLE",
    "COLOR_BORDER_ACTIVE",
    "COLOR_BORDER_HIGHLIGHT",
    "COLOR_TEXT_PRIMARY",
    "COLOR_TEXT_SECONDARY",
    "COLOR_TEXT_MUTED",
    "COLOR_TEXT_DARK",
    "COLOR_ACCENT_CYAN",
    "COLOR_THROTTLE_GREEN",
    "COLOR_BRAKE_RED",
    "COLOR_ALERT_ORANGE",
    "COLOR_WARNING_YELLOW",
    "COLOR_VIOLET",
    "ARDUINO_LED_COLORS",
    "parse_color",
]

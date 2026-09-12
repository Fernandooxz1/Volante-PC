"""
Core Engine and Processing Pipeline for Volante-PC.
Includes 100Hz engine, binary serial protocol, DSP filters, calibration math,
and virtual gamepad abstraction.
"""

from core.calibration import (
    calculate_pedal,
    calculate_steering,
    evaluate_curve_point,
    generate_curve_points,
)
from core.config_manager import ConfigManager
from core.dsp import SteeringFilter
from core.engine import (
    Engine,
    MODE_CONDUCCION,
    MODE_CRUCETAS,
    TelemetrySnapshot,
    auto_detect_arduino_port,
    find_available_ports,
    label_to_pin,
    pin_to_label,
)
from core.gamepad import VirtualGamepadManager, check_gamepad_prerequisites
from core.protocol import (
    CONFIG_BUTTON_KEYS,
    LED_COLORS,
    PIN_NAMES,
    StreamParser,
    encode_led_command,
    unpack_payload,
)

__all__ = [
    "Engine",
    "TelemetrySnapshot",
    "MODE_CONDUCCION",
    "MODE_CRUCETAS",
    "find_available_ports",
    "auto_detect_arduino_port",
    "label_to_pin",
    "pin_to_label",
    "ConfigManager",
    "VirtualGamepadManager",
    "check_gamepad_prerequisites",
    "SteeringFilter",
    "calculate_steering",
    "calculate_pedal",
    "evaluate_curve_point",
    "generate_curve_points",
    "StreamParser",
    "encode_led_command",
    "unpack_payload",
    "PIN_NAMES",
    "CONFIG_BUTTON_KEYS",
    "LED_COLORS",
]

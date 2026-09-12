"""
Interactive Input Mapping Wizard for Volante-PC.
Provides:
1) Guided Full Wizard: Walks through essential controls one by one with live detection and debouncing.
2) Quick Single-Button Mapper: Modal dialog to quickly bind a single action to physical hardware.

Zero emojis. Clean, high-contrast, minimalist motorsport UI.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.config_manager import ConfigManager
from core.protocol import CONFIG_BUTTON_KEYS, PIN_NAMES
from ui.i18n import tr

TARGET_CONTROLS: List[str] = [
    "Left Trigger (LT) - Brake",
    "Right Trigger (RT) - Throttle",
    "Steering Wheel Axis",
    "Button A",
    "Button B",
    "Button X",
    "Button Y",
    "Button LB",
    "Button RB",
    "Button Start",
    "Button Back",
    "D-Pad UP",
    "D-Pad DOWN",
    "D-Pad LEFT",
    "D-Pad RIGHT",
]

# Map physical pin names to config keys in ConfigManager
PIN_NAME_TO_KEY: Dict[str, str] = dict(zip(PIN_NAMES, CONFIG_BUTTON_KEYS))

# Action normalization mapping for ConfigManager / Gamepad compatibility
ACTION_NORMALIZATION: Dict[str, str] = {
    "Button LB": "Button LB (Left Shoulder)",
    "Button RB": "Button RB (Right Shoulder)",
    "Left Trigger (LT) - Brake": "Left Trigger (LT)",
    "Right Trigger (RT) - Throttle": "Right Trigger (RT)",
    "Steering Wheel Axis": "Left Stick X",
}


def normalize_target_action(action: str) -> str:
    """Normalize user-facing action name to configuration dictionary value."""
    return ACTION_NORMALIZATION.get(action, action)


def get_control_type(control_name: str) -> str:
    """Returns classification of control: 'axis', 'trigger', or 'button'."""
    if "Axis" in control_name:
        return "axis"
    elif "Trigger" in control_name:
        return "trigger"
    return "button"


def get_control_description(control_name: str) -> str:
    """Returns technical motorsport description for the target action."""
    descriptions = {
        "Left Trigger (LT) - Brake": tr("mapping_wizard.desc_brake"),
        "Right Trigger (RT) - Throttle": tr("mapping_wizard.desc_throttle"),
        "Steering Wheel Axis": tr("mapping_wizard.desc_steer"),
        "Button A": tr("mapping_wizard.desc_btn_a"),
        "Button B": tr("mapping_wizard.desc_btn_b"),
        "Button X": tr("mapping_wizard.desc_btn_x"),
        "Button Y": tr("mapping_wizard.desc_btn_y"),
        "Button LB": tr("mapping_wizard.desc_btn_lb"),
        "Button RB": tr("mapping_wizard.desc_btn_rb"),
        "Button Start": tr("mapping_wizard.desc_btn_start"),
        "Button Back": tr("mapping_wizard.desc_btn_back"),
        "D-Pad UP": tr("mapping_wizard.desc_dpad_up"),
        "D-Pad DOWN": tr("mapping_wizard.desc_dpad_down"),
        "D-Pad LEFT": tr("mapping_wizard.desc_dpad_left"),
        "D-Pad RIGHT": tr("mapping_wizard.desc_dpad_right"),
    }
    return descriptions.get(control_name, tr("mapping_wizard.desc_default"))


class InputDispatcher(QObject):
    """Thread-safe event bridge between hardware engine callbacks and Qt GUI thread."""
    raw_input_received = pyqtSignal(object)


def apply_dark_motorsport_style(widget: QWidget, accent_color: str = "#00e5ff") -> None:
    """Applies high-contrast dark minimalist motorsport stylesheet to a dialog."""
    widget.setStyleSheet(f"""
        QDialog {{
            background-color: #0a0c10;
            color: #f1f5f9;
            font-family: 'Segoe UI', 'Ubuntu', 'Inter', sans-serif;
        }}
        QLabel {{
            color: #f1f5f9;
        }}
        QFrame[card="true"] {{
            background-color: #11151c;
            border: 1px solid #202736;
            border-radius: 6px;
        }}
        QFrame[indicator="true"] {{
            background-color: #161c24;
            border: 1px solid #202736;
            border-radius: 4px;
        }}
        QPushButton {{
            background-color: #161c24;
            color: #f1f5f9;
            border: 1px solid #202736;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
        }}
        QPushButton:hover {{
            background-color: #1f2733;
            border-color: #334155;
            color: #ffffff;
        }}
        QPushButton:pressed {{
            background-color: {accent_color};
            color: #0a0c10;
        }}
        QPushButton[primary="true"] {{
            background-color: {accent_color};
            color: #0a0c10;
            border: 1px solid {accent_color};
            font-weight: 700;
        }}
        QPushButton[primary="true"]:hover {{
            background-color: #33eeff;
            border-color: #33eeff;
        }}
        QPushButton[danger="true"] {{
            background-color: #1a1215;
            color: #ff3344;
            border: 1px solid #4a1520;
        }}
        QPushButton[danger="true"]:hover {{
            background-color: #ff3344;
            color: #0a0c10;
        }}
        QProgressBar {{
            background-color: #11151c;
            border: 1px solid #202736;
            border-radius: 3px;
            text-align: center;
            height: 6px;
            color: transparent;
        }}
        QProgressBar::chunk {{
            background-color: {accent_color};
            border-radius: 2px;
        }}
        QTableWidget {{
            background-color: #11151c;
            border: 1px solid #202736;
            gridline-color: #1a2230;
            color: #f1f5f9;
            font-family: 'Consolas', 'Liberation Mono', monospace;
            font-size: 11px;
            selection-background-color: #1f2733;
            selection-color: #00e5ff;
        }}
        QHeaderView::section {{
            background-color: #161c24;
            color: #94a3b8;
            font-weight: 700;
            font-size: 10px;
            border: 1px solid #202736;
            padding: 6px;
            text-transform: uppercase;
        }}
    """)


class MappingWizardDialog(QDialog):
    """
    Guided Input Mapping Wizard.
    Iterates through all essential controls (axes, pedals, and digital buttons),
    capturing physical hardware events, debouncing, binding to ConfigManager,
    and providing clear visual feedback with zero emojis.
    """

    wizard_finished = pyqtSignal()

    def __init__(
        self,
        engine: Optional[Any] = None,
        config_manager: Optional[ConfigManager] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.engine = engine
        self.config_manager = config_manager or ConfigManager()
        self.accent_color = self.config_manager.get_theme_accent() if hasattr(self.config_manager, "get_theme_accent") else "#00e5ff"

        self.setWindowTitle(tr("mapping_wizard.window_title"))
        self.setMinimumSize(680, 520)
        self.setModal(True)

        # State tracking
        self._current_step_index: int = 0
        self._awaiting_input: bool = True
        self._last_trigger_time: float = 0.0
        self._debounce_interval: float = 0.35
        self._axis_movement_threshold: int = 150

        # Baselines for axis motion detection
        self._baseline_steer: Optional[int] = None
        self._baseline_accel: Optional[int] = None
        self._baseline_brake: Optional[int] = None

        # Button state tracking (11 pins)
        self._last_buttons: Optional[List[int]] = None

        # Result record
        self._mapped_results: Dict[str, str] = {}

        # Thread-safe event dispatcher
        self._dispatcher = InputDispatcher()
        self._dispatcher.raw_input_received.connect(self._on_input_event)

        # Single-shot advance timer
        self._advance_timer = QTimer(self)
        self._advance_timer.setSingleShot(True)
        self._advance_timer.timeout.connect(self._advance_step)

        self._build_ui()
        apply_dark_motorsport_style(self, self.accent_color)
        self._register_engine_listener()
        self._show_step(0)

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        # Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)

        title_row = QHBoxLayout()
        self.lbl_header_title = QLabel(tr("mapping_wizard.header_title"))
        self.lbl_header_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_header_title.setStyleSheet("color: #94a3b8; letter-spacing: 1px;")
        title_row.addWidget(self.lbl_header_title)

        title_row.addStretch()

        self.lbl_step_counter = QLabel(tr("mapping_wizard.step_counter", current=1, total=len(TARGET_CONTROLS)))
        self.lbl_step_counter.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.lbl_step_counter.setStyleSheet(f"color: {self.accent_color}; letter-spacing: 1px;")
        title_row.addWidget(self.lbl_step_counter)

        header_layout.addLayout(title_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(TARGET_CONTROLS))
        self.progress_bar.setValue(1)
        header_layout.addWidget(self.progress_bar)

        main_layout.addLayout(header_layout)

        # Wizard Active Step Card
        self.card_wizard = QFrame()
        self.card_wizard.setProperty("card", "true")
        card_layout = QVBoxLayout(self.card_wizard)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(14)

        # Type badge and name row
        type_row = QHBoxLayout()
        self.lbl_type_badge = QLabel(tr("mapping_wizard.badge_analog_pedal"))
        self.lbl_type_badge.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.lbl_type_badge.setStyleSheet("color: #00e5ff; background: #0e202d; padding: 3px 8px; border-radius: 3px;")
        type_row.addWidget(self.lbl_type_badge)
        type_row.addStretch()
        card_layout.addLayout(type_row)

        # Large Target Action Name
        self.lbl_action_name = QLabel("LEFT TRIGGER (LT) - BRAKE")
        self.lbl_action_name.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.lbl_action_name.setStyleSheet("color: #f1f5f9; letter-spacing: 0.5px;")
        card_layout.addWidget(self.lbl_action_name)

        # Instruction / Description
        self.lbl_instruction = QLabel(get_control_description(TARGET_CONTROLS[0]))
        self.lbl_instruction.setFont(QFont("Segoe UI", 11))
        self.lbl_instruction.setStyleSheet("color: #94a3b8; line-height: 1.4;")
        self.lbl_instruction.setWordWrap(True)
        card_layout.addWidget(self.lbl_instruction)

        card_layout.addSpacing(6)

        # Status & Awaiting Hardware Feedback Box
        self.frame_status = QFrame()
        self.frame_status.setProperty("indicator", "true")
        self.frame_status.setFixedHeight(64)
        status_layout = QHBoxLayout(self.frame_status)
        status_layout.setContentsMargins(16, 12, 16, 12)

        self.lbl_status_text = QLabel(tr("mapping_wizard.awaiting_input"))
        self.lbl_status_text.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.lbl_status_text.setStyleSheet(f"color: {self.accent_color}; letter-spacing: 0.5px;")
        status_layout.addWidget(self.lbl_status_text)
        status_layout.addStretch()

        card_layout.addWidget(self.frame_status)

        # Live telemetry monitor footer
        self.lbl_live_monitor = QLabel(tr("mapping_wizard.live_monitor", steer=512, accel=0, brake=0, pins=tr("mapping_wizard.none")))
        self.lbl_live_monitor.setFont(QFont("Consolas", 9))
        self.lbl_live_monitor.setStyleSheet("color: #475569;")
        card_layout.addWidget(self.lbl_live_monitor)

        main_layout.addWidget(self.card_wizard)

        # Summary Card (hidden initially, shown after last step)
        self.card_summary = QFrame()
        self.card_summary.setProperty("card", "true")
        summary_layout = QVBoxLayout(self.card_summary)
        summary_layout.setContentsMargins(20, 20, 20, 20)
        summary_layout.setSpacing(12)

        lbl_summary_title = QLabel(tr("mapping_wizard.summary_title"))
        lbl_summary_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_summary_title.setStyleSheet("color: #00e676; letter-spacing: 0.5px;")
        summary_layout.addWidget(lbl_summary_title)

        self.table_summary = QTableWidget()
        self.table_summary.setColumnCount(3)
        self.table_summary.setHorizontalHeaderLabels([tr("mapping_wizard.col_target"), tr("mapping_wizard.col_assigned"), tr("mapping_wizard.col_status")])
        self.table_summary.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_summary.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_summary.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table_summary.setColumnWidth(2, 110)
        self.table_summary.verticalHeader().setVisible(False)
        self.table_summary.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        summary_layout.addWidget(self.table_summary)

        self.card_summary.setVisible(False)
        main_layout.addWidget(self.card_summary)

        # Bottom Button Action Bar
        self.bar_buttons = QHBoxLayout()
        self.bar_buttons.setSpacing(10)

        self.btn_back = QPushButton(tr("mapping_wizard.btn_back"))
        self.btn_back.clicked.connect(self._on_btn_back_clicked)
        self.bar_buttons.addWidget(self.btn_back)

        self.btn_skip = QPushButton(tr("mapping_wizard.btn_skip"))
        self.btn_skip.clicked.connect(self._on_btn_skip_clicked)
        self.bar_buttons.addWidget(self.btn_skip)

        self.bar_buttons.addStretch()

        self.btn_cancel = QPushButton(tr("mapping_wizard.btn_cancel"))
        self.btn_cancel.setProperty("danger", "true")
        self.btn_cancel.clicked.connect(self.reject)
        self.bar_buttons.addWidget(self.btn_cancel)

        # Summary Finish button (shown on summary view)
        self.btn_finish = QPushButton(tr("mapping_wizard.btn_finish"))
        self.btn_finish.setProperty("primary", "true")
        self.btn_finish.clicked.connect(self._on_btn_finish_clicked)
        self.btn_finish.setVisible(False)
        self.bar_buttons.addWidget(self.btn_finish)

        main_layout.addLayout(self.bar_buttons)

    def _register_engine_listener(self) -> None:
        """Registers callback listener with the core hardware engine."""
        if not self.engine:
            return

        def _callback(*args, **kwargs):
            if len(args) == 1:
                self._dispatcher.raw_input_received.emit(args[0])
            elif len(args) == 4:
                self._dispatcher.raw_input_received.emit(args)
            elif len(args) > 1:
                self._dispatcher.raw_input_received.emit(args)

        self._engine_callback_ref = _callback

        if hasattr(self.engine, "set_input_listener"):
            try:
                self.engine.set_input_listener(_callback)
            except Exception as e:
                print(f"[MappingWizard] Error setting input listener: {e}")

    def _unregister_engine_listener(self) -> None:
        """Detaches listener from engine upon wizard closure."""
        if not self.engine:
            return
        if hasattr(self.engine, "set_input_listener"):
            try:
                self.engine.set_input_listener(None)
            except Exception:
                pass
        if hasattr(self.engine, "remove_input_listener"):
            try:
                self.engine.remove_input_listener(self._engine_callback_ref)
            except Exception:
                pass

    def _show_step(self, step_index: int) -> None:
        """Configures the UI for the target step."""
        if step_index >= len(TARGET_CONTROLS):
            self._show_summary_view()
            return

        self._current_step_index = step_index
        self._awaiting_input = True
        self._baseline_steer = None
        self._baseline_accel = None
        self._baseline_brake = None

        control_name = TARGET_CONTROLS[step_index]
        ctrl_type = get_control_type(control_name)

        self.lbl_step_counter.setText(tr("mapping_wizard.step_counter", current=step_index + 1, total=len(TARGET_CONTROLS)))
        self.progress_bar.setValue(step_index + 1)

        if ctrl_type == "axis":
            self.lbl_type_badge.setText(tr("mapping_wizard.badge_analog_steer"))
            self.lbl_type_badge.setStyleSheet("color: #00e5ff; background: #0d2330; padding: 3px 8px; border-radius: 3px;")
        elif ctrl_type == "trigger":
            self.lbl_type_badge.setText(tr("mapping_wizard.badge_analog_pedal"))
            self.lbl_type_badge.setStyleSheet("color: #ffd600; background: #262208; padding: 3px 8px; border-radius: 3px;")
        else:
            self.lbl_type_badge.setText(tr("mapping_wizard.badge_digital_button"))
            self.lbl_type_badge.setStyleSheet("color: #00e676; background: #092617; padding: 3px 8px; border-radius: 3px;")

        self.lbl_action_name.setText(control_name.upper())
        self.lbl_instruction.setText(get_control_description(control_name))

        # Reset status box styling
        self._set_status_awaiting()

        # Update button states
        self.btn_back.setEnabled(step_index > 0)
        self.btn_skip.setEnabled(True)

    def _set_status_awaiting(self) -> None:
        """Sets status box to idle awaiting state."""
        self.frame_status.setStyleSheet("""
            QFrame[indicator="true"] {
                background-color: #11151c;
                border: 1px solid #202736;
                border-radius: 4px;
            }
        """)
        self.lbl_status_text.setText(tr("mapping_wizard.awaiting_input"))
        self.lbl_status_text.setStyleSheet(f"color: {self.accent_color}; letter-spacing: 0.5px;")

    def _set_status_confirmed(self, message: str) -> None:
        """Flashes green confirmation on successful input detection."""
        self.frame_status.setStyleSheet("""
            QFrame[indicator="true"] {
                background-color: #00e676;
                border: 2px solid #00ff88;
                border-radius: 4px;
            }
        """)
        self.lbl_status_text.setText(f"[{tr('mapping_wizard.tag_mapped')}] {message}")
        self.lbl_status_text.setStyleSheet("color: #0a0c10; font-weight: 700; letter-spacing: 0.5px;")

    def _on_input_event(self, data: Any) -> None:
        """Slot receiving telemetry and hardware input on Qt GUI thread."""
        if not self._awaiting_input:
            return

        # Case 1: Raw 4-tuple (steer, accel, brake, buttons)
        if isinstance(data, (tuple, list)) and len(data) == 4 and isinstance(data[3], (list, tuple)):
            steer, accel, brake, buttons = data
            self._process_raw_telemetry(int(steer), int(accel), int(brake), list(buttons))
            return

        # Case 2: Dict payload
        if isinstance(data, dict):
            raw = data.get("raw", data)
            if "buttons" in raw:
                self._process_raw_telemetry(
                    int(raw.get("steer", 512)),
                    int(raw.get("accel", 0)),
                    int(raw.get("brake", 0)),
                    list(raw.get("buttons", []))
                )
                return
            if "pin" in data:
                self._handle_pin_trigger(str(data["pin"]))
                return
            if "axis" in data:
                self._handle_axis_trigger(str(data["axis"]))
                return

        # Case 3: Direct event tuple (event_type, id, value)
        if isinstance(data, (tuple, list)) and len(data) >= 2:
            ev_type, ev_id = str(data[0]).lower(), str(data[1])
            if ev_type in ("button", "pin", "digital"):
                self._handle_pin_trigger(ev_id)
                return
            elif ev_type in ("axis", "analog"):
                self._handle_axis_trigger(ev_id)
                return

        # Case 4: Direct pin string
        if isinstance(data, str):
            clean = data.replace("Pin ", "").strip().upper()
            if clean in PIN_NAMES:
                self._handle_pin_trigger(clean)
            elif clean.lower() in ("steer", "accel", "brake"):
                self._handle_axis_trigger(clean.lower())

    def _process_raw_telemetry(self, steer: int, accel: int, brake: int, buttons: List[int]) -> None:
        """Processes raw Arduino packet: checks rising edge on pins and axis thresholds."""
        # 1. Update live monitor readout
        active_pins = [PIN_NAMES[i] for i, val in enumerate(buttons) if val == 1 and i < len(PIN_NAMES)]
        pin_str = ", ".join(active_pins) if active_pins else tr("mapping_wizard.none")
        self.lbl_live_monitor.setText(tr("mapping_wizard.live_monitor", steer=steer, accel=accel, brake=brake, pins=pin_str))

        now = time.time()
        if now - self._last_trigger_time < self._debounce_interval:
            self._last_buttons = list(buttons)
            return

        # 2. Check Digital Pin Rising Edge (0 -> 1)
        if self._last_buttons is not None and len(buttons) >= 11:
            for i in range(min(len(buttons), len(PIN_NAMES))):
                if buttons[i] == 1 and self._last_buttons[i] == 0:
                    self._last_buttons = list(buttons)
                    self._handle_pin_trigger(PIN_NAMES[i])
                    return

        self._last_buttons = list(buttons)

        # 3. Check Axis Movement Threshold
        if self._baseline_steer is None:
            self._baseline_steer = steer
            self._baseline_accel = accel
            self._baseline_brake = brake
            return

        current_target = TARGET_CONTROLS[self._current_step_index]
        ctrl_type = get_control_type(current_target)

        if ctrl_type in ("axis", "trigger"):
            if "Steering" in current_target:
                if abs(steer - self._baseline_steer) >= self._axis_movement_threshold:
                    self._handle_axis_trigger("steer")
                    return
            elif "Throttle" in current_target:
                if abs(accel - self._baseline_accel) >= self._axis_movement_threshold:
                    self._handle_axis_trigger("accel")
                    return
            elif "Brake" in current_target:
                if abs(brake - self._baseline_brake) >= self._axis_movement_threshold:
                    self._handle_axis_trigger("brake")
                    return

    def _handle_pin_trigger(self, pin_name: str) -> None:
        """Binds detected physical pin to current target control."""
        now = time.time()
        if now - self._last_trigger_time < self._debounce_interval:
            return
        self._last_trigger_time = now

        clean_pin = pin_name.replace("Pin ", "").strip().upper()
        if clean_pin not in PIN_NAME_TO_KEY:
            return

        current_target = TARGET_CONTROLS[self._current_step_index]
        config_action = normalize_target_action(current_target)
        pin_key = PIN_NAME_TO_KEY[clean_pin]

        # Prevent duplicate bindings: reset any other pin previously mapped to this action
        for k, v in list(self.config_manager.config.items()):
            if k.startswith("btn_map_") and v == config_action:
                self.config_manager.set(k, "Ninguno")

        # Set new mapping in ConfigManager
        self.config_manager.set(pin_key, config_action)
        self.config_manager.save()

        assigned_text = tr("mapping_wizard.assigned_pin", pin=clean_pin)
        self._mapped_results[current_target] = assigned_text

        # Flash visual feedback and advance
        self._awaiting_input = False
        self._set_status_confirmed(f"{assigned_text} -> {current_target}")
        self._advance_timer.start(500)

    def _handle_axis_trigger(self, axis_id: str) -> None:
        """Binds detected axis motion to current target control."""
        now = time.time()
        if now - self._last_trigger_time < self._debounce_interval:
            return
        self._last_trigger_time = now

        current_target = TARGET_CONTROLS[self._current_step_index]

        if "Steering" in current_target or axis_id == "steer":
            self.config_manager.set("steer_target", "Left Stick X")
            assigned_text = tr("mapping_wizard.assigned_steer")
        elif "Throttle" in current_target or axis_id == "accel":
            self.config_manager.set("accel_target", "Right Trigger (RT)")
            assigned_text = tr("mapping_wizard.assigned_throttle")
        elif "Brake" in current_target or axis_id == "brake":
            self.config_manager.set("brake_target", "Left Trigger (LT)")
            assigned_text = tr("mapping_wizard.assigned_brake")
        else:
            assigned_text = tr("mapping_wizard.assigned_axis", axis=axis_id.upper())

        self.config_manager.save()
        self._mapped_results[current_target] = assigned_text

        self._awaiting_input = False
        self._set_status_confirmed(f"{assigned_text} -> {current_target}")
        self._advance_timer.start(500)

    def _advance_step(self) -> None:
        """Advances to the next control in sequence."""
        self._advance_timer.stop()
        next_step = self._current_step_index + 1
        self._show_step(next_step)

    def _on_btn_skip_clicked(self) -> None:
        """Skips the current control without updating config."""
        current_target = TARGET_CONTROLS[self._current_step_index]
        if current_target not in self._mapped_results:
            self._mapped_results[current_target] = tr("mapping_wizard.val_preserved")
        self._advance_step()

    def _on_btn_back_clicked(self) -> None:
        """Returns to the previous control."""
        if self._current_step_index > 0:
            self._show_step(self._current_step_index - 1)

    def _show_summary_view(self) -> None:
        """Displays completion summary table of all controls."""
        self._unregister_engine_listener()
        self.card_wizard.setVisible(False)
        self.card_summary.setVisible(True)

        self.btn_back.setVisible(False)
        self.btn_skip.setVisible(False)
        self.btn_cancel.setVisible(False)
        self.btn_finish.setVisible(True)

        self.lbl_step_counter.setText(tr("mapping_wizard.completed"))
        self.progress_bar.setValue(len(TARGET_CONTROLS))

        self.table_summary.setRowCount(len(TARGET_CONTROLS))
        for row, target in enumerate(TARGET_CONTROLS):
            assigned = self._mapped_results.get(target, tr("mapping_wizard.val_existing"))
            item_target = QTableWidgetItem(f" {target}")
            item_assigned = QTableWidgetItem(f" {assigned}")
            item_status = QTableWidgetItem(f" {tr('mapping_wizard.status_active')}")

            item_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_status.setForeground(Qt.GlobalColor.green)

            self.table_summary.setItem(row, 0, item_target)
            self.table_summary.setItem(row, 1, item_assigned)
            self.table_summary.setItem(row, 2, item_status)

    def _on_btn_finish_clicked(self) -> None:
        """Saves configuration and closes the wizard."""
        self.config_manager.save()
        self.wizard_finished.emit()
        self.accept()

    def simulate_input(self, input_data: Any) -> None:
        """Helper method to simulate input for unit tests and headless environments."""
        self._dispatcher.raw_input_received.emit(input_data)

    def closeEvent(self, event) -> None:
        self._unregister_engine_listener()
        super().closeEvent(event)

    def reject(self) -> None:
        self._unregister_engine_listener()
        super().reject()


class SingleButtonMapperDialog(QDialog):
    """
    Quick Single-Button Mapper modal dialog.
    Binds a specific action (e.g., 'Button A') to the next physical button press.
    """

    mapping_completed = pyqtSignal(str, str)  # (target_action, assigned_pin)

    def __init__(
        self,
        target_action: str,
        engine: Optional[Any] = None,
        config_manager: Optional[ConfigManager] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.target_action = target_action
        self.engine = engine
        self.config_manager = config_manager or ConfigManager()
        self.accent_color = self.config_manager.get_theme_accent() if hasattr(self.config_manager, "get_theme_accent") else "#00e5ff"

        self.setWindowTitle(tr("mapping_wizard.quick_bind_window", target=self.target_action.upper()))
        self.setFixedSize(500, 260)
        self.setModal(True)

        self._last_trigger_time: float = 0.0
        self._last_buttons: Optional[List[int]] = None
        self._is_active: bool = True
        self.mapped_pin: Optional[str] = None

        self._dispatcher = InputDispatcher()
        self._dispatcher.raw_input_received.connect(self._on_input_event)

        self._build_ui()
        apply_dark_motorsport_style(self, self.accent_color)
        self._register_engine_listener()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        lbl_header = QLabel(tr("mapping_wizard.quick_bind_header"))
        lbl_header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_header.setStyleSheet("color: #94a3b8; letter-spacing: 1px;")
        layout.addWidget(lbl_header)

        # Target card
        card = QFrame()
        card.setProperty("card", "true")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)

        lbl_target_title = QLabel(tr("mapping_wizard.quick_bind_target", target=self.target_action.upper()))
        lbl_target_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_target_title.setStyleSheet(f"color: {self.accent_color}; letter-spacing: 0.5px;")
        card_layout.addWidget(lbl_target_title)

        self.frame_status = QFrame()
        self.frame_status.setProperty("indicator", "true")
        self.frame_status.setFixedHeight(48)
        status_layout = QHBoxLayout(self.frame_status)
        status_layout.setContentsMargins(12, 8, 12, 8)

        self.lbl_status = QLabel(tr("mapping_wizard.quick_bind_awaiting"))
        self.lbl_status.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.lbl_status.setStyleSheet("color: #f1f5f9;")
        status_layout.addWidget(self.lbl_status)
        card_layout.addWidget(self.frame_status)

        layout.addWidget(card)

        # Cancel button row
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_cancel = QPushButton(tr("common.cancel"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)
        layout.addLayout(btn_row)

    def _register_engine_listener(self) -> None:
        if not self.engine:
            return

        def _callback(*args, **kwargs):
            if len(args) == 1:
                self._dispatcher.raw_input_received.emit(args[0])
            elif len(args) == 4:
                self._dispatcher.raw_input_received.emit(args)
            elif len(args) > 1:
                self._dispatcher.raw_input_received.emit(args)

        self._engine_callback_ref = _callback
        if hasattr(self.engine, "set_input_listener"):
            try:
                self.engine.set_input_listener(_callback)
            except Exception:
                pass

    def _unregister_engine_listener(self) -> None:
        if not self.engine:
            return
        if hasattr(self.engine, "set_input_listener"):
            try:
                self.engine.set_input_listener(None)
            except Exception:
                pass

    def _on_input_event(self, data: Any) -> None:
        if not self._is_active:
            return

        # Case 1: Raw 4-tuple
        if isinstance(data, (tuple, list)) and len(data) == 4 and isinstance(data[3], (list, tuple)):
            buttons = list(data[3])
            if self._last_buttons is not None:
                for i in range(min(len(buttons), len(PIN_NAMES))):
                    if buttons[i] == 1 and self._last_buttons[i] == 0:
                        self._last_buttons = buttons
                        self._bind_pin(PIN_NAMES[i])
                        return
            self._last_buttons = buttons
            return

        # Case 2: Direct pin string or dict
        if isinstance(data, str):
            clean = data.replace("Pin ", "").strip().upper()
            if clean in PIN_NAMES:
                self._bind_pin(clean)
                return
        elif isinstance(data, dict) and "pin" in data:
            self._bind_pin(str(data["pin"]))
            return

        # Case 3: Direct event tuple (event_type, id, value)
        if isinstance(data, (tuple, list)) and len(data) >= 2:
            ev_type, ev_id = str(data[0]).lower(), str(data[1])
            if ev_type in ("button", "pin", "digital"):
                self._bind_pin(ev_id)
                return

    def _bind_pin(self, pin_name: str) -> None:
        clean_pin = pin_name.replace("Pin ", "").strip().upper()
        if clean_pin not in PIN_NAME_TO_KEY:
            return

        self._is_active = False
        self.mapped_pin = f"Pin {clean_pin}"
        pin_key = PIN_NAME_TO_KEY[clean_pin]
        config_action = normalize_target_action(self.target_action)

        # Clear duplicate mappings
        for k, v in list(self.config_manager.config.items()):
            if k.startswith("btn_map_") and v == config_action:
                self.config_manager.set(k, "Ninguno")

        self.config_manager.set(pin_key, config_action)
        self.config_manager.save()

        # Flash green feedback
        self.frame_status.setStyleSheet("""
            QFrame[indicator="true"] {
                background-color: #00e676;
                border: 2px solid #00ff88;
                border-radius: 4px;
            }
        """)
        self.lbl_status.setText(f"[{tr('mapping_wizard.tag_mapped')}] Pin {clean_pin} -> {self.target_action}")
        self.lbl_status.setStyleSheet("color: #0a0c10; font-weight: 700;")

        self.mapping_completed.emit(self.target_action, self.mapped_pin)
        QTimer.singleShot(400, self.accept)

    def simulate_input(self, input_data: Any) -> None:
        self._dispatcher.raw_input_received.emit(input_data)

    def closeEvent(self, event) -> None:
        self._unregister_engine_listener()
        super().closeEvent(event)

    def reject(self) -> None:
        self._unregister_engine_listener()
        super().reject()

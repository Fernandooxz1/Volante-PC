"""
Hardware Calibration Wizard for Volante-PC.
Guides user step-by-step to calibrate physical limits:
Step 1: Turn Steering Wheel fully to LEFT lock -> Save Left Limit
Step 2: Release Steering Wheel to CENTER -> Save Center
Step 3: Turn Steering Wheel fully to RIGHT lock -> Save Right Limit
Step 4: Pedals released vs fully pressed -> Save Throttle & Brake min/max limits.

Features real-time sensor feedback bars with zero emojis.
Clean, high-contrast, minimalist motorsport UI.
"""

from typing import Any, Dict, List, Optional, Tuple

from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.config_manager import ConfigManager
from ui.dialogs.mapping_wizard import apply_dark_motorsport_style


class CalibrationDispatcher(QObject):
    """Thread-safe event bridge between hardware engine callbacks and Qt GUI thread."""
    telemetry_received = pyqtSignal(int, int, int)


class SensorBarWidget(QWidget):
    """
    Motorsport DDU-style live sensor telemetry bar.
    Visualizes raw ADC readings (0..1023), percentage, and calibration markers (Min, Center, Max).
    """

    def __init__(
        self,
        label: str,
        bar_color: str = "#00e5ff",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.label = label
        self.bar_color = QColor(bar_color)
        self.raw_value: int = 512
        self.saved_min: Optional[int] = None
        self.saved_center: Optional[int] = None
        self.saved_max: Optional[int] = None
        self.setFixedHeight(50)

    def set_value(self, raw_val: int) -> None:
        """Updates the current raw sensor value (clamped 0..1023)."""
        clamped = max(0, min(1023, int(raw_val)))
        if clamped != self.raw_value:
            self.raw_value = clamped
            self.update()

    def set_markers(
        self,
        min_val: Optional[int] = None,
        center_val: Optional[int] = None,
        max_val: Optional[int] = None,
    ) -> None:
        """Sets calibration limit markers to render over the bar."""
        self.saved_min = min_val
        self.saved_center = center_val
        self.saved_max = max_val
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Top text row (Label left, numeric readout right)
        font_label = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font_label)
        painter.setPen(QPen(QColor("#94a3b8")))
        painter.drawText(0, 14, self.label.upper())

        pct = (self.raw_value / 1023.0) * 100.0
        readout_text = f"RAW: {self.raw_value:4d}  |  {pct:5.1f}%"
        font_readout = QFont("Consolas", 9, QFont.Weight.Bold)
        painter.setFont(font_readout)
        painter.setPen(QPen(QColor("#f1f5f9")))
        readout_rect = QRectF(0, 0, width, 16)
        painter.drawText(readout_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, readout_text)

        # Bar dimensions
        bar_top = 22
        bar_height = 18
        bar_rect = QRectF(0, bar_top, width, bar_height)

        # Background track
        painter.setBrush(QBrush(QColor("#11151c")))
        painter.setPen(QPen(QColor("#202736"), 1))
        painter.drawRoundedRect(bar_rect, 3, 3)

        # Filled active level
        fill_width = (self.raw_value / 1023.0) * (width - 2)
        if fill_width > 0:
            fill_rect = QRectF(1, bar_top + 1, fill_width, bar_height - 2)
            painter.setBrush(QBrush(self.bar_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(fill_rect, 2, 2)

        # Calibration markers
        def draw_marker(val: int, color: QColor, label: str):
            x = 1 + (val / 1023.0) * (width - 2)
            painter.setPen(QPen(color, 2))
            painter.drawLine(QPointF(x, bar_top), QPointF(x, bar_top + bar_height))

        if self.saved_min is not None:
            draw_marker(self.saved_min, QColor("#ffd600"), "MIN")
        if self.saved_center is not None:
            draw_marker(self.saved_center, QColor("#ffffff"), "CTR")
        if self.saved_max is not None:
            draw_marker(self.saved_max, QColor("#ffd600"), "MAX")


class CalibrationWizardDialog(QDialog):
    """
    Step-by-step limits wizard:
    Step 1: Turn Steering Wheel fully to LEFT lock -> Press "Save Left Limit"
    Step 2: Release Steering Wheel to CENTER -> Press "Save Center"
    Step 3: Turn Steering Wheel fully to RIGHT lock -> Press "Save Right Limit"
    Step 4: Pedals released vs fully pressed -> Save Throttle & Brake min/max limits.
    Step 5: Review & Save to ConfigManager.
    """

    calibration_applied = pyqtSignal(dict)

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

        self.setWindowTitle("CALIBRATION WIZARD // HARDWARE LIMITS")
        self.setMinimumSize(700, 560)
        self.setModal(True)

        # State tracking
        self._current_step: int = 0  # 0: Left, 1: Center, 2: Right, 3: Pedals, 4: Summary
        self._current_steer: int = 512
        self._current_accel: int = 0
        self._current_brake: int = 0

        # Saved limit values
        self.saved_steer_left: Optional[int] = None
        self.saved_steer_center: Optional[int] = None
        self.saved_steer_right: Optional[int] = None

        self.saved_accel_min: Optional[int] = None
        self.saved_accel_max: Optional[int] = None
        self.saved_brake_min: Optional[int] = None
        self.saved_brake_max: Optional[int] = None

        # Auto-detect tracking on pedal step
        self._auto_detect_pedals: bool = False
        self._observed_accel_min: int = 1023
        self._observed_accel_max: int = 0
        self._observed_brake_min: int = 1023
        self._observed_brake_max: int = 0

        # Dispatcher for thread safety
        self._dispatcher = CalibrationDispatcher()
        self._dispatcher.telemetry_received.connect(self._on_telemetry_slot)

        # Single-shot advance timer
        self._next_step_timer = QTimer(self)
        self._next_step_timer.setSingleShot(True)
        self._next_step_timer.timeout.connect(self._on_next_step)

        self._build_ui()
        apply_dark_motorsport_style(self, self.accent_color)
        self._register_engine_listener()
        self._update_step_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header Title and Progress
        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)

        title_row = QHBoxLayout()
        lbl_main_title = QLabel("SYSTEM CALIBRATION // SENSOR LIMITS WIZARD")
        lbl_main_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_main_title.setStyleSheet("color: #94a3b8; letter-spacing: 1px;")
        title_row.addWidget(lbl_main_title)

        title_row.addStretch()

        self.lbl_step_header = QLabel("STEP 01 OF 04")
        self.lbl_step_header.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        self.lbl_step_header.setStyleSheet(f"color: {self.accent_color}; letter-spacing: 1px;")
        title_row.addWidget(self.lbl_step_header)

        header_layout.addLayout(title_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 4)
        self.progress_bar.setValue(1)
        header_layout.addWidget(self.progress_bar)

        main_layout.addLayout(header_layout)

        # Central Card
        self.card_main = QFrame()
        self.card_main.setProperty("card", "true")
        self.card_layout = QVBoxLayout(self.card_main)
        self.card_layout.setContentsMargins(24, 24, 24, 24)
        self.card_layout.setSpacing(14)

        # Step Title
        self.lbl_step_title = QLabel("STEP 1: STEERING WHEEL - LEFT LIMIT")
        self.lbl_step_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_step_title.setStyleSheet("color: #f1f5f9; letter-spacing: 0.5px;")
        self.card_layout.addWidget(self.lbl_step_title)

        # Step Instructions
        self.lbl_step_instructions = QLabel("Turn steering wheel fully to the LEFT lock position and hold it steady.")
        self.lbl_step_instructions.setFont(QFont("Segoe UI", 11))
        self.lbl_step_instructions.setStyleSheet("color: #94a3b8; line-height: 1.4;")
        self.lbl_step_instructions.setWordWrap(True)
        self.card_layout.addWidget(self.lbl_step_instructions)

        self.card_layout.addSpacing(6)

        # Sensor Bars Container
        self.bars_container = QVBoxLayout()
        self.bars_container.setSpacing(12)

        self.bar_steer = SensorBarWidget("Steering Wheel Axis", bar_color="#00e5ff")
        self.bars_container.addWidget(self.bar_steer)

        self.bar_accel = SensorBarWidget("Throttle Pedal", bar_color="#00e676")
        self.bars_container.addWidget(self.bar_accel)

        self.bar_brake = SensorBarWidget("Brake Pedal", bar_color="#ff3344")
        self.bars_container.addWidget(self.bar_brake)

        self.card_layout.addLayout(self.bars_container)

        self.card_layout.addSpacing(6)

        # Feedback / Confirmation Box
        self.frame_feedback = QFrame()
        self.frame_feedback.setProperty("indicator", "true")
        self.frame_feedback.setFixedHeight(48)
        feedback_layout = QHBoxLayout(self.frame_feedback)
        feedback_layout.setContentsMargins(16, 8, 16, 8)

        self.lbl_feedback = QLabel("Real-time sensor feedback active. Follow instruction above.")
        self.lbl_feedback.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.lbl_feedback.setStyleSheet("color: #94a3b8;")
        feedback_layout.addWidget(self.lbl_feedback)
        feedback_layout.addStretch()

        self.card_layout.addWidget(self.frame_feedback)

        main_layout.addWidget(self.card_main)

        # Step Action Buttons Container (Step-specific buttons)
        self.layout_step_actions = QHBoxLayout()
        self.layout_step_actions.setSpacing(10)

        self.btn_action_1 = QPushButton("Save Left Limit")
        self.btn_action_1.setProperty("primary", "true")
        self.btn_action_1.clicked.connect(self._on_action_1_clicked)
        self.layout_step_actions.addWidget(self.btn_action_1)

        self.btn_action_2 = QPushButton("Save Throttle Max")
        self.btn_action_2.clicked.connect(self._on_action_2_clicked)
        self.btn_action_2.setVisible(False)
        self.layout_step_actions.addWidget(self.btn_action_2)

        self.btn_action_3 = QPushButton("Save Brake Max")
        self.btn_action_3.clicked.connect(self._on_action_3_clicked)
        self.btn_action_3.setVisible(False)
        self.layout_step_actions.addWidget(self.btn_action_3)

        self.btn_auto_detect = QPushButton("Auto-Detect Travel: OFF")
        self.btn_auto_detect.clicked.connect(self._toggle_auto_detect)
        self.btn_auto_detect.setVisible(False)
        self.layout_step_actions.addWidget(self.btn_auto_detect)

        self.card_layout.addLayout(self.layout_step_actions)

        # Summary Frame (shown on step 4)
        self.frame_summary = QFrame()
        self.frame_summary.setProperty("card", "true")
        summary_layout = QVBoxLayout(self.frame_summary)
        summary_layout.setContentsMargins(16, 16, 16, 16)
        summary_layout.setSpacing(8)

        self.lbl_summary_content = QLabel()
        self.lbl_summary_content.setFont(QFont("Consolas", 10))
        self.lbl_summary_content.setStyleSheet("color: #f1f5f9; line-height: 1.5;")
        summary_layout.addWidget(self.lbl_summary_content)
        self.frame_summary.setVisible(False)
        self.card_layout.addWidget(self.frame_summary)

        # Bottom Navigation Row
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)

        self.btn_prev = QPushButton("Previous Step")
        self.btn_prev.clicked.connect(self._on_prev_step)
        nav_layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton("Next Step")
        self.btn_next.clicked.connect(self._on_next_step)
        nav_layout.addWidget(self.btn_next)

        nav_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setProperty("danger", "true")
        self.btn_cancel.clicked.connect(self.reject)
        nav_layout.addWidget(self.btn_cancel)

        self.btn_save_config = QPushButton("Apply & Save Calibration")
        self.btn_save_config.setProperty("primary", "true")
        self.btn_save_config.clicked.connect(self._on_save_config_clicked)
        self.btn_save_config.setVisible(False)
        nav_layout.addWidget(self.btn_save_config)

        main_layout.addLayout(nav_layout)

    def _register_engine_listener(self) -> None:
        if not self.engine:
            return

        def _callback(*args, **kwargs):
            if len(args) == 4 and isinstance(args[3], (list, tuple)):
                self._dispatcher.telemetry_received.emit(int(args[0]), int(args[1]), int(args[2]))
            elif len(args) == 1 and isinstance(args[0], dict):
                raw = args[0].get("raw", args[0])
                steer = raw.get("steer", 512)
                accel = raw.get("accel", 0)
                brake = raw.get("brake", 0)
                self._dispatcher.telemetry_received.emit(int(steer), int(accel), int(brake))

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

    def _on_telemetry_slot(self, steer: int, accel: int, brake: int) -> None:
        """Slot receiving telemetry updates from engine."""
        self._current_steer = steer
        self._current_accel = accel
        self._current_brake = brake

        self.bar_steer.set_value(steer)
        self.bar_accel.set_value(accel)
        self.bar_brake.set_value(brake)

        # Auto-detect pedal travel if active on step 3
        if self._current_step == 3 and self._auto_detect_pedals:
            if accel < self._observed_accel_min:
                self._observed_accel_min = accel
            if accel > self._observed_accel_max:
                self._observed_accel_max = accel

            if brake < self._observed_brake_min:
                self._observed_brake_min = brake
            if brake > self._observed_brake_max:
                self._observed_brake_max = brake

            self.saved_accel_min = self._observed_accel_min
            self.saved_accel_max = self._observed_accel_max
            self.saved_brake_min = self._observed_brake_min
            self.saved_brake_max = self._observed_brake_max

            self.bar_accel.set_markers(min_val=self.saved_accel_min, max_val=self.saved_accel_max)
            self.bar_brake.set_markers(min_val=self.saved_brake_min, max_val=self.saved_brake_max)

            self.lbl_feedback.setText(
                f"[TRACKING] Accel: {self.saved_accel_min}..{self.saved_accel_max} | "
                f"Brake: {self.saved_brake_min}..{self.saved_brake_max}"
            )

    def set_sensor_values(self, steer: int, accel: int, brake: int) -> None:
        """Direct method to set sensor values (useful for tests and manual feeds)."""
        self._dispatcher.telemetry_received.emit(steer, accel, brake)

    def _update_step_ui(self) -> None:
        """Updates all controls and texts according to current step."""
        step = self._current_step

        self.lbl_step_header.setText(f"STEP {min(step + 1, 4):02d} OF 04")
        self.progress_bar.setValue(min(step + 1, 4))
        self.btn_prev.setEnabled(step > 0 and step < 4)

        # Reset action button visibility
        self.btn_action_1.setVisible(step < 4)
        self.btn_action_2.setVisible(step == 3)
        self.btn_action_3.setVisible(step == 3)
        self.btn_auto_detect.setVisible(step == 3)
        self.frame_summary.setVisible(step == 4)
        self.btn_save_config.setVisible(step == 4)
        self.btn_next.setVisible(step < 4)

        if step == 0:
            # Step 1: Steering Left
            self.lbl_step_title.setText("STEP 1: STEERING WHEEL - LEFT LIMIT")
            self.lbl_step_instructions.setText(
                "Turn the steering wheel fully to the MAXIMUM LEFT lock position and hold it firmly. "
                "Observe the live sensor reading below, then click 'Save Left Limit'."
            )
            self.bar_steer.setVisible(True)
            self.bar_accel.setVisible(False)
            self.bar_brake.setVisible(False)
            self.btn_action_1.setText("Save Left Limit")
            self._set_feedback_default("Turn wheel fully left, then click 'Save Left Limit'.")

        elif step == 1:
            # Step 2: Steering Center
            self.lbl_step_title.setText("STEP 2: STEERING WHEEL - CENTER POSITION")
            self.lbl_step_instructions.setText(
                "Release the steering wheel completely to its physical CENTER neutral position. "
                "Ensure the wheel is straight, then click 'Save Center'."
            )
            self.bar_steer.setVisible(True)
            self.bar_accel.setVisible(False)
            self.bar_brake.setVisible(False)
            self.btn_action_1.setText("Save Center Position")
            self._set_feedback_default("Center the wheel, then click 'Save Center Position'.")

        elif step == 2:
            # Step 3: Steering Right
            self.lbl_step_title.setText("STEP 3: STEERING WHEEL - RIGHT LIMIT")
            self.lbl_step_instructions.setText(
                "Turn the steering wheel fully to the MAXIMUM RIGHT lock position and hold it firmly. "
                "Observe the live sensor reading below, then click 'Save Right Limit'."
            )
            self.bar_steer.setVisible(True)
            self.bar_accel.setVisible(False)
            self.bar_brake.setVisible(False)
            self.btn_action_1.setText("Save Right Limit")
            self._set_feedback_default("Turn wheel fully right, then click 'Save Right Limit'.")

        elif step == 3:
            # Step 4: Pedals
            self.lbl_step_title.setText("STEP 4: PEDALS - THROTTLE & BRAKE LIMITS")
            self.lbl_step_instructions.setText(
                "1. Release both pedals completely -> Click 'Save Rest Limits'.\n"
                "2. Press Throttle fully -> Click 'Save Throttle Max'.\n"
                "3. Press Brake fully -> Click 'Save Brake Max'.\n"
                "Or toggle 'Auto-Detect Travel' and pump both pedals through full stroke."
            )
            self.bar_steer.setVisible(False)
            self.bar_accel.setVisible(True)
            self.bar_brake.setVisible(True)
            self.btn_action_1.setText("Save Rest Limits (Min)")
            self.btn_action_2.setText("Save Throttle Max")
            self.btn_action_3.setText("Save Brake Max")
            self._set_feedback_default("Calibrate pedal rest and full travel limits.")

        elif step == 4:
            # Step 5: Summary
            self._unregister_engine_listener()
            self.lbl_step_header.setText("COMPLETED")
            self.lbl_step_title.setText("CALIBRATION COMPLETE // SENSOR LIMITS SUMMARY")
            self.lbl_step_instructions.setText(
                "Verify the calibrated limits below. Click 'Apply & Save Calibration' to commit changes to system configuration."
            )
            self.bar_steer.setVisible(True)
            self.bar_accel.setVisible(True)
            self.bar_brake.setVisible(True)
            self._generate_summary_text()

    def _set_feedback_default(self, message: str) -> None:
        self.frame_feedback.setStyleSheet("""
            QFrame[indicator="true"] {
                background-color: #11151c;
                border: 1px solid #202736;
                border-radius: 4px;
            }
        """)
        self.lbl_feedback.setText(message)
        self.lbl_feedback.setStyleSheet("color: #94a3b8;")

    def _set_feedback_success(self, message: str) -> None:
        self.frame_feedback.setStyleSheet("""
            QFrame[indicator="true"] {
                background-color: #00e676;
                border: 2px solid #00ff88;
                border-radius: 4px;
            }
        """)
        self.lbl_feedback.setText(f"[SAVED] {message}")
        self.lbl_feedback.setStyleSheet("color: #0a0c10; font-weight: 700;")

    def _on_action_1_clicked(self) -> None:
        """Handler for primary action button per step."""
        if self._current_step == 0:
            self.saved_steer_left = self._current_steer
            self.bar_steer.set_markers(min_val=self.saved_steer_left)
            self._set_feedback_success(f"Steering Left Limit: {self.saved_steer_left}")
            self._next_step_timer.start(400)

        elif self._current_step == 1:
            self.saved_steer_center = self._current_steer
            self.bar_steer.set_markers(min_val=self.saved_steer_left, center_val=self.saved_steer_center)
            self._set_feedback_success(f"Steering Center Position: {self.saved_steer_center}")
            self._next_step_timer.start(400)

        elif self._current_step == 2:
            self.saved_steer_right = self._current_steer
            self.bar_steer.set_markers(
                min_val=self.saved_steer_left,
                center_val=self.saved_steer_center,
                max_val=self.saved_steer_right,
            )
            self._set_feedback_success(f"Steering Right Limit: {self.saved_steer_right}")
            self._next_step_timer.start(400)

        elif self._current_step == 3:
            # Save Pedal Rest positions
            self.saved_accel_min = self._current_accel
            self.saved_brake_min = self._current_brake
            self.bar_accel.set_markers(min_val=self.saved_accel_min, max_val=self.saved_accel_max)
            self.bar_brake.set_markers(min_val=self.saved_brake_min, max_val=self.saved_brake_max)
            self._set_feedback_success(f"Rest Limits -> Throttle: {self.saved_accel_min} | Brake: {self.saved_brake_min}")

    def _on_action_2_clicked(self) -> None:
        """Step 4: Save Throttle Max."""
        self.saved_accel_max = self._current_accel
        self.bar_accel.set_markers(min_val=self.saved_accel_min, max_val=self.saved_accel_max)
        self._set_feedback_success(f"Throttle Max Limit: {self.saved_accel_max}")

    def _on_action_3_clicked(self) -> None:
        """Step 4: Save Brake Max."""
        self.saved_brake_max = self._current_brake
        self.bar_brake.set_markers(min_val=self.saved_brake_min, max_val=self.saved_brake_max)
        self._set_feedback_success(f"Brake Max Limit: {self.saved_brake_max}")

    def _toggle_auto_detect(self) -> None:
        """Toggles dynamic pedal travel envelope tracker."""
        self._auto_detect_pedals = not self._auto_detect_pedals
        if self._auto_detect_pedals:
            self.btn_auto_detect.setText("Auto-Detect Travel: ON")
            self.btn_auto_detect.setStyleSheet("background-color: #00e5ff; color: #0a0c10; font-weight: bold;")
            self._observed_accel_min = self._current_accel
            self._observed_accel_max = self._current_accel
            self._observed_brake_min = self._current_brake
            self._observed_brake_max = self._current_brake
            self._set_feedback_default("Pump both pedals fully to register travel envelope.")
        else:
            self.btn_auto_detect.setText("Auto-Detect Travel: OFF")
            self.btn_auto_detect.setStyleSheet("")
            self._set_feedback_success(
                f"Envelope captured -> Throttle: [{self.saved_accel_min}..{self.saved_accel_max}], "
                f"Brake: [{self.saved_brake_min}..{self.saved_brake_max}]"
            )

    def _on_next_step(self) -> None:
        self._next_step_timer.stop()
        if self._current_step < 4:
            self._current_step += 1
            self._update_step_ui()

    def _on_prev_step(self) -> None:
        if self._current_step > 0:
            self._current_step -= 1
            self._update_step_ui()

    def _generate_summary_text(self) -> None:
        """Constructs calibration summary display and detects potentiometer inversion."""
        s_left = self.saved_steer_left if self.saved_steer_left is not None else 0
        s_center = self.saved_steer_center if self.saved_steer_center is not None else 512
        s_right = self.saved_steer_right if self.saved_steer_right is not None else 1023

        # Inversion analysis
        invert_steer = False
        if s_left > s_right:
            invert_steer = True
            steer_min = s_right
            steer_max = s_left
        else:
            steer_min = s_left
            steer_max = s_right

        a_min = self.saved_accel_min if self.saved_accel_min is not None else 0
        a_max = self.saved_accel_max if self.saved_accel_max is not None else 1023
        invert_accel = False
        if a_min > a_max:
            invert_accel = True
            a_min, a_max = a_max, a_min

        b_min = self.saved_brake_min if self.saved_brake_min is not None else 0
        b_max = self.saved_brake_max if self.saved_brake_max is not None else 1023
        invert_brake = False
        if b_min > b_max:
            invert_brake = True
            b_min, b_max = b_max, b_min

        summary = (
            f"STEERING WHEEL AXIS:\n"
            f"  - Physical Left Lock:    {s_left:4d}\n"
            f"  - Physical Center:       {s_center:4d}\n"
            f"  - Physical Right Lock:   {s_right:4d}\n"
            f"  - Calibrated Min/Max:    [{steer_min}..{steer_max}] (Span: {steer_max - steer_min} counts)\n"
            f"  - Axis Inversion:        {'INVERTED (Auto-corrected)' if invert_steer else 'NORMAL'}\n\n"
            f"THROTTLE PEDAL:\n"
            f"  - Rest (Min) -> Full:    [{a_min}..{a_max}] (Travel: {a_max - a_min} counts)\n"
            f"  - Invert Throttle:       {'INVERTED' if invert_accel else 'NORMAL'}\n\n"
            f"BRAKE PEDAL:\n"
            f"  - Rest (Min) -> Full:    [{b_min}..{b_max}] (Travel: {b_max - b_min} counts)\n"
            f"  - Invert Brake:          {'INVERTED' if invert_brake else 'NORMAL'}"
        )
        self.lbl_summary_content.setText(summary)

        # Store resolved values for save
        self._resolved_limits = {
            "steer_min": steer_min,
            "steer_center": s_center,
            "steer_max": steer_max,
            "invert_steer": invert_steer,
            "accel_min": a_min,
            "accel_max": a_max,
            "invert_accel": invert_accel,
            "brake_min": b_min,
            "brake_max": b_max,
            "invert_brake": invert_brake,
        }

    def _on_save_config_clicked(self) -> None:
        """Commits resolved limits to ConfigManager."""
        if hasattr(self, "_resolved_limits"):
            self.config_manager.update(self._resolved_limits, auto_save=True)
            self._set_feedback_success("Calibration successfully written to config_volante.json.")
            self.calibration_applied.emit(self._resolved_limits)
            QTimer.singleShot(400, self.accept)

    def closeEvent(self, event) -> None:
        self._unregister_engine_listener()
        super().closeEvent(event)

    def reject(self) -> None:
        self._unregister_engine_listener()
        super().reject()

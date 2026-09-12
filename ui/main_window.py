"""
MainWindow: Ventana principal de ensamblaje e instrumentación para Volante-PC.
Diseño Motorsport DDU (Driver Display Unit) de alta velocidad y legibilidad.
Integra:
- Instrumentación vectorial: WheelGauge, PedalBar (acelerador y freno), CurveCanvas y pulsadores digitales.
- Gestor de conexión serie con selección de puerto, autodetección y reconexión.
- Controles de sintonía en vivo (sensibilidad, pendiente expo, deadzones, filtro anti-jitter e inversión de ejes).
- Selector y gestor de presets con guardado/borrado y retroalimentación LED.
- Consola de eventos y telemetría en tiempo real a 30-60 Hz.
- Toolbar superior con alternancia rápida de idioma [EN|ES], selector de temas y asistentes de calibración y mapeo.
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpacerItem,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.config_manager import ConfigManager
from core.engine import (
    AVAILABLE_MODES,
    MODE_CONDUCCION,
    MODE_CRUCETAS,
    Engine,
    TelemetrySnapshot,
    find_available_ports,
)
from core.protocol import PIN_NAMES
from ui.dialogs import CalibrationWizardDialog, MappingWizardDialog, ThemeDialog
from ui.i18n import get_language, set_language, subscribe, tr, unsubscribe
from ui.themes import get_stylesheet
from ui.widgets import ARDUINO_LED_COLORS, CurveCanvas, PedalBar, WheelGauge, parse_color

logger = logging.getLogger("VolantePC.UI")


class MainWindow(QMainWindow):
    """
    Ventana principal de instrumentación y control para Volante-PC.
    """

    def __init__(
        self,
        engine: Optional[Engine] = None,
        config_manager: Optional[ConfigManager] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.config_manager = config_manager or (engine.config_manager if engine else ConfigManager())
        self.engine = engine or Engine(config_manager=self.config_manager)

        # Estado interno de la interfaz
        self._is_updating_ui: bool = False
        self._last_status: str = ""
        self._last_active_preset: str = self.config_manager.get("active_preset", "Personalizado")
        self._btn_indicators: Dict[str, QLabel] = {}

        # Configuración inicial de la ventana
        self.setWindowTitle(tr("app.title"))
        self.setMinimumSize(860, 520)
        self.resize(1100, 720)

        # Construir UI
        self._build_toolbar()
        self._build_central_ui()
        self._build_statusbar()

        # Cargar valores iniciales en sliders y controles
        self._sync_sliders_from_config()
        self._sync_presets_from_config()

        # Aplicar estilo visual
        self._apply_current_theme()

        # Suscripción al sistema reactivo de traducción
        self._unsubscribe_i18n = subscribe(self._on_language_changed)

        # Timer de refresco de telemetría e interfaz (30 Hz = 33 ms)
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.setInterval(33)
        self._telemetry_timer.timeout.connect(self._update_telemetry_ui)
        self._telemetry_timer.start()

        self._log("Volante-PC Simracing Dashboard inicializado.", "info")

    # -------------------------------------------------------------------------
    # Construcción de la Barra de Herramientas (Toolbar)
    # -------------------------------------------------------------------------
    def _build_toolbar(self) -> None:
        self.toolbar = QToolBar("MainToolbar", self)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        # Indicador de estado visual (Punto LED)
        self.status_dot = QLabel("●", self)
        self.status_dot.setStyleSheet("color: #ff3344; font-size: 16px; margin-right: 4px;")
        self.toolbar.addWidget(self.status_dot)

        # Etiqueta de estado
        self.status_lbl = QLabel(tr("status.disconnected"), self)
        self.status_lbl.setStyleSheet("font-weight: 700; margin-right: 12px;")
        self.toolbar.addWidget(self.status_lbl)

        # Selector de Puerto Serie
        self.port_combo = QComboBox(self)
        self.port_combo.setMinimumWidth(140)
        self._refresh_ports()
        self.toolbar.addWidget(self.port_combo)

        # Botón Refrescar Puertos
        self.btn_refresh_ports = QPushButton("↻", self)
        self.btn_refresh_ports.setToolTip(tr("status.refresh_ports"))
        self.btn_refresh_ports.setFixedWidth(32)
        self.btn_refresh_ports.clicked.connect(self._refresh_ports)
        self.toolbar.addWidget(self.btn_refresh_ports)

        # Botón Conectar / Desconectar
        self.btn_connect = QPushButton(tr("status.connect"), self)
        self.btn_connect.setProperty("primary", "true")
        self.btn_connect.clicked.connect(self._toggle_connection)
        self.toolbar.addWidget(self.btn_connect)

        self.toolbar.addSeparator()

        # Selector de Modo de Operación
        self.mode_combo = QComboBox(self)
        for m in AVAILABLE_MODES:
            self.mode_combo.addItem(m)
        current_mode = getattr(self.engine, "mode", MODE_CONDUCCION)
        self.mode_combo.setCurrentText(current_mode)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self.toolbar.addWidget(self.mode_combo)

        self.toolbar.addSeparator()

        # Selector de Presets
        self.preset_lbl = QLabel(tr("presets.title") + ":", self)
        self.toolbar.addWidget(self.preset_lbl)

        self.preset_combo = QComboBox(self)
        self.preset_combo.setMinimumWidth(160)
        self.preset_combo.currentTextChanged.connect(self._on_preset_selected)
        self.toolbar.addWidget(self.preset_combo)

        # Botón Guardar Preset
        self.btn_save_preset = QPushButton(tr("presets.save"), self)
        self.btn_save_preset.clicked.connect(self._save_new_preset)
        self.toolbar.addWidget(self.btn_save_preset)

        # Botón Eliminar Preset
        self.btn_delete_preset = QPushButton(tr("presets.delete"), self)
        self.btn_delete_preset.clicked.connect(self._delete_current_preset)
        self.toolbar.addWidget(self.btn_delete_preset)

        # Espaciador flexible
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)

        # Botón Asistente de Calibración
        self.btn_calib_wizard = QPushButton(tr("common.calibration"), self)
        self.btn_calib_wizard.clicked.connect(self._open_calibration_wizard)
        self.toolbar.addWidget(self.btn_calib_wizard)

        # Botón Asistente de Mapeo de Botones
        self.btn_map_wizard = QPushButton(tr("common.controls"), self)
        self.btn_map_wizard.clicked.connect(self._open_mapping_wizard)
        self.toolbar.addWidget(self.btn_map_wizard)

        # Botón de Temas / Configuración
        self.btn_theme = QPushButton("⚙ " + tr("common.settings"), self)
        self.btn_theme.clicked.connect(self._open_theme_dialog)
        self.toolbar.addWidget(self.btn_theme)

        # Selector de Idioma [ES | EN]
        self.btn_lang = QPushButton(f"[{get_language().upper()}]", self)
        self.btn_lang.setFixedWidth(50)
        self.btn_lang.setToolTip(tr("themes.language"))
        self.btn_lang.clicked.connect(self._toggle_language)
        self.toolbar.addWidget(self.btn_lang)

    # -------------------------------------------------------------------------
    # Construcción de la Interfaz Central
    # -------------------------------------------------------------------------
    def _build_central_ui(self) -> None:
        main_scroll = QScrollArea(self)
        main_scroll.setWidgetResizable(True)
        main_scroll.setFrameShape(QFrame.Shape.NoFrame)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        central_widget = QWidget()
        main_scroll.setWidget(central_widget)
        self.setCentralWidget(main_scroll)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(14)

        # Panel Izquierdo: Instrumentación Motorsport DDU (Visualización en Tiempo Real)
        left_card = QFrame(central_widget)
        left_card.setObjectName("leftCard")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(12)

        # 1. Cabecera DDU
        ddu_header = QHBoxLayout()
        self.ddu_title = QLabel(tr("telemetry.title").upper())
        self.ddu_title.setStyleSheet("font-weight: 800; font-size: 13px; letter-spacing: 1px; color: #00e5ff;")
        self.hz_badge = QLabel("100 HZ // ACTIVE")
        self.hz_badge.setStyleSheet("font-weight: 700; font-size: 11px; color: #94a3b8;")
        ddu_header.addWidget(self.ddu_title)
        ddu_header.addStretch()
        ddu_header.addWidget(self.hz_badge)
        left_layout.addLayout(ddu_header)

        # 2. Área principal de instrumentos (Volante al centro + Pedales a los costados)
        gauges_layout = QHBoxLayout()
        gauges_layout.setSpacing(14)

        # Pedal de Freno (Brake)
        self.pedal_brake = PedalBar(label=tr("telemetry.brake"), pedal_type="brake", parent=self)
        gauges_layout.addWidget(self.pedal_brake)

        # Instrumento de Volante (WheelGauge)
        self.wheel_gauge = WheelGauge(parent=self)
        gauges_layout.addWidget(self.wheel_gauge, stretch=2)

        # Pedal de Acelerador (Throttle)
        self.pedal_throttle = PedalBar(label=tr("telemetry.throttle"), pedal_type="throttle", parent=self)
        gauges_layout.addWidget(self.pedal_throttle)

        left_layout.addLayout(gauges_layout, stretch=3)

        # 3. Gráfico de Curva Matemática (CurveCanvas)
        self.curve_canvas = CurveCanvas(parent=self)
        self.curve_canvas.setMinimumHeight(150)
        left_layout.addWidget(self.curve_canvas, stretch=2)

        # 4. Indicadores de Pines y Pulsadores Digitales (Pines Arduino)
        buttons_box = QGroupBox(tr("mapping.digital_pins"), self)
        buttons_layout = QGridLayout(buttons_box)
        buttons_layout.setContentsMargins(8, 12, 8, 8)
        buttons_layout.setSpacing(6)

        for idx, pin in enumerate(PIN_NAMES):
            lbl = QLabel(pin, buttons_box)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedHeight(24)
            lbl.setStyleSheet("""
                background-color: #161c24;
                color: #94a3b8;
                border: 1px solid #202736;
                border-radius: 4px;
                font-weight: 700;
                font-size: 10px;
            """)
            row = idx // 6
            col = idx % 6
            buttons_layout.addWidget(lbl, row, col)
            self._btn_indicators[pin] = lbl

        left_layout.addWidget(buttons_box)
        main_layout.addWidget(left_card, stretch=5)

        # Panel Derecho: Pestañas de Sintonía Fina y Consola de Eventos
        right_card = QFrame(central_widget)
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget(right_card)

        # Tab 1: Sintonía en Vivo (Sliders con ScrollArea)
        scroll_tuning = QScrollArea()
        scroll_tuning.setWidgetResizable(True)
        scroll_tuning.setFrameShape(QFrame.Shape.NoFrame)
        scroll_tuning.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_tuning.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        tab_tuning = QWidget()
        self._build_tuning_tab(tab_tuning)
        scroll_tuning.setWidget(tab_tuning)
        self.tabs.addTab(scroll_tuning, tr("sliders.title"))

        # Tab 2: Consola de Diagnóstico y Logs
        tab_logs = QWidget()
        self._build_logs_tab(tab_logs)
        self.tabs.addTab(tab_logs, "Logs / Telemetría")

        right_layout.addWidget(self.tabs)
        main_layout.addWidget(right_card, stretch=4)

    # -------------------------------------------------------------------------
    # Pestaña de Sintonía Dinámica y Filtros
    # -------------------------------------------------------------------------
    def _build_tuning_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(14)

        # 1. Slider: Sensibilidad (0.10 a 2.00)
        self.slider_sens, self.val_sens = self._create_slider_row(
            layout,
            title_key="sliders.sensitivity",
            desc_key="sliders.sensitivity_desc",
            min_val=10,
            max_val=200,
            initial=int(self.config_manager.get("sensitivity", 1.0) * 100),
            format_fn=lambda v: f"{v / 100.0:.2f}x",
            on_change=lambda v: self._on_slider_changed("sensitivity", v / 100.0),
        )

        # 2. Slider: Pendiente de Linealidad / Expo (0.50 a 3.00)
        self.slider_slope, self.val_slope = self._create_slider_row(
            layout,
            title_key="sliders.slope",
            desc_key="sliders.slope_desc",
            min_val=50,
            max_val=300,
            initial=int(self.config_manager.get("slope", 1.85) * 100),
            format_fn=lambda v: f"{v / 100.0:.2f}",
            on_change=lambda v: self._on_slider_changed("slope", v / 100.0),
        )

        # 3. Slider: Anti-Deadzone (0.00 a 0.40)
        self.slider_anti_dz, self.val_anti_dz = self._create_slider_row(
            layout,
            title_key="sliders.anti_deadzone",
            desc_key="sliders.anti_deadzone_desc",
            min_val=0,
            max_val=40,
            initial=int(self.config_manager.get("anti_deadzone", 0.0) * 100),
            format_fn=lambda v: f"{v}%",
            on_change=lambda v: self._on_slider_changed("anti_deadzone", v / 100.0),
        )

        # 4. Slider: Zona Muerta Pedales (0.00 a 0.30)
        self.slider_deadzone, self.val_deadzone = self._create_slider_row(
            layout,
            title_key="sliders.deadzone",
            desc_key="sliders.deadzone_desc",
            min_val=0,
            max_val=30,
            initial=int(self.config_manager.get("deadzone", 0.13) * 100),
            format_fn=lambda v: f"{v}%",
            on_change=lambda v: self._on_slider_changed("deadzone", v / 100.0),
        )

        # 5. Slider: Filtro Anti-Ruido DSP (0.00 a 0.90)
        self.slider_filter, self.val_filter = self._create_slider_row(
            layout,
            title_key="sliders.filter",
            desc_key="sliders.filter_desc",
            min_val=0,
            max_val=90,
            initial=int(self.config_manager.get("filter", 0.0) * 100),
            format_fn=lambda v: f"{v / 100.0:.2f}",
            on_change=lambda v: self._on_slider_changed("filter", v / 100.0),
        )

        # Inversión de Ejes
        invert_group = QGroupBox(tr("mapping.title"), parent)
        invert_layout = QVBoxLayout(invert_group)
        invert_layout.setContentsMargins(8, 10, 8, 8)
        invert_layout.setSpacing(6)

        self.chk_invert_steer = QCheckBox(tr("mapping.invert_steer"), invert_group)
        self.chk_invert_steer.setChecked(bool(self.config_manager.get("invert_steer", False)))
        self.chk_invert_steer.toggled.connect(lambda c: self._on_checkbox_changed("invert_steer", c))
        invert_layout.addWidget(self.chk_invert_steer)

        self.chk_invert_accel = QCheckBox(tr("mapping.invert_accel"), invert_group)
        self.chk_invert_accel.setChecked(bool(self.config_manager.get("invert_accel", False)))
        self.chk_invert_accel.toggled.connect(lambda c: self._on_checkbox_changed("invert_accel", c))
        invert_layout.addWidget(self.chk_invert_accel)

        self.chk_invert_brake = QCheckBox(tr("mapping.invert_brake"), invert_group)
        self.chk_invert_brake.setChecked(bool(self.config_manager.get("invert_brake", False)))
        self.chk_invert_brake.toggled.connect(lambda c: self._on_checkbox_changed("invert_brake", c))
        invert_layout.addWidget(self.chk_invert_brake)

        layout.addWidget(invert_group)
        layout.addStretch()

    def _create_slider_row(
        self,
        layout: QVBoxLayout,
        title_key: str,
        desc_key: str,
        min_val: int,
        max_val: int,
        initial: int,
        format_fn: Any,
        on_change: Any,
    ) -> Tuple[QSlider, QLabel]:
        header_layout = QHBoxLayout()
        title_lbl = QLabel(tr(title_key))
        title_lbl.setStyleSheet("font-weight: 700;")
        val_lbl = QLabel(format_fn(initial))
        val_lbl.setObjectName("valueLabel")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(val_lbl)
        layout.addLayout(header_layout)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(initial)
        slider.wheelEvent = lambda event: event.ignore()

        def handle_change(val: int):
            val_lbl.setText(format_fn(val))
            on_change(val)

        slider.valueChanged.connect(handle_change)
        layout.addWidget(slider)

        desc_lbl = QLabel(tr(desc_key))
        desc_lbl.setObjectName("descLabel")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        return slider, val_lbl

    # -------------------------------------------------------------------------
    # Pestaña de Consola y Logs
    # -------------------------------------------------------------------------
    def _build_logs_tab(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.log_console = QPlainTextEdit(parent)
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumBlockCount(1000)
        layout.addWidget(self.log_console)

        btn_box = QHBoxLayout()
        btn_clear = QPushButton(tr("common.reset"), parent)
        btn_clear.clicked.connect(self.log_console.clear)
        btn_box.addStretch()
        btn_box.addWidget(btn_clear)
        layout.addLayout(btn_box)

    # -------------------------------------------------------------------------
    # Barra de Estado (Status Bar)
    # -------------------------------------------------------------------------
    def _build_statusbar(self) -> None:
        statusbar = QStatusBar(self)
        self.setStatusBar(statusbar)

        self.lbl_sb_port = QLabel(f"{tr('status.port')}: --")
        self.lbl_sb_baud = QLabel(f"{tr('status.baudrate')}: 115200")
        self.lbl_sb_hz = QLabel("Tasa: 0 Hz")
        self.lbl_sb_f1 = QLabel("F1 UDP: Esperando...")
        self.lbl_sb_gamepad = QLabel(f"{tr('status.virtual_gamepad')}: OK")

        statusbar.addWidget(self.lbl_sb_port, 2)
        statusbar.addWidget(self.lbl_sb_baud, 1)
        statusbar.addWidget(self.lbl_sb_hz, 1)
        statusbar.addWidget(self.lbl_sb_f1, 2)
        statusbar.addPermanentWidget(self.lbl_sb_gamepad)

    # -------------------------------------------------------------------------
    # Actualización en Tiempo Real (Timer 30 Hz)
    # -------------------------------------------------------------------------
    def _update_telemetry_ui(self) -> None:
        snapshot = self.engine.get_telemetry()

        # 1. Actualizar estado de conexión
        status = snapshot.status
        if status != self._last_status:
            self._last_status = status
            if status == "connected":
                self.status_dot.setStyleSheet("color: #00e676; font-size: 16px; margin-right: 4px;")
                self.status_lbl.setText(tr("status.connected"))
                self.btn_connect.setText(tr("status.disconnect"))
                self.lbl_sb_port.setText(f"{tr('status.port')}: {snapshot.active_port or '--'}")
                self._log(f"Arduino conectado en {snapshot.active_port}.", "success")
            elif status == "connecting":
                self.status_dot.setStyleSheet("color: #ff9100; font-size: 16px; margin-right: 4px;")
                self.status_lbl.setText(tr("status.connecting"))
                self.btn_connect.setText(tr("status.disconnect"))
            else:
                self.status_dot.setStyleSheet("color: #ff3344; font-size: 16px; margin-right: 4px;")
                self.status_lbl.setText(tr("status.disconnected"))
                self.btn_connect.setText(tr("status.connect"))
                self.lbl_sb_port.setText(f"{tr('status.port')}: --")

        # 2. Actualizar Volante Vectorial
        self.wheel_gauge.set_angle(snapshot.steer_angle)
        self.wheel_gauge._raw_value = snapshot.raw_steer

        # 3. Actualizar Barras de Pedales
        self.pedal_throttle.set_value(snapshot.throttle_pct / 100.0, snapshot.raw_accel)
        self.pedal_brake.set_value(snapshot.brake_pct / 100.0, snapshot.raw_brake)

        # 4. Actualizar Curva Matemática
        self.curve_canvas.set_follower(snapshot.steer_phys_norm, snapshot.steer_out_norm)

        # 5. Actualizar Indicadores de Pulsadores Físicos
        raw_buttons = snapshot.raw_buttons
        accent = self.config_manager.get_theme_accent() if hasattr(self.config_manager, "get_theme_accent") else "#00e5ff"
        for i, pin in enumerate(PIN_NAMES):
            lbl = self._btn_indicators.get(pin)
            if lbl and i < len(raw_buttons):
                pressed = raw_buttons[i] == 1
                if pressed:
                    lbl.setStyleSheet(f"""
                        background-color: {accent};
                        color: #0a0c10;
                        border: 1px solid #ffffff;
                        border-radius: 4px;
                        font-weight: 800;
                        font-size: 10px;
                    """)
                else:
                    lbl.setStyleSheet("""
                        background-color: #161c24;
                        color: #94a3b8;
                        border: 1px solid #202736;
                        border-radius: 4px;
                        font-weight: 700;
                        font-size: 10px;
                    """)

        # 6. Sincronización de Preset y Modo si cambiaron por botón físico (estilo 'Q')
        if hasattr(snapshot, "preset") and snapshot.preset and snapshot.preset != self.preset_combo.currentText():
            self._is_updating_ui = True
            try:
                idx = self.preset_combo.findText(snapshot.preset)
                if idx >= 0:
                    self.preset_combo.setCurrentIndex(idx)
                else:
                    self.preset_combo.addItem(snapshot.preset)
                    self.preset_combo.setCurrentText(snapshot.preset)
            finally:
                self._is_updating_ui = False
            self._sync_sliders_from_config()

        if hasattr(snapshot, "mode") and snapshot.mode and snapshot.mode != self.mode_combo.currentText():
            self._is_updating_ui = True
            try:
                self.mode_combo.setCurrentText(snapshot.mode)
            finally:
                self._is_updating_ui = False

        # 7. Barra de estado y métricas
        self.lbl_sb_hz.setText(f"Tasa: {snapshot.loop_hz:.0f} Hz")
        self.hz_badge.setText(f"{snapshot.loop_hz:.0f} HZ // {status.upper()}")

        gp_ok = snapshot.gamepad_connected
        self.lbl_sb_gamepad.setText(f"{tr('status.virtual_gamepad')}: {'OK' if gp_ok else 'ERR'}")
        if not gp_ok:
            self.lbl_sb_gamepad.setStyleSheet("color: #ff3344; font-weight: bold;")
        else:
            self.lbl_sb_gamepad.setStyleSheet("color: #00e676;")

        # 8. Estado F1 UDP y Shift Light
        if getattr(snapshot, "f1_telemetry_active", False):
            gear = snapshot.f1_gear
            gear_str = "R" if gear == -1 else ("N" if gear == 0 else f"M{gear}")
            self.lbl_sb_f1.setText(
                f"🏎️ F1: {snapshot.f1_rpm} RPM [{gear_str}] {snapshot.f1_rev_lights}% | LED: {snapshot.led_color}"
            )
            self.lbl_sb_f1.setStyleSheet("color: #00e5ff; font-weight: bold;")
        else:
            active_preset = getattr(snapshot, "preset", "")
            mode = getattr(snapshot, "mode", "")
            if "F1" in active_preset.upper() and mode == "Conducción":
                self.lbl_sb_f1.setText(f"🏎️ F1 UDP: Puerto 20777 listo | LED: {snapshot.led_color}")
                self.lbl_sb_f1.setStyleSheet("color: #64748b;")
            else:
                self.lbl_sb_f1.setText(f"LED: {snapshot.led_color}")
                self.lbl_sb_f1.setStyleSheet("color: #64748b;")

    # -------------------------------------------------------------------------
    # Manejadores de Sintonía, Presets y Hardware
    # -------------------------------------------------------------------------
    def _refresh_ports(self) -> None:
        """Escanea y actualiza los puertos serie disponibles."""
        current = self.port_combo.currentText()
        ports = find_available_ports()
        self.port_combo.clear()
        for p in ports:
            self.port_combo.addItem(p)
        if current and current in ports:
            self.port_combo.setCurrentText(current)
        elif self.engine.target_port and self.engine.target_port in ports:
            self.port_combo.setCurrentText(self.engine.target_port)

    def _toggle_connection(self) -> None:
        if self._last_status in ("connected", "connecting"):
            self.engine.disconnect()
            self._last_status = "disconnected"
            self.status_dot.setStyleSheet("color: #ff3344; font-size: 16px; margin-right: 4px;")
            self.status_lbl.setText(tr("status.disconnected"))
            self.btn_connect.setText(tr("status.connect"))
            self.lbl_sb_port.setText(f"{tr('status.port')}: --")
            self._log(tr("status.disconnected"), "info")
        else:
            port = self.port_combo.currentText()
            if not port:
                self._log(tr("status.no_ports_found"), "warn")
                return
            self._log(f"Conectando a {port}...", "info")
            self.engine.connect(port)

    def _on_mode_changed(self, new_mode: str) -> None:
        if self._is_updating_ui or not new_mode:
            return
        if hasattr(self.engine, "set_mode"):
            self.engine.set_mode(new_mode)
            self._log(f"Modo operativo cambiado a: {new_mode}", "info")
        else:
            self.config_manager.set("mode", new_mode)
            self.config_manager.save()

    def _on_slider_changed(self, key: str, value: float) -> None:
        if self._is_updating_ui:
            return
        self.config_manager.set(key, value)
        self.config_manager.save()

        # Actualizar widget de curva en vivo si corresponde
        if key in ("slope", "sensitivity", "anti_deadzone"):
            self.curve_canvas.set_parameters(
                slope=self.config_manager.get("slope", 1.85),
                sensitivity=self.config_manager.get("sensitivity", 1.0),
                anti_deadzone=self.config_manager.get("anti_deadzone", 0.0),
            )
        elif key == "deadzone":
            dz = self.config_manager.get("deadzone", 0.13)
            self.pedal_throttle.set_deadzone(dz)
            self.pedal_brake.set_deadzone(dz)

    def _on_checkbox_changed(self, key: str, checked: bool) -> None:
        if self._is_updating_ui:
            return
        self.config_manager.set(key, checked)
        self.config_manager.save()
        self._log(f"Ajuste '{key}' cambiado a {checked}", "info")

    def _sync_sliders_from_config(self) -> None:
        self._is_updating_ui = True
        try:
            sens = self.config_manager.get("sensitivity", 1.0)
            slope = self.config_manager.get("slope", 1.85)
            anti_dz = self.config_manager.get("anti_deadzone", 0.0)
            dz = self.config_manager.get("deadzone", 0.13)
            filt = self.config_manager.get("filter", 0.0)

            self.slider_sens.setValue(int(sens * 100))
            self.val_sens.setText(f"{sens:.2f}x")

            self.slider_slope.setValue(int(slope * 100))
            self.val_slope.setText(f"{slope:.2f}")

            self.slider_anti_dz.setValue(int(anti_dz * 100))
            self.val_anti_dz.setText(f"{int(anti_dz * 100)}%")

            self.slider_deadzone.setValue(int(dz * 100))
            self.val_deadzone.setText(f"{int(dz * 100)}%")

            self.slider_filter.setValue(int(filt * 100))
            self.val_filter.setText(f"{filt:.2f}")

            self.chk_invert_steer.setChecked(bool(self.config_manager.get("invert_steer", False)))
            self.chk_invert_accel.setChecked(bool(self.config_manager.get("invert_accel", False)))
            self.chk_invert_brake.setChecked(bool(self.config_manager.get("invert_brake", False)))

            self.curve_canvas.set_parameters(slope=slope, sensitivity=sens, anti_deadzone=anti_dz)
            self.pedal_throttle.set_deadzone(dz)
            self.pedal_brake.set_deadzone(dz)
        finally:
            self._is_updating_ui = False

    def _sync_presets_from_config(self) -> None:
        self._is_updating_ui = True
        try:
            presets = self.config_manager.get_presets_list()
            active = self.config_manager.get("active_preset", "Personalizado")
            self.preset_combo.clear()
            for p in presets:
                self.preset_combo.addItem(p)
            if active in presets:
                self.preset_combo.setCurrentText(active)
            else:
                self.preset_combo.setCurrentText("Personalizado")
        finally:
            self._is_updating_ui = False

    def _on_preset_selected(self, preset_name: str) -> None:
        if self._is_updating_ui or not preset_name:
            return
        if hasattr(self.engine, "load_preset"):
            success = self.engine.load_preset(preset_name)
        else:
            success = self.config_manager.load_preset(preset_name)
            self.config_manager.save()

        if success:
            self._sync_sliders_from_config()
            self._log(f"Preset '{preset_name}' cargado con éxito.", "success")

    def _save_new_preset(self) -> None:
        name, ok = QInputDialog.getText(
            self,
            tr("presets.save_preset"),
            tr("presets.enter_name"),
        )
        if ok and name.strip():
            clean = name.strip()
            if hasattr(self.engine, "save_preset"):
                success = self.engine.save_preset(clean)
            else:
                success = self.config_manager.save_current_as_preset(clean)

            if success:
                self._sync_presets_from_config()
                self._log(f"Preset '{clean}' guardado.", "success")
            else:
                QMessageBox.warning(self, tr("common.warning"), tr("presets.invalid_name"))

    def _delete_current_preset(self) -> None:
        current = self.preset_combo.currentText()
        if current in ("Personalizado", "F1 RACING", "F1 RACING CRUCETAS", "RALLY / DRIFT", "SIMULADOR CAMIONES"):
            QMessageBox.information(self, tr("common.warning"), tr("presets.cannot_delete_default"))
            return

        res = QMessageBox.question(
            self,
            tr("presets.confirm_delete_title"),
            tr("presets.confirm_delete_msg", name=current),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res == QMessageBox.StandardButton.Yes:
            if hasattr(self.engine, "delete_preset"):
                self.engine.delete_preset(current)
            else:
                self.config_manager.delete_preset(current)
            self._sync_presets_from_config()
            self._sync_sliders_from_config()
            self._log(f"Preset '{current}' eliminado.", "info")

    # -------------------------------------------------------------------------
    # Diálogos y Asistentes
    # -------------------------------------------------------------------------
    def _open_calibration_wizard(self) -> None:
        dlg = CalibrationWizardDialog(engine=self.engine, config_manager=self.config_manager, parent=self)
        dlg.calibration_applied.connect(lambda d: self._sync_sliders_from_config())
        dlg.exec()

    def _open_mapping_wizard(self) -> None:
        current_mode = getattr(self.engine, "mode", MODE_CONDUCCION)
        dlg = MappingWizardDialog(
            engine=self.engine,
            config_manager=self.config_manager,
            mode=current_mode,
            parent=self,
        )
        dlg.wizard_finished.connect(lambda: (
            self._sync_presets_from_config(),
            self._sync_sliders_from_config(),
            self._on_preset_selected(self.config_manager.get("active_preset", "Personalizado"))
        ))
        dlg.exec()

    def _open_theme_dialog(self) -> None:
        dlg = ThemeDialog(config_manager=self.config_manager, parent=self)
        dlg.theme_changed.connect(self._on_theme_changed)
        dlg.exec()

    def _on_theme_changed(self, accent_hex: str, lang: str) -> None:
        self._apply_current_theme(custom_accent=accent_hex)
        self.wheel_gauge.set_accent_color(accent_hex)
        self.curve_canvas.set_accent_color(accent_hex)
        if lang != get_language():
            set_language(lang)

    def _toggle_language(self) -> None:
        new_lang = "en" if get_language() == "es" else "es"
        set_language(new_lang)
        if hasattr(self.config_manager, "set_language"):
            self.config_manager.set_language(new_lang)

    def _on_language_changed(self, lang: str) -> None:
        """Actualiza todas las etiquetas dinámicas al cambiar de idioma."""
        self.setWindowTitle(tr("app.title"))
        self.btn_lang.setText(f"[{lang.upper()}]")
        self.status_lbl.setText(tr(f"status.{self._last_status}") if self._last_status else tr("status.disconnected"))
        self.btn_connect.setText(tr("status.disconnect") if self._last_status == "connected" else tr("status.connect"))
        self.preset_lbl.setText(tr("presets.title") + ":")
        self.btn_save_preset.setText(tr("presets.save"))
        self.btn_delete_preset.setText(tr("presets.delete"))
        self.btn_calib_wizard.setText(tr("common.calibration"))
        self.btn_map_wizard.setText(tr("common.controls"))
        self.btn_theme.setText("⚙ " + tr("common.settings"))
        self.ddu_title.setText(tr("telemetry.title").upper())
        self.tabs.setTabText(0, tr("sliders.title"))
        self._log(f"Idioma cambiado a {lang.upper()}.", "info")

    def _apply_current_theme(self, custom_accent: str = "") -> None:
        accent = custom_accent or (
            self.config_manager.get_theme_accent()
            if hasattr(self.config_manager, "get_theme_accent")
            else "#00e5ff"
        )
        self.setStyleSheet(get_stylesheet(custom_accent=accent))

    def _log(self, text: str, level: str = "info") -> None:
        timestamp = time.strftime("%H:%M:%S")
        color_map = {
            "success": "#00e676",
            "warn": "#ff9100",
            "error": "#ff3344",
            "info": "#94a3b8",
        }
        color = color_map.get(level, "#f1f5f9")
        html = f"<span style='color: #64748b;'>[{timestamp}]</span> <span style='color: {color}; font-weight: 600;'>{text}</span>"
        self.log_console.appendHtml(html)

    # -------------------------------------------------------------------------
    # Cierre Seguro de la Ventana
    # -------------------------------------------------------------------------
    def closeEvent(self, event) -> None:
        self._telemetry_timer.stop()
        if hasattr(self, "_unsubscribe_i18n") and self._unsubscribe_i18n:
            self._unsubscribe_i18n()
        if self.engine:
            self.engine.stop()
        event.accept()

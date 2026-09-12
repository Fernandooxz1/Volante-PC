"""
ButtonGrid: Matriz de estado de hardware para los 11 pines digitales de Volante-PC.
Muestra badges o pastillas tipo hardware de alta tecnología (D2..D8, A3, A5, A4, D12)
con iluminación reactiva al ser pulsados físicamente y la función asignada de Xbox.
"""

from typing import Dict, List, Optional, Union

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import QGridLayout, QWidget

try:
    from core.protocol import CONFIG_BUTTON_KEYS, PIN_NAMES
except ImportError:
    PIN_NAMES = ['D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'A3', 'A5', 'A4', 'D12']
    CONFIG_BUTTON_KEYS = [
        'btn_map_p2', 'btn_map_p3', 'btn_map_p4', 'btn_map_p5',
        'btn_map_p6', 'btn_map_p7', 'btn_map_p8', 'btn_map_pa3',
        'btn_map_pa5', 'btn_map_pa4', 'btn_map_p12'
    ]
from ui.widgets.theme import (
    COLOR_ACCENT_CYAN,
    COLOR_BG_CARD,
    COLOR_BG_DEEP,
    COLOR_BORDER_ACTIVE,
    COLOR_BORDER_SUBTLE,
    COLOR_TEXT_DARK,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    parse_color,
)

# Abreviaturas legibles para telemetría compacta
ACTION_ABBREVIATIONS: Dict[str, str] = {
    "button a": "BTN A",
    "button b": "BTN B",
    "button x": "BTN X",
    "button y": "BTN Y",
    "button start": "START",
    "button back": "BACK",
    "button lb (left shoulder)": "LB",
    "button rb (right shoulder)": "RB",
    "button l3 (left click)": "L3",
    "button r3 (right click)": "R3",
    "d-pad up": "DPAD UP",
    "d-pad down": "DPAD DN",
    "d-pad left": "DPAD LF",
    "d-pad right": "DPAD RT",
    "ninguno": "NONE",
    "none": "NONE",
}


def format_action_label(action: str) -> str:
    """Formatea la acción asignada a una versión compacta de instrumentación."""
    clean = action.strip().lower()
    if clean in ACTION_ABBREVIATIONS:
        return ACTION_ABBREVIATIONS[clean]
    # Si contiene D-Pad o Button, simplificar
    clean_upper = action.upper()
    clean_upper = clean_upper.replace("BUTTON ", "BTN ")
    clean_upper = clean_upper.replace("D-PAD ", "DPAD ")
    return clean_upper


class ButtonPill(QWidget):
    """
    Pastilla/Badge individual para un pin físico de la placa.
    Dibuja el identificador de pin (e.g. 'D2'), la acción Xbox asociada,
    y un LED de estado que se ilumina con resplandor al presionarse.
    """

    clicked = pyqtSignal(str)

    def __init__(
        self,
        pin_name: str,
        action: str = "NONE",
        parent: Optional[QWidget] = None,
        accent_color: str | QColor = COLOR_ACCENT_CYAN,
    ):
        super().__init__(parent)
        self._pin_name: str = pin_name.upper()
        self._action_raw: str = action
        self._action_label: str = format_action_label(action)
        self._is_pressed: bool = False
        self._accent_color: QColor = parse_color(accent_color)

        self.setMinimumSize(70, 32)
        self.setToolTip(f"Pin {self._pin_name}: {self._action_raw}")

    def set_pressed(self, pressed: bool) -> None:
        """Actualiza el estado de pulsación física del botón."""
        is_p = bool(pressed)
        if self._is_pressed != is_p:
            self._is_pressed = is_p
            self.update()

    def set_action(self, action: str) -> None:
        """Actualiza la acción vinculada de Xbox."""
        if self._action_raw != action:
            self._action_raw = action
            self._action_label = format_action_label(action)
            self.setToolTip(f"Pin {self._pin_name}: {self._action_raw}")
            self.update()

    def set_accent_color(self, color: str | QColor) -> None:
        """Modifica el color de iluminación activa."""
        self._accent_color = parse_color(color)
        self.update()

    def is_pressed(self) -> bool:
        return self._is_pressed

    def get_pin_name(self) -> str:
        return self._pin_name

    def sizeHint(self) -> QSize:
        return QSize(95, 36)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._pin_name)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        width = self.width()
        height = self.height()
        if width <= 10 or height <= 10:
            return

        corner_r = 5.0
        rect = QRectF(1.0, 1.0, width - 2.0, height - 2.0)

        # 1. Contenedor exterior y fondo
        if self._is_pressed:
            # Fondo activo brillante con gradiente del color de acento
            grad_bg = QLinearGradient(0, 0, width, height)
            bg_start = QColor(self._accent_color)
            bg_start.setAlpha(210)
            bg_end = QColor(self._accent_color.darker(170))
            bg_end.setAlpha(240)
            grad_bg.setColorAt(0.0, bg_start)
            grad_bg.setColorAt(1.0, bg_end)

            pen_border = QPen(self._accent_color.lighter(150), 1.8)
            painter.setPen(pen_border)
            painter.setBrush(QBrush(grad_bg))
            painter.drawRoundedRect(rect, corner_r, corner_r)
        else:
            # Fondo reposo sutil
            grad_bg = QLinearGradient(0, 0, width, height)
            grad_bg.setColorAt(0.0, COLOR_BG_CARD)
            grad_bg.setColorAt(1.0, COLOR_BG_DEEP)

            pen_border = QPen(COLOR_BORDER_SUBTLE, 1.0)
            painter.setPen(pen_border)
            painter.setBrush(QBrush(grad_bg))
            painter.drawRoundedRect(rect, corner_r, corner_r)

        # 2. Chip de identificación del Pin (Izquierda)
        badge_w = 34.0
        badge_rect = QRectF(rect.left() + 2.0, rect.top() + 2.0, badge_w, rect.height() - 4.0)

        badge_path = QPainterPath()
        badge_path.addRoundedRect(badge_rect, corner_r - 1.0, corner_r - 1.0)

        if self._is_pressed:
            badge_bg = QColor("#0a0c10")
            badge_text_color = self._accent_color.lighter(140)
        else:
            badge_bg = QColor("#19202b")
            badge_text_color = COLOR_TEXT_SECONDARY

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(badge_bg))
        painter.drawPath(badge_path)

        font_pin = QFont("monospace")
        font_pin.setStyleHint(QFont.StyleHint.Monospace)
        font_pin.setBold(True)
        font_pin.setPixelSize(10)
        painter.setFont(font_pin)
        painter.setPen(badge_text_color)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self._pin_name)

        # 3. Pip LED de estado (Derecha)
        led_radius = 3.0
        led_cx = rect.right() - 8.0
        led_cy = rect.top() + rect.height() / 2.0

        if self._is_pressed:
            # LED resplandeciente
            led_grad = QRadialGradient(led_cx, led_cy, led_radius * 2.2)
            led_grad.setColorAt(0.0, QColor("#ffffff"))
            led_grad.setColorAt(0.5, self._accent_color.lighter(130))
            led_grad.setColorAt(1.0, QColor(0, 0, 0, 0))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(led_grad))
            painter.drawEllipse(QPointF(led_cx, led_cy), led_radius * 2.2, led_radius * 2.2)

            painter.setPen(QPen(QColor("#ffffff"), 1.0))
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawEllipse(QPointF(led_cx, led_cy), led_radius, led_radius)
        else:
            # LED apagado
            painter.setPen(QPen(COLOR_BORDER_ACTIVE, 0.8))
            painter.setBrush(QBrush(QColor("#151b24")))
            painter.drawEllipse(QPointF(led_cx, led_cy), led_radius, led_radius)

        # 4. Texto de acción asignada (Centro)
        action_rect = QRectF(
            badge_rect.right() + 4.0,
            rect.top(),
            (led_cx - led_radius - 4.0) - (badge_rect.right() + 4.0),
            rect.height(),
        )

        font_act = QFont("monospace")
        font_act.setStyleHint(QFont.StyleHint.Monospace)
        font_act.setBold(True)
        font_act.setPixelSize(9)
        painter.setFont(font_act)

        if self._is_pressed:
            painter.setPen(COLOR_TEXT_DARK if self._accent_color.lightness() > 160 else COLOR_TEXT_PRIMARY)
        elif self._action_label == "NONE":
            painter.setPen(COLOR_TEXT_MUTED)
        else:
            painter.setPen(COLOR_TEXT_PRIMARY)

        # Truncado seguro si el texto excede el espacio
        metrics = QFontMetrics(font_act)
        elided = metrics.elidedText(self._action_label, Qt.TextElideMode.ElideRight, int(action_rect.width()))
        painter.drawText(action_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)


class ButtonGrid(QWidget):
    """
    Matriz contenedora con los 11 pines físicos del volante.
    Gestiona la actualización individual o masiva de estados y mapeos.
    """

    button_clicked = pyqtSignal(str)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        columns: int = 4,
        accent_color: str | QColor = COLOR_ACCENT_CYAN,
    ):
        super().__init__(parent)
        self._columns = max(1, columns)
        self._accent_color = parse_color(accent_color)

        self._pills: Dict[str, ButtonPill] = {}
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(6)

        self._init_pills()

    def _init_pills(self) -> None:
        """Crea e inserta las pastillas para los 11 pines de PIN_NAMES."""
        row = 0
        col = 0
        for pin in PIN_NAMES:
            pill = ButtonPill(pin_name=pin, accent_color=self._accent_color, parent=self)
            pill.clicked.connect(self._on_pill_clicked)
            self._pills[pin] = pill
            self._layout.addWidget(pill, row, col)

            col += 1
            if col >= self._columns:
                col = 0
                row += 1

    def _on_pill_clicked(self, pin_name: str) -> None:
        self.button_clicked.emit(pin_name)

    # -------------------------------------------------------------------------
    # API Pública
    # -------------------------------------------------------------------------

    def set_button_states(self, states: List[int]) -> None:
        """
        Actualiza el estado de los 11 botones a partir de la lista binaria recibida del paquete.
        states: lista de 11 enteros (0 o 1) correspondientes a PIN_NAMES.
        """
        for i, pin in enumerate(PIN_NAMES):
            if i < len(states):
                pill = self._pills.get(pin)
                if pill is not None:
                    pill.set_pressed(bool(states[i]))

    def set_button_state(self, pin_identifier: Union[str, int], pressed: bool | int) -> None:
        """Actualiza el estado de un pin específico por su nombre o índice."""
        if isinstance(pin_identifier, int):
            if 0 <= pin_identifier < len(PIN_NAMES):
                pin_name = PIN_NAMES[pin_identifier]
            else:
                return
        else:
            pin_name = pin_identifier.upper()

        pill = self._pills.get(pin_name)
        if pill is not None:
            pill.set_pressed(bool(pressed))

    def set_mapping(self, mapping: Dict[str, str]) -> None:
        """
        Actualiza los nombres de acción asignados para cada pin.
        mapping puede indexar por clave de config ('btn_map_p2') o por pin ('D2').
        """
        # Mapeo directo de claves de configuración a pines
        config_key_to_pin = dict(zip(CONFIG_BUTTON_KEYS, PIN_NAMES))

        for key, action in mapping.items():
            pin = config_key_to_pin.get(key, key.upper())
            pill = self._pills.get(pin)
            if pill is not None:
                pill.set_action(str(action))

    def set_pin_mapping(self, pin: str, action: str) -> None:
        """Establece la acción de un pin individual."""
        pill = self._pills.get(pin.upper())
        if pill is not None:
            pill.set_action(str(action))

    def set_accent_color(self, color: str | QColor) -> None:
        """Actualiza el color de iluminación activa en todas las pastillas."""
        self._accent_color = parse_color(color)
        for pill in self._pills.values():
            pill.set_accent_color(self._accent_color)

    def get_button_state(self, pin: str) -> bool:
        """Retorna si el pin especificado está presionado."""
        pill = self._pills.get(pin.upper())
        return pill.is_pressed() if pill else False

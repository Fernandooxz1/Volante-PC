"""
LedIndicator: Barra horizontal de indicadores LED simulados de alta fidelidad.
Muestra el modo activo ('DRIVE MODE' vs 'D-PAD / CRUCETAS') y replica visualmente
el color y estado del LED RGB físico de la placa Arduino UNO en tiempo real.
"""

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import QWidget

from ui.widgets.theme import (
    COLOR_ACCENT_CYAN,
    COLOR_ALERT_ORANGE,
    COLOR_BG_CARD,
    COLOR_BG_DEEP,
    COLOR_BORDER_ACTIVE,
    COLOR_BORDER_SUBTLE,
    COLOR_TEXT_DARK,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_THROTTLE_GREEN,
    COLOR_WARNING_YELLOW,
    parse_color,
)


class LedIndicator(QWidget):
    """
    Instrumento de barra LED horizontal con lentes ópticos simulados y badge de modo.
    Diseñado con estética de volante de Fórmula 1 / GT3.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        led_count: int = 10,
        mode: str = "DRIVE MODE",
        led_color: str | int | QColor = "azul",
    ):
        super().__init__(parent)

        self._led_count: int = max(4, min(24, led_count))
        self._mode_str: str = mode.upper()
        self._is_alert: bool = ("D-PAD" in self._mode_str or "CRUCETA" in self._mode_str)
        self._led_color: QColor = parse_color(led_color)
        self._brightness: float = 1.0  # 0.0 .. 1.0
        self._rpm_ratio: Optional[float] = None  # Opcional: modo shift-light (0.0 .. 1.0)

        self.setMinimumSize(220, 38)

    # -------------------------------------------------------------------------
    # API Pública
    # -------------------------------------------------------------------------

    def set_mode(self, mode: str, is_alert: Optional[bool] = None) -> None:
        """
        Establece el modo activo ('DRIVE MODE', 'D-PAD / CRUCETAS', etc.).
        Si is_alert es None, se infiere según el contenido del texto.
        """
        mode_clean = mode.strip().upper()
        if is_alert is None:
            alert = ("D-PAD" in mode_clean or "CRUCETA" in mode_clean)
        else:
            alert = bool(is_alert)

        if self._mode_str != mode_clean or self._is_alert != alert:
            self._mode_str = mode_clean
            self._is_alert = alert
            self.update()

    def set_led_color(self, color: str | int | QColor) -> None:
        """
        Actualiza el color para replicar el LED RGB físico del Arduino.
        Acepta nombres en español/inglés, códigos de protocolo (0..7) o QColor.
        """
        new_color = parse_color(color)
        if self._led_color != new_color:
            self._led_color = new_color
            self.update()

    def set_brightness(self, level: float) -> None:
        """Ajusta el brillo global de los LEDs (0.0 a 1.0)."""
        clamped = max(0.0, min(1.0, float(level)))
        if abs(self._brightness - clamped) > 0.01:
            self._brightness = clamped
            self.update()

    def set_rpm_ratio(self, ratio: Optional[float]) -> None:
        """
        Opcional: activa el modo de barra de cambio de marchas (Shift Light / Rev Counter).
        ratio en [0.0, 1.0], o None para volver al modo de sincronización RGB estático.
        """
        if ratio is not None:
            clamped = max(0.0, min(1.0, float(ratio)))
            if self._rpm_ratio != clamped:
                self._rpm_ratio = clamped
                self.update()
        elif self._rpm_ratio is not None:
            self._rpm_ratio = None
            self.update()

    def set_led_count(self, count: int) -> None:
        """Modifica el número de LEDs del cluster."""
        cnt = max(4, min(24, int(count)))
        if self._led_count != cnt:
            self._led_count = cnt
            self.update()

    def get_mode(self) -> str:
        return self._mode_str

    def get_led_color(self) -> QColor:
        return self._led_color

    def is_alert_mode(self) -> bool:
        return self._is_alert

    def sizeHint(self) -> QSize:
        return QSize(340, 42)

    # -------------------------------------------------------------------------
    # Renderizado vectorial
    # -------------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        width = self.width()
        height = self.height()
        if width <= 20 or height <= 15:
            return

        # 1. Contenedor principal de fondo tipo cápsula DDU
        container_rect = QRectF(1.0, 1.0, width - 2.0, height - 2.0)
        corner_r = 6.0

        grad_bg = QLinearGradient(0, 0, width, height)
        grad_bg.setColorAt(0.0, COLOR_BG_DEEP)
        grad_bg.setColorAt(0.5, COLOR_BG_CARD)
        grad_bg.setColorAt(1.0, COLOR_BG_DEEP)

        painter.setPen(QPen(COLOR_BORDER_SUBTLE, 1.0))
        painter.setBrush(QBrush(grad_bg))
        painter.drawRoundedRect(container_rect, corner_r, corner_r)

        # 2. Pastilla de Modo Activo a la izquierda
        badge_w = min(150.0, max(110.0, width * 0.36))
        badge_rect = QRectF(container_rect.left() + 4.0, container_rect.top() + 4.0, badge_w, container_rect.height() - 8.0)
        self._draw_mode_badge(painter, badge_rect)

        # 3. Tira horizontal de LEDs a la derecha
        led_strip_rect = QRectF(
            badge_rect.right() + 8.0,
            container_rect.top() + 4.0,
            container_rect.right() - (badge_rect.right() + 12.0),
            container_rect.height() - 8.0,
        )
        if led_strip_rect.width() > 20:
            self._draw_led_strip(painter, led_strip_rect)

    def _draw_mode_badge(self, painter: QPainter, rect: QRectF) -> None:
        """Dibuja el badge de estado del modo (Drive Mode vs D-Pad/Crucetas)."""
        corner_r = 4.0
        accent = COLOR_ALERT_ORANGE if self._is_alert else (
            self._led_color if self._led_color != QColor("#1e2530") else COLOR_ACCENT_CYAN
        )

        # Fondo del badge
        badge_bg = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
        c_start = QColor(accent)
        c_start.setAlpha(45 if not self._is_alert else 75)
        c_end = QColor(accent)
        c_end.setAlpha(20 if not self._is_alert else 40)

        badge_bg.setColorAt(0.0, c_start)
        badge_bg.setColorAt(1.0, c_end)

        pen_border = QPen(accent if self._is_alert else COLOR_BORDER_ACTIVE, 1.2)
        painter.setPen(pen_border)
        painter.setBrush(QBrush(badge_bg))
        painter.drawRoundedRect(rect, corner_r, corner_r)

        # Pip luminoso indicador de modo en el badge
        pip_r = 3.2
        pip_cx = rect.left() + 10.0
        pip_cy = rect.top() + rect.height() / 2.0

        painter.setPen(Qt.PenStyle.NoPen)
        pip_glow = QColor(accent)
        pip_glow.setAlpha(120)
        painter.setBrush(QBrush(pip_glow))
        painter.drawEllipse(QPointF(pip_cx, pip_cy), pip_r * 1.8, pip_r * 1.8)

        painter.setPen(QPen(QColor("#ffffff"), 0.8))
        painter.setBrush(QBrush(accent.lighter(130)))
        painter.drawEllipse(QPointF(pip_cx, pip_cy), pip_r, pip_r)

        # Texto del modo
        font_mode = QFont("monospace")
        font_mode.setStyleHint(QFont.StyleHint.Monospace)
        font_mode.setBold(True)
        font_mode.setPixelSize(10)
        painter.setFont(font_mode)

        text_rect = QRectF(pip_cx + pip_r + 5.0, rect.top(), rect.right() - (pip_cx + pip_r + 7.0), rect.height())
        painter.setPen(COLOR_TEXT_PRIMARY if self._is_alert else COLOR_TEXT_SECONDARY)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._mode_str)

    def _draw_led_strip(self, painter: QPainter, rect: QRectF) -> None:
        """Dibuja la matriz horizontal de lentes ópticos de LED."""
        count = self._led_count
        slot_w = rect.width() / count
        max_diameter = min(rect.height() - 4.0, slot_w - 4.0)
        radius = max(3.0, max_diameter / 2.0)
        cy = rect.top() + rect.height() / 2.0

        for i in range(count):
            cx = rect.left() + (i + 0.5) * slot_w

            # Determinar color y estado para este LED
            led_c, is_on = self._get_led_state_at(i, count)
            self._draw_single_led(painter, cx, cy, radius, led_c, is_on)

    def _get_led_state_at(self, index: int, total: int) -> tuple[QColor, bool]:
        """Calcula el color y estado (on/off) para el LED en la posición dada."""
        # Modo Shift Light / RPM si está activo
        if self._rpm_ratio is not None:
            step = float(index + 1) / float(total)
            if self._rpm_ratio >= step:
                # Gradiente F1 de RPM: Verdes -> Amarillos -> Rojos
                ratio_pos = float(index) / float(total)
                if ratio_pos < 0.5:
                    c = COLOR_THROTTLE_GREEN
                elif ratio_pos < 0.8:
                    c = COLOR_WARNING_YELLOW
                else:
                    c = QColor("#ff1744")
                return c, True
            else:
                return QColor("#19212c"), False

        # Modo D-Pad Alert: Todos destellan en naranja de alerta
        if self._is_alert:
            return COLOR_ALERT_ORANGE, True

        # Modo Normal: Réplica del LED RGB físico de Arduino
        # Si el color es apagado (off)
        if self._led_color == QColor("#1e2530") or self._brightness < 0.05:
            return QColor("#19212c"), False

        return self._led_color, True

    def _draw_single_led(
        self,
        painter: QPainter,
        cx: float,
        cy: float,
        radius: float,
        color: QColor,
        is_on: bool,
    ) -> None:
        """Dibuja un LED óptico con lente cóncava, die emisor y resplandor."""
        # 1. Bisel metálico exterior oscuro
        painter.setPen(QPen(COLOR_BORDER_SUBTLE, 1.2))
        painter.setBrush(QBrush(QColor("#11151c")))
        painter.drawEllipse(QPointF(cx, cy), radius + 1.0, radius + 1.0)

        # 2. Reflector cóncavo interno
        refl_grad = QRadialGradient(cx, cy, radius)
        refl_grad.setColorAt(0.0, QColor("#1c222c"))
        refl_grad.setColorAt(1.0, QColor("#0c0f14"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(refl_grad))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        if is_on:
            # 3. Resplandor exterior (Bloom Halo)
            glow_c = QColor(color)
            glow_c.setAlpha(int(60 * self._brightness))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow_c))
            painter.drawEllipse(QPointF(cx, cy), radius * 2.0, radius * 2.0)

            # 4. Cuerpo luminoso del LED
            body_grad = QRadialGradient(cx, cy, radius)
            c_center = QColor(color).lighter(150)
            c_center.setAlpha(int(255 * self._brightness))
            c_edge = QColor(color)
            c_edge.setAlpha(int(220 * self._brightness))

            body_grad.setColorAt(0.0, c_center)
            body_grad.setColorAt(0.6, c_edge)
            body_grad.setColorAt(1.0, color.darker(140))

            painter.setPen(QPen(color.lighter(130), 0.8))
            painter.setBrush(QBrush(body_grad))
            painter.drawEllipse(QPointF(cx, cy), radius * 0.85, radius * 0.85)

            # 5. Punto focal emisor ultrabrillante
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, int(220 * self._brightness))))
            painter.drawEllipse(QPointF(cx, cy), radius * 0.32, radius * 0.32)

            # 6. Destello de lente especular (Lens Flare Highlight)
            spec_path = QPainterPath()
            spec_cx = cx - radius * 0.3
            spec_cy = cy - radius * 0.3
            spec_r = radius * 0.28
            spec_path.addEllipse(QPointF(spec_cx, spec_cy), spec_r, spec_r * 0.65)

            painter.setBrush(QBrush(QColor(255, 255, 255, int(180 * self._brightness))))
            painter.drawPath(spec_path)
        else:
            # Lente apagada con sutil reflejo vítreo
            painter.setPen(QPen(QColor("#252e3d"), 0.8))
            painter.setBrush(QBrush(QColor("#151b24")))
            painter.drawEllipse(QPointF(cx, cy), radius * 0.85, radius * 0.85)

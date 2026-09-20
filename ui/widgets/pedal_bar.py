"""
PedalBar: Widget vertical de precisión para telemetría de acelerador y freno.
Estética Motorsport DDU con barras redondeadas, indicador de zona muerta punteado,
lectura de porcentaje digital en tiempo real y lectura directa de ADC.
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
)
from PyQt6.QtWidgets import QWidget

from ui.widgets.theme import (
    COLOR_ACCENT_CYAN,
    COLOR_BG_CARD,
    COLOR_BG_DEEP,
    COLOR_BORDER_ACTIVE,
    COLOR_BORDER_SUBTLE,
    COLOR_BRAKE_RED,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_THROTTLE_GREEN,
    COLOR_WARNING_YELLOW,
    parse_color,
)


class PedalBar(QWidget):
    """
    Barra vertical de instrumentación para pedales (Acelerador / Freno / Embrague).
    Muestra el porcentaje efectivo (0..100%), lectura cruda de ADC (0..1023),
    y la línea punteada del umbral de zona muerta activa.
    """

    def __init__(
        self,
        label: str = "THROTTLE",
        pedal_type: str = "throttle",
        parent: Optional[QWidget] = None,
        color: Optional[str | QColor] = None,
    ):
        super().__init__(parent)

        self._label: str = label.upper()
        self._pedal_type: str = pedal_type.lower()
        self._fill_percentage: float = 0.0  # 0.0 .. 1.0
        self._raw_adc: int = 0  # 0 .. 1023
        self._deadzone: float = 0.08  # 0.0 .. 1.0

        # Asignación de color según tipo de pedal
        if color is not None:
            self._bar_color = parse_color(color)
        elif self._pedal_type == "brake":
            self._bar_color = COLOR_BRAKE_RED
        elif self._pedal_type == "clutch":
            self._bar_color = COLOR_ACCENT_CYAN
        else:
            self._bar_color = COLOR_THROTTLE_GREEN

        self.setMinimumSize(75, 220)
        self.setMaximumSize(120, 520)

    # -------------------------------------------------------------------------
    # API Pública
    # -------------------------------------------------------------------------

    def set_value(self, normalized: float, raw_adc: Optional[int] = None) -> None:
        """
        Establece el nivel de salida efectivo (0.0 .. 1.0 o 0.0 .. 100.0) y opcionalmente el ADC crudo.
        """
        val = float(normalized)
        if val > 1.0:
            val /= 100.0
        norm_clamped = max(0.0, min(1.0, val))
        changed = False

        if abs(self._fill_percentage - norm_clamped) > 0.002:
            self._fill_percentage = norm_clamped
            changed = True

        if raw_adc is not None and self._raw_adc != raw_adc:
            self._raw_adc = max(0, min(1023, int(raw_adc)))
            changed = True

        if changed:
            self.update()

    def set_raw_adc(self, raw: int) -> None:
        """Establece la lectura directa del conversor analógico-digital (0..1023)."""
        raw_val = max(0, min(1023, int(raw)))
        if self._raw_adc != raw_val:
            self._raw_adc = raw_val
            self.update()

    def set_deadzone(self, deadzone: float) -> None:
        """Establece la zona muerta como porcentaje normalizado (0.0 .. 0.5)."""
        dz_clamped = max(0.0, min(0.5, float(deadzone)))
        if abs(self._deadzone - dz_clamped) > 0.001:
            self._deadzone = dz_clamped
            self.update()

    def set_label(self, label: str) -> None:
        """Modifica la etiqueta superior del pedal."""
        self._label = label.upper()
        self.update()

    def set_bar_color(self, color: str | QColor) -> None:
        """Modifica el color temático de la barra."""
        self._bar_color = parse_color(color)
        self.update()

    def set_pedal_type(self, pedal_type: str) -> None:
        """Configura el tipo ('throttle', 'brake' o 'clutch')."""
        self._pedal_type = pedal_type.lower()
        if self._pedal_type == "brake":
            self._bar_color = COLOR_BRAKE_RED
        elif self._pedal_type == "clutch":
            self._bar_color = COLOR_ACCENT_CYAN
        else:
            self._bar_color = COLOR_THROTTLE_GREEN
        self.update()

    def get_value(self) -> float:
        return self._fill_percentage

    def get_raw_adc(self) -> int:
        return self._raw_adc

    def get_deadzone(self) -> float:
        return self._deadzone

    def sizeHint(self) -> QSize:
        return QSize(100, 480)

    # -------------------------------------------------------------------------
    # Renderizado vectorial
    # -------------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        width = self.width()
        height = self.height()
        if width <= 10 or height <= 30:
            return

        # Distribución vertical de zonas:
        # 1. Cabecera (Etiqueta + Porcentaje digital): 44px
        # 2. Canal de barra vertical central: restante - 28px
        # 3. Pie (Lectura ADC): 24px
        pad_x = 8.0
        pad_top = 6.0
        pad_bottom = 6.0

        header_h = 42.0
        footer_h = 24.0

        bar_x = pad_x + 6.0
        bar_w = width - (pad_x * 2.0) - 12.0
        bar_y = pad_top + header_h
        bar_h = height - pad_top - pad_bottom - header_h - footer_h

        if bar_h <= 10 or bar_w <= 6:
            return

        # 1. Cabecera
        self._draw_header(painter, 0, pad_top, width, header_h)

        # 2. Barra vertical y zona muerta
        self._draw_bar(painter, bar_x, bar_y, bar_w, bar_h)

        # 3. Pie de página (ADC)
        self._draw_footer(painter, 0, bar_y + bar_h + 4.0, width, footer_h)

    def _draw_header(
        self, painter: QPainter, x: float, y: float, w: float, h: float
    ) -> None:
        """Dibuja el título del pedal y el porcentaje numérico grande."""
        # Nombre del pedal
        font_tag = QFont("monospace")
        font_tag.setStyleHint(QFont.StyleHint.Monospace)
        font_tag.setBold(True)
        font_tag.setPixelSize(10)
        painter.setFont(font_tag)
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.drawText(
            QRectF(x, y, w, 15.0),
            Qt.AlignmentFlag.AlignCenter,
            self._label,
        )

        # Porcentaje digital grande (e.g. "85%")
        font_pct = QFont("monospace")
        font_pct.setStyleHint(QFont.StyleHint.Monospace)
        font_pct.setBold(True)
        font_pct.setPixelSize(16)
        painter.setFont(font_pct)

        pct_int = int(round(self._fill_percentage * 100.0))
        if pct_int > 0:
            painter.setPen(COLOR_TEXT_PRIMARY)
        else:
            painter.setPen(COLOR_TEXT_MUTED)

        painter.drawText(
            QRectF(x, y + 15.0, w, 22.0),
            Qt.AlignmentFlag.AlignCenter,
            f"{pct_int}%",
        )

    def _draw_bar(
        self, painter: QPainter, bx: float, by: float, bw: float, bh: float
    ) -> None:
        """Dibuja el contenedor redondeado, el llenado dinámico y la línea de zona muerta."""
        corner_r = min(6.0, bw / 2.0)
        container_rect = QRectF(bx, by, bw, bh)

        # 1. Contenedor de fondo (Canal oscuro con bisel interior)
        grad_bg = QLinearGradient(bx, by, bx + bw, by)
        grad_bg.setColorAt(0.0, COLOR_BG_DEEP)
        grad_bg.setColorAt(0.5, COLOR_BG_CARD)
        grad_bg.setColorAt(1.0, COLOR_BG_DEEP)

        painter.setPen(QPen(COLOR_BORDER_SUBTLE, 1.2))
        painter.setBrush(QBrush(grad_bg))
        painter.drawRoundedRect(container_rect, corner_r, corner_r)

        # 2. Escala de marcas sutiles a la derecha (0%, 25%, 50%, 75%, 100%)
        painter.setPen(QPen(COLOR_BORDER_ACTIVE, 1.0))
        for step in [0.0, 0.25, 0.50, 0.75, 1.0]:
            tick_y = by + bh - (step * bh)
            painter.drawLine(
                QPointF(bx + bw - 4.0, tick_y),
                QPointF(bx + bw - 1.0, tick_y),
            )

        # 3. Llenado dinámico de la barra
        fill_h = bh * self._fill_percentage
        if fill_h > 1.0:
            fill_y = by + bh - fill_h
            fill_rect = QRectF(bx + 1.0, fill_y, bw - 2.0, fill_h)

            # Gradiente luminoso para dar estética de barra de telemetría LED
            grad_fill = QLinearGradient(bx, by + bh, bx, fill_y)
            grad_fill.setColorAt(0.0, self._bar_color.darker(160))
            grad_fill.setColorAt(0.7, self._bar_color)
            grad_fill.setColorAt(1.0, self._bar_color.lighter(135))

            painter.save()
            # Clip con los bordes redondeados del contenedor
            clip_path = QPainterPath()
            clip_path.addRoundedRect(container_rect, corner_r, corner_r)
            painter.setClipPath(clip_path)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad_fill))
            painter.drawRect(fill_rect)

            # Línea de cresta superior luminosa (menisco brillante)
            crest_pen = QPen(self._bar_color.lighter(170), 1.5)
            painter.setPen(crest_pen)
            painter.drawLine(
                QPointF(bx + 2.0, fill_y),
                QPointF(bx + bw - 2.0, fill_y),
            )
            painter.restore()

        # 4. Línea punteada de umbral de zona muerta activa
        if self._deadzone > 0.001:
            dz_y = by + bh - (self._deadzone * bh)
            dz_pen = QPen(COLOR_WARNING_YELLOW, 1.5, Qt.PenStyle.DashLine)
            painter.setPen(dz_pen)
            painter.drawLine(
                QPointF(bx - 2.0, dz_y),
                QPointF(bx + bw + 2.0, dz_y),
            )

            # Pequeño marcador indicador de zona muerta
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(COLOR_WARNING_YELLOW))
            dz_indicator = QPainterPath()
            dz_indicator.moveTo(bx - 1.0, dz_y - 2.5)
            dz_indicator.lineTo(bx + 2.5, dz_y)
            dz_indicator.lineTo(bx - 1.0, dz_y + 2.5)
            dz_indicator.closeSubpath()
            painter.drawPath(dz_indicator)

    def _draw_footer(
        self, painter: QPainter, x: float, y: float, w: float, h: float
    ) -> None:
        """Dibuja la lectura de telemetría cruda del convertidor ADC."""
        font_adc = QFont("monospace")
        font_adc.setStyleHint(QFont.StyleHint.Monospace)
        font_adc.setBold(True)
        font_adc.setPixelSize(10)
        painter.setFont(font_adc)

        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.drawText(
            QRectF(x, y, w, h),
            Qt.AlignmentFlag.AlignCenter,
            f"ADC: {self._raw_adc}",
        )

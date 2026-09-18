"""
WheelGauge: Widget de cuadrante de dirección vectorial con estética Motorsport DDU.
Renderizado de alto rendimiento con QPainter, antialiasing y rotación suave multi-giro (-540° a +540°).
"""

import math
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
    COLOR_BG_CARD,
    COLOR_BG_DEEP,
    COLOR_BORDER_ACTIVE,
    COLOR_BORDER_SUBTLE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_THROTTLE_GREEN,
    parse_color,
)


class WheelGauge(QWidget):
    """
    Instrumento de visualización de volante de carreras.
    Dibuja un volante vectorial con llanta exterior, franja de centrado a las 12,
    radios con aligeramientos mecánicos, tornillería hexagonal de competición,
    indicador fijo de zona muerta y pantalla digital central de telemetría.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        max_angle: float = 90.0,
        accent_color: str | QColor = COLOR_ACCENT_CYAN,
    ):
        super().__init__(parent)

        self._angle: float = 0.0  # Grados actuales (-max_angle .. +max_angle)
        self._max_angle: float = max_angle
        self._deadzone: float = 0.03  # Fracción normalizada (0.0 .. 1.0)
        self._accent_color: QColor = parse_color(accent_color)
        self._raw_value: Optional[int] = 512

        # Configuración de widget
        self.setMinimumSize(180, 180)
        self.setSizePolicy(
            self.sizePolicy().horizontalPolicy(),
            self.sizePolicy().verticalPolicy(),
        )

    # -------------------------------------------------------------------------
    # API Pública
    # -------------------------------------------------------------------------

    def set_angle(self, degrees: float) -> None:
        """Establece el ángulo físico del volante en grados (-max_angle .. +max_angle)."""
        clamped = max(-self._max_angle, min(self._max_angle, float(degrees)))
        if abs(self._angle - clamped) > 0.01:
            self._angle = clamped
            self.update()

    def get_angle(self) -> float:
        return self._angle

    def set_normalized_value(self, val: float) -> None:
        """Establece el ángulo a partir de un valor normalizado entre -1.0 y +1.0."""
        clamped = max(-1.0, min(1.0, float(val)))
        self.set_angle(clamped * self._max_angle)

    def set_raw_value(
        self,
        raw: int,
        steer_min: int = 0,
        steer_center: int = 512,
        steer_max: int = 1023,
    ) -> None:
        """Calcula y actualiza el ángulo a partir de la lectura analógica directa del ADC."""
        self._raw_value = raw
        if raw < steer_center:
            span = steer_center - steer_min
            norm = (raw - steer_center) / span if span > 0 else 0.0
        else:
            span = steer_max - steer_center
            norm = (raw - steer_center) / span if span > 0 else 0.0
        self.set_normalized_value(norm)

    def set_deadzone(self, deadzone: float) -> None:
        """Establece el umbral de zona muerta neutra (0.0 .. 0.5)."""
        val = max(0.0, min(0.5, float(deadzone)))
        if abs(self._deadzone - val) > 0.001:
            self._deadzone = val
            self.update()

    def set_max_angle(self, max_angle: float) -> None:
        """Establece el rango de deflexión máxima (de 90.0° a 540.0°)."""
        if max_angle > 0:
            self._max_angle = float(max_angle)
            clamped = max(-self._max_angle, min(self._max_angle, self._angle))
            if abs(self._angle - clamped) > 0.01:
                self._angle = clamped
            self.update()

    def set_accent_color(self, color: str | QColor) -> None:
        """Modifica el color de acento para la franja de las 12 e iluminación."""
        self._accent_color = parse_color(color)
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(260, 260)

    # -------------------------------------------------------------------------
    # Renderizado vectorial
    # -------------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        width = self.width()
        height = self.height()
        size = min(width, height)
        if size <= 10:
            return

        cx = width / 2.0
        cy = height / 2.0
        radius = (size / 2.0) - 8.0

        # Fondo sutil del cuadrante
        self._draw_background(painter, cx, cy, radius)

        # Escala fija exterior y marcas de zona muerta (no rotan)
        self._draw_fixed_bezel(painter, cx, cy, radius)

        # Volante rotatorio (aro, franja de las 12, radios, tornillos)
        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self._angle)
        self._draw_rotating_wheel(painter, radius)
        painter.restore()

        # Display digital central de telemetría (fijo, sin rotación para legibilidad)
        self._draw_center_display(painter, cx, cy, radius)

    def _draw_background(
        self, painter: QPainter, cx: float, cy: float, radius: float
    ) -> None:
        """Dibuja el fondo circular de la bahía del instrumento."""
        bg_rect = QRectF(cx - radius, cy - radius, radius * 2.0, radius * 2.0)

        # Gradiente radial sutil para dar profundidad de cápsula
        grad = QRadialGradient(cx, cy, radius)
        grad.setColorAt(0.0, COLOR_BG_CARD)
        grad.setColorAt(0.85, COLOR_BG_DEEP)
        grad.setColorAt(1.0, QColor("#07090c"))

        painter.setPen(QPen(COLOR_BORDER_SUBTLE, 1.5))
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(bg_rect)

    def _draw_fixed_bezel(
        self, painter: QPainter, cx: float, cy: float, radius: float
    ) -> None:
        """Dibuja las marcas fijas de grados en el bisel exterior y el marcador de centro."""
        r_outer = radius
        r_inner_major = radius - 7.0
        r_inner_minor = radius - 4.0

        is_centered = abs(self._angle) <= (self._deadzone * self._max_angle)

        # Arco de sector de zona muerta en la parte superior (12 o'clock)
        if self._deadzone > 0.001:
            dz_angle = self._deadzone * self._max_angle
            dz_span_deg = min(360.0, dz_angle * 2.0)
            dz_start_angle = 90.0 - dz_angle

            dz_rect = QRectF(cx - r_outer + 1.0, cy - r_outer + 1.0, (r_outer - 1.0) * 2.0, (r_outer - 1.0) * 2.0)
            dz_pen_color = self._accent_color if is_centered else QColor(COLOR_BORDER_ACTIVE)
            dz_pen = QPen(dz_pen_color, 2.5)
            painter.setPen(dz_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(dz_rect, int(dz_start_angle * 16), int(dz_span_deg * 16))

        # Marcas dinámicas de escala exterior según deflexión máxima
        if self._max_angle <= 100:
            interval = 30
        elif self._max_angle <= 200:
            interval = 45
        elif self._max_angle <= 380:
            interval = 90
        else:
            interval = 180

        ticks = []
        t = 0
        while t <= self._max_angle:
            ticks.append(t)
            if t > 0:
                ticks.append(-t)
            t += interval
        ticks.sort()

        for tick in ticks:
            # Ángulo en sistema trigonométrico (0° arriba = 90° trigonométrico)
            angle_rad = math.radians(270.0 + tick)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)

            p1 = QPointF(cx + r_outer * cos_a, cy + r_outer * sin_a)
            p2 = QPointF(cx + r_inner_major * cos_a, cy + r_inner_major * sin_a)

            if tick == 0:
                pen = QPen(self._accent_color if is_centered else COLOR_TEXT_SECONDARY, 2.0)
            else:
                pen = QPen(COLOR_BORDER_ACTIVE, 1.2)

            painter.setPen(pen)
            painter.drawLine(p1, p2)

        # Marcador triangular central en 12 o'clock (Posición Neutra)
        notch_color = self._accent_color if is_centered else COLOR_BORDER_ACTIVE
        notch_path = QPainterPath()
        notch_path.moveTo(cx, cy - r_outer + 1.5)
        notch_path.lineTo(cx - 4.5, cy - r_outer + 8.5)
        notch_path.lineTo(cx + 4.5, cy - r_outer + 8.5)
        notch_path.closeSubpath()

        painter.setPen(QPen(notch_color, 1.0))
        painter.setBrush(QBrush(notch_color))
        painter.drawPath(notch_path)

    def _draw_rotating_wheel(self, painter: QPainter, radius: float) -> None:
        """Dibuja el volante de carreras vectorial centrado en (0, 0)."""
        r_rim_outer = radius * 0.88
        r_rim_inner = radius * 0.68
        r_hub_outer = radius * 0.36
        rim_width = r_rim_outer - r_rim_inner

        # 1. Radios estructurales del volante (3 radios de aluminio fresado: 9h, 3h, 6h)
        self._draw_spokes(painter, r_hub_outer, r_rim_inner)

        # 2. Aro exterior del volante (Aro compuesto estilo GT)
        rim_path = QPainterPath()
        rim_path.addEllipse(QPointF(0, 0), r_rim_outer, r_rim_outer)
        rim_inner_path = QPainterPath()
        rim_inner_path.addEllipse(QPointF(0, 0), r_rim_inner, r_rim_inner)
        rim_ring = rim_path.subtracted(rim_inner_path)

        # Textura del aro: gradiente metálico oscuro de alta tecnología
        rim_grad = QRadialGradient(0, 0, r_rim_outer)
        rim_grad.setColorAt(0.68, QColor("#1e2430"))
        rim_grad.setColorAt(0.85, QColor("#28303f"))
        rim_grad.setColorAt(1.0, QColor("#141821"))

        painter.setPen(QPen(QColor("#3d495d"), 1.5))
        painter.setBrush(QBrush(rim_grad))
        painter.drawPath(rim_ring)

        # Grips ergonómicos en 9h y 3h (empuñaduras contorneadas)
        self._draw_rim_grips(painter, r_rim_inner, r_rim_outer)

        # 3. Franja central de centrado a las 12 (12 o'clock center stripe)
        stripe_angle = 7.0  # Semiancho en grados
        stripe_path = QPainterPath()
        stripe_rect_outer = QRectF(-r_rim_outer, -r_rim_outer, r_rim_outer * 2, r_rim_outer * 2)
        stripe_rect_inner = QRectF(-r_rim_inner, -r_rim_inner, r_rim_inner * 2, r_rim_inner * 2)

        stripe_path.arcMoveTo(stripe_rect_outer, 90.0 - stripe_angle)
        stripe_path.arcTo(stripe_rect_outer, 90.0 - stripe_angle, stripe_angle * 2.0)
        stripe_path.arcTo(stripe_rect_inner, 90.0 + stripe_angle, -stripe_angle * 2.0)
        stripe_path.closeSubpath()

        painter.setPen(QPen(self._accent_color.lighter(130), 1.0))
        painter.setBrush(QBrush(self._accent_color))
        painter.drawPath(stripe_path)

        # 4. Cubo central (Hub exterior con tornillería de competición)
        hub_grad = QRadialGradient(0, 0, r_hub_outer)
        hub_grad.setColorAt(0.0, QColor("#1a212b"))
        hub_grad.setColorAt(0.8, QColor("#222c3a"))
        hub_grad.setColorAt(1.0, QColor("#121720"))

        painter.setPen(QPen(QColor("#374354"), 1.5))
        painter.setBrush(QBrush(hub_grad))
        painter.drawEllipse(QPointF(0, 0), r_hub_outer, r_hub_outer)

        # Tornillos hexagonales de montaje (PCD de 6 tornillos a 60°)
        r_bolts = r_hub_outer * 0.82
        bolt_radius = max(2.0, radius * 0.018)
        painter.setPen(QPen(QColor("#54647a"), 1.0))
        painter.setBrush(QBrush(QColor("#11151c")))

        for i in range(6):
            b_angle = math.radians(i * 60.0)
            bx = r_bolts * math.cos(b_angle)
            by = r_bolts * math.sin(b_angle)
            painter.drawEllipse(QPointF(bx, by), bolt_radius, bolt_radius)

    def _draw_spokes(self, painter: QPainter, r_hub: float, r_rim: float) -> None:
        """Dibuja los 3 radios del volante con ranuras de alivio de peso."""
        spoke_pen = QPen(QColor("#2d3748"), 1.0)
        spoke_brush = QBrush(QColor("#1c222c"))
        painter.setPen(spoke_pen)
        painter.setBrush(spoke_brush)

        # Anchos de los radios
        w_h = r_hub * 0.38  # Ancho radios horizontales
        w_v = r_hub * 0.34  # Ancho radio inferior

        # Radio Izquierdo (-X)
        spoke_left = QPainterPath()
        spoke_left.moveTo(-r_hub * 0.8, -w_h * 0.6)
        spoke_left.lineTo(-r_rim + 1.0, -w_h * 0.9)
        spoke_left.lineTo(-r_rim + 1.0, w_h * 0.9)
        spoke_left.lineTo(-r_hub * 0.8, w_h * 0.6)
        spoke_left.closeSubpath()
        painter.drawPath(spoke_left)

        # Radio Derecho (+X)
        spoke_right = QPainterPath()
        spoke_right.moveTo(r_hub * 0.8, -w_h * 0.6)
        spoke_right.lineTo(r_rim - 1.0, -w_h * 0.9)
        spoke_right.lineTo(r_rim - 1.0, w_h * 0.9)
        spoke_right.lineTo(r_hub * 0.8, w_h * 0.6)
        spoke_right.closeSubpath()
        painter.drawPath(spoke_right)

        # Radio Inferior (+Y)
        spoke_bottom = QPainterPath()
        spoke_bottom.moveTo(-w_v * 0.6, r_hub * 0.8)
        spoke_bottom.lineTo(-w_v * 0.9, r_rim - 1.0)
        spoke_bottom.lineTo(w_v * 0.9, r_rim - 1.0)
        spoke_bottom.lineTo(w_v * 0.6, r_hub * 0.8)
        spoke_bottom.closeSubpath()
        painter.drawPath(spoke_bottom)

        # Ranuras de aligeramiento en los radios (Slots aligerados)
        painter.setPen(QPen(QColor("#11151c"), 1.0))
        painter.setBrush(QBrush(QColor("#0e1218")))

        # Ranura izquierda
        slot_w = (r_rim - r_hub) * 0.45
        slot_h = w_h * 0.35
        painter.drawRoundedRect(
            QRectF(-r_hub - slot_w * 0.85, -slot_h / 2, slot_w, slot_h),
            slot_h / 2,
            slot_h / 2,
        )

        # Ranura derecha
        painter.drawRoundedRect(
            QRectF(r_hub + slot_w * 0.15, -slot_h / 2, slot_w, slot_h),
            slot_h / 2,
            slot_h / 2,
        )

        # Ranura inferior
        painter.drawRoundedRect(
            QRectF(-slot_h / 2, r_hub + slot_w * 0.15, slot_h, slot_w),
            slot_h / 2,
            slot_h / 2,
        )

    def _draw_rim_grips(
        self, painter: QPainter, r_inner: float, r_outer: float
    ) -> None:
        """Dibuja marcas de agarre contorneadas en los costados 9h y 3h."""
        grip_pen = QPen(QColor("#384457"), 1.2)
        painter.setPen(grip_pen)

        # Pequeñas ranuras estriadas de agarre a 0° y 180°
        r_mid = (r_inner + r_outer) / 2.0
        for side in [-1, 1]:
            for offset_deg in [-15, -7.5, 0, 7.5, 15]:
                rad = math.radians(offset_deg)
                gx = side * (r_mid * math.cos(rad))
                gy = r_mid * math.sin(rad)
                painter.drawPoint(QPointF(gx, gy))

    def _draw_center_display(
        self, painter: QPainter, cx: float, cy: float, radius: float
    ) -> None:
        """
        Dibuja la pantalla central estática (DDU central).
        Permanece siempre horizontal para lectura instantánea a alta velocidad.
        """
        r_display = radius * 0.28
        disp_rect = QRectF(cx - r_display, cy - r_display, r_display * 2, r_display * 2)

        # Bisel y pantalla interna profunda
        disp_grad = QRadialGradient(cx, cy, r_display)
        disp_grad.setColorAt(0.0, QColor("#080a0e"))
        disp_grad.setColorAt(0.9, QColor("#0d1117"))
        disp_grad.setColorAt(1.0, COLOR_BG_DEEP)

        painter.setPen(QPen(COLOR_BORDER_SUBTLE, 1.5))
        painter.setBrush(QBrush(disp_grad))
        painter.drawEllipse(disp_rect)

        # Anillo perimetral del display con brillo según estado de centro
        is_centered = abs(self._angle) <= (self._deadzone * self._max_angle)
        ring_color = self._accent_color if is_centered else COLOR_BORDER_ACTIVE
        painter.setPen(QPen(ring_color, 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(cx - r_display + 2, cy - r_display + 2, (r_display - 2) * 2, (r_display - 2) * 2))

        # Texto 1: Etiqueta superior "STEER"
        font_tag = QFont("monospace")
        font_tag.setStyleHint(QFont.StyleHint.Monospace)
        font_tag.setBold(True)
        font_tag.setPixelSize(max(8, int(r_display * 0.22)))
        painter.setFont(font_tag)
        painter.setPen(COLOR_TEXT_SECONDARY)
        painter.drawText(
            QRectF(cx - r_display, cy - r_display * 0.72, r_display * 2, r_display * 0.35),
            Qt.AlignmentFlag.AlignCenter,
            "STEER",
        )

        # Texto 2: Lectura digital de grados grande (e.g. "+180.0°", "+450.0°", "-270.0°", "0.0°")
        if abs(self._angle) < 0.05:
            deg_str = "0.0°"
            deg_color = self._accent_color
        else:
            sign = "+" if self._angle > 0 else ""
            deg_str = f"{sign}{self._angle:.1f}°"
            deg_color = COLOR_TEXT_PRIMARY

        font_deg = QFont("monospace")
        font_deg.setStyleHint(QFont.StyleHint.Monospace)
        font_deg.setBold(True)
        font_scale = 0.34 if len(deg_str) >= 7 else 0.40
        font_deg.setPixelSize(max(10, int(r_display * font_scale)))
        painter.setFont(font_deg)
        painter.setPen(deg_color)

        painter.drawText(
            QRectF(cx - r_display, cy - r_display * 0.28, r_display * 2, r_display * 0.55),
            Qt.AlignmentFlag.AlignCenter,
            deg_str,
        )

        # Texto 3: Estado de zona muerta o centrado en la parte inferior
        font_status = QFont("monospace")
        font_status.setStyleHint(QFont.StyleHint.Monospace)
        font_status.setBold(True)
        font_status.setPixelSize(max(7, int(r_display * 0.19)))
        painter.setFont(font_status)

        if is_centered:
            painter.setPen(COLOR_THROTTLE_GREEN)
            status_str = "CENTER"
        else:
            norm_pct = min(100, int(round((abs(self._angle) / self._max_angle) * 100.0)))
            direction = "R" if self._angle > 0 else "L"
            painter.setPen(COLOR_TEXT_MUTED)
            status_str = f"{direction} {norm_pct}%"

        painter.drawText(
            QRectF(cx - r_display, cy + r_display * 0.35, r_display * 2, r_display * 0.30),
            Qt.AlignmentFlag.AlignCenter,
            status_str,
        )

"""
CurveCanvas: Widget de plano cartesiano con visualización de curva matemática exponencial.
Traza la respuesta no lineal de la dirección evaluada con core.calibration.evaluate_curve_point,
proyección de ejes y marcador seguidor en tiempo real de la posición física del volante.
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

try:
    from core.calibration import evaluate_curve_point
except ImportError:
    def evaluate_curve_point(
        x: float,
        slope: float = 1.0,
        sensitivity: float = 1.0,
        anti_deadzone: float = 0.0,
        rest_deadzone: float = 0.01,
    ) -> float:
        abs_x = abs(x)
        sign = 1.0 if x >= 0 else -1.0
        x_expo = sign * (abs_x ** max(0.1, slope))
        x_sloped = max(-1.0, min(1.0, x_expo * sensitivity))
        abs_val = abs(x_sloped)
        sloped_sign = 1.0 if x_sloped >= 0 else -1.0
        if abs_val <= rest_deadzone:
            return 0.0
        scaled = (abs_val - rest_deadzone) / (1.0 - rest_deadzone)
        scaled = max(0.0, min(1.0, scaled))
        return sloped_sign * (anti_deadzone + (1.0 - anti_deadzone) * scaled)
from ui.widgets.theme import (
    COLOR_ACCENT_CYAN,
    COLOR_BG_CARD,
    COLOR_BG_DEEP,
    COLOR_BORDER_ACTIVE,
    COLOR_BORDER_SUBTLE,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING_YELLOW,
    parse_color,
)


class CurveCanvas(QWidget):
    """
    Plano de coordenadas de precisión para la calibración matemática de dirección.
    Muestra la cuadrícula de -1.0 a +1.0 en ambos ejes, la curva exponencial suavizada
    con efecto de resplandor antialiasing y el punto seguidor en vivo.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        slope: float = 1.85,
        sensitivity: float = 1.0,
        anti_deadzone: float = 0.0,
        rest_deadzone: float = 0.01,
        accent_color: str | QColor = COLOR_ACCENT_CYAN,
    ):
        super().__init__(parent)

        self._slope: float = max(0.1, float(slope))
        self._sensitivity: float = max(0.1, min(2.0, float(sensitivity)))
        self._anti_deadzone: float = max(0.0, min(0.5, float(anti_deadzone)))
        self._rest_deadzone: float = max(0.0, min(0.2, float(rest_deadzone)))

        self._input_x: float = 0.0  # Posición física (-1.0 .. +1.0)
        self._output_y: float = 0.0  # Salida virtual calculada (-1.0 .. +1.0)

        self._accent_color: QColor = parse_color(accent_color)

        self.setMinimumSize(220, 180)

    # -------------------------------------------------------------------------
    # API Pública
    # -------------------------------------------------------------------------

    def set_parameters(
        self,
        slope: Optional[float] = None,
        sensitivity: Optional[float] = None,
        anti_deadzone: Optional[float] = None,
        rest_deadzone: Optional[float] = None,
    ) -> None:
        """Actualiza los parámetros matemáticos de la curva exponencial."""
        changed = False
        if slope is not None and abs(self._slope - float(slope)) > 0.001:
            self._slope = max(0.1, float(slope))
            changed = True
        if sensitivity is not None and abs(self._sensitivity - float(sensitivity)) > 0.001:
            self._sensitivity = max(0.1, min(2.0, float(sensitivity)))
            changed = True
        if anti_deadzone is not None and abs(self._anti_deadzone - float(anti_deadzone)) > 0.001:
            self._anti_deadzone = max(0.0, min(0.5, float(anti_deadzone)))
            changed = True
        if rest_deadzone is not None and abs(self._rest_deadzone - float(rest_deadzone)) > 0.001:
            self._rest_deadzone = max(0.0, min(0.2, float(rest_deadzone)))
            changed = True

        if changed:
            # Reevaluar salida del seguidor actual
            self._output_y = evaluate_curve_point(
                self._input_x,
                self._slope,
                self._sensitivity,
                self._anti_deadzone,
                self._rest_deadzone,
            )
            self.update()

    def set_follower(self, input_x: float, output_y: Optional[float] = None) -> None:
        """
        Actualiza la posición del punto seguidor en tiempo real.
        input_x: entrada física en [-1.0, 1.0].
        output_y: opcional, salida evaluada en [-1.0, 1.0]. Si es None se calcula automáticamente.
        """
        clamped_x = max(-1.0, min(1.0, float(input_x)))
        if output_y is not None:
            clamped_y = max(-1.0, min(1.0, float(output_y)))
        else:
            clamped_y = evaluate_curve_point(
                clamped_x,
                self._slope,
                self._sensitivity,
                self._anti_deadzone,
                self._rest_deadzone,
            )

        if abs(self._input_x - clamped_x) > 0.002 or abs(self._output_y - clamped_y) > 0.002:
            self._input_x = clamped_x
            self._output_y = clamped_y
            self.update()

    def set_accent_color(self, color: str | QColor) -> None:
        """Modifica el color del resplandor de la curva y del punto seguidor."""
        self._accent_color = parse_color(color)
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(320, 240)

    # -------------------------------------------------------------------------
    # Renderizado vectorial
    # -------------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        width = self.width()
        height = self.height()
        if width <= 20 or height <= 20:
            return

        # Márgenes para etiquetas de ejes y telemetría
        margin_left = 34.0
        margin_right = 16.0
        margin_top = 26.0
        margin_bottom = 24.0

        plot_w = width - margin_left - margin_right
        plot_h = height - margin_top - margin_bottom

        if plot_w <= 10 or plot_h <= 10:
            return

        plot_rect = QRectF(margin_left, margin_top, plot_w, plot_h)

        # 1. Fondo de pantalla de instrumentos
        self._draw_background(painter, plot_rect)

        # 2. Cuadrícula cartesiana y ejes
        self._draw_grid(painter, plot_rect)

        # 3. Curva exponencial con resplandor
        self._draw_curve(painter, plot_rect)

        # 4. Marcador seguidor en tiempo real y guías
        self._draw_follower(painter, plot_rect)

        # 5. Etiquetas de telemetría y HUD
        self._draw_hud(painter, plot_rect)

    def _coord_to_pixel(self, x: float, y: float, rect: QRectF) -> QPointF:
        """Convierte coordenadas matemáticas [-1.0, 1.0] a píxeles de pantalla."""
        px = rect.left() + ((x + 1.0) / 2.0) * rect.width()
        py = rect.top() + ((1.0 - y) / 2.0) * rect.height()
        return QPointF(px, py)

    def _draw_background(self, painter: QPainter, rect: QRectF) -> None:
        """Dibuja el fondo del osciloscopio con marco sutil."""
        painter.setPen(QPen(COLOR_BORDER_SUBTLE, 1.0))
        painter.setBrush(QBrush(COLOR_BG_CARD))
        painter.drawRect(rect)

        # Si hay zona muerta configurada, sombrear el área neutra
        if self._rest_deadzone > 0.001:
            p_dz_left = self._coord_to_pixel(-self._rest_deadzone, 1.0, rect)
            p_dz_right = self._coord_to_pixel(self._rest_deadzone, -1.0, rect)
            dz_rect = QRectF(
                p_dz_left.x(),
                rect.top(),
                p_dz_right.x() - p_dz_left.x(),
                rect.height(),
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 214, 0, 12)))
            painter.drawRect(dz_rect)

    def _draw_grid(self, painter: QPainter, rect: QRectF) -> None:
        """Dibuja la cuadrícula técnica de -1.0 a +1.0 y los ejes centrales."""
        font_axis = QFont("monospace")
        font_axis.setStyleHint(QFont.StyleHint.Monospace)
        font_axis.setPixelSize(9)
        painter.setFont(font_axis)

        # Línea de referencia lineal (1:1 y = x) punteada
        p_lin_start = self._coord_to_pixel(-1.0, -1.0, rect)
        p_lin_end = self._coord_to_pixel(1.0, 1.0, rect)
        pen_linear = QPen(QColor("#1e2837"), 1.0, Qt.PenStyle.DashLine)
        painter.setPen(pen_linear)
        painter.drawLine(p_lin_start, p_lin_end)

        # Subcuadrícula (-0.75, -0.25, +0.25, +0.75)
        pen_sub = QPen(QColor("#141a24"), 0.8)
        painter.setPen(pen_sub)
        for val in [-0.75, -0.25, 0.25, 0.75]:
            # Vertical
            p1 = self._coord_to_pixel(val, -1.0, rect)
            p2 = self._coord_to_pixel(val, 1.0, rect)
            painter.drawLine(p1, p2)
            # Horizontal
            p3 = self._coord_to_pixel(-1.0, val, rect)
            p4 = self._coord_to_pixel(1.0, val, rect)
            painter.drawLine(p3, p4)

        # Cuadrícula mayor (-1.0, -0.5, 0.0, 0.5, 1.0)
        pen_major = QPen(COLOR_BORDER_SUBTLE, 1.0)
        painter.setPen(pen_major)
        for val in [-0.5, 0.5]:
            # Vertical
            p1 = self._coord_to_pixel(val, -1.0, rect)
            p2 = self._coord_to_pixel(val, 1.0, rect)
            painter.drawLine(p1, p2)
            # Horizontal
            p3 = self._coord_to_pixel(-1.0, val, rect)
            p4 = self._coord_to_pixel(1.0, val, rect)
            painter.drawLine(p3, p4)

        # Ejes centrales principales (X = 0, Y = 0)
        pen_axis = QPen(COLOR_BORDER_ACTIVE, 1.5)
        painter.setPen(pen_axis)

        center_x = self._coord_to_pixel(0.0, 0.0, rect).x()
        center_y = self._coord_to_pixel(0.0, 0.0, rect).y()

        # Eje Y central
        painter.drawLine(QPointF(center_x, rect.top()), QPointF(center_x, rect.bottom()))
        # Eje X central
        painter.drawLine(QPointF(rect.left(), center_y), QPointF(rect.right(), center_y))

        # Etiquetas de escala en los bordes
        painter.setPen(COLOR_TEXT_MUTED)
        # Eje Y (Izquierda): +1.0, +0.5, 0, -0.5, -1.0
        y_labels = [(-1.0, "-1.0"), (-0.5, "-0.5"), (0.0, " 0.0"), (0.5, "+0.5"), (1.0, "+1.0")]
        for y_val, label in y_labels:
            pt = self._coord_to_pixel(-1.0, y_val, rect)
            label_rect = QRectF(rect.left() - 32.0, pt.y() - 6.0, 28.0, 12.0)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)

        # Eje X (Abajo): -1.0, -0.5, 0, +0.5, +1.0
        x_labels = [(-1.0, "-1.0"), (-0.5, "-0.5"), (0.0, "0"), (0.5, "+0.5"), (1.0, "+1.0")]
        for x_val, label in x_labels:
            pt = self._coord_to_pixel(x_val, -1.0, rect)
            label_rect = QRectF(pt.x() - 15.0, rect.bottom() + 4.0, 30.0, 12.0)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, label)

    def _draw_curve(self, painter: QPainter, rect: QRectF) -> None:
        """Dibuja la curva matemática con gradiente y resplandor de neón."""
        num_samples = 160
        curve_path = QPainterPath()

        step = 2.0 / float(num_samples - 1)
        for i in range(num_samples):
            x = -1.0 + i * step
            y = evaluate_curve_point(
                x,
                self._slope,
                self._sensitivity,
                self._anti_deadzone,
                self._rest_deadzone,
            )
            pt = self._coord_to_pixel(x, y, rect)
            if i == 0:
                curve_path.moveTo(pt)
            else:
                curve_path.lineTo(pt)

        # 1. Área sutil sombreada bajo la curva
        fill_path = QPainterPath(curve_path)
        center_y_pt = self._coord_to_pixel(1.0, 0.0, rect)
        center_start_pt = self._coord_to_pixel(-1.0, 0.0, rect)
        fill_path.lineTo(center_y_pt)
        fill_path.lineTo(center_start_pt)
        fill_path.closeSubpath()

        fill_color = QColor(self._accent_color)
        fill_color.setAlpha(16)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(fill_color))
        painter.drawPath(fill_path)

        # 2. Resplandor exterior de la curva (Glow exterior)
        glow_color_outer = QColor(self._accent_color)
        glow_color_outer.setAlpha(28)
        painter.setPen(QPen(glow_color_outer, 6.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(curve_path)

        # 3. Resplandor intermedio
        glow_color_mid = QColor(self._accent_color)
        glow_color_mid.setAlpha(70)
        painter.setPen(QPen(glow_color_mid, 3.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(curve_path)

        # 4. Trazo nítido principal de alta precisión
        core_color = self._accent_color.lighter(130)
        painter.setPen(QPen(core_color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(curve_path)

    def _draw_follower(self, painter: QPainter, rect: QRectF) -> None:
        """Dibuja el punto seguidor en vivo que rastrea la posición actual."""
        pt = self._coord_to_pixel(self._input_x, self._output_y, rect)

        # Guías punteadas proyectadas hacia los ejes
        p_x_axis = self._coord_to_pixel(self._input_x, 0.0, rect)
        p_y_axis = self._coord_to_pixel(0.0, self._output_y, rect)

        pen_guide = QPen(COLOR_BORDER_ACTIVE, 1.0, Qt.PenStyle.DotLine)
        painter.setPen(pen_guide)
        painter.drawLine(pt, p_x_axis)
        painter.drawLine(pt, p_y_axis)

        # Halo exterior del punto seguidor
        halo_color = QColor(self._accent_color)
        halo_color.setAlpha(60)
        painter.setPen(QPen(halo_color, 1.5))
        painter.setBrush(QBrush(halo_color))
        painter.drawEllipse(pt, 7.0, 7.0)

        # Núcleo interior brillante
        painter.setPen(QPen(QColor("#ffffff"), 1.2))
        painter.setBrush(QBrush(self._accent_color.lighter(140)))
        painter.drawEllipse(pt, 3.2, 3.2)

    def _draw_hud(self, painter: QPainter, rect: QRectF) -> None:
        """Dibuja la telemetría textual en la cabecera del gráfico."""
        font_hud = QFont("monospace")
        font_hud.setStyleHint(QFont.StyleHint.Monospace)
        font_hud.setBold(True)
        font_hud.setPixelSize(10)
        painter.setFont(font_hud)

        # Telemetría en vivo: IN y OUT
        sign_in = "+" if self._input_x > 0 else ""
        sign_out = "+" if self._output_y > 0 else ""
        hud_text = f"IN: {sign_in}{self._input_x:.2f}  OUT: {sign_out}{self._output_y:.2f}  EXP: {self._slope:.2f}"

        painter.setPen(COLOR_TEXT_PRIMARY)
        painter.drawText(
            QRectF(rect.left(), 4.0, rect.width(), 18.0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            hud_text,
        )

        # Etiqueta de función del eje
        painter.setPen(COLOR_TEXT_MUTED)
        painter.drawText(
            QRectF(rect.left(), 4.0, rect.width(), 18.0),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "STEERING EXPO",
        )

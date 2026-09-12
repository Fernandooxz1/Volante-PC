"""
Constantes de diseño y paleta cromática Motorsport DDU para Volante-PC.
Diseño de alto contraste, legible a altas velocidades y con estética de telemetría profesional.
"""

from PyQt6.QtGui import QColor

# Colores de fondo e interfaz (Tema Oscuro Carbono / Slate)
COLOR_BG_DEEP = QColor("#0a0c10")
COLOR_BG_CARD = QColor("#11151c")
COLOR_BG_SURFACE = QColor("#161c24")
COLOR_BG_HOVER = QColor("#1f2733")

# Bordes y líneas técnicas
COLOR_BORDER_SUBTLE = QColor("#202736")
COLOR_BORDER_ACTIVE = QColor("#334155")
COLOR_BORDER_HIGHLIGHT = QColor("#00e5ff")

# Tipografía de telemetría
COLOR_TEXT_PRIMARY = QColor("#f1f5f9")
COLOR_TEXT_SECONDARY = QColor("#94a3b8")
COLOR_TEXT_MUTED = QColor("#475569")
COLOR_TEXT_DARK = QColor("#0a0c10")

# Colores funcionales de instrumentación de carreras
COLOR_ACCENT_CYAN = QColor("#00e5ff")
COLOR_THROTTLE_GREEN = QColor("#00e676")
COLOR_BRAKE_RED = QColor("#ff3344")
COLOR_ALERT_ORANGE = QColor("#ff9100")
COLOR_WARNING_YELLOW = QColor("#ffd600")
COLOR_VIOLET = QColor("#a855f7")

# Mapeo de colores para el indicador LED (coincide con core/protocol.py)
ARDUINO_LED_COLORS = {
    0: QColor("#1e2530"),  # off / apagado
    "off": QColor("#1e2530"),
    "apagado": QColor("#1e2530"),

    1: QColor("#ff2238"),  # rojo
    "rojo": QColor("#ff2238"),
    "red": QColor("#ff2238"),

    2: QColor("#00e676"),  # verde
    "verde": QColor("#00e676"),
    "green": QColor("#00e676"),

    3: QColor("#0091ff"),  # azul
    "azul": QColor("#0091ff"),
    "blue": QColor("#0091ff"),

    4: QColor("#ffd600"),  # amarillo
    "amarillo": QColor("#ffd600"),
    "yellow": QColor("#ffd600"),

    5: QColor("#c026d3"),  # violeta
    "violeta": QColor("#c026d3"),
    "violet": QColor("#c026d3"),

    6: QColor("#00e5ff"),  # celeste / cian
    "celeste": QColor("#00e5ff"),
    "cian": QColor("#00e5ff"),
    "cyan": QColor("#00e5ff"),

    7: QColor("#ff6d00"),  # naranja
    "naranja": QColor("#ff6d00"),
    "orange": QColor("#ff6d00"),
}


def parse_color(color: str | int | QColor, default: QColor = COLOR_ACCENT_CYAN) -> QColor:
    """Convierte una cadena hex, nombre o entero a QColor de forma segura."""
    if isinstance(color, QColor):
        return color
    if isinstance(color, int) and color in ARDUINO_LED_COLORS:
        return ARDUINO_LED_COLORS[color]
    if isinstance(color, str):
        color_clean = color.strip().lower()
        if color_clean in ARDUINO_LED_COLORS:
            return ARDUINO_LED_COLORS[color_clean]
        qc = QColor(color)
        if qc.isValid():
            return qc
    return default

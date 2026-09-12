"""
Sistema de temas visuales y hojas de estilo QSS para Volante-PC.
Diseño de inspiración Motorsport DDU (Driver Display Unit) de alto contraste,
con tipografía técnica, bordes nítidos y estética de telemetría profesional.
"""

from typing import Dict, Any

THEME_PRESETS: Dict[str, Dict[str, str]] = {
    "cyan_neon": {
        "name": "Cyan Neon",
        "bg_deep": "#0a0c10",
        "bg_card": "#11151c",
        "bg_surface": "#161c24",
        "bg_hover": "#1f2733",
        "border_subtle": "#202736",
        "border_active": "#334155",
        "accent": "#00e5ff",
        "text_primary": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "text_muted": "#475569",
    },
    "racing_red": {
        "name": "Racing Red",
        "bg_deep": "#0a0c10",
        "bg_card": "#121318",
        "bg_surface": "#1a1921",
        "bg_hover": "#25222c",
        "border_subtle": "#2e2836",
        "border_active": "#4a3b52",
        "accent": "#ff3344",
        "text_primary": "#f8fafc",
        "text_secondary": "#94a3b8",
        "text_muted": "#64748b",
    },
    "acid_green": {
        "name": "Porsche Acid Green",
        "bg_deep": "#090d0b",
        "bg_card": "#0f1612",
        "bg_surface": "#141f19",
        "bg_hover": "#1c2c23",
        "border_subtle": "#1e382b",
        "border_active": "#2b523e",
        "accent": "#00e676",
        "text_primary": "#f1f5f9",
        "text_secondary": "#94a3b8",
        "text_muted": "#475569",
    },
    "mclaren_orange": {
        "name": "McLaren Orange",
        "bg_deep": "#0c0a08",
        "bg_card": "#16130f",
        "bg_surface": "#201a14",
        "bg_hover": "#2c241c",
        "border_subtle": "#3d3224",
        "border_active": "#594833",
        "accent": "#ff9100",
        "text_primary": "#f8fafc",
        "text_secondary": "#94a3b8",
        "text_muted": "#64748b",
    },
    "tokyo_violet": {
        "name": "Tokyo Night Violet",
        "bg_deep": "#0b0912",
        "bg_card": "#13101e",
        "bg_surface": "#1b172a",
        "bg_hover": "#26203a",
        "border_subtle": "#2f274a",
        "border_active": "#4d3d78",
        "accent": "#a855f7",
        "text_primary": "#f8fafc",
        "text_secondary": "#a78bfa",
        "text_muted": "#6b5b95",
    },
    "oled_black": {
        "name": "OLED Black",
        "bg_deep": "#000000",
        "bg_card": "#080808",
        "bg_surface": "#101010",
        "bg_hover": "#181818",
        "border_subtle": "#222222",
        "border_active": "#444444",
        "accent": "#ffffff",
        "text_primary": "#ffffff",
        "text_secondary": "#a0a0a0",
        "text_muted": "#555555",
    },
}

DEFAULT_THEME = "cyan_neon"


def get_stylesheet(theme: str = DEFAULT_THEME, custom_accent: str = "") -> str:
    """
    Genera la hoja de estilos QSS para PyQt6 según el tema seleccionado.
    """
    theme_data = THEME_PRESETS.get(theme, THEME_PRESETS[DEFAULT_THEME]).copy()
    if custom_accent and custom_accent.startswith("#"):
        theme_data["accent"] = custom_accent

    accent = theme_data["accent"]
    bg_deep = theme_data["bg_deep"]
    bg_card = theme_data["bg_card"]
    bg_surface = theme_data["bg_surface"]
    bg_hover = theme_data["bg_hover"]
    border_subtle = theme_data["border_subtle"]
    border_active = theme_data["border_active"]
    text_primary = theme_data["text_primary"]
    text_secondary = theme_data["text_secondary"]
    text_muted = theme_data["text_muted"]

    return f"""
/* Ventana principal y contenedores base */
QMainWindow, QDialog, QWidget {{
    background-color: {bg_deep};
    color: {text_primary};
    font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
    font-size: 13px;
}}

/* Barra de herramientas / Toolbar */
QToolBar {{
    background-color: {bg_card};
    border-bottom: 1px solid {border_subtle};
    padding: 6px 12px;
    spacing: 10px;
}}

QToolBar QLabel {{
    color: {text_secondary};
    font-weight: 600;
}}

/* Grupos y Tarjetas */
QGroupBox {{
    background-color: {bg_card};
    border: 1px solid {border_subtle};
    border-radius: 8px;
    margin-top: 24px;
    padding: 16px 14px 14px 14px;
    font-weight: 700;
    font-size: 12px;
    color: {accent};
    letter-spacing: 0.5px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 6px;
    padding: 0 6px;
    background-color: {bg_card};
}}

/* Botones con aspecto Motorsport */
QPushButton {{
    background-color: {bg_surface};
    color: {text_primary};
    border: 1px solid {border_subtle};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 12px;
}}

QPushButton:hover {{
    background-color: {bg_hover};
    border-color: {border_active};
    color: #ffffff;
}}

QPushButton:pressed {{
    background-color: {accent};
    border-color: {accent};
    color: {bg_deep};
}}

QPushButton:disabled {{
    background-color: {bg_card};
    border-color: {border_subtle};
    color: {text_muted};
}}

/* Botón primario de acento */
QPushButton#primaryButton, QPushButton[primary="true"] {{
    background-color: {accent};
    color: {bg_deep};
    border: 1px solid {accent};
    font-weight: 700;
}}

QPushButton#primaryButton:hover, QPushButton[primary="true"]:hover {{
    background-color: #ffffff;
    border-color: #ffffff;
    color: {bg_deep};
}}

/* Campos de selección (ComboBox) */
QComboBox {{
    background-color: {bg_surface};
    color: {text_primary};
    border: 1px solid {border_subtle};
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 22px;
}}

QComboBox:hover {{
    border-color: {border_active};
}}

QComboBox:focus {{
    border-color: {accent};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}}

QComboBox QAbstractItemView {{
    background-color: {bg_card};
    border: 1px solid {border_active};
    selection-background-color: {bg_hover};
    selection-color: {accent};
    padding: 4px;
    outline: none;
}}

/* Sliders de precisión */
QSlider::groove:horizontal {{
    height: 6px;
    background-color: {bg_surface};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background-color: {accent};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background-color: #ffffff;
    border: 2px solid {accent};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {accent};
    border-color: #ffffff;
}}

/* Etiquetas */
QLabel {{
    color: {text_primary};
}}

QLabel#valueLabel {{
    color: {accent};
    font-weight: 700;
    font-family: 'Consolas', 'Monaco', monospace;
}}

QLabel#descLabel {{
    color: {text_muted};
    font-size: 11px;
}}

/* Consola de logs / TextEdit */
QTextEdit, QPlainTextEdit {{
    background-color: {bg_surface};
    color: {text_secondary};
    border: 1px solid {border_subtle};
    border-radius: 6px;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 12px;
    padding: 8px;
}}

/* Áreas de desplazamiento / ScrollAreas */
QScrollArea {{
    background-color: transparent;
    border: none;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* Barras de desplazamiento / ScrollBars */
QScrollBar:vertical {{
    background-color: {bg_card};
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {border_active};
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {accent};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {bg_card};
    height: 10px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {border_active};
    border-radius: 5px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {accent};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* Pestañas / TabWidget */
QTabWidget::pane {{
    border: 1px solid {border_subtle};
    background-color: {bg_card};
    border-radius: 8px;
    padding: 10px;
}}

QTabBar::tab {{
    background-color: {bg_surface};
    color: {text_secondary};
    border: 1px solid {border_subtle};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 18px;
    margin-right: 4px;
    font-weight: 600;
}}

QTabBar::tab:selected {{
    background-color: {bg_card};
    color: {accent};
    border-color: {border_active};
    border-bottom: 2px solid {accent};
}}

QTabBar::tab:hover:!selected {{
    background-color: {bg_hover};
    color: {text_primary};
}}

/* Barra de estado */
QStatusBar {{
    background-color: {bg_card};
    border-top: 1px solid {border_subtle};
    color: {text_secondary};
    font-size: 12px;
}}
"""

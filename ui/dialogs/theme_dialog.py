"""
Theme and Localization Customization Dialog for Volante-PC.
Provides:
1) Visual color palette picker with motorsport presets:
   - Cyan Neon (#00E5FF)
   - Racing Red (#FF1744)
   - Porsche Acid Green (#76FF03)
   - McLaren Orange (#FF6D00)
   - Tokyo Night Violet (#7C4DFF)
   - Custom Color Dialog (QColorDialog)
2) Real-time interactive UI preview card.
3) Language selector toggle ([EN] English / [ES] Español).
4) Seamless persistence to ConfigManager.

Zero emojis. Clean, high-contrast, minimalist motorsport UI.
"""

from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from core.config_manager import ConfigManager
from ui.dialogs.mapping_wizard import apply_dark_motorsport_style
from ui.i18n import i18n, tr

PRESET_COLORS: List[Tuple[str, str, str]] = [
    ("Cyan Neon", "#00E5FF", "High visibility cockpit cyan"),
    ("Racing Red", "#FF1744", "Classic Scuderia crimson"),
    ("Porsche Acid Green", "#76FF03", "Hypercar telemetry acid green"),
    ("McLaren Orange", "#FF6D00", "Heritage Papaya racing orange"),
    ("Tokyo Night Violet", "#7C4DFF", "Ultra high contrast neon violet"),
]

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "title": "SYSTEM PREFERENCES // THEME & LOCALIZATION",
        "subtitle": "SELECT COCKPIT DISPLAY ACCENT AND INTERFACE LANGUAGE",
        "color_presets_title": "ACCENT COLOR PRESETS",
        "custom_color_btn": "Custom Color...",
        "custom_color_dialog": "Select Custom Motorsport Accent Color",
        "live_preview_title": "LIVE HUD & TELEMETRY PREVIEW",
        "preview_badge": "TELEMETRY DDU",
        "preview_status": "ONLINE // 100 HZ",
        "preview_btn": "PRIMARY ACTION",
        "preview_slider_lbl": "TELEMETRY GAUGE // 78%",
        "language_title": "INTERFACE LANGUAGE",
        "lang_en": "[EN] English",
        "lang_es": "[ES] Español",
        "btn_apply": "Apply",
        "btn_save": "Save & Close",
        "btn_cancel": "Cancel",
        "active_tag": "[ACTIVE]",
    },
    "es": {
        "title": "PREFERENCIAS DEL SISTEMA // TEMA Y LOCALIZACIÓN",
        "subtitle": "SELECCIONAR COLOR DE ACENTO DEL COCKPIT E IDIOMA",
        "color_presets_title": "PRESETS DE COLOR DE ACENTO",
        "custom_color_btn": "Color Personalizado...",
        "custom_color_dialog": "Seleccionar Color de Acento Motorsport",
        "live_preview_title": "VISTA PREVIA DE INTERFAZ Y TELEMETRÍA",
        "preview_badge": "DDU TELEMETRÍA",
        "preview_status": "EN LÍNEA // 100 HZ",
        "preview_btn": "ACCIÓN PRINCIPAL",
        "preview_slider_lbl": "INDICADOR TELEMETRÍA // 78%",
        "language_title": "IDIOMA DE LA INTERFAZ",
        "lang_en": "[EN] English",
        "lang_es": "[ES] Español",
        "btn_apply": "Aplicar",
        "btn_save": "Guardar y Cerrar",
        "btn_cancel": "Cancelar",
        "active_tag": "[ACTIVO]",
    },
}


class PresetCardWidget(QFrame):
    """Clickable preset card displaying a color swatch, title, and hex code."""

    clicked = pyqtSignal(str)  # Emits hex code

    def __init__(
        self,
        name: str,
        hex_code: str,
        description: str,
        is_active: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.preset_name = name
        self.hex_code = hex_code
        self.description = description
        self.is_active = is_active

        self.setFixedHeight(68)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui()
        self.update_active_state(is_active)

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # Color swatch pill
        self.swatch = QFrame()
        self.swatch.setFixedSize(28, 28)
        self.swatch.setStyleSheet(f"""
            background-color: {self.hex_code};
            border: 1px solid #f1f5f9;
            border-radius: 4px;
        """)
        layout.addWidget(self.swatch)

        # Text labels (name and hex)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_name = QLabel(self.preset_name.upper())
        self.lbl_name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        text_layout.addWidget(self.lbl_name)

        self.lbl_hex = QLabel(self.hex_code)
        self.lbl_hex.setFont(QFont("Consolas", 9))
        self.lbl_hex.setStyleSheet("color: #94a3b8;")
        text_layout.addWidget(self.lbl_hex)

        layout.addLayout(text_layout)
        layout.addStretch()

        # Active tag
        self.lbl_active_tag = QLabel(tr("themes.active_tag"))
        self.lbl_active_tag.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        layout.addWidget(self.lbl_active_tag)

    def update_active_state(self, active: bool, lang: Optional[str] = None) -> None:
        self.is_active = active
        self.lbl_active_tag.setText(tr("themes.active_tag", lang=lang))
        if active:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: #1a2333;
                    border: 2px solid {self.hex_code};
                    border-radius: 6px;
                }}
            """)
            self.lbl_name.setStyleSheet(f"color: {self.hex_code};")
            self.lbl_active_tag.setVisible(True)
            self.lbl_active_tag.setStyleSheet(f"color: {self.hex_code};")
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #11151c;
                    border: 1px solid #202736;
                    border-radius: 6px;
                }
                QFrame:hover {
                    background-color: #161c24;
                    border-color: #334155;
                }
            """)
            self.lbl_name.setStyleSheet("color: #f1f5f9;")
            self.lbl_active_tag.setVisible(False)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.hex_code)
        super().mousePressEvent(event)


class ThemeDialog(QDialog):
    """
    Theme and Localization Customization Dialog.
    Allows user to select accent colors, configure custom hex colors,
    switch UI language, and persist preferences.
    """

    theme_changed = pyqtSignal(str, str)  # (accent_hex, language)

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.config_manager = config_manager or ConfigManager()

        self.initial_accent = self.config_manager.get_theme_accent()
        self.initial_lang = self.config_manager.get_language()

        self.current_accent = self.initial_accent
        self.current_lang = self.initial_lang

        self.setWindowTitle(tr("themes.dialog_title", lang=self.current_lang))
        self.setMinimumSize(660, 620)
        self.setModal(True)

        self.preset_cards: List[PresetCardWidget] = []

        self._build_ui()
        self._update_texts()
        self._refresh_palette_selection()
        self._refresh_preview()

    def _t(self, key: str) -> str:
        """Retrieves translated text string for active language."""
        if key == "title":
            return tr("themes.dialog_title", lang=self.current_lang)
        val = tr(f"themes.{key}", lang=self.current_lang)
        if val != f"themes.{key}":
            return val
        val = tr(f"common.{key}", lang=self.current_lang)
        if val != f"common.{key}":
            return val
        lang_dict = TRANSLATIONS.get(self.current_lang, TRANSLATIONS.get("es", {}))
        return lang_dict.get(key, key)

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        self.lbl_main_title = QLabel()
        self.lbl_main_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_main_title.setStyleSheet("color: #94a3b8; letter-spacing: 1px;")
        header_layout.addWidget(self.lbl_main_title)

        self.lbl_subtitle = QLabel()
        self.lbl_subtitle.setFont(QFont("Segoe UI", 10))
        self.lbl_subtitle.setStyleSheet("color: #475569;")
        header_layout.addWidget(self.lbl_subtitle)

        main_layout.addLayout(header_layout)

        # Section 1: Color Presets
        self.lbl_presets_title = QLabel()
        self.lbl_presets_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_presets_title.setStyleSheet("color: #f1f5f9; letter-spacing: 0.5px;")
        main_layout.addWidget(self.lbl_presets_title)

        # Grid of presets
        presets_grid = QGridLayout()
        presets_grid.setSpacing(10)

        for i, (name, hex_code, desc) in enumerate(PRESET_COLORS):
            row = i // 2
            col = i % 2
            card = PresetCardWidget(name, hex_code, desc, is_active=(hex_code.lower() == self.current_accent.lower()))
            card.clicked.connect(self._on_preset_clicked)
            presets_grid.addWidget(card, row, col)
            self.preset_cards.append(card)

        # Custom Color Card in the last grid slot
        self.btn_custom_color = QPushButton()
        self.btn_custom_color.setFixedHeight(68)
        self.btn_custom_color.setStyleSheet("""
            QPushButton {
                background-color: #11151c;
                border: 1px dashed #334155;
                border-radius: 6px;
                color: #94a3b8;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #161c24;
                border-color: #00e5ff;
                color: #f1f5f9;
            }
        """)
        self.btn_custom_color.clicked.connect(self._open_custom_color_dialog)
        presets_grid.addWidget(self.btn_custom_color, (len(PRESET_COLORS)) // 2, (len(PRESET_COLORS)) % 2)

        main_layout.addLayout(presets_grid)

        # Section 2: Live Preview Card
        self.lbl_preview_title = QLabel()
        self.lbl_preview_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_preview_title.setStyleSheet("color: #f1f5f9; letter-spacing: 0.5px;")
        main_layout.addWidget(self.lbl_preview_title)

        self.card_preview = QFrame()
        self.card_preview.setProperty("card", "true")
        preview_layout = QVBoxLayout(self.card_preview)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.setSpacing(12)

        preview_top_row = QHBoxLayout()
        self.lbl_preview_badge = QLabel()
        self.lbl_preview_badge.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.lbl_preview_badge.setStyleSheet("color: #f1f5f9; background-color: #1f2733; padding: 4px 8px; border-radius: 3px;")
        preview_top_row.addWidget(self.lbl_preview_badge)

        self.lbl_preview_status = QLabel()
        self.lbl_preview_status.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        preview_top_row.addWidget(self.lbl_preview_status)
        preview_top_row.addStretch()

        self.lbl_preview_hex_badge = QLabel()
        self.lbl_preview_hex_badge.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        preview_top_row.addWidget(self.lbl_preview_hex_badge)

        preview_layout.addLayout(preview_top_row)

        # Interactive preview elements row (button and progress bar)
        preview_elements_row = QHBoxLayout()
        preview_elements_row.setSpacing(14)

        self.preview_button = QPushButton()
        self.preview_button.setFixedWidth(160)
        self.preview_button.setFixedHeight(34)
        preview_elements_row.addWidget(self.preview_button)

        preview_bar_container = QVBoxLayout()
        preview_bar_container.setSpacing(4)
        self.lbl_preview_slider = QLabel()
        self.lbl_preview_slider.setFont(QFont("Consolas", 8))
        self.lbl_preview_slider.setStyleSheet("color: #94a3b8;")
        preview_bar_container.addWidget(self.lbl_preview_slider)

        self.preview_bar = QProgressBar()
        self.preview_bar.setRange(0, 100)
        self.preview_bar.setValue(78)
        self.preview_bar.setFixedHeight(8)
        preview_bar_container.addWidget(self.preview_bar)

        preview_elements_row.addLayout(preview_bar_container)
        preview_layout.addLayout(preview_elements_row)

        main_layout.addWidget(self.card_preview)

        # Section 3: Interface Language Selector
        self.lbl_lang_title = QLabel()
        self.lbl_lang_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_lang_title.setStyleSheet("color: #f1f5f9; letter-spacing: 0.5px;")
        main_layout.addWidget(self.lbl_lang_title)

        lang_container = QFrame()
        lang_container.setProperty("card", "true")
        lang_layout = QHBoxLayout(lang_container)
        lang_layout.setContentsMargins(16, 12, 16, 12)
        lang_layout.setSpacing(20)

        self.rb_lang_en = QRadioButton("[EN] English")
        self.rb_lang_en.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.rb_lang_en.setChecked(self.current_lang == "en")
        self.rb_lang_en.toggled.connect(self._on_lang_toggled)
        lang_layout.addWidget(self.rb_lang_en)

        self.rb_lang_es = QRadioButton("[ES] Español")
        self.rb_lang_es.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.rb_lang_es.setChecked(self.current_lang == "es")
        self.rb_lang_es.toggled.connect(self._on_lang_toggled)
        lang_layout.addWidget(self.rb_lang_es)

        lang_layout.addStretch()
        main_layout.addWidget(lang_container)

        # Bottom Button Row
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_apply = QPushButton()
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        btn_bar.addWidget(self.btn_apply)

        btn_bar.addStretch()

        self.btn_cancel = QPushButton()
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        btn_bar.addWidget(self.btn_cancel)

        self.btn_save = QPushButton()
        self.btn_save.setProperty("primary", "true")
        self.btn_save.clicked.connect(self._on_save_clicked)
        btn_bar.addWidget(self.btn_save)

        main_layout.addLayout(btn_bar)

    def _update_texts(self) -> None:
        """Refreshes all displayed strings according to current language."""
        self.setWindowTitle(self._t("title"))
        self.lbl_main_title.setText(self._t("title"))
        self.lbl_subtitle.setText(self._t("subtitle"))
        self.lbl_presets_title.setText(self._t("color_presets_title"))
        self.btn_custom_color.setText(f"+ {self._t('custom_color_btn')}")
        self.lbl_preview_title.setText(self._t("live_preview_title"))
        self.lbl_preview_badge.setText(self._t("preview_badge"))
        self.lbl_preview_status.setText(self._t("preview_status"))
        self.preview_button.setText(self._t("preview_btn"))
        self.lbl_preview_slider.setText(self._t("preview_slider_lbl"))
        self.lbl_lang_title.setText(self._t("language_title"))
        self.rb_lang_en.setText(self._t("lang_en"))
        self.rb_lang_es.setText(self._t("lang_es"))
        self.btn_apply.setText(self._t("btn_apply"))
        self.btn_save.setText(self._t("btn_save"))
        self.btn_cancel.setText(self._t("btn_cancel"))

    def _refresh_palette_selection(self) -> None:
        """Updates preset card highlights."""
        norm_current = self.current_accent.lower()
        has_matched_preset = False
        for card in self.preset_cards:
            is_active = (card.hex_code.lower() == norm_current)
            card.update_active_state(is_active, lang=self.current_lang)
            if is_active:
                has_matched_preset = True

        if not has_matched_preset:
            custom_tag = tr("themes.custom_tag", lang=self.current_lang)
            self.btn_custom_color.setText(f"{custom_tag} {self.current_accent.upper()}")
            self.btn_custom_color.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1a2333;
                    border: 2px solid {self.current_accent};
                    border-radius: 6px;
                    color: {self.current_accent};
                    font-size: 11px;
                    font-weight: 700;
                }}
            """)
        else:
            self.btn_custom_color.setText(f"+ {self._t('custom_color_btn')}")
            self.btn_custom_color.setStyleSheet("""
                QPushButton {
                    background-color: #11151c;
                    border: 1px dashed #334155;
                    border-radius: 6px;
                    color: #94a3b8;
                    font-size: 11px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background-color: #161c24;
                    border-color: #00e5ff;
                    color: #f1f5f9;
                }
            """)

    def _refresh_preview(self) -> None:
        """Updates live preview HUD elements with active accent color."""
        accent = self.current_accent

        self.lbl_preview_status.setStyleSheet(f"""
            color: #0a0c10;
            background-color: {accent};
            padding: 4px 8px;
            border-radius: 3px;
        """)

        self.lbl_preview_hex_badge.setText(f"HEX: {accent}")
        self.lbl_preview_hex_badge.setStyleSheet(f"color: {accent};")

        self.preview_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #0a0c10;
                border: 1px solid {accent};
                font-weight: 700;
                font-size: 11px;
                border-radius: 4px;
            }}
        """)

        self.preview_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #11151c;
                border: 1px solid #202736;
                border-radius: 3px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: {accent};
                border-radius: 2px;
            }}
        """)

        apply_dark_motorsport_style(self, accent)

    def _on_preset_clicked(self, hex_code: str) -> None:
        """Slot called when a preset card is clicked."""
        self.current_accent = hex_code
        self._refresh_palette_selection()
        self._refresh_preview()

    def _open_custom_color_dialog(self) -> None:
        """Opens QColorDialog to pick any custom hex color."""
        dialog = QColorDialog(QColor(self.current_accent), self)
        dialog.setWindowTitle(self._t("custom_color_dialog"))
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            chosen = dialog.selectedColor()
            if chosen.isValid():
                self.current_accent = chosen.name().upper()
                self._refresh_palette_selection()
                self._refresh_preview()

    def _on_lang_toggled(self) -> None:
        """Slot called when language radio button changes."""
        if self.rb_lang_en.isChecked():
            self.current_lang = "en"
        else:
            self.current_lang = "es"
        i18n.set_language(self.current_lang)
        self._update_texts()
        self._refresh_palette_selection()
        self._refresh_preview()

    def _on_apply_clicked(self) -> None:
        """Applies configuration without closing dialog."""
        self.config_manager.set_theme_accent(self.current_accent, auto_save=True)
        self.config_manager.set_language(self.current_lang, auto_save=True)
        i18n.set_language(self.current_lang)
        self.theme_changed.emit(self.current_accent, self.current_lang)

    def _on_save_clicked(self) -> None:
        """Saves configuration to disk and closes dialog."""
        self.config_manager.set_theme_accent(self.current_accent, auto_save=True)
        self.config_manager.set_language(self.current_lang, auto_save=True)
        i18n.set_language(self.current_lang)
        self.theme_changed.emit(self.current_accent, self.current_lang)
        self.accept()

    def _on_cancel_clicked(self) -> None:
        """Reverts to initial settings and closes dialog."""
        if self.current_accent != self.initial_accent or self.current_lang != self.initial_lang:
            self.config_manager.set_theme_accent(self.initial_accent, auto_save=True)
            self.config_manager.set_language(self.initial_lang, auto_save=True)
            i18n.set_language(self.initial_lang)
            self.theme_changed.emit(self.initial_accent, self.initial_lang)
        self.reject()

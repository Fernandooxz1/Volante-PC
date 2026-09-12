"""
Pruebas unitarias para ui/i18n.py y core/i18n.py.
Verifica la paridad total de claves entre Español (ES) e Inglés (EN),
ausencia de cadenas vacías, ausencia estricta de emojis en textos de ingeniería/simracing,
y reactividad del gestor de traducciones.
"""

import re
import pytest
from ui.i18n import (
    TRANSLATIONS,
    SUPPORTED_LANGUAGES,
    tr,
    set_language,
    get_language,
    subscribe,
)

# Patrón regex para detectar emojis comunes y pictogramas
EMOJI_REGEX = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticonos
    "\U0001F300-\U0001F5FF"  # Símbolos y pictogramas
    "\U0001F680-\U0001F6FF"  # Transporte y mapas
    "\U0001F700-\U0001FAFF"  # Pictogramas suplementarios
    "\U00002702-\U000027B0"  # Dingbats
    "\U00002600-\U000026FF"  # Símbolos misceláneos
    "]",
    flags=re.UNICODE
)


def test_supported_languages():
    """Verifica los idiomas declarados y disponibles."""
    assert "es" in SUPPORTED_LANGUAGES
    assert "en" in SUPPORTED_LANGUAGES
    assert len(SUPPORTED_LANGUAGES) >= 2


def test_translation_keys_parity():
    """Verifica que todas las claves existan en ambos idiomas sin omisiones."""
    keys_es = set(TRANSLATIONS["es"].keys())
    keys_en = set(TRANSLATIONS["en"].keys())

    missing_in_en = keys_es - keys_en
    missing_in_es = keys_en - keys_es

    assert not missing_in_en, f"Claves faltantes en inglés (EN): {missing_in_en}"
    assert not missing_in_es, f"Claves faltantes en español (ES): {missing_in_es}"
    assert len(keys_es) > 50, "El diccionario de traducción debe cubrir todas las secciones de la app"


@pytest.mark.parametrize("lang", ["es", "en"])
def test_no_empty_translations(lang):
    """Verifica que ninguna traducción sea una cadena vacía o espacios en blanco."""
    for key, text in TRANSLATIONS[lang].items():
        assert isinstance(text, str), f"[{lang}] La clave '{key}' no es una cadena"
        assert len(text.strip()) > 0, f"[{lang}] La clave '{key}' contiene una cadena vacía"


@pytest.mark.parametrize("lang", ["es", "en"])
def test_no_emojis_in_translations(lang):
    """Verifica que ningún texto de interfaz contenga emojis o pictogramas no profesionales."""
    for key, text in TRANSLATIONS[lang].items():
        match = EMOJI_REGEX.search(text)
        assert match is None, f"[{lang}] Emoji detectado en '{key}': '{match.group()}' dentro de '{text}'"


def test_tr_function_and_language_switching():
    """Verifica la función global tr() y el cambio reactivo de idioma."""
    set_language("es")
    assert get_language() == "es"
    assert tr("status.connected") == "Conectado"

    set_language("en")
    assert get_language() == "en"
    assert tr("status.connected") == "Connected"

    # Restaurar al predeterminado
    set_language("es")


def test_tr_formatting_interpolation():
    """Verifica la sustitución segura de variables de formato."""
    set_language("es")
    msg_es = tr("status.packets_per_sec", rate=100)
    assert "100 Hz" in msg_es

    set_language("en")
    msg_en = tr("status.packets_per_sec", rate=100)
    assert "100 Hz" in msg_en
    set_language("es")


def test_i18n_subscriber_notification():
    """Verifica que los suscriptores reciban la notificación de cambio de idioma."""
    events = []

    def on_lang_change(new_lang):
        events.append(new_lang)

    unsubscribe = subscribe(on_lang_change)
    try:
        set_language("en")
        set_language("es")
        assert "en" in events
        assert "es" in events
    finally:
        unsubscribe()

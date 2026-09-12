"""
Re-exportación del módulo de internacionalización en core para acceso desacoplado.
"""

from ui.i18n import (
    TRANSLATIONS,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    LANGUAGE_METADATA,
    I18nManager,
    tr,
    set_language,
    get_language,
    subscribe,
    unsubscribe,
    get_signal,
    get_available_languages,
)

__all__ = [
    "TRANSLATIONS",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "LANGUAGE_METADATA",
    "I18nManager",
    "tr",
    "set_language",
    "get_language",
    "subscribe",
    "unsubscribe",
    "get_signal",
    "get_available_languages",
]

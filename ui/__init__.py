"""
Volante-PC UI module.
Contains internationalization (i18n), modern styling themes, and motorsport widgets.
"""

try:
    from .i18n import tr, set_language, get_language, subscribe
except ImportError:
    tr = lambda s, **kw: s
    set_language = lambda l: None
    get_language = lambda: "es"
    subscribe = lambda cb: None

try:
    from .themes import get_stylesheet, THEME_PRESETS
except ImportError:
    get_stylesheet = lambda t="dark": ""
    THEME_PRESETS = {}

__all__ = [
    "tr",
    "set_language",
    "get_language",
    "subscribe",
    "get_stylesheet",
    "THEME_PRESETS",
]

"""
i18n.py
Internationalization for Creator Manager.

Language packs live in the `languages/` subfolder as Python modules
(e.g. languages/en.py) each exposing a STRINGS dict.

To add a new language: create languages/<code>.py with a STRINGS dict
containing the same keys as languages/en.py (the source of truth).
Missing keys fall back to English, then to the key itself.
"""
from __future__ import annotations

import importlib
import os

BASE = os.path.dirname(os.path.abspath(__file__))
LANG_DIR = os.path.join(BASE, "languages")

# Metadata for built-in languages (code -> (display_name, module_name)).
LANG_META = {
    "en":    ("English",        "en"),
    "es":    ("Español",        "es"),
    "zh_cn": ("中文 (简体)",    "zh_cn"),
}
DEFAULT_LANG = "en"

_current_lang = DEFAULT_LANG
_cache = {}


def get_available_languages() -> dict:
    """Return {code: display_name} for all available language packs."""
    result = {}
    # Built-in metadata first.
    for code, (display, _) in LANG_META.items():
        result[code] = display
    # Auto-discover extra modules in languages/.
    if os.path.isdir(LANG_DIR):
        for fn in os.listdir(LANG_DIR):
            if fn.endswith(".py") and fn != "__init__.py":
                code = fn[:-3]
                if code not in result:
                    result[code] = code
    return result


def _load_strings(code: str) -> dict:
    if code in _cache:
        return _cache[code]
    # English fallback always loaded.
    en = _load_module("en")
    strings = dict(en)
    if code != "en":
        strings.update(_load_module(code))
    _cache[code] = strings
    return strings


def _load_module(code: str) -> dict:
    mod_name = LANG_META.get(code, (code, code))[1]
    try:
        mod = importlib.import_module(f"languages.{mod_name}")
        return getattr(mod, "STRINGS", {})
    except Exception:
        return {}


def set_language(code: str) -> None:
    global _current_lang
    if code in get_available_languages():
        _current_lang = code


def get_language() -> str:
    return _current_lang


def t(key: str, **kwargs) -> str:
    """Translate a key with optional format kwargs.

    Falls back to English, then to the key itself.
    """
    strings = _load_strings(_current_lang)
    s = strings.get(key)
    if s is None:
        s = _load_module("en").get(key, key)
    if kwargs:
        try:
            return s.format(**kwargs)
        except Exception:
            return s
    return s


def reload() -> None:
    """Clear cache (use after installing/changing a language pack)."""
    global _cache
    _cache = {}


if __name__ == "__main__":
    print("Available:", get_available_languages())
    set_language("es")
    print("ES add_profile:", t("add_profile"))
    set_language("zh_cn")
    print("ZH add_profile:", t("add_profile"))
    set_language("en")
    print("EN add_profile:", t("add_profile"))

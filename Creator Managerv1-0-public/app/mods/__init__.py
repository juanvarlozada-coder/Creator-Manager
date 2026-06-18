"""
mods/__init__.py
Mod loader — scans *.py files in this directory (except this one),
imports them, and calls register(app) if the function exists.
"""

import importlib.util
import os
import sys


MODS_DIR = os.path.dirname(os.path.abspath(__file__))


def cargar_mods(app):
    loaded = []
    for fname in sorted(os.listdir(MODS_DIR)):
        if not fname.endswith(".py") or fname == "__init__.py":
            continue
        path = os.path.join(MODS_DIR, fname)
        mod_name = f"mods.{fname[:-3]}"
        try:
            spec = importlib.util.spec_from_file_location(mod_name, path)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            if hasattr(mod, "register"):
                mod.register(app)
                loaded.append(getattr(mod, "MOD_NAME", fname))
        except Exception as e:
            from logger import log_exception
            log_exception(f"Failed to load mod {fname}: {e}")
    return loaded

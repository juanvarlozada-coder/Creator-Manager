"""
auto_cleanup — Official Creator Manager mod.
After the watcher moves a file, if the source folder is empty,
it is automatically deleted.
File: mods/auto_cleanup.py
"""

MOD_NAME = "Auto Cleanup"
MOD_DESCRIPTION = "Deletes source folders after they become empty"

import os as _os


def register(app):
    app.cfg_app.setdefault("auto_cleanup", True)

    orig_on_move = app._on_movimiento

    def patched_on_move(entrada):
        src_dir = _os.path.dirname(entrada.get("ruta_original", ""))
        if src_dir and _os.path.isdir(src_dir):
            try:
                if not _os.listdir(src_dir):
                    _os.rmdir(src_dir)
            except Exception:
                pass
        orig_on_move(entrada)

    app._on_movimiento = patched_on_move

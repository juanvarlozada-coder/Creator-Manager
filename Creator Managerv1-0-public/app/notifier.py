"""
notifier.py
Unified desktop-notification wrapper.
Uses plyer (must be installed) with a safe fallback if it fails.
"""
from __future__ import annotations

import os

try:
    from plyer import notification as _plyer_notif
    _PLYER_OK = True
except Exception:
    _PLYER_OK = False

APP_NAME = "Creator Manager"
BASE     = os.path.dirname(os.path.abspath(__file__))
SOUND_PATH = os.path.join(BASE, "notification.mp3")

_SOUND_ENABLED = True


def set_sound_enabled(enabled: bool) -> None:
    global _SOUND_ENABLED
    _SOUND_ENABLED = enabled


def _play_sound() -> None:
    if not _SOUND_ENABLED:
        return
    if not os.path.isfile(SOUND_PATH):
        return
    try:
        if os.name == "nt":
            ext = os.path.splitext(SOUND_PATH)[1].lower()
            if ext == ".wav":
                import winsound
                winsound.PlaySound(SOUND_PATH, winsound.SND_ASYNC | winsound.SND_NOWAIT)
            else:
                import ctypes
                alias = "notif_sound"
                winmm = ctypes.windll.winmm
                winmm.mciSendStringW(
                    f'open "{SOUND_PATH}" alias {alias}', None, 0, 0)
                winmm.mciSendStringW(f'play {alias}', None, 0, 0)
    except Exception:
        pass


def notificar(titulo: str, mensaje: str, timeout: int = 8) -> bool:
    """Send a desktop notification.

    Returns True if sent successfully, False on error
    (the event will still be recorded in history.txt).
    """
    _play_sound()
    titulo  = titulo  or APP_NAME
    mensaje = mensaje or ""
    if not _PLYER_OK:
        return False
    try:
        _plyer_notif.notify(
            title    = titulo,
            message  = mensaje,
            app_name = APP_NAME,
            timeout  = timeout,
        )
        return True
    except Exception:
        return False


if __name__ == "__main__":
    ok = notificar("Creator Manager", "Notifications are working correctly.")
    print("Notification sent:", ok)

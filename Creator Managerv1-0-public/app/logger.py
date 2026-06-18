from __future__ import annotations

import os
import traceback
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE, "error_log.txt")

_LOCK = None


def _get_lock():
    global _LOCK
    if _LOCK is None:
        import threading
        _LOCK = threading.Lock()
    return _LOCK


def log_error(message: str, details: str = "") -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if details:
        line = f"[{timestamp}] ERROR: {message}\n  {details}\n"
    else:
        line = f"[{timestamp}] ERROR: {message}\n"
    try:
        with _get_lock():
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception:
        pass


def log_exception(message: str) -> None:
    tb = traceback.format_exc()
    log_error(message, tb)


def clear_log() -> None:
    try:
        open(LOG_PATH, "w", encoding="utf-8").close()
    except Exception:
        pass

"""
app_config.py
User-facing application settings: language, theme, cycle frequency/anchor,
watch interval. Stored in app_config.json, editable from the Settings panel.

Kept separate from config.json (tool rules/limits) so users can reset tool
config without losing their preferences, and vice versa.
"""
from __future__ import annotations

import json
import os

BASE         = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(BASE, "app_config.json")

DEFAULTS = {
    "language":           "en",
    "theme":              "light",
    "cycle_frequency":    "monthly",   # daily | weekly | monthly | yearly
    "cycle_anchor_day":   17,          # monthly: day-of-month; weekly: weekday 0=Mon
                                       # yearly: month 1-12; daily: unused
    "watch_interval_sec": 15,
    "notification_sound": True,
    "auto_start_watch": True,
    "_first_launch_done": False,
}


def cargar_config_app(path: str = DEFAULT_PATH) -> dict:
    """Load user settings, merged over defaults."""
    data = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    merged = dict(DEFAULTS)
    for k, default_v in DEFAULTS.items():
        if k in data and isinstance(data[k], type(default_v)):
            merged[k] = data[k]
    # bool is a subclass of int — guard separately.
    if "_first_launch_done" in data:
        merged["_first_launch_done"] = bool(data["_first_launch_done"])
    return merged


def guardar_config_app(cfg: dict, path: str = DEFAULT_PATH) -> None:
    """Persist user settings."""
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in cfg.items() if k in DEFAULTS})
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


if __name__ == "__main__":
    cfg = cargar_config_app()
    print(cfg)

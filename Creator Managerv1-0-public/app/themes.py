"""
themes.py
Theme loader for Creator Manager.

Themes are stored in themes.json (user-editable). To add a new theme, add a
new object to themes.json with a unique name and the same keys as the built-in
'light' / 'dark' themes.
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import ttk

BASE          = os.path.dirname(os.path.abspath(__file__))
DEFAULT_THEME = "light"
FALLBACK = {
    "bg": "#f0f0f0", "fg": "#1e1e1e", "panel_bg": "#ffffff",
    "accent": "#2e7d32", "accent_fg": "#ffffff",
    "canvas_bg": "#fafafa", "tab_active": "#ffffff",
    "tab_inactive": "#d0d0d0", "tab_hover": "#e0e0e0",
    "video_list_bg": "#ffffff", "gallery_bg": "#fafafa",
    "font": "Segoe UI", "border": "#c0c0c0",
    "warning": "#a06000", "error": "#b00020", "success": "#2e7d32",
}


def _themes_path() -> str:
    return os.path.join(BASE, "themes.json")


def get_themes() -> list:
    """Return a sorted list of available theme names."""
    try:
        with open(_themes_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return sorted([k for k in data.keys() if not k.startswith("_")])
    except Exception:
        return [DEFAULT_THEME]


def load_theme(name: str) -> dict:
    """Return the theme dict for the given name (with fallback values filled)."""
    try:
        with open(_themes_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        theme = data.get(name) or data.get(DEFAULT_THEME) or {}
    except Exception:
        theme = {}
    merged = dict(FALLBACK)
    merged.update({k: v for k, v in theme.items() if not k.startswith("_")})
    return merged


def apply_theme(root: tk.Misc, name: str) -> dict:
    """Apply a theme to the whole Tk root and return the theme dict.

    Configures ttk styles + default widget backgrounds/foregrounds.
    Can be called again at any time to switch themes live.
    """
    theme       = load_theme(name)
    font_family = theme.get("font", "Segoe UI")
    style       = ttk.Style(root)

    for candidate in ("clam", "vista", "xpnative", "default"):
        if candidate in style.theme_names():
            try:
                style.theme_use(candidate)
                break
            except Exception:
                continue

    style.configure(".", background=theme["bg"], foreground=theme["fg"],
                    font=(font_family, 10), bordercolor=theme["border"],
                    lightcolor=theme["border"], darkcolor=theme["border"])
    style.configure("TFrame",        background=theme["bg"])
    style.configure("TLabel",        background=theme["bg"], foreground=theme["fg"])
    style.configure("TLabelframe",   background=theme["bg"], foreground=theme["fg"])
    style.configure("TLabelframe.Label", background=theme["bg"], foreground=theme["fg"])
    style.configure("TButton",       background=theme["panel_bg"],
                    foreground=theme["fg"], bordercolor=theme["border"],
                    focusthickness=1)
    style.map("TButton",
              background=[("active", theme["tab_hover"])],
              foreground=[("active", theme["fg"])])
    style.configure("Accent.TButton", background=theme["accent"],
                    foreground=theme["accent_fg"],
                    font=(font_family, 10, "bold"))
    style.map("Accent.TButton",
              background=[("active", theme["accent"])],
              foreground=[("active", theme["accent_fg"])])
    style.configure("TCombobox",
                    fieldbackground=theme["panel_bg"],
                    background=theme["bg"], foreground=theme["fg"])
    style.map("TCombobox",
              fieldbackground=[("readonly", theme["panel_bg"])],
              selectbackground=[("readonly", theme["accent"])],
              selectforeground=[("readonly", theme["accent_fg"])])
    style.configure("Treeview",
                    background=theme["panel_bg"],
                    foreground=theme["fg"],
                    fieldbackground=theme["panel_bg"],
                    bordercolor=theme["border"], rowheight=22)
    style.map("Treeview",
              background=[("selected", theme["accent"])],
              foreground=[("selected", theme["accent_fg"])])
    style.configure("Treeview.Heading",
                    background=theme["panel_bg"],
                    foreground=theme["fg"],
                    font=(font_family, 10, "bold"))
    style.configure("TNotebook",     background=theme["bg"])
    style.configure("TNotebook.Tab", background=theme["tab_inactive"],
                    foreground=theme["fg"], padding=(12, 6))
    style.map("TNotebook.Tab",
              background=[("selected", theme["tab_active"])],
              foreground=[("selected", theme["fg"])])
    style.configure("TEntry",       fieldbackground=theme["panel_bg"],
                    foreground=theme["fg"], bordercolor=theme["border"])
    style.configure("TScrollbar",   background=theme["panel_bg"],
                    troughcolor=theme["bg"])
    try:
        root.configure(bg=theme["bg"])
    except Exception:
        pass
    return theme


if __name__ == "__main__":
    print("Themes available:", get_themes())
    print("Light sample:", load_theme("light"))

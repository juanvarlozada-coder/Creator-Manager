"""
thumbnail_size — Official Creator Manager mod.
Adds a thumbnail size slider in Settings to adjust image gallery thumbnail size.
File: mods/thumbnail_size.py

To uninstall, delete this file.
"""

MOD_NAME = "Thumbnail Size"
MOD_DESCRIPTION = "Adds a slider in Settings to adjust thumbnail size"

import tkinter as tk
from tkinter import ttk
import os as _os

import i18n
import app_config as cfg_app_mod
import notifier


def register(app):
    app.cfg_app.setdefault("thumbnail_size", 150)

    orig = app._dialogo_settings

    def patched_settings():
        dlg = tk.Toplevel(app.root)
        dlg.title(i18n.t("settings_title"))
        dlg.geometry("480x500")
        dlg.resizable(False, False)
        dlg.transient(app.root)
        dlg.grab_set()

        f = ttk.Frame(dlg, padding=20)
        f.pack(fill="both", expand=True)

        row = 0
        ttk.Label(f, text=i18n.t("language"),
                  font=("Segoe UI", 9, "bold")).grid(
                      row=row, column=0, sticky="w", pady=4)
        lang_var = tk.StringVar(value=app.cfg_app.get("language", "en"))
        lang_cb = ttk.Combobox(f, textvariable=lang_var, state="readonly",
                                values=list(i18n.LANGUAGES.keys()), width=16)
        lang_cb.grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        ttk.Label(f, text=i18n.t("theme"),
                  font=("Segoe UI", 9, "bold")).grid(
                      row=row, column=0, sticky="w", pady=4)
        theme_var = tk.StringVar(value=app.cfg_app.get("theme", "light"))
        ttk.Combobox(f, textvariable=theme_var, state="readonly",
                      values=list(app.temas.keys()), width=16).grid(
                          row=row, column=1, sticky="w", pady=4)
        row += 1

        ttk.Label(f, text=i18n.t("cycle_frequency"),
                  font=("Segoe UI", 9, "bold")).grid(
                      row=row, column=0, sticky="w", pady=4)
        freq_var = tk.StringVar(value=app.cfg_app.get("cycle_frequency", "monthly"))
        freq_map = {
            i18n.t("freq_daily"): "daily",
            i18n.t("freq_weekly"): "weekly",
            i18n.t("freq_monthly"): "monthly",
            i18n.t("freq_yearly"): "yearly",
        }
        freq_cb = ttk.Combobox(f, textvariable=freq_var, state="readonly",
                                values=list(freq_map.keys()), width=16)
        freq_cb.grid(row=row, column=1, sticky="w", pady=4)
        row += 1

        ttk.Label(f, text=i18n.t("cycle_anchor"),
                  font=("Segoe UI", 9, "bold")).grid(
                      row=row, column=0, sticky="w", pady=4)
        anchor_var = tk.StringVar(value=str(app.cfg_app.get("cycle_anchor", 17)))
        ttk.Spinbox(f, from_=1, to=28, textvariable=anchor_var, width=5).grid(
            row=row, column=1, sticky="w", pady=4)
        row += 1

        ttk.Label(f, text=i18n.t("watch_interval"),
                  font=("Segoe UI", 9, "bold")).grid(
                      row=row, column=0, sticky="w", pady=4)
        interval_var = tk.StringVar(
            value=str(app.cfg_app.get("watch_interval_sec", 15)))
        ttk.Spinbox(f, from_=2, to=300, textvariable=interval_var, width=5).grid(
            row=row, column=1, sticky="w", pady=4)
        row += 1

        sound_var = tk.BooleanVar(value=app.cfg_app.get("notification_sound", True))
        ttk.Checkbutton(f, text=i18n.t("notification_sound"),
                        variable=sound_var).grid(
                            row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1

        auto_var = tk.BooleanVar(value=app.cfg_app.get("auto_start_watch", True))
        ttk.Checkbutton(f, text=i18n.t("auto_start_watch"),
                        variable=auto_var).grid(
                            row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1

        # Thumbnail size slider (added by this mod)
        ttk.Separator(f, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=8)
        row += 1
        ttk.Label(f, text="Thumbnail Size:",
                  font=("Segoe UI", 9, "bold")).grid(
                      row=row, column=0, sticky="w", pady=4)
        ts_var = tk.IntVar(value=int(app.cfg_app.get("thumbnail_size", 150)))
        ts_scale = ttk.Scale(f, from_=50, to=400, variable=ts_var,
                             orient="horizontal", length=200)
        ts_scale.grid(row=row, column=1, sticky="w", pady=4)
        ts_lbl = ttk.Label(f, textvariable=ts_var)
        ts_lbl.grid(row=row, column=1, sticky="e", padx=(220, 0), pady=4)
        row += 1

        def do_save():
            app.cfg_app["language"] = lang_var.get()
            app.cfg_app["theme"] = theme_var.get()
            app.cfg_app["cycle_frequency"] = freq_map.get(freq_var.get(), "monthly")
            app.cfg_app["cycle_anchor"] = int(anchor_var.get())
            app.cfg_app["watch_interval_sec"] = int(interval_var.get())
            app.cfg_app["notification_sound"] = sound_var.get()
            app.cfg_app["auto_start_watch"] = auto_var.get()
            app.cfg_app["thumbnail_size"] = ts_var.get()
            i18n.set_language(app.cfg_app["language"])
            notifier.set_sound_enabled(app.cfg_app["notification_sound"])
            base = _os.path.dirname(_os.path.abspath(__file__))
            cfg_app_mod.guardar_config_app(
                app.cfg_app,
                _os.path.join(base, "..", "app_config.json"))
            app._tema_actual = app.cfg_app.get("theme", "light")
            app._tema = app.temas.get(app._tema_actual, {})
            app._apply_style()
            app._refrescar_idioma()
            app._refrescar_todo()
            dlg.destroy()

        bf = ttk.Frame(f)
        bf.grid(row=row, column=0, columnspan=2, pady=(16, 0))
        ttk.Button(bf, text=f"✓  {i18n.t('save')}",
                   command=do_save).pack(side="left", padx=4)
        ttk.Button(bf, text=i18n.t("cancel"),
                   command=dlg.destroy).pack(side="left", padx=4)

        dlg.wait_window()

    app._dialogo_settings = patched_settings

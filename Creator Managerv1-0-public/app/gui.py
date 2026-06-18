"""
gui.py
Creator Manager v1.0 Beta — Main GUI (tkinter).

Tabs:
  - One tab per profile (dynamic).  Each has: image gallery (clickable
    thumbnails) + video list (names only; double-click opens) + cycle selector.
  - Credits & Generations — counters table + pending TensorArt confirmations.
  - History — viewer for history.txt.
  - Settings — language, theme, cycle frequency/anchor, watch interval.

Profile data lives in profiles.json (separate from config.json so the tool
can be published without personal data).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from PIL import Image, ImageTk

import state
import i18n
import app_config as cfg_app_mod
import logger
from watcher import Vigilante
from notifier import notificar
import notifier

BASE             = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH      = os.path.join(BASE, "config.json")
PROFILES_PATH    = os.path.join(BASE, "profiles.json")
STATE_PATH       = os.path.join(BASE, "state.json")
HISTORY_PATH     = os.path.join(BASE, "history.txt")
THEMES_PATH      = os.path.join(BASE, "themes.json")
CONFIG_APP_PATH  = os.path.join(BASE, "app_config.json")
CHANGELOG_BASE   = os.path.join(BASE, "changelog")
LOGO_PATH        = os.path.join(BASE, "creator-manager-logo.png")

MAX_THUMBS = 150


# ─────────────────────────────────────────────
#  Thumbnail helpers
# ─────────────────────────────────────────────

def cargar_miniatura(ruta: str, tam=(150, 150)):
    try:
        im = Image.open(ruta)
        im.thumbnail(tam, Image.LANCZOS)
        return ImageTk.PhotoImage(im)
    except Exception:
        return None


# ─────────────────────────────────────────────
#  profiles.json helpers
# ─────────────────────────────────────────────

def cargar_profiles_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def guardar_profiles_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
#  Theme loading
# ─────────────────────────────────────────────

def cargar_temas(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        return {}


# ─────────────────────────────────────────────
#  First-launch language dialog
# ─────────────────────────────────────────────

def _first_launch_dialog(root: tk.Tk, cfg_app: dict) -> None:
    """Show a blocking language-choice dialog on first run."""
    dlg = tk.Toplevel(root)
    dlg.title("Welcome / Bienvenido / 欢迎")
    dlg.geometry("400x220")
    dlg.resizable(False, False)
    dlg.transient(root)
    dlg.grab_set()
    dlg.protocol("WM_DELETE_WINDOW", lambda: None)  # force a choice

    tk.Label(dlg,
             text="Welcome to Creator Manager\nSelect your language:",
             font=("Segoe UI", 13, "bold"), justify="center"
             ).pack(pady=(24, 12))

    langs      = i18n.get_available_languages()
    lang_codes = list(langs.keys())
    lang_names = [langs[c] for c in lang_codes]

    var = tk.StringVar()
    cb  = ttk.Combobox(dlg, textvariable=var, values=lang_names,
                       state="readonly", width=26)
    cb.pack(pady=6)
    if lang_codes:
        cb.current(0)

    def ok():
        idx  = cb.current()
        code = lang_codes[idx] if idx >= 0 else "en"
        i18n.set_language(code)
        cfg_app["language"]         = code
        cfg_app["_first_launch_done"] = True
        cfg_app_mod.guardar_config_app(cfg_app, CONFIG_APP_PATH)
        dlg.destroy()

    ttk.Button(dlg, text="Continue / Continuar / 继续",
               command=ok).pack(pady=16)
    dlg.wait_window()


# ─────────────────────────────────────────────
#  Application
# ─────────────────────────────────────────────

class App:
    def __init__(self, root: tk.Tk):
        self.root = root

        # ── Config & state ────────────────────────────────────────────
        self.config  = state.cargar_config(CONFIG_PATH)
        self.cfg_app = cfg_app_mod.cargar_config_app(CONFIG_APP_PATH)

        # First-launch: ask language if not yet chosen.
        if not self.cfg_app.get("_first_launch_done"):
            _first_launch_dialog(root, self.cfg_app)

        i18n.set_language(self.cfg_app.get("language", "en"))
        notifier.set_sound_enabled(self.cfg_app.get("notification_sound", True))

        self.profiles_disk = cargar_profiles_json(PROFILES_PATH)
        self.config["perfiles"] = dict(self.profiles_disk)

        self.state_data = state.cargar_estado(STATE_PATH, self.config, self.cfg_app)
        self.state_data, _ = state.aplicar_rotaciones(
            self.state_data, self.config, self.cfg_app)
        state.guardar_estado(STATE_PATH, self.state_data)

        # ── Theme ─────────────────────────────────────────────────────
        self.temas        = cargar_temas(THEMES_PATH)
        self._tema_actual = self.cfg_app.get("theme", "light")
        self._tema        = self.temas.get(self._tema_actual, {})

        # ── Per-profile data structures ────────────────────────────────
        self._thumbs:          list = []
        self._galeria_frames:  dict = {}   # perfil → {canvas, frame}
        self._listas_videos:   dict = {}   # perfil → Treeview
        self._ciclo_vars:      dict = {}   # perfil → tk.StringVar
        self._pestanas_perfil: dict = {}   # perfil → ttk.Frame

        # ── Watcher ───────────────────────────────────────────────────
        self.vigilante = Vigilante(
            callback_movimiento=lambda e: self.root.after(
                0, lambda ev=e: self._on_movimiento(ev)),
            callback_error=lambda msg: self.root.after(
                0, lambda m=msg: self._on_error(m)),
            config_app_data=self.cfg_app,
        )

        # ── Build UI ──────────────────────────────────────────────────
        self._apply_style()
        self._build_ui()
        self._construir_pestanas_perfiles()
        self._refrescar_creditos()
        self._refrescar_historial()
        self._auto_refresco()

        # ── Auto-start watching ─────────────────────────────────────────
        if self.cfg_app.get("auto_start_watch", True) and self.config.get("perfiles"):
            self.root.after(500, self._toggle_vigilancia)

        # ── Auto-refresh on tab switch ──────────────────────────────────
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # ── Load mods ──────────────────────────────────────────────────
        self._mods_cargados = []
        try:
            from mods import cargar_mods
            self._mods_cargados = cargar_mods(self)
        except Exception as e:
            logger.log_exception(f"Mod loader: {e}")

    # ================================================================
    #  STYLE / THEME
    # ================================================================

    def _apply_style(self):
        t       = self._tema
        bg      = t.get("bg",           "#f0f0f0")
        fg      = t.get("fg",           "#1e1e1e")
        panel   = t.get("panel_bg",     bg)
        accent  = t.get("accent",       "#2e7d32")
        acc_fg  = t.get("accent_fg",    "#ffffff")
        font    = t.get("font",         "Segoe UI")
        border  = t.get("border",       "#c0c0c0")

        self.root.configure(bg=bg)
        st = ttk.Style(self.root)
        for candidate in ("clam", "vista", "xpnative", "default"):
            if candidate in st.theme_names():
                try:
                    st.theme_use(candidate)
                    break
                except Exception:
                    continue

        st.configure(".", background=bg, foreground=fg,
                     fieldbackground=panel, font=(font, 9),
                     bordercolor=border, lightcolor=border, darkcolor=border)
        st.configure("TFrame",            background=bg)
        st.configure("TLabel",            background=bg, foreground=fg)
        st.configure("TLabelframe",       background=bg, foreground=fg)
        st.configure("TLabelframe.Label", background=bg, foreground=fg)
        st.configure("TButton",           background=panel, foreground=fg,
                     bordercolor=border)
        st.map("TButton",
               background=[("active", t.get("tab_hover", "#e0e0e0"))])
        st.configure("Accent.TButton",    background=accent, foreground=acc_fg,
                     font=(font, 10, "bold"))
        st.map("Accent.TButton",
               background=[("active", accent)], foreground=[("active", acc_fg)])
        st.configure("TCombobox",         fieldbackground=panel,
                     foreground=fg, background=panel)
        st.configure("Treeview",          background=panel, foreground=fg,
                     fieldbackground=panel, rowheight=22)
        st.configure("Treeview.Heading",  background=bg, foreground=fg)
        st.map("Treeview",
               background=[("selected", accent)],
               foreground=[("selected", acc_fg)])
        st.configure("TNotebook",         background=bg)
        st.configure("TNotebook.Tab",     background=t.get("tab_inactive", "#d0d0d0"),
                     foreground=fg, padding=(10, 5))
        st.map("TNotebook.Tab",
               background=[("selected", t.get("tab_active", panel)),
                            ("active",  t.get("tab_hover",  panel))],
               foreground=[("selected", fg)])
        st.configure("TEntry",            fieldbackground=panel,
                     foreground=fg, bordercolor=border)
        st.configure("TScrollbar",        background=panel,
                     troughcolor=bg)
        st.configure("TCheckbutton",      background=bg, foreground=fg)
        st.map("TCheckbutton",
               background=[("active", bg)],
               foreground=[("active", fg)],
               indicatorcolor=[("selected", accent), ("!selected", border)])

    # ================================================================
    #  BUILD MAIN UI
    # ================================================================

    def _build_ui(self):
        t      = self._tema
        bg     = t.get("bg", "#f0f0f0")
        acc    = t.get("accent", "#2e7d32")
        acc_fg = t.get("accent_fg", "#ffffff")

        self.root.title(f"{i18n.t('app_title')} {i18n.t('version')}")
        self.root.geometry("1200x780")
        self.root.minsize(900, 580)

        # ── Window icon ─────────────────────────────────────────────────
        self._logo_img = None
        if os.path.isfile(LOGO_PATH):
            try:
                img = Image.open(LOGO_PATH)
                self._logo_img = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self._logo_img)
            except Exception:
                pass

        # ── Top bar ───────────────────────────────────────────────────
        top = ttk.Frame(self.root, padding=(8, 6))
        top.pack(fill="x")

        self.btn_vigilar = ttk.Button(
            top, text=f"▶  {i18n.t('start_watch')}",
            command=self._toggle_vigilancia)
        self.btn_vigilar.pack(side="left")

        self.lbl_vigila = tk.Label(
            top, text=f"○ {i18n.t('paused')}",
            fg=t.get("error", "#b00020"), bg=bg, font=("Segoe UI", 9))
        self.lbl_vigila.pack(side="left", padx=(10, 0))

        self.btn_refresh = ttk.Button(top, text=f"↻  {i18n.t('refresh_all')}",
                   command=self._refrescar_todo)
        self.btn_refresh.pack(side="left", padx=10)

        self.btn_changelog = ttk.Button(top, text=f"📋  {i18n.t('changelog')}",
                   command=self._mostrar_changelog)
        self.btn_changelog.pack(side="left", padx=4)

        self.btn_settings = ttk.Button(top, text=f"⚙  {i18n.t('settings')}",
                   command=self._dialogo_settings)
        self.btn_settings.pack(side="left", padx=4)

        # Delete All Data (red accent)
        self.btn_reset = tk.Button(
            top, text=f"🗑️  {i18n.t('reset_all_data')}",
            font=("Segoe UI", 9),
            bg=t.get("error", "#b00020"), fg="#ffffff",
            activebackground=t.get("error", "#b00020"),
            activeforeground="#ffffff", relief="raised", bd=2,
            padx=10, pady=2, cursor="hand2",
            command=self._reset_all_data)
        self.btn_reset.pack(side="left", padx=4)

        # Add Profile (green accent)
        self.btn_add = tk.Button(
            top, text=f"＋  {i18n.t('add_profile')}",
            font=("Segoe UI", 10, "bold"),
            bg=acc, fg=acc_fg, activebackground=acc,
            activeforeground=acc_fg, relief="raised", bd=2,
            padx=14, pady=4, cursor="hand2",
            command=self._dialogo_anadir_perfil)
        self.btn_add.pack(side="right", padx=4)

        self.btn_open_folder = ttk.Button(top, text=f"📂  {i18n.t('open_program_folder')}",
                   command=lambda: self._abrir_explorer(
                       self.config["base_dir"]))
        self.btn_open_folder.pack(side="right", padx=4)

        # ── Main Notebook ─────────────────────────────────────────────
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=8, pady=4)

        # Fixed tabs (Credits, History) — created once, re-added after profiles.
        self.tab_creditos  = ttk.Frame(self.nb)
        self.tab_historial = ttk.Frame(self.nb)
        self._build_tab_creditos()
        self._build_tab_historial()

        # ── Status bar ────────────────────────────────────────────────
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", side="bottom")
        barra = ttk.Frame(self.root, padding=(8, 3))
        barra.pack(fill="x", side="bottom")
        self.lbl_barra = ttk.Label(
            barra,
            text=(f"{i18n.t('cycle')} "
                  f"{state.ciclo_actual(self.config, self.cfg_app)}"
                  f"   ·   {i18n.t('today')}: {state.hoy_str()}"))
        self.lbl_barra.pack(side="left")

        self.root.protocol("WM_DELETE_WINDOW", self._cerrar)

    # ── Credits tab ────────────────────────────────────────────────────
    def _build_tab_creditos(self):
        t = self._tema
        top = ttk.Frame(self.tab_creditos)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Button(top, text=f"↻ {i18n.t('credits_refresh')}",
                   command=self._refrescar_creditos).pack(side="left")
        ttk.Button(top, text=f"⟲ {i18n.t('reset_cycle')}",
                   command=self._reiniciar_ciclo).pack(side="left", padx=8)
        ttk.Button(top, text=f"🗑️  {i18n.t('remove_profile_title')}",
                   command=self._dialogo_eliminar_perfil).pack(side="right")

        cont = ttk.Frame(self.tab_creditos)
        cont.pack(fill="both", expand=True, padx=8, pady=4)

        self._cols_fijas = ["perfil", "chatgpt", "gemini", "ta", "kling", "higgs"]
        self._cols_fijas_cfg = [
            ("perfil",  "profile_col", 150),
            ("chatgpt", "chatgpt_col", 160),
            ("gemini",  "gemini_col",  160),
            ("ta",      "ta_col",      180),
            ("kling",   "kling_col",   140),
            ("higgs",   "higgs_col",   160),
        ]
        self.tree_creditos = ttk.Treeview(
            cont, columns=list(self._cols_fijas), show="headings", height=8)
        for c, key, w in self._cols_fijas_cfg:
            self.tree_creditos.heading(c, text=i18n.t(key))
            self.tree_creditos.column(c, width=w, anchor="center")
        self.tree_creditos.column("perfil", anchor="w")
        self.tree_creditos.pack(fill="x")
        self.tree_creditos.tag_configure(
            "excedido", foreground=t.get("error", "#b00020"))
        self.tree_creditos.tag_configure(
            "warn",     foreground=t.get("warning", "#a06000"))
        # Right-click context menu for per-profile reset
        self._ctx_menu = tk.Menu(self.root, tearoff=0)
        self.tree_creditos.bind("<Button-3>", self._mostrar_ctx_menu)

    # ── History tab ───────────────────────────────────────────────────
    def _build_tab_historial(self):
        t         = self._tema
        canvas_bg = t.get("canvas_bg", "#1e1e1e")
        fg        = t.get("fg",        "#d4d4d4")

        top = ttk.Frame(self.tab_historial)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Button(top, text=f"↻ {i18n.t('credits_refresh')}",
                   command=self._refrescar_historial).pack(side="left")
        ttk.Button(top, text=f"📂 {i18n.t('history_open_file')}",
                   command=lambda: self._abrir_archivo(HISTORY_PATH)
                   ).pack(side="left", padx=8)
        ttk.Button(top, text=f"🧹 {i18n.t('history_clear')}",
                   command=self._vaciar_historial).pack(side="left")

        txt = tk.Text(self.tab_historial, wrap="none",
                      bg=canvas_bg, fg=fg,
                      insertbackground=fg, font=("Consolas", 10))
        sb  = ttk.Scrollbar(self.tab_historial, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)
        self.txt_historial = txt

    # ================================================================
    #  PROFILE TABS  (dynamic)
    # ================================================================

    def _construir_pestanas_perfiles(self):
        """Rebuild all profile tabs from scratch."""
        # Save current tab text before rebuilding
        tab_ids = self.nb.tabs()
        cur_text = None
        if tab_ids:
            try:
                cur_text = self.nb.tab(self.nb.select(), "text")
            except Exception:
                pass

        self._thumbs.clear()
        self._galeria_frames.clear()
        self._listas_videos.clear()
        self._ciclo_vars.clear()
        self._pestanas_perfil.clear()

        for tab_id in self.nb.tabs():
            self.nb.forget(tab_id)

        perfiles = list(self.config.get("perfiles", {}).keys())

        if not perfiles:
            tab_bien = ttk.Frame(self.nb)
            self.nb.add(tab_bien,
                        text=f"👤  {i18n.t('welcome_title')}")
            self._pestanas_perfil["_bienvenida"] = tab_bien
            inner = ttk.Frame(tab_bien)
            inner.place(relx=0.5, rely=0.5, anchor="center")
            ttk.Label(inner, text=i18n.t("welcome_no_profiles"),
                      font=("Segoe UI", 14), justify="center",
                      foreground="#555").pack(pady=20)
            t      = self._tema
            acc    = t.get("accent",     "#2e7d32")
            acc_fg = t.get("accent_fg",  "#ffffff")
            tk.Button(inner, text=f"＋  {i18n.t('add_profile')}",
                      font=("Segoe UI", 16, "bold"),
                      bg=acc, fg=acc_fg, activebackground=acc,
                      activeforeground=acc_fg, padx=30, pady=16,
                      cursor="hand2",
                      command=self._dialogo_anadir_perfil).pack(pady=10)
        else:
            for perfil in perfiles:
                tab = ttk.Frame(self.nb)
                self.nb.add(tab, text=f"👤  {perfil}")
                self._pestanas_perfil[perfil] = tab
                self._build_contenido_perfil(tab, perfil)

        # Fixed tabs always at the end.
        self.nb.add(self.tab_creditos,
                    text=f"🎟️  {i18n.t('credits_tab')}")
        self.nb.add(self.tab_historial,
                    text=f"📜  {i18n.t('history_tab')}")

        # Restore previously selected tab
        if cur_text:
            for tab_id in self.nb.tabs():
                try:
                    if self.nb.tab(tab_id, "text") == cur_text:
                        self.nb.select(tab_id)
                        break
                except Exception:
                    pass

    def _build_contenido_perfil(self, parent: ttk.Frame, perfil: str):
        """Build the interior of one profile tab."""
        t           = self._tema
        gallery_bg  = t.get("gallery_bg", "#252526")
        fg          = t.get("fg",          "#d4d4d4")

        # ── Top bar: cycle selector ────────────────────────────────────
        bar = ttk.Frame(parent, padding=(6, 4))
        bar.pack(fill="x")

        perfiles_dir = self.config["perfiles_dir"]
        perfil_dir   = os.path.join(perfiles_dir, perfil)
        ciclos       = []
        if os.path.isdir(perfil_dir):
            ciclos = sorted(
                [d for d in os.listdir(perfil_dir)
                 if os.path.isdir(os.path.join(perfil_dir, d))],
                reverse=True)

        ciclo_actual_val = state.ciclo_actual(self.config, self.cfg_app)
        default_ciclo    = ciclos[0] if ciclos else ciclo_actual_val

        ciclo_var = tk.StringVar(value=default_ciclo)
        self._ciclo_vars[perfil] = ciclo_var   # ← per-profile StringVar

        ttk.Label(bar, text=i18n.t("cycle"),
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        cb_ciclo = ttk.Combobox(bar, textvariable=ciclo_var,
                                values=ciclos, width=11, state="readonly")
        cb_ciclo.pack(side="left")
        cb_ciclo.bind("<<ComboboxSelected>>",
                      lambda e, p=perfil: self._mostrar_perfil(p))

        ttk.Button(bar, text=f"↻ {i18n.t('credits_refresh')}",
                   command=lambda p=perfil: self._mostrar_perfil(p)
                   ).pack(side="left", padx=8)
        ttk.Button(bar, text=f"📂 {i18n.t('open_folder')}",
                   command=lambda p=perfil: self._abrir_explorer(
                       os.path.join(perfiles_dir, p,
                                    self._ciclo_vars[p].get()))
                   ).pack(side="left", padx=4)
        ttk.Button(bar, text="🗑️",
                   command=lambda p=perfil: self._dialogo_eliminar_perfil(p)
                   ).pack(side="right", padx=4)

        # ── Paned: images (left) + videos (right) ─────────────────────
        paned = ttk.Panedwindow(parent, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=4, pady=4)

        # IMAGES ───────────────────────────────────────────────────────
        frame_img = ttk.LabelFrame(paned,
                                   text=f"  🖼️  {i18n.t('images')}  ",
                                   padding=4)
        paned.add(frame_img, weight=3)

        cont_img   = ttk.Frame(frame_img)
        cont_img.pack(fill="both", expand=True)
        canvas_img = tk.Canvas(cont_img, bg=gallery_bg, highlightthickness=0)
        scroll_img = ttk.Scrollbar(cont_img, orient="vertical",
                                   command=canvas_img.yview)
        galeria    = tk.Frame(canvas_img, bg=gallery_bg)
        galeria.bind("<Configure>",
                     lambda e, c=canvas_img: c.configure(
                         scrollregion=c.bbox("all")))
        canvas_img.create_window((0, 0), window=galeria, anchor="nw")
        canvas_img.configure(yscrollcommand=scroll_img.set)
        canvas_img.pack(side="left", fill="both", expand=True)
        scroll_img.pack(side="right", fill="y")

        def _scroll(event, c=canvas_img):
            bbox = c.bbox("all")
            if not bbox:
                return
            if bbox[3] - bbox[1] <= c.winfo_height():
                return
            c.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas_img.bind("<MouseWheel>", _scroll)
        galeria.bind("<MouseWheel>", _scroll)

        # Store per-profile reference (not reset each iteration).
        self._galeria_frames[perfil] = {"canvas": canvas_img, "frame": galeria}

        # VIDEOS ───────────────────────────────────────────────────────
        frame_vid = ttk.LabelFrame(paned,
                                   text=f"  🎬  {i18n.t('videos')}  ",
                                   padding=4)
        paned.add(frame_vid, weight=1)

        tree_vid = ttk.Treeview(frame_vid, columns=("nombre",),
                                show="headings", height=15, selectmode="browse")
        tree_vid.heading("nombre", text=i18n.t("videos"))
        tree_vid.column("nombre", width=280, anchor="w")
        sb_vid   = ttk.Scrollbar(frame_vid, orient="vertical",
                                 command=tree_vid.yview)
        tree_vid.configure(yscrollcommand=sb_vid.set)
        tree_vid.pack(side="left", fill="both", expand=True)
        sb_vid.pack(side="right", fill="y")
        tree_vid.bind("<Double-1>", self._abrir_video_seleccionado)
        tree_vid.bind("<Button-3>",
                      lambda e, p=perfil: self._menu_video(e, p))

        self._listas_videos[perfil] = tree_vid   # ← per-profile reference

        self.root.after(120, lambda p=perfil: self._mostrar_perfil(p))

    def _mostrar_perfil(self, perfil: str):
        """Load images and videos for the selected cycle into the tab."""
        ciclo_var = self._ciclo_vars.get(perfil)
        if ciclo_var is None:
            return
        ciclo        = ciclo_var.get()
        perfiles_dir = self.config["perfiles_dir"]
        base_dir     = os.path.join(perfiles_dir, perfil, ciclo)

        exts_img = [e.lower() for e in self.config.get("extensiones_imagen", [])]
        exts_vid = [e.lower() for e in self.config.get("extensiones_video", [])]
        t         = self._tema
        gallery_bg = t.get("gallery_bg", "#252526")
        fg         = t.get("fg",         "#d4d4d4")

        # ── Images ─────────────────────────────────────────────────────
        info_gal = self._galeria_frames.get(perfil)
        if info_gal:
            frame  = info_gal["frame"]
            canvas = info_gal["canvas"]
            for w in frame.winfo_children():
                w.destroy()
            self._thumbs.clear()

            # Try 'images' subfolder first, fall back to 'imagenes'.
            img_dir = os.path.join(base_dir, "images")
            if not os.path.isdir(img_dir):
                img_dir = os.path.join(base_dir, "imagenes")

            archivos_img = []
            if os.path.isdir(img_dir):
                archivos_img = sorted(
                    [f for f in os.listdir(img_dir)
                     if os.path.splitext(f)[1].lower() in exts_img]
                )[:MAX_THUMBS]

            cols = 4
            for i, nombre in enumerate(archivos_img):
                ruta  = os.path.join(img_dir, nombre)
                thumb = cargar_miniatura(
                    ruta, tam=(self.cfg_app.get("thumbnail_size", 150),)*2)
                cell  = tk.Frame(frame, bg=gallery_bg, padx=3, pady=3)
                cell.grid(row=i // cols, column=i % cols,
                          sticky="nsew", padx=3, pady=3)
                if thumb is None:
                    lbl = tk.Label(cell, text="[?]", bg=gallery_bg, fg="#888",
                                   font=("Segoe UI", 20), width=10, height=6)
                    lbl.pack()
                else:
                    self._thumbs.append(thumb)
                    lbl = tk.Label(cell, image=thumb, bg=gallery_bg,
                                   cursor="hand2")
                    lbl.pack()
                    lbl.bind("<Double-Button-1>",
                             lambda e, r=ruta: self._abrir_archivo(r))
                lbl.bind("<Button-3>",
                         lambda e, r=ruta: self._menu_archivo(e, r))
                corte = nombre if len(nombre) <= 22 else nombre[:19] + "..."
                tk.Label(cell, text=corte, wraplength=140, justify="center",
                         font=("Segoe UI", 8), bg=gallery_bg,
                         fg=fg).pack(fill="x")

            for c in range(cols):
                frame.columnconfigure(c, weight=1)
            canvas.configure(scrollregion=canvas.bbox("all"))

        # ── Videos ─────────────────────────────────────────────────────
        tree_vid = self._listas_videos.get(perfil)
        if tree_vid:
            for iid in tree_vid.get_children():
                tree_vid.delete(iid)
            # Try 'videos' subfolder directly.
            vid_dir = os.path.join(base_dir, "videos")
            if os.path.isdir(vid_dir):
                archivos_vid = sorted(
                    [f for f in os.listdir(vid_dir)
                     if os.path.splitext(f)[1].lower() in exts_vid])
                for nombre in archivos_vid:
                    tree_vid.insert("", "end", values=(nombre,))
            if not tree_vid.get_children():
                tree_vid.insert("", "end", values=(i18n.t("no_videos"),))

    # ── File context menus ──────────────────────────────────────────
    def _menu_archivo(self, event, ruta):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=f"📂 {i18n.t('open_file')}",
                         command=lambda: self._abrir_archivo(ruta))
        menu.add_separator()
        menu.add_command(label=f"✏  {i18n.t('rename')}",
                         command=lambda: self._renombrar_archivo(ruta))
        menu.add_command(label=f"📋 {i18n.t('duplicate')}",
                         command=lambda: self._duplicar_archivo(ruta))
        menu.add_command(label=f"🗑️  {i18n.t('delete')}",
                         command=lambda: self._eliminar_archivo(ruta))
        menu.tk_popup(event.x_root, event.y_root)

    def _menu_video(self, event, perfil):
        tree_vid = self._listas_videos.get(perfil)
        if not tree_vid:
            return
        sel = tree_vid.selection()
        if not sel:
            return
        nombre = tree_vid.item(sel[0], "values")[0]
        base_dir = self.config.get("perfiles", {}).get(perfil, "")
        if isinstance(base_dir, list):
            base_dir = base_dir[0] if base_dir else ""
        vid_dir = os.path.join(base_dir, "videos")
        ruta = os.path.join(vid_dir, nombre)
        if os.path.isfile(ruta):
            self._menu_archivo(event, ruta)

    def _eliminar_archivo(self, ruta):
        if not messagebox.askyesno(i18n.t("delete_title"),
                                   i18n.t("confirm_delete", name=os.path.basename(ruta))):
            return
        try:
            os.remove(ruta)
            self._refrescar_todo()
        except Exception as e:
            messagebox.showerror(i18n.t("error"), str(e))

    def _duplicar_archivo(self, ruta):
        base, ext = os.path.splitext(ruta)
        nueva = f"{base} - {i18n.t('copy_suffix')}{ext}"
        i = 1
        while os.path.exists(nueva):
            nueva = f"{base} - {i18n.t('copy_suffix')} ({i}){ext}"
            i += 1
        try:
            shutil.copy2(ruta, nueva)
            self._refrescar_todo()
        except Exception as e:
            messagebox.showerror(i18n.t("error"), str(e))

    def _renombrar_archivo(self, ruta):
        old_name = os.path.basename(ruta)
        dlg = tk.Toplevel(self.root)
        dlg.title(i18n.t("rename_title"))
        dlg.geometry("360x120")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        f = ttk.Frame(dlg, padding=16)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=i18n.t("rename_prompt")).pack(anchor="w")
        var = tk.StringVar(value=old_name)
        ttk.Entry(f, textvariable=var, width=40).pack(fill="x", pady=8)
        def confirmar():
            new_name = var.get().strip()
            if not new_name:
                return
            dst = os.path.join(os.path.dirname(ruta), new_name)
            if dst != ruta and os.path.exists(dst):
                messagebox.showwarning(i18n.t("rename_title"),
                                       i18n.t("rename_exists"), parent=dlg)
                return
            try:
                os.rename(ruta, dst)
            except Exception as e:
                messagebox.showerror(i18n.t("error"), str(e), parent=dlg)
                return
            dlg.destroy()
            self._refrescar_todo()
        bf = ttk.Frame(f)
        bf.pack(fill="x", pady=(8, 0))
        ttk.Button(bf, text=f"✓  {i18n.t('save')}",
                   command=confirmar).pack(side="left", padx=4)
        ttk.Button(bf, text=i18n.t("cancel"),
                   command=dlg.destroy).pack(side="left", padx=4)
        dlg.wait_window()

    def _abrir_video_seleccionado(self, evt=None):
        if evt is None:
            return
        tree_vid    = None
        perfil_sel  = None
        for p, tv in self._listas_videos.items():
            if str(tv) == str(evt.widget):
                tree_vid   = tv
                perfil_sel = p
                break
        if not tree_vid or not perfil_sel:
            return
        sel = tree_vid.selection()
        if not sel:
            return
        nombre = tree_vid.item(sel[0], "values")[0]
        if nombre.startswith("("):
            return
        ciclo = self._ciclo_vars[perfil_sel].get()
        ruta  = os.path.join(self.config["perfiles_dir"],
                             perfil_sel, ciclo, "videos", nombre)
        self._abrir_archivo(ruta)

    # ================================================================
    #  CHANGELOG VIEWER
    # ================================================================

    def _mostrar_changelog(self):
        t          = self._tema
        canvas_bg  = t.get("canvas_bg", "#1e1e1e")
        fg         = t.get("fg",        "#d4d4d4")
        bg         = t.get("bg",        "#f0f0f0")

        lang = i18n.get_language()
        changelog_path = f"{CHANGELOG_BASE}_{lang}.txt"
        if not os.path.isfile(changelog_path):
            changelog_path = f"{CHANGELOG_BASE}_en.txt"
        if not os.path.isfile(changelog_path):
            changelog_path = f"{CHANGELOG_BASE}.txt"

        dlg = tk.Toplevel(self.root)
        dlg.title(i18n.t("changelog"))
        dlg.geometry("700x520")
        dlg.transient(self.root)
        dlg.configure(bg=bg)

        top = ttk.Frame(dlg, padding=(8, 6))
        top.pack(fill="x")
        ttk.Label(top, text=i18n.t("changelog"),
                  font=("Segoe UI", 13, "bold")).pack(side="left")
        ttk.Button(top, text=f"📂 {i18n.t('open_folder')}",
                   command=lambda: self._abrir_archivo(changelog_path)
                   ).pack(side="right")

        txt = tk.Text(dlg, wrap="word", bg=canvas_bg, fg=fg,
                      insertbackground=fg, font=("Consolas", 10),
                      padx=10, pady=8)
        sb  = ttk.Scrollbar(dlg, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        try:
            with open(changelog_path, "r", encoding="utf-8") as f:
                contenido = f.read()
        except Exception:
            contenido = "(changelog not found)"

        txt.insert("end", contenido)
        txt.configure(state="disabled")

    # ================================================================
    #  ADD / REMOVE PROFILES
    # ================================================================

    def _dialogo_anadir_perfil(self):
        t      = self._tema
        acc    = t.get("accent",    "#2e7d32")
        acc_fg = t.get("accent_fg", "#ffffff")

        dlg = tk.Toplevel(self.root)
        dlg.title(i18n.t("add_profile_title"))
        dlg.geometry("520x340")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(dlg, text=i18n.t("profile_name"),
                  font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=16, pady=(16, 4))
        var_nombre = tk.StringVar()
        entry = ttk.Entry(dlg, textvariable=var_nombre, font=("Segoe UI", 11))
        entry.pack(fill="x", padx=16)
        entry.focus_set()

        ttk.Label(dlg, text=i18n.t("watch_folders"),
                  font=("Segoe UI", 11, "bold")).pack(
            anchor="w", padx=16, pady=(12, 4))

        frame_lista = ttk.Frame(dlg)
        frame_lista.pack(fill="both", expand=True, padx=16)
        listbox = tk.Listbox(frame_lista, font=("Segoe UI", 9), height=4)
        sb_l    = ttk.Scrollbar(frame_lista, orient="vertical",
                                command=listbox.yview)
        listbox.configure(yscrollcommand=sb_l.set)
        listbox.pack(side="left", fill="both", expand=True)
        sb_l.pack(side="right", fill="y")

        def agregar_carpeta():
            carpeta = filedialog.askdirectory(parent=dlg,
                                             title=i18n.t("add_folder"))
            if carpeta and carpeta not in listbox.get(0, "end"):
                listbox.insert("end", carpeta)

        def quitar_carpeta():
            sel = listbox.curselection()
            if sel:
                listbox.delete(sel[0])

        fb = ttk.Frame(dlg)
        fb.pack(fill="x", padx=16, pady=(2, 8))
        ttk.Button(fb, text=f"＋ {i18n.t('add_folder')}",
                   command=agregar_carpeta).pack(side="left")
        ttk.Button(fb, text=f"－ {i18n.t('remove_selected')}",
                   command=quitar_carpeta).pack(side="left", padx=8)

        def aceptar():
            nombre   = var_nombre.get().strip()
            if not nombre:
                messagebox.showwarning(
                    "Warning", i18n.t("warn_enter_name"), parent=dlg)
                return
            carpetas = list(listbox.get(0, "end"))
            if not carpetas:
                messagebox.showwarning(
                    "Warning", i18n.t("warn_add_folder"), parent=dlg)
                return
            if nombre in self.config.get("perfiles", {}):
                messagebox.showwarning(
                    "Warning",
                    i18n.t("warn_profile_exists", name=nombre),
                    parent=dlg)
                return
            self.config["perfiles"][nombre] = carpetas
            self.profiles_disk[nombre]      = carpetas
            guardar_profiles_json(PROFILES_PATH, self.profiles_disk)
            self.state_data = state.cargar_estado(STATE_PATH, self.config, self.cfg_app)
            state.guardar_estado(STATE_PATH, self.state_data)
            if self.vigilante.vigila_activo():
                self.vigilante.recargar_perfiles()
                self.vigilante.sincronizar_estado()
            self._construir_pestanas_perfiles()
            self._refrescar_creditos()
            notificar("Creator Manager",
                      i18n.t("profile_added", name=nombre, n=len(carpetas)))
            dlg.destroy()

        fa = ttk.Frame(dlg)
        fa.pack(fill="x", padx=16, pady=(4, 16))
        ttk.Button(fa, text=f"✓  {i18n.t('confirm_add')}",
                   command=aceptar).pack(side="right")

    def _dialogo_eliminar_perfil(self, perfil=None):
        perfiles = list(self.config.get("perfiles", {}).keys())
        if not perfiles:
            messagebox.showinfo("Info", "No profiles to remove.")
            return
        if perfil is None:
            sel_var = tk.StringVar()
            dlg = tk.Toplevel(self.root)
            dlg.title(i18n.t("remove_profile_title"))
            dlg.geometry("360x150")
            dlg.resizable(False, False)
            dlg.transient(self.root)
            dlg.grab_set()
            ttk.Label(dlg, text=i18n.t("select_profile_remove"),
                      font=("Segoe UI", 10, "bold")).pack(
                anchor="w", padx=16, pady=(16, 6))
            cb = ttk.Combobox(dlg, textvariable=sel_var,
                              values=perfiles, state="readonly", width=30)
            cb.pack(padx=16)
            if perfiles:
                cb.current(0)

            def confirmar():
                p = sel_var.get()
                dlg.destroy()
                if p:
                    self._eliminar_perfil(p)

            ttk.Button(dlg, text=f"🗑️  {i18n.t('remove')}",
                       command=confirmar).pack(pady=16)
        else:
            if messagebox.askyesno(
                    i18n.t("remove_profile_title"),
                    i18n.t("confirm_remove", name=perfil)):
                self._eliminar_perfil(perfil)

    def _eliminar_perfil(self, perfil: str):
        self.config["perfiles"].pop(perfil, None)
        self.profiles_disk.pop(perfil, None)
        guardar_profiles_json(PROFILES_PATH, self.profiles_disk)
        self.state_data["perfiles"].pop(perfil, None)
        state.guardar_estado(STATE_PATH, self.state_data)
        if self.vigilante.vigila_activo():
            self.vigilante.recargar_perfiles()
            self.vigilante.sincronizar_estado()
        self._construir_pestanas_perfiles()
        self._refrescar_creditos()
        notificar("Creator Manager",
                  i18n.t("profile_removed", name=perfil))


    # ================================================================
    #  CREDITS
    # ================================================================

    def _refrescar_creditos(self):
        self.state_data = state.cargar_estado(STATE_PATH, self.config, self.cfg_app)
        for iid in self.tree_creditos.get_children():
            self.tree_creditos.delete(iid)

        # Determine extra user-defined systems not in fixed set
        fijas = {"perfil", "chatgpt", "gemini", "ta", "kling", "higgs"}
        nombres_fijos = ["ChatGPT", "Gemini", "TensorArt", "Kling", "Higgsfield"]
        extra_systems = [s for s in self.config.get("herramientas", {})
                         if s not in nombres_fijos]
        extra_cols = [f"usr_{i}" for i in range(len(extra_systems))]

        # Reconfigure tree columns if they changed
        current_cols = list(self.tree_creditos["columns"])
        wanted_cols = list(self._cols_fijas) + extra_cols
        if current_cols != wanted_cols:
            self.tree_creditos["columns"] = wanted_cols
            for c in current_cols:
                if c not in wanted_cols:
                    try:
                        self.tree_creditos.heading(c, text="")
                    except Exception:
                        pass
            for c, key, w in self._cols_fijas_cfg:
                self.tree_creditos.heading(c, text=i18n.t(key))
                self.tree_creditos.column(c, width=w, anchor="center")
            self.tree_creditos.column("perfil", anchor="w")
            for col, sys_name in zip(extra_cols, extra_systems):
                self.tree_creditos.heading(col, text=sys_name)
                self.tree_creditos.column(col, width=140, anchor="center")

        # Pre-read limits for all systems
        limits = {}
        for name in nombres_fijos + extra_systems:
            cfg_h = self.config["herramientas"].get(name, {})
            if "credito" in cfg_h.get("tipo", ""):
                limits[name] = ("credito", float(cfg_h.get("creditos_iniciales", 50)))
            elif "generacion" in cfg_h.get("tipo", ""):
                lim = int(cfg_h.get("limite_diario", cfg_h.get("limite_mensual", 999)))
                limits[name] = ("generacion", lim)
            else:
                limits[name] = ("mensual", int(cfg_h.get("limite_mensual", 1)))

        for perfil in self.config.get("perfiles", {}):
            datos  = self.state_data["perfiles"].get(perfil, {})
            vals   = [perfil]
            tags   = set()
            for name in nombres_fijos + extra_systems:
                cfg_h = self.config["herramientas"].get(name, {})
                tipo_sys, lim = limits[name]
                d = datos.get(name, {})
                if tipo_sys == "credito":
                    rest = float(d.get("creditos_restantes", lim))
                    vals.append(f"{rest:.2f} / {lim:.2f}")
                    if rest <= 0:
                        tags.add("excedido")
                    elif rest <= 5:
                        tags.add("warn")
                elif tipo_sys == "generacion":
                    usado = int(d.get("usado_hoy",
                              d.get("usado_mes", 0)))
                    vals.append(f"{usado} / {lim}")
                    if usado >= lim:
                        tags.add("excedido")
                    elif usado >= lim - 1:
                        tags.add("warn")
                else:
                    usado = int(d.get("usado_mes", 0))
                    vals.append(f"{usado} / {lim}")
                    if usado >= lim:
                        tags.add("excedido")
                    elif usado >= lim - 1:
                        tags.add("warn")
            self.tree_creditos.insert(
                "", "end",
                values=tuple(vals),
                tags=tuple(tags) if tags else ("",))

    def _mostrar_ctx_menu(self, event):
        iid = self.tree_creditos.identify_row(event.y)
        if iid:
            vals = self.tree_creditos.item(iid, "values")
            nombre = vals[0] if vals else ""
            self._ctx_menu.delete(0, "end")
            self._ctx_menu.add_command(
                label=f"⟲ {i18n.t('reset_cycle')} \"{nombre}\"",
                command=lambda p=nombre: self._reiniciar_ciclo(p))
            self._ctx_menu.tk_popup(event.x_root, event.y_root)

    def _reiniciar_ciclo(self, perfil=None):
        self.state_data = state.cargar_estado(STATE_PATH, self.config, self.cfg_app)
        if perfil:
            perfiles = [perfil]
        else:
            if not messagebox.askyesno(i18n.t("reset_cycle"),
                                       i18n.t("reset_cycle_confirm")):
                return
            perfiles = list(self.state_data.get("perfiles", {}).keys())
        ta_ini = float(
            self.config["herramientas"]["TensorArt"]["creditos_iniciales"])
        hoy = state.hoy_str()
        for p in perfiles:
            datos = self.state_data["perfiles"].get(p)
            if datos is None:
                continue
            datos.setdefault("ChatGPT",    {})["usado_hoy"] = 0
            datos.setdefault("Gemini",     {})["usado_hoy"] = 0
            datos["ChatGPT"]["fecha"]      = hoy
            datos["Gemini"]["fecha"]       = hoy
            datos["TensorArt"]["creditos_restantes"] = ta_ini
            datos["Kling"]["usado_mes"]              = 0
            datos["Higgsfield"]["usado_mes"]         = 0
        state.guardar_estado(STATE_PATH, self.state_data)
        if self.vigilante.vigila_activo():
            self.vigilante.sincronizar_estado()
        notificar("Creator Manager", i18n.t("cycle_reset"))
        self._refrescar_todo()

    # ================================================================
    #  HISTORY
    # ================================================================

    def _refrescar_historial(self):
        contenido = state.leer_historial(HISTORY_PATH)
        self.txt_historial.configure(state="normal")
        self.txt_historial.delete("1.0", "end")
        self.txt_historial.insert("end", contenido or i18n.t("history_empty"))
        self.txt_historial.see("end")
        self.txt_historial.configure(state="disabled")

    def _vaciar_historial(self):
        if not messagebox.askyesno(i18n.t("history_clear"),
                                   i18n.t("clear_history_confirm")):
            return
        try:
            open(HISTORY_PATH, "w", encoding="utf-8").close()
        except Exception as e:
            messagebox.showerror(i18n.t("history_cleared_error"), str(e))
        self._refrescar_historial()

    # ================================================================
    #  SETTINGS
    # ================================================================

    def _dialogo_settings(self):
        dlg = tk.Toplevel(self.root)
        dlg.title(i18n.t("settings_title"))
        dlg.geometry("440x420")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        f = ttk.Frame(dlg, padding=20)
        f.pack(fill="both", expand=True)
        row = 0

        # Language
        ttk.Label(f, text=i18n.t("language"),
                  font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=6)
        langs      = i18n.get_available_languages()
        lang_codes = list(langs.keys())
        lang_names = [langs[c] for c in lang_codes]
        lang_var   = tk.StringVar()
        lang_cb    = ttk.Combobox(f, textvariable=lang_var,
                                  values=lang_names, state="readonly", width=22)
        cur_lang   = self.cfg_app.get("language", "en")
        if cur_lang in lang_codes:
            lang_cb.current(lang_codes.index(cur_lang))
        lang_cb.grid(row=row, column=1, sticky="w", pady=6, padx=8)
        row += 1

        # Theme
        ttk.Label(f, text=i18n.t("theme"),
                  font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=6)
        tema_names = list(self.temas.keys())
        tema_var   = tk.StringVar(value=self._tema_actual)
        tema_cb    = ttk.Combobox(f, textvariable=tema_var,
                                  values=tema_names, state="readonly", width=22)
        if self._tema_actual in tema_names:
            tema_cb.current(tema_names.index(self._tema_actual))
        tema_cb.grid(row=row, column=1, sticky="w", pady=6, padx=8)
        row += 1

        # Cycle frequency
        freq_map   = {
            "daily":   i18n.t("freq_daily"),
            "weekly":  i18n.t("freq_weekly"),
            "monthly": i18n.t("freq_monthly"),
            "yearly":  i18n.t("freq_yearly"),
        }
        freq_codes = list(freq_map.keys())
        freq_names = list(freq_map.values())
        ttk.Label(f, text=i18n.t("cycle_frequency"),
                  font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=6)
        freq_var = tk.StringVar()
        freq_cb  = ttk.Combobox(f, textvariable=freq_var,
                                values=freq_names, state="readonly", width=22)
        cur_freq = self.cfg_app.get("cycle_frequency", "monthly")
        if cur_freq in freq_codes:
            freq_cb.current(freq_codes.index(cur_freq))
        freq_cb.grid(row=row, column=1, sticky="w", pady=6, padx=8)
        row += 1

        # Cycle anchor
        ttk.Label(f, text=i18n.t("cycle_anchor"),
                  font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=6)
        anchor_var = tk.IntVar(value=self.cfg_app.get("cycle_anchor_day", 17))
        ttk.Spinbox(f, textvariable=anchor_var, from_=1, to=28,
                    width=6).grid(row=row, column=1, sticky="w",
                                  pady=6, padx=8)
        row += 1

        # Watch interval
        ttk.Label(f, text=i18n.t("watch_interval"),
                  font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=6)
        interval_var = tk.IntVar(value=self.cfg_app.get("watch_interval_sec", 15))
        ttk.Spinbox(f, textvariable=interval_var, from_=5, to=3600,
                    width=8).grid(row=row, column=1, sticky="w",
                                  pady=6, padx=8)
        row += 1

        # Notification sound
        sound_var = tk.BooleanVar(value=self.cfg_app.get("notification_sound", True))
        ttk.Checkbutton(f, text=i18n.t("notification_sound"),
                        variable=sound_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=6, padx=0)
        row += 1

        # Auto-start watch
        auto_var = tk.BooleanVar(value=self.cfg_app.get("auto_start_watch", True))
        ttk.Checkbutton(f, text=i18n.t("auto_start_watch"),
                        variable=auto_var).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=6, padx=0)
        row += 1

        bf = ttk.Frame(f)
        bf.grid(row=row, column=0, columnspan=2, pady=(16, 0))

        def guardar():
            li          = lang_cb.current()
            new_lang    = lang_codes[li] if li >= 0 else "en"
            lang_changed = new_lang != self.cfg_app.get("language")
            new_tema    = tema_var.get()
            tema_changed = new_tema != self._tema_actual
            fi          = freq_cb.current()
            new_freq    = freq_codes[fi] if fi >= 0 else "monthly"

            self.cfg_app["language"]          = new_lang
            self.cfg_app["theme"]             = new_tema
            self.cfg_app["cycle_frequency"]   = new_freq
            self.cfg_app["cycle_anchor_day"]  = anchor_var.get()
            self.cfg_app["watch_interval_sec"] = interval_var.get()
            self.cfg_app["notification_sound"] = sound_var.get()
            self.cfg_app["auto_start_watch"]   = auto_var.get()
            self.cfg_app["_first_launch_done"] = True
            notifier.set_sound_enabled(sound_var.get())
            cfg_app_mod.guardar_config_app(self.cfg_app, CONFIG_APP_PATH)

            if lang_changed:
                i18n.set_language(new_lang)
                self._refrescar_idioma()
            if tema_changed:
                self._tema_actual = new_tema
                self._tema        = self.temas.get(new_tema, {})
                self._apply_style()
                self._refrescar_todo()

            messagebox.showinfo(i18n.t("settings_title"),
                                i18n.t("settings_saved"), parent=dlg)
            dlg.destroy()

        ttk.Button(bf, text=f"✓ {i18n.t('save')}",
                   command=guardar).pack(side="left", padx=8)
        ttk.Button(bf, text=i18n.t("cancel"),
                   command=dlg.destroy).pack(side="left")

    # ================================================================
    #  RESET ALL DATA
    # ================================================================

    def _reset_all_data(self):
        if not messagebox.askyesno(
                i18n.t("reset_all_data_title"),
                i18n.t("reset_all_data_confirm"),
                icon="warning"):
            return
        import shutil
        try:
            # Stop watcher
            if self.vigilante.vigila_activo():
                self.vigilante.detener()
            # Delete profiles
            perfiles_dir = self.config.get("perfiles_dir", os.path.join(BASE, "Profiles"))
            if os.path.isdir(perfiles_dir):
                shutil.rmtree(perfiles_dir, ignore_errors=True)
            # Reset profiles.json
            guardar_profiles_json(PROFILES_PATH, {})
            self.profiles_disk = {}
            self.config["perfiles"] = {}
            # Reset state.json
            empty_state = {"ciclo_actual": "", "perfiles": {}}
            state.guardar_estado(STATE_PATH, empty_state)
            # Clear history
            try:
                open(HISTORY_PATH, "w", encoding="utf-8").close()
            except Exception:
                pass
            # Clear error log
            logger.clear_log()
            # Reset app config to defaults except language/theme
            lang_keep = self.cfg_app.get("language", "en")
            theme_keep = self.cfg_app.get("theme", "light")
            self.cfg_app = dict(cfg_app_mod.DEFAULTS)
            self.cfg_app["language"] = lang_keep
            self.cfg_app["theme"] = theme_keep
            self.cfg_app["_first_launch_done"] = True
            cfg_app_mod.guardar_config_app(self.cfg_app, CONFIG_APP_PATH)
            # Refresh UI
            self._construir_pestanas_perfiles()
            self._refrescar_creditos()
            self._refrescar_historial()
            messagebox.showinfo(i18n.t("reset_all_data_title"),
                                i18n.t("data_reset_done"))
            # Close the app so user reopens fresh
            self.root.after(500, self.root.destroy)
        except Exception as e:
            logger.log_exception(f"Reset all data failed: {e}")
            messagebox.showerror(i18n.t("reset_all_data_title"),
                                 f"Error: {e}")

    # ================================================================
    #  WATCHING
    # ================================================================

    def _toggle_vigilancia(self):
        if self.vigilante.vigila_activo():
            self.vigilante.detener()
            self.btn_vigilar.config(text=f"▶  {i18n.t('start_watch')}")
            self.lbl_vigila.config(
                text=f"○ {i18n.t('paused')}",
                fg=self._tema.get("error", "#b00020"))
            notificar("Creator Manager", i18n.t("notif_watch_paused"))
        else:
            self.vigilante.config["perfiles"] = dict(self.profiles_disk)
            self.vigilante.sincronizar_estado()
            self.vigilante.recargar_perfiles()
            self.vigilante.iniciar()
            self.btn_vigilar.config(text=f"⏸  {i18n.t('pause_watch')}")
            self.lbl_vigila.config(
                text=f"● {i18n.t('watching')}",
                fg=self._tema.get("success", "#2e7d32"))
            n = sum(len(v) if isinstance(v, list) else 1
                    for v in self.profiles_disk.values())
            notificar("Creator Manager",
                      i18n.t("notif_watch_started", n=n))

    def _on_error(self, mensaje: str):
        messagebox.showerror(
            i18n.t("settings_title") + " - Error",
            mensaje)

    def _on_tab_change(self, event=None):
        sel = self.nb.select()
        if not sel:
            return
        tab_text = self.nb.tab(sel, "text")
        # Remove emoji prefix to get profile name: "👤  ProfileName" → "ProfileName"
        for prefix in ("👤", "🎟️", "📜"):
            tab_text = tab_text.replace(prefix, "").strip()
        if tab_text and tab_text in self._pestanas_perfil:
            self._mostrar_perfil(tab_text)

    def _on_movimiento(self, entrada: dict):
        self._refrescar_creditos()
        self._refrescar_historial()
        perfil = entrada.get("perfil", "")
        if perfil in self._pestanas_perfil:
            self._mostrar_perfil(perfil)
        self.lbl_barra.config(
            text=i18n.t("last_move",
                        perfil=entrada["perfil"],
                        herramienta=entrada["herramienta"],
                        estado=entrada["estado"]))

    # ================================================================
    #  REFRESH & UTILS
    # ================================================================

    def _refrescar_todo(self):
        self._construir_pestanas_perfiles()
        self._refrescar_creditos()
        self._refrescar_historial()

    def _refrescar_idioma(self):
        """Rebuild all UI text to reflect the current language."""
        self.root.title(f"{i18n.t('app_title')} {i18n.t('version')}")
        self.btn_vigilar.config(
            text=f"▶  {i18n.t('start_watch')}" if not self.vigilante.vigila_activo()
            else f"⏸  {i18n.t('pause_watch')}")
        estado = f"● {i18n.t('watching')}" if self.vigilante.vigila_activo() else f"○ {i18n.t('paused')}"
        self.lbl_vigila.config(text=estado)
        self.btn_refresh.config(text=f"↻  {i18n.t('refresh_all')}")
        self.btn_changelog.config(text=f"📋  {i18n.t('changelog')}")
        self.btn_settings.config(text=f"⚙  {i18n.t('settings')}")
        self.btn_add.config(text=f"＋  {i18n.t('add_profile')}")
        self.btn_reset.config(text=f"🗑️  {i18n.t('reset_all_data')}")
        self.btn_open_folder.config(text=f"📂  {i18n.t('open_program_folder')}")
        self.lbl_barra.config(
            text=(f"{i18n.t('cycle')} "
                  f"{state.ciclo_actual(self.config, self.cfg_app)}"
                  f"   ·   {i18n.t('today')}: {state.hoy_str()}"))
        # Full UI rebuild with translated content
        self._construir_pestanas_perfiles()
        self._refrescar_creditos()
        self._refrescar_historial()

    def _auto_refresco(self):
        try:
            self._refrescar_creditos()
        except Exception:
            pass
        self.root.after(20_000, self._auto_refresco)

    def _abrir_explorer(self, ruta: str):
        if not os.path.exists(ruta):
            try:
                os.makedirs(ruta, exist_ok=True)
            except Exception:
                pass
        try:
            if os.name == "nt":
                os.startfile(ruta)          # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as e:
            messagebox.showerror("Open folder", str(e))

    def _abrir_archivo(self, ruta: str):
        try:
            if os.name == "nt":
                os.startfile(ruta)          # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", ruta])
        except Exception as e:
            messagebox.showerror("Open file", str(e))

    def _cerrar(self):
        if self.vigilante.vigila_activo():
            if messagebox.askyesno(i18n.t("close_title"),
                                   i18n.t("close_watch_active")):
                self.vigilante.detener()
            else:
                return
        self.root.destroy()


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

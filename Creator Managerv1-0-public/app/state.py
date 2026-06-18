"""
state.py
State persistence (state.json) + movement history (history.txt) +
generalised cycle logic (daily / weekly / monthly / yearly).

Paths in config.json are RELATIVE to the app directory and are resolved here.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime, timedelta
from typing import Optional

BASE  = os.path.dirname(os.path.abspath(__file__))
_LOCK = threading.Lock()

# User-defined system overrides file
SYSTEMS_USER_FILE = "systems_user.json"


# ─────────────────────────────────────────────────────────────────────
#  Path resolution
# ─────────────────────────────────────────────────────────────────────

def resolver_path(rel_o_abs: str) -> str:
    """Resolve a path. If relative, anchor to the app BASE dir."""
    if not rel_o_abs:
        return rel_o_abs
    if os.path.isabs(rel_o_abs):
        return rel_o_abs
    return os.path.normpath(os.path.join(BASE, rel_o_abs))


def resolver_paths_config(config: dict) -> dict:
    """Resolve all known path keys in config to absolute paths in-place."""
    for key in ("base_dir", "perfiles_dir", "historial_path", "estado_path",
                "perfiles_path", "temas_path", "config_app_path"):
        if key in config and config[key]:
            config[key] = resolver_path(config[key])
    config.setdefault("base_dir",     BASE)
    config.setdefault("perfiles_dir", resolver_path("Profiles"))
    return config


# ─────────────────────────────────────────────────────────────────────
#  JSON helpers
# ─────────────────────────────────────────────────────────────────────

def _read_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def cargar_config(path: str) -> dict:
    config = _read_json(path, {})
    if isinstance(config, dict):
        resolver_paths_config(config)
    return config


# ─────────────────────────────────────────────────────────────────────
#  Cycle logic
# ─────────────────────────────────────────────────────────────────────

def ciclo_para_fecha(d: date, frecuencia: str = "monthly",
                     ancla: int = 17) -> str:
    """Return the cycle id (used as folder name) that `d` belongs to.

    - daily:   "YYYY-MM-DD"  (ancla ignored)
    - weekly:  "YYYY-Www"    (ISO week); ancla = weekday that starts the week
                               (0=Mon … 6=Sun). Days before the anchor
                               belong to the previous week.
    - monthly: "YYYY-MM"     ancla = day-of-month (default 17).
                               day < ancla → previous month.
    - yearly:  "YYYY"        ancla = month 1-12. month < ancla → previous year.
    """
    frecuencia = (frecuencia or "monthly").lower()
    if frecuencia == "daily":
        return d.strftime("%Y-%m-%d")

    if frecuencia == "weekly":
        ancla = int(ancla) % 7
        dias_desde_ancla = (d.weekday() - ancla) % 7
        base = d - timedelta(days=dias_desde_ancla)
        iso_year, iso_week, _ = base.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"

    if frecuencia == "yearly":
        ancla = max(1, min(12, int(ancla)))
        if d.month < ancla:
            return f"{d.year - 1}"
        return f"{d.year}"

    # monthly (default)
    ancla = max(1, min(28, int(ancla)))
    if d.day >= ancla:
        base = d
    else:
        base = d.replace(day=1) - timedelta(days=1)
    return base.strftime("%Y-%m")


def ciclo_actual(config: dict, config_app: Optional[dict] = None) -> str:
    freq  = "monthly"
    ancla = 17
    if config_app:
        freq  = config_app.get("cycle_frequency",  "monthly")
        ancla = config_app.get("cycle_anchor_day", 17)
    return ciclo_para_fecha(date.today(), freq, ancla)


def hoy_str() -> str:
    return date.today().strftime("%Y-%m-%d")


def ahora_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────────────────────────────
#  Default state
# ─────────────────────────────────────────────────────────────────────

def _plantilla_perfil(config: dict, config_app: Optional[dict] = None) -> dict:
    ta_ini = float(config["herramientas"]["TensorArt"]["creditos_iniciales"])
    ciclo  = ciclo_actual(config, config_app)
    return {
        "ChatGPT":    {"usado_hoy": 0, "fecha": hoy_str()},
        "Gemini":     {"usado_hoy": 0, "fecha": hoy_str()},
        "TensorArt":  {"creditos_restantes": ta_ini, "ciclo": ciclo},
        "Kling":      {"usado_mes": 0, "ciclo": ciclo},
        "Higgsfield": {"usado_mes": 0, "ciclo": ciclo},
        "pendientes": [],
    }


def _normalizar_estado(estado_data: dict, config: dict,
                       config_app: Optional[dict] = None) -> dict:
    estado_data.setdefault("ciclo_actual", ciclo_actual(config, config_app))
    estado_data.setdefault("perfiles", {})
    for perfil in config.get("perfiles", {}):
        if perfil not in estado_data["perfiles"]:
            estado_data["perfiles"][perfil] = _plantilla_perfil(config, config_app)
        else:
            plant = _plantilla_perfil(config, config_app)
            for k, v in plant.items():
                estado_data["perfiles"][perfil].setdefault(k, v)
    return estado_data


def cargar_estado(path: str, config: dict,
                  config_app: Optional[dict] = None) -> dict:
    estado_data = _read_json(path, None)
    if not isinstance(estado_data, dict):
        estado_data = {}
    return _normalizar_estado(estado_data, config, config_app)


def guardar_estado(path: str, estado_data: dict) -> None:
    _write_json(path, estado_data)


# ─────────────────────────────────────────────────────────────────────
#  User-defined system overrides
# ─────────────────────────────────────────────────────────────────────

def cargar_sistemas_usuario() -> dict:
    path = os.path.join(BASE, SYSTEMS_USER_FILE)
    data = _read_json(path, {})
    return data if isinstance(data, dict) else {}


def guardar_sistemas_usuario(data: dict) -> None:
    path = os.path.join(BASE, SYSTEMS_USER_FILE)
    _write_json(path, data)


def merge_systems(builtin: dict, user: dict) -> dict:
    result = dict(builtin)
    for name, cfg in user.items():
        if not isinstance(cfg, dict):
            continue
        if name in result:
            if isinstance(result[name], dict):
                result[name].update(cfg)
        else:
            result[name] = cfg
    return result


# ─────────────────────────────────────────────────────────────────────
#  Daily / cycle resets
# ─────────────────────────────────────────────────────────────────────

def aplicar_rotaciones(estado_data: dict, config: dict,
                       config_app: Optional[dict] = None) -> tuple:
    """Apply daily/cycle resets. Returns (estado, changed)."""
    ta_ini     = float(config["herramientas"]["TensorArt"]["creditos_iniciales"])
    ciclo_hoy  = ciclo_actual(config, config_app)
    hoy        = hoy_str()
    cambiado   = False

    estado_data["ciclo_actual"] = ciclo_hoy
    for perfil, datos in estado_data.get("perfiles", {}).items():
        for herramienta in ("ChatGPT", "Gemini"):
            d = datos.get(herramienta, {})
            if d.get("fecha") != hoy:
                d["usado_hoy"] = 0
                d["fecha"]     = hoy
                datos[herramienta] = d
                cambiado = True
        ta = datos.get("TensorArt", {})
        if ta.get("ciclo") != ciclo_hoy:
            ta["creditos_restantes"] = ta_ini
            ta["ciclo"]              = ciclo_hoy
            datos["TensorArt"]       = ta
            cambiado = True
        for herramienta in ("Kling", "Higgsfield"):
            d = datos.get(herramienta, {})
            if d.get("ciclo") != ciclo_hoy:
                d["usado_mes"]     = 0
                d["ciclo"]         = ciclo_hoy
                datos[herramienta] = d
                cambiado = True

    return estado_data, cambiado


# ─────────────────────────────────────────────────────────────────────
#  Discount functions
# ─────────────────────────────────────────────────────────────────────

def descontar_chatgpt_gemini(estado_data: dict, perfil: str,
                              herramienta: str, config: dict) -> dict:
    with _LOCK:
        datos    = estado_data["perfiles"][perfil]
        cfg_h    = config["herramientas"][herramienta]
        limite   = int(cfg_h["limite_diario"])
        d        = datos[herramienta]
        usado    = int(d.get("usado_hoy", 0))
        excedido = usado >= limite
        nuevo    = usado + 1 if not excedido else usado
        if not excedido:
            d["usado_hoy"] = nuevo
            d["fecha"]     = hoy_str()
            datos[herramienta] = d
        restantes = max(0, limite - nuevo)
        return {
            "ok": not excedido, "excedido": excedido,
            "usado": nuevo, "limite": limite, "restantes": restantes,
            "descuento_texto": f"1 generation (remaining={restantes}/{limite})",
        }


def descontar_tensorart_imagen(estado_data: dict, perfil: str,
                                config: dict) -> dict:
    with _LOCK:
        datos  = estado_data["perfiles"][perfil]
        costo  = float(config["herramientas"]["TensorArt"]["costo_imagen"])
        ta     = datos["TensorArt"]
        antes  = float(ta.get("creditos_restantes", 0))
        if antes >= costo:
            despues = round(antes - costo, 2)
            ta["creditos_restantes"] = despues
            datos["TensorArt"] = ta
            ok, excedido = True, False
        else:
            despues = antes
            ok, excedido = False, True
        return {
            "ok": ok, "excedido": excedido, "costo": costo,
            "restantes": despues,
            "descuento_texto": f"{costo} credits (remaining={despues:.2f}/50.03)",
        }


def descontar_tensorart_video(estado_data: dict, perfil: str, config: dict,
                               duracion: float, resolucion: str) -> dict:
    with _LOCK:
        datos   = estado_data["perfiles"][perfil]
        ta_cfg  = config["herramientas"]["TensorArt"]
        clave   = ("costo_video_por_segundo_480p"
                   if resolucion == "480p"
                   else "costo_video_por_segundo_720p")
        por_seg      = float(ta_cfg[clave])
        d_min        = float(ta_cfg.get("duracion_min_seg", 3))
        d_max        = float(ta_cfg.get("duracion_max_seg", 10))
        dur_efectiva = min(max(duracion, d_min), d_max)
        costo        = round(por_seg * dur_efectiva, 2)
        ta           = datos["TensorArt"]
        antes        = float(ta.get("creditos_restantes", 0))
        if antes >= costo:
            despues = round(antes - costo, 2)
            ta["creditos_restantes"] = despues
            datos["TensorArt"] = ta
            ok, excedido = True, False
        else:
            despues = antes
            ok, excedido = False, True
        return {
            "ok": ok, "excedido": excedido, "costo": costo,
            "duracion": dur_efectiva, "resolucion": resolucion,
            "restantes": despues,
            "descuento_texto": (f"{costo} credits "
                                f"(video {resolucion} {dur_efectiva:.1f}s, "
                                f"remaining={despues:.2f}/50.03)"),
        }


def descontar_mensual(estado_data: dict, perfil: str, herramienta: str,
                      config: dict) -> dict:
    with _LOCK:
        datos    = estado_data["perfiles"][perfil]
        cfg_h    = config["herramientas"][herramienta]
        limite   = int(cfg_h["limite_mensual"])
        d        = datos[herramienta]
        usado    = int(d.get("usado_mes", 0))
        excedido = usado >= limite
        nuevo    = usado + 1 if not excedido else usado
        if not excedido:
            d["usado_mes"]     = nuevo
            datos[herramienta] = d
        restantes = max(0, limite - nuevo)
        return {
            "ok": not excedido, "excedido": excedido,
            "usado": nuevo, "limite": limite, "restantes": restantes,
            "descuento_texto": f"1 monthly video (remaining={restantes}/{limite})",
        }


# ─────────────────────────────────────────────────────────────────────
#  Generic user-defined system handlers
# ─────────────────────────────────────────────────────────────────────

def _cfg_herramienta(config: dict, herramienta: str) -> dict:
    return config.get("herramientas", {}).get(herramienta, {})


def descontar_generacion(estado_data: dict, perfil: str, herramienta: str,
                          config: dict) -> dict:
    """Generic discount for generation-based systems (daily/weekly/monthly/yearly)."""
    with _LOCK:
        cfg_h  = _cfg_herramienta(config, herramienta)
        datos  = estado_data["perfiles"].get(perfil, {})
        d      = datos.setdefault(herramienta, {"usado_hoy": 0, "usado_mes": 0, "fecha": ""})
        hoy    = hoy_str()
        ciclo  = cfg_h.get("ciclo", "daily")
        if ciclo == "daily":
            limite_key, usado_key = "limite_diario", "usado_hoy"
        else:
            limite_key, usado_key = "limite_mensual", "usado_mes"
        limite = int(cfg_h.get(limite_key, cfg_h.get("limite_diario", 999)))
        usado  = int(d.get(usado_key, 0))
        excedido = usado >= limite
        if not excedido:
            d[usado_key] = usado + 1
            d["fecha"]   = hoy
        restantes = max(0, limite - (usado + 1 if not excedido else usado))
        return {
            "ok": not excedido, "excedido": excedido,
            "usado": usado + 1, "limite": limite, "restantes": restantes,
            "descuento_texto": f"1 {herramienta} (remaining={restantes}/{limite})",
        }


def descontar_credito(estado_data: dict, perfil: str, herramienta: str,
                       config: dict, tipo_archivo: Optional[str] = None,
                       duracion: Optional[float] = None,
                       resolucion: Optional[str] = None) -> dict:
    """Generic discount for credit-based systems with optional cost table."""
    with _LOCK:
        cfg_h = _cfg_herramienta(config, herramienta)
        datos = estado_data["perfiles"].get(perfil, {})
        d     = datos.setdefault(herramienta, {"creditos_restantes": 0})
        antes = float(d.get("creditos_restantes",
                      cfg_h.get("creditos_iniciales", 50)))

        if tipo_archivo == "imagen" or (duracion is None and resolucion is None):
            costo = float(cfg_h.get("costo_imagen",
                        cfg_h.get("costo_default", 1)))
        else:
            costos = cfg_h.get("costos", [])
            costo = None
            res = resolucion or "480p"
            dur = duracion or 10
            for c in costos:
                if (str(c.get("resolucion", "")) == res
                        and int(c.get("duracion", 0)) == int(dur)):
                    costo = float(c["costo"])
                    break
            if costo is None:
                por_seg = float(cfg_h.get(
                    f"costo_video_por_segundo_{res}", 1))
                costo = round(por_seg * dur, 2)

        if antes >= costo:
            despues = round(antes - costo, 2)
            d["creditos_restantes"] = despues
            ok, excedido = True, False
        else:
            despues = antes
            ok, excedido = False, True
        return {
            "ok": ok, "excedido": excedido, "costo": costo,
            "restantes": despues,
            "descuento_texto": f"{costo} credits (remaining={despues:.2f})",
        }


def registrar_pendiente_ta(estado_data: dict, perfil: str,
                            ruta_destino: str, nombre_archivo: str) -> None:
    with _LOCK:
        datos = estado_data["perfiles"][perfil]
        datos.setdefault("pendientes", []).append({
            "herramienta": "TensorArt", "tipo": "video",
            "archivo": nombre_archivo, "ruta": ruta_destino,
            "registrado": ahora_str(),
        })


def resolver_pendiente_ta(estado_data: dict, perfil: str, indice: int,
                           duracion: float, resolucion: str,
                           config: dict) -> dict:
    with _LOCK:
        datos     = estado_data["perfiles"][perfil]
        pendientes = datos.get("pendientes", [])
        if indice < 0 or indice >= len(pendientes):
            return {"ok": False, "error": "invalid_index"}
        info = descontar_tensorart_video(estado_data, perfil, config,
                                         duracion, resolucion)
        if info["ok"]:
            pendientes.pop(indice)
            datos["pendientes"] = pendientes
        return info


# ─────────────────────────────────────────────────────────────────────
#  History
# ─────────────────────────────────────────────────────────────────────

def escribir_historial(historial_path: str, entrada: dict) -> None:
    os.makedirs(os.path.dirname(historial_path) or ".", exist_ok=True)
    lineas = [
        f"[{entrada.get('timestamp','')}] "
        f"PROFILE={entrada.get('perfil','')} "
        f"TOOL={entrada.get('herramienta','')} "
        f"TYPE={entrada.get('tipo','')}",
        f"  FILE=\"{entrada.get('archivo','')}\"",
        f"  FROM=\"{entrada.get('origen','')}\"",
        f"  TO=\"{entrada.get('destino','')}\"",
        f"  DISCOUNT={entrada.get('descuento_texto','')}",
    ]
    for k, v in (entrada.get("extra") or {}).items():
        lineas.append(f"  {k.upper()}={v}")
    lineas.append(f"  STATUS={entrada.get('estado','OK')}")
    lineas.append("")
    with _LOCK:
        with open(historial_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lineas) + "\n")


def leer_historial(historial_path: str, max_bytes: Optional[int] = None) -> str:
    try:
        if max_bytes is None:
            with open(historial_path, "r", encoding="utf-8") as f:
                return f.read()
        size = os.path.getsize(historial_path)
        with open(historial_path, "rb") as fb:
            if size > max_bytes:
                fb.seek(-max_bytes, os.SEEK_END)
                fb.readline()
            data = fb.read()
        return data.decode("utf-8", errors="replace")
    except FileNotFoundError:
        return ""
    except Exception:
        return ""

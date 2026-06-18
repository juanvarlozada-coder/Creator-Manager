"""
watcher.py
Background file watcher for the download folders.

- Polls every N seconds (from app_config.watch_interval_sec).
- For each new file: classify → verify stable → move → discount →
  log to history.txt + desktop notification.

Paths in config.json are relative; resolved via state.resolver_paths_config.
Profiles are loaded dynamically from profiles.json.
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
from typing import Callable, Optional

import app_config
import state
import costs
import logger
from metadata import resumen_video
from notifier import notificar


def _resolver_config_path(p: Optional[str]) -> str:
    if p:
        return os.path.abspath(p)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


class Vigilante:
    def __init__(self, config_path: Optional[str] = None,
                 callback_movimiento: Optional[Callable[[dict], None]] = None,
                 callback_error: Optional[Callable[[str], None]] = None,
                 config_app_data: Optional[dict] = None):
        self.config_path = _resolver_config_path(config_path)
        base = os.path.dirname(self.config_path)

        self.config = state.cargar_config(self.config_path)
        state.resolver_paths_config(self.config)
        self.estado_path   = self.config.get("estado_path")  or os.path.join(base, "state.json")
        self.historial_path = self.config.get("historial_path") or os.path.join(base, "history.txt")
        self.perfiles_path = self.config.get("perfiles_path") or os.path.join(base, "profiles.json")

        self.config_app = config_app_data or app_config.cargar_config_app(
            self.config.get("config_app_path") or
            os.path.join(base, "app_config.json"))

        self._cargar_perfiles()

        self.estado = state.cargar_estado(self.estado_path, self.config, self.config_app)
        self.estado, _ = state.aplicar_rotaciones(self.estado, self.config, self.config_app)
        state.guardar_estado(self.estado_path, self.estado)

        self.callback       = callback_movimiento
        self.callback_error = callback_error
        self._stop          = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.procesados:  set = set()
        self.ultimo_dia   = state.hoy_str()
        self._lock_estado = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────

    def _notificar_error(self, mensaje: str) -> None:
        if self.callback_error:
            try:
                self.callback_error(mensaje)
            except Exception:
                pass
        try:
            notificar("Creator Manager Error", mensaje)
        except Exception:
            pass

    def _cargar_perfiles(self) -> None:
        try:
            with open(self.perfiles_path, "r", encoding="utf-8") as f:
                perfiles = json.load(f)
            if isinstance(perfiles, dict):
                self.config["perfiles"] = perfiles
        except Exception as e:
            logger.log_error(f"Failed to load profiles from {self.perfiles_path}", str(e))
            self.config.setdefault("perfiles", {})

    def recargar_perfiles(self) -> None:
        self._cargar_perfiles()
        self.procesados.clear()

    def sincronizar_estado(self) -> None:
        """Re-load and normalize state from disk for current profiles."""
        with self._lock_estado:
            self.estado = state.cargar_estado(
                self.estado_path, self.config, self.config_app)
            self.estado, _ = state.aplicar_rotaciones(
                self.estado, self.config, self.config_app)

    def iniciar(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def detener(self) -> None:
        self._stop.set()

    def vigila_activo(self) -> bool:
        return bool(self._thread and self._thread.is_alive()
                    and not self._stop.is_set())

    # ── Main loop ─────────────────────────────────────────────────────

    def _loop(self) -> None:
        intervalo = max(2, int(self.config_app.get("watch_interval_sec", 15)))
        while not self._stop.is_set():
            try:
                self._comprobar_rotaciones()
                self._escanear()
            except Exception as e:
                logger.log_exception(f"Watcher loop error: {e}")
                self._notificar_error(f"Watcher error: {e}")
            self._stop.wait(intervalo)

    def _comprobar_rotaciones(self) -> None:
        with self._lock_estado:
            nuevo, cambiado = state.aplicar_rotaciones(
                self.estado, self.config, self.config_app)
            self.estado = nuevo
            if cambiado:
                state.guardar_estado(self.estado_path, self.estado)
        hoy = state.hoy_str()
        if hoy != self.ultimo_dia:
            self.ultimo_dia = hoy
            self.procesados.clear()

    # ── Scan ──────────────────────────────────────────────────────────

    def _escanear(self) -> None:
        for perfil, carpetas in self.config.get("perfiles", {}).items():
            if isinstance(carpetas, str):
                carpetas = [carpetas]
            for carpeta in carpetas:
                if not os.path.isdir(carpeta):
                    continue
                try:
                    with os.scandir(carpeta) as it:
                        entradas = list(it)
                except Exception:
                    continue
                for entrada in entradas:
                    if self._stop.is_set():
                        return
                    if not entrada.is_file():
                        continue
                    ruta = os.path.normpath(entrada.path)
                    if ruta in self.procesados:
                        continue
                    self._manejar_archivo(ruta, perfil, carpeta)

    def _manejar_archivo(self, ruta: str, perfil: str,
                         carpeta_origen: str) -> None:
        herramienta, tipo = costs.clasificar(ruta, self.config)
        if herramienta is None or tipo is None:
            self.procesados.add(ruta)
            return
        if not self._archivo_estable(ruta):
            return

        destino_dir = self._ruta_destino(perfil, tipo)
        try:
            os.makedirs(destino_dir, exist_ok=True)
        except Exception as e:
            msg = f"Cannot create {destino_dir}: {e}"
            logger.log_error(msg)
            self._notificar_error(msg)
            self.procesados.add(ruta)
            return

        destino  = self._resolver_nombre_unico(destino_dir, os.path.basename(ruta))
        try:
            resultado = self._descontar(herramienta, tipo, ruta, perfil)
        except Exception as e:
            msg = f"Discount error for {os.path.basename(ruta)}: {e}"
            logger.log_exception(msg)
            self._notificar_error(msg)
            self.procesados.add(ruta)
            return

        try:
            shutil.move(ruta, destino)
        except Exception as e:
            msg = f"Cannot move {os.path.basename(ruta)} to {destino}: {e}"
            logger.log_error(msg)
            self._notificar_error(msg)
            self.procesados.add(ruta)
            return

        entrada = {
            "timestamp":       state.ahora_str(),
            "perfil":          perfil,
            "herramienta":     herramienta,
            "tipo":            tipo,
            "archivo":         os.path.basename(ruta),
            "origen":          carpeta_origen,
            "destino":         destino,
            "descuento_texto": resultado.get("descuento_texto", ""),
            "estado":          resultado.get("estado_texto", "OK"),
            "extra":           resultado.get("extra", {}),
        }
        state.escribir_historial(self.historial_path, entrada)
        state.guardar_estado(self.estado_path, self.estado)

        estado_final = entrada["estado"]
        titulo = f"{perfil} · {herramienta}"
        msg = (f"{tipo.capitalize()} moved to "
               f"{os.path.basename(os.path.dirname(destino))}/"
               f"\n{resultado.get('descuento_texto','')}"
               + (f"  [{estado_final}]" if estado_final != "OK" else ""))
        notificar(titulo, msg)

        if self.callback:
            try:
                self.callback(entrada)
            except Exception:
                pass

        self.procesados.add(ruta)
        self.procesados.add(os.path.normpath(destino))

    # ── Discount ──────────────────────────────────────────────────────

    def _descontar(self, herramienta: str, tipo: str, ruta: str,
                   perfil: str) -> dict:
        extra = {}
        with self._lock_estado:
            if herramienta in ("ChatGPT", "Gemini"):
                info = state.descontar_chatgpt_gemini(
                    self.estado, perfil, herramienta, self.config)
                estado_texto = "OK" if info["ok"] else "EXCEEDED"
            elif herramienta == "TensorArt":
                if tipo == "imagen":
                    info = state.descontar_tensorart_imagen(
                        self.estado, perfil, self.config)
                    estado_texto = "OK" if info["ok"] else "EXCEEDED"
                else:
                    res = resumen_video(ruta, self.config)
                    if res is None:
                        state.registrar_pendiente_ta(
                            self.estado, perfil, ruta, os.path.basename(ruta))
                        info = {"ok": False,
                                "descuento_texto":
                                    "PENDING CONFIRMATION (TA video without metadata)"}
                        estado_texto = "PENDING_CONFIRM"
                        extra["NOTE"] = ("Open Credits tab to confirm "
                                         "duration/quality.")
                    else:
                        info = state.descontar_tensorart_video(
                            self.estado, perfil, self.config,
                            res["duracion"], res["resolucion"])
                        estado_texto = "OK" if info["ok"] else "EXCEEDED"
                        extra["DURATION"]   = f"{res['duracion']}s"
                        extra["RESOLUTION"] = res["resolucion"]
                        extra["DIMENSIONS"] = f"{res['ancho']}x{res['alto']}"
            elif herramienta in ("Kling", "Higgsfield"):
                info = state.descontar_mensual(
                    self.estado, perfil, herramienta, self.config)
                estado_texto = "OK" if info["ok"] else "EXCEEDED"
            else:
                cfg_h = self.config.get("herramientas", {}).get(herramienta, {})
                tool_tipo = cfg_h.get("tipo", "")
                if "credito" in tool_tipo.lower():
                    if tipo == "imagen":
                        info = state.descontar_credito(
                            self.estado, perfil, herramienta, self.config,
                            tipo_archivo="imagen")
                    else:
                        res = resumen_video(ruta, self.config)
                        if res is not None:
                            info = state.descontar_credito(
                                self.estado, perfil, herramienta, self.config,
                                duracion=res["duracion"],
                                resolucion=res["resolucion"])
                            extra["DURATION"]   = f"{res['duracion']}s"
                            extra["RESOLUTION"] = res["resolucion"]
                            extra["DIMENSIONS"] = f"{res['ancho']}x{res['alto']}"
                        else:
                            info = {"ok": False,
                                    "descuento_texto":
                                        "PENDING CONFIRMATION (no metadata)"}
                            estado_texto = "PENDING_CONFIRM"
                    estado_texto = "OK" if info["ok"] else "EXCEEDED"
                elif "generacion" in tool_tipo.lower():
                    info = state.descontar_generacion(
                        self.estado, perfil, herramienta, self.config)
                    estado_texto = "OK" if info["ok"] else "EXCEEDED"
                else:
                    info = {"ok": False, "descuento_texto": "unknown tool"}
                    estado_texto = "ERROR"
        info["estado_texto"] = estado_texto
        info["extra"]        = extra
        return info

    # ── File helpers ──────────────────────────────────────────────────

    def _archivo_estable(self, ruta: str, intentos: int = 2,
                         espera: float = 0.8) -> bool:
        try:
            s1 = os.path.getsize(ruta)
        except OSError:
            return False
        for _ in range(intentos):
            time.sleep(espera)
            try:
                s2 = os.path.getsize(ruta)
            except OSError:
                return False
            if s1 == s2:
                return True
            s1 = s2
        return False

    def _ruta_destino(self, perfil: str, tipo: str) -> str:
        ciclo = state.ciclo_actual(self.config, self.config_app)
        sub   = "images" if tipo == "imagen" else "videos"
        return os.path.join(self.config["perfiles_dir"], perfil, ciclo, sub)

    def _resolver_nombre_unico(self, carpeta: str, nombre: str) -> str:
        destino = os.path.join(carpeta, nombre)
        if not os.path.exists(destino):
            return destino
        base_, ext = os.path.splitext(nombre)
        i = 1
        while True:
            cand = os.path.join(carpeta, f"{base_}_{i}{ext}")
            if not os.path.exists(cand):
                return cand
            i += 1


def _run_standalone():
    v = Vigilante()
    v.iniciar()
    print("Watcher running. Ctrl+C to quit.")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        v.detener()
        print("Stopped.")


if __name__ == "__main__":
    _run_standalone()

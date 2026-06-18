"""
metadata.py
Read video duration and resolution using OpenCV (cv2).
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

try:
    import cv2
    _CV2_OK = True
except Exception:
    _CV2_OK = False


def leer_metadatos_video(ruta: str) -> Optional[Tuple[float, int, int]]:
    """Return (duration_seconds, width, height) of a video file.

    Returns None if cv2 is unavailable or the file cannot be read reliably
    (invalid fps, 0 frames, etc.).
    """
    if not _CV2_OK:
        return None
    if not os.path.isfile(ruta):
        return None
    cap = None
    try:
        cap = cv2.VideoCapture(ruta)
        if not cap.isOpened():
            return None
        fps    = cap.get(cv2.CAP_PROP_FPS)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        ancho  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        alto   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        cap = None
        if not fps or fps <= 0 or not frames or frames <= 0:
            return None
        if ancho <= 0 or alto <= 0:
            return None
        duracion = frames / fps
        return duracion, ancho, alto
    except Exception:
        return None
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


def clasificar_resolucion(ancho: int, alto: int,
                          umbral_alto: int = 720,
                          umbral_largo: int = 1280) -> str:
    """Classify resolution as '480p' or '720p'."""
    if alto >= (umbral_alto + 1) or ancho >= umbral_largo:
        return "720p"
    return "480p"


def resumen_video(ruta: str, config: dict) -> Optional[dict]:
    """Combine reading + classification according to config.

    Returns dict with: duracion, ancho, alto, resolucion ('480p'|'720p').
    Returns None if the file could not be read.
    """
    ta = config.get("herramientas", {}).get("TensorArt", {})
    umbral_alto  = int(ta.get("umbral_alto_720p_alto",  1280))
    umbral_largo = int(ta.get("umbral_alto_720p_largo", 720))
    res = leer_metadatos_video(ruta)
    if res is None:
        return None
    duracion, ancho, alto = res
    resolucion = clasificar_resolucion(
        ancho, alto,
        umbral_alto=umbral_largo,
        umbral_largo=umbral_alto,
    )
    return {
        "duracion":   round(duracion, 2),
        "ancho":      ancho,
        "alto":       alto,
        "resolucion": resolucion,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        r = leer_metadatos_video(sys.argv[1])
        print("Raw:", r)
        if r:
            d, w, h = r
            print("Classification:", clasificar_resolucion(w, h))
    else:
        print("Usage: python metadata.py <video_path>")

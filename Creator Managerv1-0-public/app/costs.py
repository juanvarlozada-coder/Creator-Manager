"""
costs.py
File classification by AI tool (from config patterns) and by type
(image / video) according to file extension.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple


def extension(ruta: str) -> str:
    """Return the lowercased extension including the dot."""
    _, ext = os.path.splitext(ruta)
    return ext.lower()


def clasificar_tipo(ruta: str, config: dict) -> Optional[str]:
    """Return 'imagen', 'video', or None."""
    ext = extension(ruta)
    if ext in [e.lower() for e in config.get("extensiones_imagen", [])]:
        return "imagen"
    if ext in [e.lower() for e in config.get("extensiones_video", [])]:
        return "video"
    return None


def clasificar_herramienta(ruta: str, config: dict) -> Optional[str]:
    """Return the tool name or None if no pattern matches.

    Check order matters: Gemini is checked before anything else
    (its 'gemini' pattern is fairly specific), and TensorArt uses 'ta-'/'ta_'.
    """
    nombre   = os.path.basename(ruta).lower()
    patrones = config.get("patrones", {})
    orden    = ["ChatGPT", "Gemini", "TensorArt", "Kling", "Higgsfield"]
    for herramienta in orden:
        for pat in patrones.get(herramienta, []):
            if pat.lower() in nombre:
                return herramienta
    return None


def clasificar(ruta: str, config: dict) -> Tuple[Optional[str], Optional[str]]:
    """Return (tool, type). Either may be None."""
    return clasificar_herramienta(ruta, config), clasificar_tipo(ruta, config)


if __name__ == "__main__":
    import json
    cfg = json.load(open("config.json", encoding="utf-8"))
    samples = [
        "ChatGPT Image 16 jun 2026, 08_03_51 p.m..png",
        "Gemini_Generated_Image_abc123.jpg",
        "TA-2026-06-14-12-59-38-Sample.mp4",
        "TA_Imagen_001.png",
        "kling_2026_06_15.mp4",
        "hf_video_sample.mp4",
        "download.jpg",
    ]
    for s in samples:
        h, t = clasificar(s, cfg)
        print(f"{s[:55]:<55} -> tool={h}  type={t}")

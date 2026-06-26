from __future__ import annotations
import base64
import json
import os
from pathlib import Path

import requests
from PIL import Image

from .models import Head

TIMEOUT = 10


def _texture_cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    d = base / "headapi" / "textures"
    d.mkdir(parents=True, exist_ok=True)
    return d


def extract_texture_url(value: str) -> str:
    padded = value + "=" * (-len(value) % 4)
    data = json.loads(base64.b64decode(padded))
    return data["textures"]["SKIN"]["url"]


def _download_skin(url: str) -> Image.Image:
    texture_hash = url.rstrip("/").split("/")[-1]
    cache_path = _texture_cache_dir() / f"{texture_hash}.png"

    if cache_path.exists():
        return Image.open(cache_path).copy()

    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    cache_path.write_bytes(resp.content)
    return Image.open(cache_path).copy()


def get_face_image(head: Head) -> Image.Image:
    skin = _download_skin(extract_texture_url(head.value))

    face = skin.crop((8, 8, 16, 16)).convert("RGBA")
    hat = skin.crop((40, 8, 48, 16)).convert("RGBA")
    face.paste(hat, (0, 0), hat)

    return face.convert("RGB")

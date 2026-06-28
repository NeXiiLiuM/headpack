from __future__ import annotations
import base64
import json
import os
from pathlib import Path

import requests
from PIL import Image, ImageEnhance

from .models import Head

TIMEOUT = 10

_FACE_UV = {
    "front": ((8,  8, 16, 16), (40,  8, 48, 16)),
    "left":  ((16, 8, 24, 16), (48,  8, 56, 16)),
    "right": ((0,  8,  8, 16), (32,  8, 40, 16)),
    "back":  ((24, 8, 32, 16), (56,  8, 64, 16)),
    "top":    ((8,  0, 16,  8), (40,  0, 48,  8)),
    "bottom": ((16, 0, 24,  8), (48,  0, 56,  8)),
}

# (face_gauche_cube, face_droite_cube, rotation_top_degrees)
_ISO_VIEWS = [
    ("front", "left",   0),
    ("left",  "back",  -90),
    ("back",  "right", 180),
    ("right", "front",  90),
]


def _texture_cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    d = base / "headpack" / "textures"
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


def _composite_face(skin: Image.Image, inner: tuple, outer: tuple) -> Image.Image:
    face = skin.crop(inner).convert("RGBA")
    hat = skin.crop(outer).convert("RGBA")
    face.paste(hat, (0, 0), hat)
    return face


def get_face_image(head: Head) -> Image.Image:
    skin = _download_skin(extract_texture_url(head.value))
    face = _composite_face(skin, *_FACE_UV["front"])
    return face.convert("RGB")


def get_face_by_name(head: Head, face_name: str, size: int = 16) -> Image.Image:
    skin = _download_skin(extract_texture_url(head.value))
    img = _composite_face(skin, *_FACE_UV[face_name]).convert("RGB")
    return img.resize((size, size), Image.NEAREST)


def get_iso_image(head: Head, rotation: int = 0, n: int = 32, bg_color: tuple[int, int, int] = (0, 0, 0)) -> Image.Image:
    skin = _download_skin(extract_texture_url(head.value))
    fl_key, fr_key, top_rot = _ISO_VIEWS[rotation % 4]

    face_l = _composite_face(skin, *_FACE_UV[fl_key]).resize((n, n), Image.NEAREST)
    face_r = _composite_face(skin, *_FACE_UV[fr_key]).resize((n, n), Image.NEAREST)
    top = _composite_face(skin, *_FACE_UV["top"]).resize((n, n), Image.NEAREST)

    if top_rot:
        top = top.rotate(top_rot, expand=False)

    face_l = ImageEnhance.Brightness(face_l.convert("RGBA")).enhance(0.80)
    face_r = ImageEnhance.Brightness(face_r.convert("RGBA")).enhance(0.60)
    top = top.convert("RGBA")

    canvas = Image.new("RGBA", (2 * n, 2 * n), (*bg_color, 255))

    def _paste(img: Image.Image, data: tuple) -> None:
        t = img.transform((2 * n, 2 * n), Image.Transform.AFFINE, data, Image.NEAREST)
        canvas.paste(t, (0, 0), t)

    fn = float(n)
    _paste(face_r, (1.0, 0.0, -fn,       0.5,  1.0, -1.5 * fn))
    _paste(face_l, (1.0, 0.0,  0.0,     -0.5,  1.0, -0.5 * fn))
    _paste(top,    (0.5, 1.0, -0.5 * fn, -0.5, 1.0,  0.5 * fn))

    return canvas.convert("RGB")

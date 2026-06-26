from __future__ import annotations
import json
import os
import time
from pathlib import Path
from .models import Head

TTL_SECONDS = 7 * 24 * 3600


def _cache_dir() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    base = Path(xdg) if xdg else Path.home() / ".cache"
    d = base / "headapi"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_file() -> Path:
    return _cache_dir() / "heads.json"


def _load_store() -> dict:
    f = _cache_file()
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_store(store: dict) -> None:
    tmp = _cache_file().with_suffix(".tmp")
    tmp.write_text(json.dumps(store))
    os.replace(tmp, _cache_file())


def get(key: str) -> list[Head] | None:
    store = _load_store()
    entry = store.get(key)
    if not entry:
        return None
    if time.time() - entry["fetched_at"] > TTL_SECONDS:
        return None
    return [Head(**h) for h in entry["data"]]


def set(key: str, heads: list[Head]) -> None:
    store = _load_store()
    store[key] = {
        "fetched_at": time.time(),
        "data": [{"name": h.name, "uuid": h.uuid, "value": h.value, "tags": h.tags} for h in heads],
    }
    _save_store(store)


def invalidate(key: str | None = None) -> None:
    if key is None:
        _cache_file().unlink(missing_ok=True)
    else:
        store = _load_store()
        store.pop(key, None)
        _save_store(store)

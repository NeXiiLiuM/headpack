from __future__ import annotations
import requests
from .models import Head

BASE_URL = "https://minecraft-heads.com/scripts/api.php"
TIMEOUT = 15


class APIError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


def fetch_category(category: str, api_key: str | None = None) -> list[Head]:
    params: dict[str, str] = {"cat": category, "tags": "true"}
    if api_key:
        params["key"] = api_key

    resp = requests.get(BASE_URL, params=params, timeout=TIMEOUT)
    if resp.status_code == 429:
        raise APIError(429, "Rate limit reached. Wait a moment or check your API key.")
    if not resp.ok:
        raise APIError(resp.status_code, resp.text[:200])

    raw: list[dict] = resp.json()
    return [Head(name=h["name"], uuid=h["uuid"], value=h["value"], tags=h.get("tags", "")) for h in raw]

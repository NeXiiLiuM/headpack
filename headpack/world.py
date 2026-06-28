from __future__ import annotations
import json
import os
import sys
from pathlib import Path

def _default_saves_dir() -> Path:
    if sys.platform == "win32":
        return Path.home() / "AppData" / "Roaming" / ".minecraft" / "saves"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "minecraft" / "saves"
    return Path.home() / ".minecraft" / "saves"

SAVES_DIR = _default_saves_dir()
DATAPACK_NAME = "headpack"
FUNCTION_REL = Path("data") / "headpack" / "function" / "give.mcfunction"
MCMETA_CONTENT = json.dumps(
    {
        "pack": {
            "description": "HeadPack — génération de têtes Minecraft",
            "min_format": 88,
            "max_format": 9999,
        }
    },
    indent=2,
    ensure_ascii=False,
)


def _find_worlds() -> list[Path]:
    if not SAVES_DIR.exists():
        return []
    return sorted(
        (d for d in SAVES_DIR.iterdir() if d.is_dir() and (d / "level.dat").exists()),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )


def list_worlds() -> list[Path]:
    return _find_worlds()


def get_world_path(override: str | None = None) -> Path:
    if override:
        return Path(override)
    env = os.environ.get("HEADPACK_WORLD_PATH")
    if env:
        return Path(env)
    worlds = _find_worlds()
    if not worlds:
        raise RuntimeError(
            f"Aucun monde trouvé dans {SAVES_DIR}\n"
            "Utilise --world-path pour spécifier le chemin manuellement."
        )
    return worlds[0]


def datapack_root(world_path: Path) -> Path:
    return world_path / "datapacks" / DATAPACK_NAME


def is_installed(world_path: Path) -> bool:
    return (datapack_root(world_path) / "pack.mcmeta").exists()


def install_skeleton(world_path: Path) -> Path:
    root = datapack_root(world_path)
    function_path = root / FUNCTION_REL
    function_path.parent.mkdir(parents=True, exist_ok=True)
    (root / "pack.mcmeta").write_text(MCMETA_CONTENT, encoding="utf-8")
    if not function_path.exists():
        function_path.write_text("# Généré par HeadPack\n", encoding="utf-8")
    return root


def deploy_mcfunction(content: str, world_path: Path) -> Path:
    function_path = datapack_root(world_path) / FUNCTION_REL
    function_path.parent.mkdir(parents=True, exist_ok=True)
    function_path.write_text(content, encoding="utf-8")
    return function_path

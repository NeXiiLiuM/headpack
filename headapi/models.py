from __future__ import annotations
import uuid as _uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Head:
    name: str
    uuid: str
    value: str
    tags: str

    def letter(self) -> str | None:
        last = self.name.split()[-1]
        if len(last) == 1 and last.upper() in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            return last.upper()
        return None

    def style(self) -> str | None:
        for tag in self.tags.split(","):
            tag = tag.strip().lower()
            if tag.startswith("font (") and tag.endswith(")"):
                return tag[6:-1]
        return None


@dataclass(frozen=True)
class ResolvedLetter:
    char: str
    head: Head
    fallback_used: bool


def uuid_to_int_array(uuid_str: str) -> list[int]:
    n = _uuid.UUID(uuid_str).int
    parts: list[int] = []
    for _ in range(4):
        chunk = n & 0xFFFFFFFF
        parts.insert(0, chunk if chunk < 0x80000000 else chunk - 0x100000000)
        n >>= 32
    return parts


def build_give_command(head: Head, selector: str = "@p") -> str:
    ints = uuid_to_int_array(head.uuid)
    id_str = f"[I;{ints[0]},{ints[1]},{ints[2]},{ints[3]}]"
    return (
        f"give {selector} minecraft:player_head"
        f"[minecraft:profile={{id:{id_str},"
        f"properties:[{{name:\"textures\",value:\"{head.value}\"}}]}}]"
    )

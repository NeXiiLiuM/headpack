from __future__ import annotations
from ..models import ResolvedLetter, build_give_command


def generate(letters: list[ResolvedLetter], selector: str = "@p") -> str:
    lines = [build_give_command(r.head, selector) for r in letters]
    return "\n".join(lines)

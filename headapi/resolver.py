from __future__ import annotations
from .models import Head, ResolvedLetter


_SPECIAL_ALPHABETS = {"standard galactic", "cyrillic", "braille", "hebrew", "japanese", "greek"}


def _prefer_standard(heads: list[Head]) -> list[Head]:
    def _is_special(h: Head) -> bool:
        for tag in h.tags.split(","):
            tag = tag.strip().lower()
            if tag.startswith("alphabet ("):
                inner = tag[10:-1]
                if inner in _SPECIAL_ALPHABETS:
                    return True
        return False

    standard = [h for h in heads if not _is_special(h)]
    return standard if standard else heads


def load_heads(api_key: str | None, no_cache: bool) -> list[Head]:
    from . import cache, api as api_module
    key = "category:alphabet"
    if not no_cache:
        cached = cache.get(key)
        if cached is not None:
            return cached
    heads = api_module.fetch_category("alphabet", api_key)
    cache.set(key, heads)
    return heads


def list_styles(heads: list[Head]) -> list[str]:
    styles: set[str] = set()
    for h in heads:
        s = h.style()
        if s:
            styles.add(s)
    return sorted(styles)


def resolve_word(
    word: str,
    style: str,
    heads: list[Head],
    fallback: str,
) -> tuple[list[ResolvedLetter], list[str]]:
    style_lower = style.lower()

    letter_index: dict[str, list[Head]] = {}
    for h in heads:
        letter = h.letter()
        if letter:
            letter_index.setdefault(letter, []).append(h)

    results: list[ResolvedLetter] = []
    warnings: list[str] = []

    for char in word.upper():
        if char == " ":
            warnings.append("Espace ignoré (pas de tête espace disponible)")
            continue
        if char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            warnings.append(f"Caractère '{char}' non supporté, ignoré")
            continue

        candidates = letter_index.get(char, [])
        if not candidates:
            if fallback == "error":
                raise ValueError(f"Aucune tête trouvée pour la lettre '{char}'")
            warnings.append(f"Lettre '{char}' introuvable dans la base de données, ignorée")
            continue

        styled = [h for h in candidates if f"font ({style_lower})" in h.tags.lower()]
        styled = _prefer_standard(styled)

        if styled:
            results.append(ResolvedLetter(char=char, head=styled[0], fallback_used=False))
        elif fallback == "first":
            chosen = candidates[0]
            actual_style = chosen.style() or "inconnu"
            warnings.append(
                f"Lettre '{char}' : style '{style}' introuvable, utilisation de '{actual_style}'"
            )
            results.append(ResolvedLetter(char=char, head=chosen, fallback_used=True))
        elif fallback == "skip":
            warnings.append(f"Lettre '{char}' : style '{style}' introuvable, ignorée")
        elif fallback == "error":
            raise ValueError(f"Lettre '{char}' introuvable dans le style '{style}'")

    return results, warnings

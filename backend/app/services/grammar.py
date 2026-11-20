"""Dictionary-style display helpers for German nouns ("der Schein, -e", "die Auskunft, -¨e")."""

# U+00A8 DIAERESIS: the dictionary convention for "the stem vowel takes an umlaut".
UMLAUT_MARK = "¨"
PLURAL_ONLY_MARK = "(Pl.)"

_UMLAUTS = {"a": "ä", "o": "ö", "u": "ü", "A": "Ä", "O": "Ö", "U": "Ü"}
_UMLAUTED = set("äöüÄÖÜ")


def umlaut_stem(word: str) -> str | None:
    """`word` with its last umlautable stem vowel umlauted ("Haus" -> "Häus", "Mutter" ->
    "Mütter", "Saal" -> "Säl"), or None if it has none ("Freund": "eu" never umlauts here)."""
    index = len(word) - 1
    while index >= 0:
        char = word[index]
        previous = word[index - 1] if index > 0 else ""
        if char in _UMLAUTED:
            return None
        if char in "uU" and previous and previous in "aA":  # au -> äu
            return word[: index - 1] + _UMLAUTS[previous] + word[index:]
        if char in "uU" and previous and previous in "eEäÄ":  # eu / äu: no umlaut
            return None
        if char in "aA" and previous and previous in "aA":  # aa -> ä (Saal -> Säle)
            return word[: index - 1] + _UMLAUTS[previous] + word[index + 1 :]
        if char in _UMLAUTS:
            return word[:index] + _UMLAUTS[char] + word[index + 1 :]
        # Consonants and non-umlauting vowels (e, i, y): keep scanning towards the start.
        index -= 1
    return None


def plural_notation(singular: str, plural: str | None, plural_only: bool = False) -> str | None:
    """Dictionary plural notation for a noun: "-" (same form), "-e"/"-en"/... (suffix),
    "-¨" (umlaut only), "-¨e" (umlaut + suffix), the full plural when it isn't one of those
    patterns ("Museum" -> "Museen"), "(Pl.)" for plural-only nouns, None when unknown."""
    if plural_only:
        return PLURAL_ONLY_MARK
    if not plural:
        return None
    if plural == singular:
        return "-"
    if plural.startswith(singular):
        return "-" + plural[len(singular) :]
    umlauted = umlaut_stem(singular)
    if umlauted is not None and plural.startswith(umlauted):
        return "-" + UMLAUT_MARK + plural[len(umlauted) :]
    return plural


def noun_display(
    lemma: str, article: str | None, plural: str | None, plural_only: bool = False
) -> str:
    """ "der Schein, -e", "die Eltern (Pl.)", "das Haus" (plural unknown), "Schein" (no
    article known)."""
    head = f"{article} {lemma}" if article else lemma
    notation = plural_notation(lemma, plural, plural_only)
    if notation is None:
        return head
    if notation == PLURAL_ONLY_MARK:
        return f"{head} {notation}"
    return f"{head}, {notation}"

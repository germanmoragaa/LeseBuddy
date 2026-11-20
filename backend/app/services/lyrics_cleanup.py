"""Removes Genius page leftovers from lyrics a user pasted (ADR 0006).

Users copy lyrics from a lyrics page themselves; the copy often drags along page chrome in
German or English: a "[Songtext zu „…"]" title, "Songtext"/"Lyrics" headings, "12 Contributors",
"Translations", "Embed", "You might also like". This only ever *removes* such lines from text
the user pasted - it never fetches anything.

Text that contains none of them is returned unchanged (byte for byte), so running the cleanup
twice, or on clean text, is a no-op.
"""

import re

_FLAGS = re.IGNORECASE

# A whole (stripped) line matching any of these is page chrome, wherever it appears.
_CHROME_LINES = tuple(
    re.compile(pattern, _FLAGS)
    for pattern in (
        r"\[(?:Songtext|Liedtext) zu\b.*\]",
        r"(?:Songtext|Lyrics)",
        r"\d[\d.,]*\s*(?:Contributors?|Mitwirkende[rn]?).*",
        r"(?:Translations|Übersetzungen)",
        r"\d*\s*(?:Embed|Einbetten)",
        r"(?:You might also like|Das könnte dir auch gefallen)",
    )
)

# Only before the first real lyric line: the page's title heading ("Nachtlicht Lyrics",
# "Nachtlicht Songtext").
_TITLE_HEADING = re.compile(r".+\s(?:Lyrics|Songtext)", _FLAGS)

# Leftovers glued onto a real lyric line by the copy: "…nach Haus12Embed" at the very end,
# "You might also likeNächste Zeile" at the start of a line.
_GLUED_EMBED = re.compile(r"\d+\s*Embed\s*$", _FLAGS)
_GLUED_RECOMMENDATION = re.compile(
    r"^(\s*)(?:You might also like|Das könnte dir auch gefallen)(?=\S)", _FLAGS
)


def _is_chrome(stripped: str, *, in_leading_block: bool) -> bool:
    if any(pattern.fullmatch(stripped) for pattern in _CHROME_LINES):
        return True
    return in_leading_block and _TITLE_HEADING.fullmatch(stripped) is not None


def clean_pasted_lyrics(text: str) -> str:
    lines = text.split("\n")
    kept: list[str] = []
    changed = False
    seen_lyric = False

    for line in lines:
        stripped = line.strip()
        if stripped and _is_chrome(stripped, in_leading_block=not seen_lyric):
            changed = True
            continue
        unglued = _GLUED_RECOMMENDATION.sub(r"\1", line)
        if unglued != line:
            changed = True
            line = unglued
        if line.strip():
            seen_lyric = True
        kept.append(line)

    # "Embed" glued to the last lyric line.
    for index in range(len(kept) - 1, -1, -1):
        if kept[index].strip():
            unglued = _GLUED_EMBED.sub("", kept[index])
            if unglued != kept[index] and unglued.strip():
                kept[index] = unglued.rstrip()
                changed = True
            break

    if not changed:
        return text

    # Removing a heading block can leave blank lines at either end.
    while kept and not kept[0].strip():
        kept.pop(0)
    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept)

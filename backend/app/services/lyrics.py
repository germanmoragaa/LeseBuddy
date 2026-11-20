"""Lyric-line helpers for articles of kind "song".

A song's context unit is its newline-delimited lyric line, not spaCy's sentence (lyrics rarely
punctuate, so a "sentence" can run across a whole verse). Section lines like "[Hook]" or
"[Strophe 2: ...]" and blank lines are never a context line. All offsets are code points into
the stored, NFC-normalized `original_text`, like every other offset in the app.
"""

import re
from dataclasses import dataclass

SECTION_HEADER = re.compile(r"^\[[^\]]*\]$")


@dataclass(frozen=True)
class TextSpan:
    start: int
    end: int

    def text(self, original_text: str) -> str:
        return original_text[self.start : self.end]


def is_context_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and SECTION_HEADER.match(stripped) is None


def lyric_lines(original_text: str) -> list[TextSpan]:
    """Every context-eligible line, in order, trimmed of surrounding whitespace (including a
    "\\r" from Windows line endings)."""
    spans: list[TextSpan] = []
    position = 0
    for raw_line in original_text.split("\n"):
        line_start, line_end = position, position + len(raw_line)
        position = line_end + 1
        if not is_context_line(raw_line):
            continue
        leading = len(raw_line) - len(raw_line.lstrip())
        trailing = len(raw_line) - len(raw_line.rstrip())
        spans.append(TextSpan(line_start + leading, line_end - trailing))
    return spans


def find_line_index(lines: list[TextSpan], start: int, end: int) -> int | None:
    """Index of the context line that fully contains [start, end), or None."""
    for index, line in enumerate(lines):
        if line.start <= start and end <= line.end:
            return index
    return None


def surrounding_lines_context(original_text: str, lines: list[TextSpan], index: int) -> str | None:
    """The previous and next context lines, joined by a newline - what DeepL gets as
    `context` when translating line `index` (it influences the translation but is never
    translated itself). None for a one-line song."""
    neighbours = [
        lines[neighbour].text(original_text)
        for neighbour in (index - 1, index + 1)
        if 0 <= neighbour < len(lines)
    ]
    return "\n".join(neighbours) or None

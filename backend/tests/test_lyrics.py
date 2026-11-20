from app.services.lyrics import (
    find_line_index,
    is_context_line,
    lyric_lines,
    surrounding_lines_context,
)

# Invented lyric-style lines — never real copyrighted lyrics (see CLAUDE.md, ADR 0006).
LYRICS = (
    "[Strophe 1]\n"
    "Die Scheine liegen auf dem Tisch\n"
    "  Ich ging allein durch die Nacht  \n"
    "\n"
    "[Hook: Die Erfundenen]\n"
    "Die Sterne sehen alles"
)


def _texts(text: str) -> list[str]:
    return [span.text(text) for span in lyric_lines(text)]


def test_section_headers_and_blank_lines_are_never_context_lines() -> None:
    assert _texts(LYRICS) == [
        "Die Scheine liegen auf dem Tisch",
        "Ich ging allein durch die Nacht",
        "Die Sterne sehen alles",
    ]
    assert not is_context_line("[Hook]")
    assert not is_context_line("   ")
    # Brackets inside a real line don't make it a header.
    assert is_context_line("Ich sag [leise] nein")


def test_line_offsets_are_trimmed_code_point_offsets_into_the_text() -> None:
    lines = lyric_lines(LYRICS)
    second = lines[1]
    assert LYRICS[second.start : second.end] == "Ich ging allein durch die Nacht"
    assert LYRICS[second.start - 2 : second.start] == "  "


def test_windows_line_endings_are_trimmed() -> None:
    assert _texts("Erste Zeile\r\nZweite Zeile\r\n") == ["Erste Zeile", "Zweite Zeile"]


def test_find_line_index() -> None:
    lines = lyric_lines(LYRICS)
    start = LYRICS.index("Scheine")
    assert find_line_index(lines, start, start + len("Scheine")) == 0
    header = LYRICS.index("Hook")
    assert find_line_index(lines, header, header + 4) is None
    # A span crossing two lines fits neither.
    tisch = LYRICS.index("Tisch")
    ich = LYRICS.index("Ich")
    assert find_line_index(lines, tisch, ich + 3) is None


def test_surrounding_context_skips_headers_and_handles_first_and_last_line() -> None:
    lines = lyric_lines(LYRICS)
    assert surrounding_lines_context(LYRICS, lines, 0) == "Ich ging allein durch die Nacht"
    assert surrounding_lines_context(LYRICS, lines, 1) == (
        "Die Scheine liegen auf dem Tisch\nDie Sterne sehen alles"
    )
    # The last line's previous neighbour is across the blank line and the "[Hook]" header.
    assert surrounding_lines_context(LYRICS, lines, 2) == "Ich ging allein durch die Nacht"


def test_single_line_song_has_no_surrounding_context() -> None:
    text = "Nur eine Zeile"
    assert surrounding_lines_context(text, lyric_lines(text), 0) is None

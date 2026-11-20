import pytest

from app.services.grammar import noun_display, plural_notation, umlaut_stem


@pytest.mark.parametrize(
    ("singular", "plural", "plural_only", "expected"),
    [
        ("Schein", "Scheine", False, "-e"),
        ("Frau", "Frauen", False, "-en"),
        ("Kind", "Kinder", False, "-er"),
        ("Auto", "Autos", False, "-s"),
        ("Lehrer", "Lehrer", False, "-"),
        ("Auskunft", "Auskünfte", False, "-¨e"),
        ("Haus", "Häuser", False, "-¨er"),
        ("Nacht", "Nächte", False, "-¨e"),
        ("Mutter", "Mütter", False, "-¨"),
        ("Apfel", "Äpfel", False, "-¨"),
        ("Vogel", "Vögel", False, "-¨"),
        ("Saal", "Säle", False, "-¨e"),
        ("Museum", "Museen", False, "Museen"),
        ("Firma", "Firmen", False, "Firmen"),
        ("Freund", "Freunde", False, "-e"),
        ("Eltern", None, True, "(Pl.)"),
        ("Eltern", "Eltern", True, "(Pl.)"),
        ("Schein", None, False, None),
    ],
)
def test_plural_notation(
    singular: str, plural: str | None, plural_only: bool, expected: str | None
) -> None:
    assert plural_notation(singular, plural, plural_only) == expected


def test_umlaut_mark_is_the_spacing_diaeresis() -> None:
    assert plural_notation("Auskunft", "Auskünfte") == "-¨e"


@pytest.mark.parametrize(
    ("word", "expected"),
    [("Haus", "Häus"), ("Mutter", "Mütter"), ("Saal", "Säl"), ("Freund", None), ("Bär", None)],
)
def test_umlaut_stem(word: str, expected: str | None) -> None:
    assert umlaut_stem(word) == expected


@pytest.mark.parametrize(
    ("lemma", "article", "plural", "plural_only", "expected"),
    [
        ("Schein", "der", "Scheine", False, "der Schein, -e"),
        ("Auskunft", "die", "Auskünfte", False, "die Auskunft, -¨e"),
        ("Haus", "das", None, False, "das Haus"),
        ("Eltern", "die", None, True, "die Eltern (Pl.)"),
        ("Schein", None, "Scheine", False, "Schein, -e"),
    ],
)
def test_noun_display(
    lemma: str, article: str | None, plural: str | None, plural_only: bool, expected: str
) -> None:
    assert noun_display(lemma, article, plural, plural_only) == expected

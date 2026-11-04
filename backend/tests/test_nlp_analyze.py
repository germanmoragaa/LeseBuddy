import json
import unicodedata
from pathlib import Path

import pytest

from app.services.nlp.analyze import analyze_text

FIXTURES_DIR = Path(__file__).parent / "fixtures"

OFFSET_INVARIANT_TEXTS = [
    pytest.param("Der große Käfer läuft über die Straße.", id="umlauts_and_eszett"),
    pytest.param("Sie sagte: „Komm schnell!“", id="curly_quotes"),
    pytest.param("Das Wetter — so sagte man — wird besser.", id="em_dash"),
    pytest.param("Erste Zeile.\nZweite Zeile.", id="linebreak"),
    pytest.param("Der Hund sieht den Hund.", id="repeated_word"),
    pytest.param(
        unicodedata.normalize("NFC", unicodedata.normalize("NFD", "Müller mag Müsli.")),
        id="nfc_decomposed_input_normalized_first",
    ),
    pytest.param("Ich liebe 🐶 Hunde.", id="emoji"),
]


class TestOffsetInvariant:
    @pytest.mark.parametrize("text", OFFSET_INVARIANT_TEXTS)
    def test_every_token_slice_matches_its_text(self, text: str) -> None:
        result = analyze_text(text)

        for token in result.tokens:
            assert text[token.start : token.end] == token.text

    @pytest.mark.parametrize("text", OFFSET_INVARIANT_TEXTS)
    def test_tokens_plus_whitespace_reconstruct_the_original_text(self, text: str) -> None:
        result = analyze_text(text)

        reconstructed = "".join(token.text + token.whitespace_after for token in result.tokens)
        assert reconstructed == text

    def test_sentence_offsets_slice_correctly(self) -> None:
        text = "Erste Zeile. Zweite Zeile."
        result = analyze_text(text)

        assert len(result.sentences) == 2
        assert text[result.sentences[0].start : result.sentences[0].end] == "Erste Zeile."
        assert text[result.sentences[1].start : result.sentences[1].end] == "Zweite Zeile."


class TestLemmaAndPos:
    @staticmethod
    def _eval_cases() -> list[tuple[str, str, str, str]]:
        data = json.loads((FIXTURES_DIR / "nlp_eval.json").read_text(encoding="utf-8"))
        return [
            (entry["sentence"], check["token_text"], check["expected_lemma"], check["expected_pos"])
            for entry in data
            for check in entry["checks"]
        ]

    @pytest.mark.parametrize("sentence,token_text,expected_lemma,expected_pos", _eval_cases())
    def test_matches_manually_reviewed_expectation(
        self, sentence: str, token_text: str, expected_lemma: str, expected_pos: str
    ) -> None:
        result = analyze_text(sentence)

        matching = [token for token in result.tokens if token.text == token_text]
        assert matching, f"no token with text {token_text!r} in {sentence!r}"
        token = matching[0]
        assert token.lemma == expected_lemma
        assert token.pos == expected_pos


class TestSeparableVerbs:
    def test_detects_anrufen(self) -> None:
        text = "Ich rufe dich morgen an."
        result = analyze_text(text)

        assert len(result.separable_verbs) == 1
        verb = result.separable_verbs[0]
        assert verb.lemma == "anrufen"
        assert result.tokens[verb.verb_token_index].text == "rufe"
        assert result.tokens[verb.particle_token_index].text == "an"

    def test_detects_abfahren(self) -> None:
        text = "Der Zug fährt um acht ab."
        result = analyze_text(text)

        assert len(result.separable_verbs) == 1
        verb = result.separable_verbs[0]
        assert verb.lemma == "abfahren"
        assert result.tokens[verb.verb_token_index].text == "fährt"
        assert result.tokens[verb.particle_token_index].text == "ab"

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("Ich bin an der Universität.", id="an_as_preposition"),
            pytest.param("Er kommt aus Berlin.", id="aus_as_preposition"),
            pytest.param("Er versteht das.", id="inseparable_prefix_verb"),
        ],
    )
    def test_does_not_false_positive(self, text: str) -> None:
        result = analyze_text(text)

        assert result.separable_verbs == []

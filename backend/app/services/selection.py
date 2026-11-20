from dataclasses import dataclass

from app.schemas.analysis import ArticleAnalysisResult
from app.services.lyrics import (
    TextSpan,
    find_line_index,
    lyric_lines,
    surrounding_lines_context,
)
from app.services.nlp.types import Sentence, SeparableVerb, Token

# Marker pos strings for selections that don't correspond to a single spaCy token — used to
# route dictionary lookups, never sent to spaCy or stored as a real UPOS tag.
SEPARABLE_VERB_POS = "VERB"
PHRASE_POS = "PHRASE"

SONG_KIND = "song"


class SelectionError(Exception):
    """Raised when {start, end} doesn't align to real token boundaries from the stored
    analysis, or doesn't fit within a single context unit (a stored sentence for texts, a
    lyric line for songs). Never trust client-sent offsets without this check — see
    docs/decisions/0004-translations-and-dictionary.md. `code` is machine-readable for the
    API's 422 body; the frontend maps it to a friendly message."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ResolvedSelection:
    tokens: list[Token]
    # The stored sentence containing the selection. None only for songs, where the context is
    # the lyric line and a spaCy "sentence" may not contain the selection at all.
    sentence: Sentence | None
    surface_text: str
    lemma: str
    pos: str
    separable_verb: SeparableVerb | None
    # The context unit: the lyric line for songs, the sentence for texts.
    context: TextSpan
    # Songs only: the neighbouring lines, passed to DeepL as context for the line itself.
    surrounding_context: str | None = None

    @property
    def is_separable_verb(self) -> bool:
        return self.separable_verb is not None

    @property
    def is_phrase(self) -> bool:
        return len(self.tokens) > 1

    def context_text(self, original_text: str) -> str:
        return self.context.text(original_text)


def _resolve_song_line(original_text: str, start: int, end: int) -> tuple[TextSpan, str | None]:
    if "\n" in original_text[start:end]:
        raise SelectionError(
            "selection_spans_lines", "Selection must be within a single lyric line."
        )
    lines = lyric_lines(original_text)
    index = find_line_index(lines, start, end)
    if index is None:
        raise SelectionError(
            "selection_not_in_lyric_line",
            "Section headers and blank lines can't be selected.",
        )
    return lines[index], surrounding_lines_context(original_text, lines, index)


def resolve_selection(
    analysis: ArticleAnalysisResult,
    original_text: str,
    start: int,
    end: int,
    kind: str = "text",
) -> ResolvedSelection:
    """Resolves a client-sent {start, end} span against the article's own stored analysis.

    Both offsets must exactly match real token boundaries (never an arbitrary mid-token
    slice), and the whole span must fit within one context unit: one stored sentence for
    texts, one lyric line for songs (`kind == "song"`).
    """
    tokens = [token for token in analysis.tokens if token.start >= start and token.end <= end]
    tokens.sort(key=lambda token: token.start)

    if not tokens or tokens[0].start != start or tokens[-1].end != end:
        raise SelectionError(
            "selection_misaligned", "Selection does not align to token boundaries."
        )

    sentence = next(
        (s for s in analysis.sentences if s.start <= start and end <= s.end),
        None,
    )
    surrounding_context = None
    if kind == SONG_KIND:
        context, surrounding_context = _resolve_song_line(original_text, start, end)
    else:
        if sentence is None:
            raise SelectionError(
                "selection_spans_sentences", "Selection must be within a single sentence."
            )
        context = TextSpan(sentence.start, sentence.end)

    surface_text = original_text[start:end]

    separable_verb = None
    if len(tokens) == 1:
        token_index = analysis.tokens.index(tokens[0])
        separable_verb = next(
            (
                verb
                for verb in analysis.separable_verbs
                if verb.verb_token_index == token_index or verb.particle_token_index == token_index
            ),
            None,
        )

    if separable_verb is not None:
        lemma, pos = separable_verb.lemma, SEPARABLE_VERB_POS
    elif len(tokens) == 1:
        lemma, pos = tokens[0].lemma, tokens[0].pos
    else:
        lemma, pos = surface_text, PHRASE_POS

    return ResolvedSelection(
        tokens=tokens,
        sentence=sentence,
        surface_text=surface_text,
        lemma=lemma,
        pos=pos,
        separable_verb=separable_verb,
        context=context,
        surrounding_context=surrounding_context,
    )

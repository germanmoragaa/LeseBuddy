from dataclasses import dataclass

from app.schemas.analysis import ArticleAnalysisResult
from app.services.nlp.types import Sentence, SeparableVerb, Token

# Marker pos strings for selections that don't correspond to a single spaCy token — used to
# route dictionary lookups, never sent to spaCy or stored as a real UPOS tag.
SEPARABLE_VERB_POS = "VERB"
PHRASE_POS = "PHRASE"


class SelectionError(Exception):
    """Raised when {start, end} doesn't align to real token boundaries from the stored
    analysis, or doesn't fit within a single stored sentence. Never trust client-sent
    offsets without this check — see docs/decisions/0004-translations-and-dictionary.md."""


@dataclass
class ResolvedSelection:
    tokens: list[Token]
    sentence: Sentence
    surface_text: str
    lemma: str
    pos: str
    separable_verb: SeparableVerb | None

    @property
    def is_separable_verb(self) -> bool:
        return self.separable_verb is not None

    @property
    def is_phrase(self) -> bool:
        return len(self.tokens) > 1


def resolve_selection(
    analysis: ArticleAnalysisResult, original_text: str, start: int, end: int
) -> ResolvedSelection:
    """Resolves a client-sent {start, end} span against the article's own stored analysis.

    Both offsets must exactly match real token boundaries (never an arbitrary mid-token
    slice), and the whole span must fit within exactly one stored sentence.
    """
    tokens = [token for token in analysis.tokens if token.start >= start and token.end <= end]
    tokens.sort(key=lambda token: token.start)

    if not tokens or tokens[0].start != start or tokens[-1].end != end:
        raise SelectionError("Selection does not align to token boundaries.")

    sentence = next(
        (s for s in analysis.sentences if s.start <= start and end <= s.end),
        None,
    )
    if sentence is None:
        raise SelectionError("Selection must be within a single sentence.")

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
    )

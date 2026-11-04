from app.services.nlp.pipeline import get_nlp
from app.services.nlp.types import AnalysisResult, Sentence, SeparableVerb, Token


def analyze_text(text: str) -> AnalysisResult:
    """Runs the German spaCy pipeline over `text` and returns our own types.

    `text` must already be the stored, NFC-normalized original_text — offsets below are
    Unicode code points into exactly that string (Python `str` indices already are code
    points, so `token.idx` needs no conversion; see docs/decisions/0003-nlp-pipeline.md for
    why the UTF-16-vs-code-point conversion happens on the frontend instead).
    """
    doc = get_nlp()(text)

    tokens = [
        Token(
            text=token.text,
            start=token.idx,
            end=token.idx + len(token.text),
            whitespace_after=token.whitespace_,
            is_punct=token.is_punct,
            is_space=token.is_space,
            lemma=token.lemma_,
            pos=token.pos_,
            morph=token.morph.to_dict(),
        )
        for token in doc
    ]

    sentences = [Sentence(start=sent.start_char, end=sent.end_char) for sent in doc.sents]

    # "svp" (separable verb particle) is the German dependency scheme's label for exactly
    # this relation; "PTKVZ" is the matching STTS fine-grained tag. Requiring both cuts false
    # positives from either signal alone. Known miss: in a "zu"-infinitive construction (e.g.
    # "fing ... an zu weinen"), the particle gets dep_="pm" with the infinitive as its head,
    # not dep_="svp" with the finite verb — undetected by design, see the ADR.
    separable_verbs = [
        SeparableVerb(
            lemma=f"{token.lemma_.lower()}{token.head.lemma_.lower()}",
            verb_token_index=token.head.i,
            particle_token_index=token.i,
        )
        for token in doc
        if token.dep_ == "svp" and token.tag_ == "PTKVZ"
    ]

    return AnalysisResult(tokens=tokens, sentences=sentences, separable_verbs=separable_verbs)

from pydantic import BaseModel


class Token(BaseModel):
    text: str
    start: int
    end: int
    # spaCy's own trailing-whitespace string ("" or " ", occasionally more for runs of
    # whitespace). Rendering token.text followed by whitespace_after for every token, in
    # order, reproduces the original text exactly — mirrors spaCy's own
    # `"".join(t.text_with_ws for t in doc) == doc.text` invariant.
    whitespace_after: str
    is_punct: bool
    is_space: bool
    lemma: str
    # Coarse universal POS tag (NOUN, VERB, ADJ, ...). A learner-friendly label is a frontend
    # concern, not this layer's.
    pos: str
    # Whatever morphological features spaCy's statistical morphologizer detected for this
    # token (e.g. {"Gender": "Fem", "Case": "Nom", "Number": "Sing"}). A guess, not a verified
    # dictionary fact — callers must present it as "detected", never as ground truth.
    morph: dict[str, str]


class Sentence(BaseModel):
    start: int
    end: int


class SeparableVerb(BaseModel):
    # Combined infinitive, e.g. "anrufen" from "rufe ... an". Best-effort: see
    # docs/decisions/0003-nlp-pipeline.md for when this can be wrong.
    lemma: str
    verb_token_index: int
    particle_token_index: int


class AnalysisResult(BaseModel):
    tokens: list[Token]
    sentences: list[Sentence]
    separable_verbs: list[SeparableVerb]

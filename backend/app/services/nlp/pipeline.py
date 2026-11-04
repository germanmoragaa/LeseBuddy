import spacy
from spacy.language import Language

MODEL_NAME = "de_core_news_md"

_nlp: Language | None = None


def get_nlp() -> Language:
    """Loads the German spaCy pipeline once per process, not once per request.

    A module-level singleton rather than e.g. `lru_cache` on a free function: it makes the
    "loaded exactly once, lazily, on first use" contract explicit and keeps `spacy.Language`
    (and every other spaCy object) from leaking past this module — the rest of the app only
    ever sees our own `app.services.nlp.types` types.
    """
    global _nlp
    if _nlp is None:
        _nlp = spacy.load(MODEL_NAME)
    return _nlp

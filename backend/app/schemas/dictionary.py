from pydantic import BaseModel, ConfigDict


class DictionaryEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pos: str
    gender: str | None
    plural: str | None
    glosses: list[str]
    # Deliberately NOT named "source" — the ORM model already has a `source` column holding
    # the dataset provenance (e.g. "kaikki-de-extract"), and from_attributes validation would
    # silently pick that up instead of this field's intended "dictionary" UI label.
    source_label: str = "dictionary"


class DictionaryLookupResponse(BaseModel):
    lemma: str
    pos_detected: str
    is_separable_verb: bool
    entry: DictionaryEntryRead | None

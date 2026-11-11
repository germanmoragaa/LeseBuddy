from pydantic import BaseModel, ConfigDict, computed_field

# Standard nominative article per spaCy/dictionary gender code. The only exception - a
# plurale-tantum noun with no gender at all still getting "die" - is handled in `article`
# below, not here, since it has nothing to do with gender.
GENDER_TO_ARTICLE = {"Masc": "der", "Fem": "die", "Neut": "das"}


class DictionaryEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pos: str
    gender: str | None
    plural_only: bool
    plural: str | None
    glosses: list[str]
    # Deliberately NOT named "source" — the ORM model already has a `source` column holding
    # the dataset provenance (e.g. "kaikki-de-extract"), and from_attributes validation would
    # silently pick that up instead of this field's intended "dictionary" UI label.
    source_label: str = "dictionary"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def article(self) -> str | None:
        """Nominative article (der/die/das) derived from gender, or "die" for a
        plurale-tantum noun that has no gender at all (e.g. "Eltern"). None when neither is
        known - never guessed."""
        if self.gender is not None:
            return GENDER_TO_ARTICLE.get(self.gender)
        if self.plural_only:
            return "die"
        return None


class DictionaryLookupResponse(BaseModel):
    lemma: str
    pos_detected: str
    is_separable_verb: bool
    entry: DictionaryEntryRead | None

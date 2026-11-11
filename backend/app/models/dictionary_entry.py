from sqlalchemy import Boolean, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class DictionaryEntry(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One row per Wiktionary sense-bearing headword+pos, imported from kaikki.org's
    English-Wiktionary German-filtered extract (see the import script and
    docs/decisions/0004-translations-and-dictionary.md). Deliberately has NO uniqueness
    constraint on (lemma, pos): German has real heteronyms (e.g. "der/die Kiefer" — jaw vs.
    pine, same spelling, same POS, different gender) that a naive unique constraint would
    wrongly collapse into one row. An unresolved, documented MVP limitation, not a bug.
    """

    __tablename__ = "dictionary_entries"

    lemma: Mapped[str] = mapped_column(String(255), nullable=False)
    # Kept verbatim from the source dataset (e.g. "noun", "verb", "phrase") — never filtered
    # to an allowlist, since idiom/phrase entries need pos=="phrase" to survive import.
    pos: Mapped[str] = mapped_column(String(32), nullable=False)
    # Normalized to spaCy's own morph codes ("Fem"/"Masc"/"Neut") at import time, not the
    # source dataset's own "masculine"/"feminine"/"neuter" tag strings — see the import
    # script. This is what lets "dictionary overrides spaCy's detected gender" be a plain
    # value swap with no second vocabulary involved.
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # True only for genuine plurale-tantum nouns (e.g. "Eltern", "Kosten"): no gender tag at
    # all, and the source's forms are exclusively plural (no nominative singular exists to
    # have a gender). Kept as its own flag rather than folded into `gender` because these
    # nouns still need a nominative article ("die") shown even though they have no singular
    # gender to derive it from — see app/schemas/dictionary.py's article derivation.
    plural_only: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    plural: Mapped[str | None] = mapped_column(String(255), nullable=True)
    glosses: Mapped[list] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    # The dump-date string the source reported at download time — kaikki.org has no stable,
    # dated download URL, so this is the closest thing to a pinned version. See the ADR.
    source_version: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (Index("ix_dictionary_entries_lemma_lower", func.lower(lemma)),)

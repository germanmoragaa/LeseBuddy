import uuid

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VocabularyItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user's canonical saved word/expression. Unique per user on the normalized
    lemma/expression — heteronym collisions (e.g. "der/die Kiefer") are an accepted,
    documented MVP limitation, not something this constraint tries to fix (widening it to
    include part_of_speech wouldn't fix that example either, since both are nouns — see
    docs/decisions/0004-translations-and-dictionary.md). All grammar/translation data below
    is a snapshot copied at save time: this table never depends on translation_cache or
    dictionary_entries staying unchanged later.
    """

    __tablename__ = "vocabulary_items"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lemma: Mapped[str] = mapped_column(String(255), nullable=False)
    display_form: Mapped[str] = mapped_column(String(255), nullable=False)
    # Deprecated: `meaning` (first dictionary gloss) and `translation` (DeepL contextual
    # translation) are dual-written alongside `meanings` until the UI reads only that - see
    # docs/architecture.md's follow-up list.
    meaning: Mapped[str | None] = mapped_column(Text, nullable=True)
    translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Ordered list of {"text", "source": "machine" | "dictionary", "sense_label"?} - the
    # contextual machine translation first, then dictionary translations in the user's
    # language. Deduplicated case-insensitively on "text" (vocabulary_service.merge_meanings).
    meanings: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    # The occurrence shown on the flashcard; NULL falls back to the first one saved.
    example_occurrence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("article_vocabulary.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    part_of_speech: Mapped[str] = mapped_column(String(32), nullable=False)
    # Snapshot of detected/dictionary morphology (e.g. {"gender": "Fem", "plural": "..."}).
    grammar_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Read-only: membership changes go through deck_service's explicit Core statements (bulk
    # ON CONFLICT DO NOTHING / targeted DELETE), never through collection mutation here, so
    # the ORM never tries to manage deck_items rows itself and step on those statements.
    decks: Mapped[list["Deck"]] = relationship(  # noqa: F821
        "Deck",
        secondary="deck_items",
        back_populates="vocabulary_items",
        viewonly=True,
        # selectin: one extra batched query for however many items were just loaded, not one
        # query per item - the "deck_ids on every vocabulary item response" requirement must
        # not turn a 20-item list page into 20+ queries.
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_vocabulary_items_user_lemma_lower", "user_id", func.lower(lemma), unique=True),
    )

    @property
    def deck_ids(self) -> list[uuid.UUID]:
        return [deck.id for deck in self.decks]

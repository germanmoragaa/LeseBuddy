import uuid

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

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
    meaning: Mapped[str | None] = mapped_column(Text, nullable=True)
    translation: Mapped[str | None] = mapped_column(Text, nullable=True)
    part_of_speech: Mapped[str] = mapped_column(String(32), nullable=False)
    # Snapshot of detected/dictionary morphology (e.g. {"gender": "Fem", "plural": "..."}).
    grammar_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_vocabulary_items_user_lemma_lower", "user_id", func.lower(lemma), unique=True),
    )

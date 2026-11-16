import uuid

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Deck(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user-defined, named grouping of vocabulary items for focused review.

    Decks are a pure filter over which flashcards get reviewed - SRS scheduling state lives
    entirely on Flashcard (one row per vocabulary item, never duplicated per deck), so
    reviewing a word while studying one deck updates its due date everywhere, including
    "All cards" and any other deck the same word happens to belong to.
    """

    __tablename__ = "decks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)

    vocabulary_items: Mapped[list["VocabularyItem"]] = relationship(  # noqa: F821
        "VocabularyItem", secondary="deck_items", back_populates="decks", viewonly=True
    )

    __table_args__ = (
        Index("ix_decks_user_id_name_lower", "user_id", func.lower(name), unique=True),
    )

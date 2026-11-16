import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DeckItem(Base):
    """Many-to-many membership between a Deck and a VocabularyItem.

    Composite primary key (no surrogate id) since the pair alone identifies a membership and
    doubles as the "already a member" uniqueness check that makes bulk-add idempotent (see
    deck_service.add_items_to_deck's ON CONFLICT DO NOTHING). The separate index on
    `vocabulary_item_id` alone backs the reverse lookups ("which decks is this word in",
    "is this card due within deck X") that the composite PK's leading column doesn't cover.
    """

    __tablename__ = "deck_items"

    deck_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("decks.id", ondelete="CASCADE"), primary_key=True
    )
    vocabulary_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vocabulary_items.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_deck_items_vocabulary_item_id", "vocabulary_item_id"),)

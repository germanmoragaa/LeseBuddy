import uuid

from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ArticleVocabulary(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One occurrence of a saved vocabulary item in a specific article. Deleting the
    article cascades here (via the FK below) without touching the canonical
    VocabularyItem row — see docs/blueprint.md section 7's deletion policy and
    docs/decisions/0004-translations-and-dictionary.md.
    """

    __tablename__ = "article_vocabulary"

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vocabulary_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vocabulary_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    context_sentence: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        # An exact span in a given article can only ever resolve to one meaning, so this
        # alone — not including vocabulary_item_id — is enough to make "don't create a
        # duplicate occurrence for the same offsets" a plain unique constraint.
        Index(
            "ix_article_vocabulary_article_offsets",
            "article_id",
            "start_offset",
            "end_offset",
            unique=True,
        ),
    )

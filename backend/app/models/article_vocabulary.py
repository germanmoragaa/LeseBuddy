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
    # Deprecated: dual-written with `context_line` until the UI reads only that - see
    # docs/architecture.md's follow-up list.
    context_sentence: Mapped[str] = mapped_column(Text, nullable=False)
    # The occurrence's context: the lyric line for songs, the sentence for plain texts (see
    # selection.resolve_selection). Nullable only for rows saved before this column existed,
    # until backfill_vocabulary_cards fills them.
    context_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    # DeepL translation of `context_line`; NULL means it failed (or predates the column) and
    # can be retried via POST /api/v1/vocabulary/occurrences/{id}/retry-translation.
    context_translation: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def needs_translation(self) -> bool:
        return self.context_translation is None

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

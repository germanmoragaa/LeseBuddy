from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class TranslationCache(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Keyed by user-independent inputs only (no user_id) — the same word in the same
    sentence is translated at most once, regardless of who asks. `cache_key` is a single
    sha256 hash of (source_text, context, target_lang, provider); `source_text`/`context` are
    stored as plain columns alongside it purely for debuggability, not for the lookup itself.
    """

    __tablename__ = "translation_cache"

    cache_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_lang: Mapped[str] = mapped_column(String(8), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (Index("ix_translation_cache_cache_key", "cache_key", unique=True),)

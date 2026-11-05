import uuid

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class DictionaryForm(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Inflected-form -> entry index, for looking up a dictionary entry by surface form
    when it doesn't match the entry's own lemma directly (e.g. "Bücher" -> "Buch")."""

    __tablename__ = "dictionary_forms"

    form: Mapped[str] = mapped_column(String(255), nullable=False)
    dictionary_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dictionary_entries.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (Index("ix_dictionary_forms_form_lower", func.lower(form)),)

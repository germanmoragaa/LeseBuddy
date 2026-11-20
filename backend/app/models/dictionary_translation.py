import uuid

from sqlalchemy import ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class DictionaryTranslation(UUIDPrimaryKeyMixin, Base):
    """One translation of a dictionary entry into another language, imported from the
    entry's Wiktionary "Übersetzungen" section (only the languages in
    import_dictionary.TRANSLATION_LANGS). `sense_index`/`sense_label` keep which sense of the
    German word it translates (e.g. "2", "Bescheinigung, Geldnote, ..."). Replaced wholesale
    by every import, together with dictionary_entries - nothing outside the dictionary tables
    may reference these ids."""

    __tablename__ = "dictionary_translations"

    entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dictionary_entries.id", ondelete="CASCADE"), nullable=False
    )
    lang: Mapped[str] = mapped_column(String(8), nullable=False)
    word: Mapped[str] = mapped_column(String(255), nullable=False)
    sense_index: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sense_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Order within the entry's source translation list: Wiktionary lists the most common
    # translation of a sense first, and the random UUID ids can't preserve that.
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")

    __table_args__ = (Index("ix_dictionary_translations_entry_id_lang", "entry_id", "lang"),)

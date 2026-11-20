"""add vocabulary card fields and dictionary translations

Revision ID: a3c9e1f27b64
Revises: f4fdad8cdd95
Create Date: 2026-11-19 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a3c9e1f27b64"
down_revision: str | Sequence[str] | None = "f4fdad8cdd95"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Written by hand: autogenerate also proposes the known cosmetic dictionary-index renames
    # (see 2ff06291449d's note), which aren't a real schema difference.

    # Nullable, no default: a metadata-only ALTER even on the multi-million-row live table.
    # Existing rows stay NULL ("not a form-of entry") until the next full import fills it.
    op.add_column(
        "dictionary_entries",
        sa.Column("form_of_lemma", sa.String(length=255), nullable=True),
    )

    op.create_table(
        "dictionary_translations",
        sa.Column("entry_id", sa.UUID(), nullable=False),
        sa.Column("lang", sa.String(length=8), nullable=False),
        sa.Column("word", sa.String(length=255), nullable=False),
        sa.Column("sense_index", sa.String(length=32), nullable=True),
        sa.Column("sense_label", sa.Text(), nullable=True),
        sa.Column("position", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["entry_id"],
            ["dictionary_entries.id"],
            name=op.f("fk_dictionary_translations_entry_id_dictionary_entries"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dictionary_translations")),
    )
    op.create_index(
        "ix_dictionary_translations_entry_id_lang",
        "dictionary_translations",
        ["entry_id", "lang"],
        unique=False,
    )

    op.add_column("article_vocabulary", sa.Column("context_line", sa.Text(), nullable=True))
    op.add_column("article_vocabulary", sa.Column("context_translation", sa.Text(), nullable=True))

    op.add_column(
        "vocabulary_items",
        sa.Column(
            "meanings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )
    op.add_column("vocabulary_items", sa.Column("example_occurrence_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f("fk_vocabulary_items_example_occurrence_id_article_vocabulary"),
        "vocabulary_items",
        "article_vocabulary",
        ["example_occurrence_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("fk_vocabulary_items_example_occurrence_id_article_vocabulary"),
        "vocabulary_items",
        type_="foreignkey",
    )
    op.drop_column("vocabulary_items", "example_occurrence_id")
    op.drop_column("vocabulary_items", "meanings")
    op.drop_column("article_vocabulary", "context_translation")
    op.drop_column("article_vocabulary", "context_line")
    # DROP TABLE also removes whatever index/FK names a later staging swap left behind.
    op.drop_table("dictionary_translations")
    op.drop_column("dictionary_entries", "form_of_lemma")

"""create decks and deck items tables

Revision ID: 2ff06291449d
Revises: 9a6ae464c930
Create Date: 2026-11-11 15:20:43.579648

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ff06291449d"
down_revision: str | Sequence[str] | None = "9a6ae464c930"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Note: autogenerate also proposed dropping/recreating the dictionary lemma/form
    # lower-case indexes under their pre-staging-swap names - that's the known cosmetic
    # naming leftover from import_dictionary.py's staging-table swap (see that module's
    # docstring), not a real schema difference. Left out here; only the two new tables below
    # are a real change.
    op.create_table(
        "decks",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_decks_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_decks")),
    )
    op.create_index(op.f("ix_decks_user_id"), "decks", ["user_id"], unique=False)
    op.create_index(
        "ix_decks_user_id_name_lower",
        "decks",
        ["user_id", sa.literal_column("lower(name)")],
        unique=True,
    )
    op.create_table(
        "deck_items",
        sa.Column("deck_id", sa.UUID(), nullable=False),
        sa.Column("vocabulary_item_id", sa.UUID(), nullable=False),
        sa.Column(
            "added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["deck_id"], ["decks.id"], name=op.f("fk_deck_items_deck_id_decks"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["vocabulary_item_id"],
            ["vocabulary_items.id"],
            name=op.f("fk_deck_items_vocabulary_item_id_vocabulary_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("deck_id", "vocabulary_item_id", name=op.f("pk_deck_items")),
    )
    op.create_index(
        "ix_deck_items_vocabulary_item_id", "deck_items", ["vocabulary_item_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_deck_items_vocabulary_item_id", table_name="deck_items")
    op.drop_table("deck_items")
    op.drop_index("ix_decks_user_id_name_lower", table_name="decks")
    op.drop_index(op.f("ix_decks_user_id"), table_name="decks")
    op.drop_table("decks")

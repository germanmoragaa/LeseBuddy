"""add last_opened_at and reading_position to articles

Revision ID: b512b81b909c
Revises: 2ff06291449d
Create Date: 2026-11-11 16:05:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b512b81b909c"
down_revision: str | Sequence[str] | None = "2ff06291449d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "articles", sa.Column("last_opened_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("articles", sa.Column("reading_position", sa.Integer(), nullable=True))
    op.create_index(
        "ix_articles_user_id_last_opened_at",
        "articles",
        ["user_id", "last_opened_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_articles_user_id_last_opened_at", table_name="articles")
    op.drop_column("articles", "reading_position")
    op.drop_column("articles", "last_opened_at")

"""add plural_only flag to dictionary entries

Revision ID: 9a6ae464c930
Revises: 1186faada3d7
Create Date: 2026-11-10 10:10:15.077398

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a6ae464c930"
down_revision: str | Sequence[str] | None = "1186faada3d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Note: autogenerate also proposed dropping/recreating the lemma/form lower-case indexes
    # under their pre-staging-swap names — that's the known cosmetic naming leftover from
    # import_dictionary.py's staging-table swap (see that module's docstring), not a real
    # schema difference. Left out here; only the new column is a real change.
    op.add_column(
        "dictionary_entries",
        sa.Column("plural_only", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("dictionary_entries", "plural_only")

"""add songs.cover_thumbnail_url

Revision ID: c5d2b8e41a09
Revises: a3c9e1f27b64
Create Date: 2026-11-20 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5d2b8e41a09"
down_revision: str | Sequence[str] | None = "a3c9e1f27b64"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("songs", sa.Column("cover_thumbnail_url", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    op.drop_column("songs", "cover_thumbnail_url")

"""add article kind and songs table

Revision ID: f4fdad8cdd95
Revises: b512b81b909c
Create Date: 2026-11-17 10:56:04.078690

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4fdad8cdd95"
down_revision: str | Sequence[str] | None = "b512b81b909c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Written by hand: autogenerate also proposes the known cosmetic dictionary-index
    # renames (see 2ff06291449d's note), which aren't a real schema difference.

    # A constant server default backfills every existing row as 'text' without a table
    # rewrite (Postgres 11+), so NOT NULL can be added in the same step.
    op.add_column(
        "articles",
        sa.Column("kind", sa.String(length=16), server_default="text", nullable=False),
    )
    op.create_check_constraint(op.f("ck_articles_kind"), "articles", "kind IN ('text', 'song')")
    # Target for songs' composite FK, so a song can never belong to another user's article.
    op.create_unique_constraint("uq_articles_id_user_id", "articles", ["id", "user_id"])

    op.create_table(
        "songs",
        sa.Column("article_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("genius_song_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("primary_artist", sa.String(length=255), nullable=False),
        sa.Column("album", sa.String(length=255), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("release_date_display", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.String(length=2048), nullable=True),
        sa.Column("genius_url", sa.String(length=2048), nullable=True),
        sa.Column("metadata_fetched_at", sa.DateTime(timezone=True), nullable=True),
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
            ["article_id", "user_id"],
            ["articles.id", "articles.user_id"],
            name=op.f("fk_songs_article_id_articles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("article_id", name=op.f("pk_songs")),
    )
    op.create_index(op.f("ix_songs_user_id"), "songs", ["user_id"], unique=False)
    op.create_index(
        "ix_songs_user_id_genius_song_id",
        "songs",
        ["user_id", "genius_song_id"],
        unique=True,
        postgresql_where=sa.text("genius_song_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_songs_user_id_genius_song_id", table_name="songs")
    op.drop_index(op.f("ix_songs_user_id"), table_name="songs")
    op.drop_table("songs")
    op.drop_constraint("uq_articles_id_user_id", "articles", type_="unique")
    op.drop_constraint(op.f("ck_articles_kind"), "articles", type_="check")
    op.drop_column("articles", "kind")

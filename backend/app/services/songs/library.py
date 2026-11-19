"""Saving a Genius song into the user's private library (ADR 0006).

The client sends only a Genius id and the lyrics it pasted. Every piece of metadata is
re-fetched from the provider by that id: a client-sent title/artist/cover is never trusted,
the same rule vocabulary save follows for lemmas and translations.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Article, Song, User
from app.schemas.article import ArticleCreate
from app.services.article_service import create_article
from app.services.songs.cache import TTLCache
from app.services.songs.provider import SongProvider
from app.services.songs.service import get_song_metadata


class SongAlreadySavedError(Exception):
    def __init__(self, article_id: uuid.UUID) -> None:
        super().__init__(f"song already saved as article {article_id}")
        self.article_id = article_id


def find_saved_song_article_id(db: Session, user: User, genius_id: int) -> uuid.UUID | None:
    return db.scalar(
        select(Song.article_id).where(Song.user_id == user.id, Song.genius_song_id == genius_id)
    )


def save_genius_song(
    db: Session,
    user: User,
    provider: SongProvider,
    cache: TTLCache,
    *,
    genius_id: int,
    lyrics_text: str,
) -> Article:
    # Checked before calling the provider, so re-adding a saved song costs no Genius request.
    existing = find_saved_song_article_id(db, user, genius_id)
    if existing is not None:
        raise SongAlreadySavedError(existing)

    metadata = get_song_metadata(provider, cache, genius_id)
    song = Song(
        genius_song_id=metadata.genius_id,
        title=metadata.title[:255],
        primary_artist=metadata.primary_artist[:255],
        album=metadata.album[:255] if metadata.album else None,
        release_date=metadata.release_date,
        release_date_display=metadata.release_date_display,
        cover_url=metadata.cover_url,
        genius_url=metadata.genius_url,
        metadata_fetched_at=datetime.now(UTC),
    )
    try:
        return create_article(
            db,
            user,
            ArticleCreate(title=metadata.title[:255], original_text=lyrics_text),
            song=song,
        )
    except IntegrityError:
        # Two concurrent saves of the same song both passed the pre-check: the partial
        # unique index lets exactly one win. Same pattern as auth_service.register_user.
        db.rollback()
        existing = find_saved_song_article_id(db, user, genius_id)
        if existing is None:
            raise
        raise SongAlreadySavedError(existing) from None

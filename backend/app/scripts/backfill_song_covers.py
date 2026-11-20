"""One-off: fill cover_url / cover_thumbnail_url for saved Genius songs that have none.

    uv run python -m app.scripts.backfill_song_covers

Only songs with a genius_song_id and a missing cover field are touched, and only their empty
fields are filled, so re-running is a no-op. Metadata comes from Genius' official API through
the songs service (cached per Genius id), never from a web page. Covers stay hotlinked URLs -
no image is ever downloaded (ADR 0006).
"""

from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_song_cache, get_song_provider
from app.core.db import UntimedSessionLocal
from app.models import Song
from app.services.songs.cache import TTLCache
from app.services.songs.provider import (
    SongNotFoundError,
    SongProvider,
    SongsProviderError,
    SongsTimeoutError,
)
from app.services.songs.service import get_song_metadata


@dataclass
class CoverBackfillStats:
    songs_missing_cover: int = 0
    covers_filled: int = 0
    thumbnails_filled: int = 0
    still_without_cover: int = 0
    provider_errors: int = 0


def backfill_song_covers(
    db: Session, provider: SongProvider, cache: TTLCache
) -> CoverBackfillStats:
    stats = CoverBackfillStats()
    songs = db.scalars(
        select(Song)
        .where(
            Song.genius_song_id.is_not(None),
            or_(Song.cover_url.is_(None), Song.cover_thumbnail_url.is_(None)),
        )
        .order_by(Song.created_at)
    ).all()
    stats.songs_missing_cover = len(songs)

    for song in songs:
        try:
            metadata = get_song_metadata(provider, cache, song.genius_song_id)
        except (SongNotFoundError, SongsProviderError, SongsTimeoutError):
            # A missing or failing song keeps its fallback tile; the next run retries it.
            # SongsNotConfiguredError propagates: without a token nothing can be filled.
            stats.provider_errors += 1
            if song.cover_url is None:
                stats.still_without_cover += 1
            continue
        if song.cover_url is None and metadata.cover_url is not None:
            song.cover_url = metadata.cover_url
            stats.covers_filled += 1
        if song.cover_thumbnail_url is None and metadata.cover_thumbnail_url is not None:
            song.cover_thumbnail_url = metadata.cover_thumbnail_url
            stats.thumbnails_filled += 1
        if song.cover_url is None:
            stats.still_without_cover += 1

    db.commit()
    return stats


def main() -> None:
    session = UntimedSessionLocal()
    try:
        stats = backfill_song_covers(session, get_song_provider(), get_song_cache())
    finally:
        session.close()
    for field, value in vars(stats).items():
        print(f"{field}: {value}")


if __name__ == "__main__":
    main()

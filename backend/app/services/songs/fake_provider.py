from dataclasses import dataclass, field
from datetime import date

from app.services.songs.provider import (
    SongMetadata,
    SongNotFoundError,
    SongSearchResult,
)

# Invented songs and artists — never real ones, and no lyrics anywhere (ADR 0006).
FAKE_SONGS: tuple[SongMetadata, ...] = (
    SongMetadata(
        genius_id=900001,
        title="Nachtlicht",
        primary_artist="Die Erfundenen",
        album="Lieder aus Papier",
        release_date=date(2021, 5, 14),
        release_date_display="May 14, 2021",
        cover_url="https://images.example.test/nachtlicht-1000x1000.jpg",
        genius_url="https://genius.example.test/die-erfundenen-nachtlicht",
        language="de",
    ),
    SongMetadata(
        genius_id=900002,
        title="Nachtclub Nights",
        primary_artist="The Inventions",
        album=None,
        release_date=None,
        release_date_display="2019",
        cover_url="https://images.example.test/nachtclub-nights-1000x1000.jpg",
        genius_url="https://genius.example.test/the-inventions-nachtclub-nights",
        language="en",
    ),
    SongMetadata(
        genius_id=900003,
        title="Nachtzug nach Nirgendwo",
        primary_artist="Die Erfundenen",
        album="Lieder aus Papier",
        release_date=date(2021, 5, 14),
        release_date_display="May 14, 2021",
        cover_url=None,
        genius_url="https://genius.example.test/die-erfundenen-nachtzug-nach-nirgendwo",
        language="de",
    ),
    SongMetadata(
        genius_id=900004,
        title="Sommerregen",
        primary_artist="Kapelle Ohnenamen",
        album=None,
        release_date=None,
        release_date_display=None,
        cover_url=None,
        genius_url=None,
        language=None,
    ),
)


def _release_year(song: SongMetadata) -> int | None:
    if song.release_date is not None:
        return song.release_date.year
    if song.release_date_display is not None and song.release_date_display.isdigit():
        return int(song.release_date_display)
    return None


def _to_search_result(song: SongMetadata) -> SongSearchResult:
    return SongSearchResult(
        genius_id=song.genius_id,
        title=song.title,
        primary_artist=song.primary_artist,
        thumbnail_url=(song.cover_url.replace("1000x1000", "300x300") if song.cover_url else None),
        cover_url=song.cover_url,
        genius_url=song.genius_url,
        release_date_display=song.release_date_display,
        release_year=_release_year(song),
        language=song.language,
    )


@dataclass
class FakeSongProvider:
    """In-memory test double — the only SongProvider tests and CI ever use. Deterministic:
    `search` matches the query case-insensitively against title or artist, in FAKE_SONGS
    order (English before German on purpose, so ranking is observable). Set `fail_with` to an
    exception instance to simulate a provider failure."""

    songs: tuple[SongMetadata, ...] = FAKE_SONGS
    search_calls: list[tuple[str, int]] = field(default_factory=list)
    get_song_calls: list[int] = field(default_factory=list)
    fail_with: Exception | None = None

    def search(self, query: str, limit: int) -> list[SongSearchResult]:
        if self.fail_with is not None:
            raise self.fail_with
        self.search_calls.append((query, limit))
        needle = query.casefold()
        ordered = sorted(self.songs, key=lambda song: song.language != "en")
        matches = [
            _to_search_result(song)
            for song in ordered
            if needle in song.title.casefold() or needle in song.primary_artist.casefold()
        ]
        return matches[:limit]

    def get_song(self, genius_id: int) -> SongMetadata:
        if self.fail_with is not None:
            raise self.fail_with
        self.get_song_calls.append(genius_id)
        for song in self.songs:
            if song.genius_id == genius_id:
                return song
        raise SongNotFoundError

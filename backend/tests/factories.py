from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Article, Song, User

DEFAULT_PASSWORD = "correct horse battery staple"


def make_user(
    db_session: Session,
    *,
    email: str,
    username: str = "testuser",
    password: str = DEFAULT_PASSWORD,
    email_verified: bool = False,
    created_at: datetime | None = None,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        email_verified_at=datetime.now(UTC) if email_verified else None,
    )
    if created_at is not None:
        user.created_at = created_at
    db_session.add(user)
    db_session.flush()
    return user


# Invented lyric-style lines — never real copyrighted lyrics (see CLAUDE.md, ADR 0006).
SAMPLE_LYRICS = "[Hook]\nIch lauf' durch die Nacht, die Stadt ist noch wach\nUnd ich denk' an dich"


def make_article(
    db_session: Session,
    user: User,
    *,
    original_text: str = "Der Hund läuft im Park.",
    title: str | None = None,
) -> Article:
    article = Article(user_id=user.id, original_text=original_text, title=title)
    db_session.add(article)
    db_session.flush()
    return article


def make_song(
    db_session: Session,
    user: User,
    *,
    title: str = "Nachtlicht",
    primary_artist: str = "Die Erfundenen",
    genius_song_id: int | None = 1234567,
    album: str | None = "Lieder aus Papier",
    release_date: date | None = date(2021, 5, 14),
    release_date_display: str | None = "May 14, 2021",
    cover_url: str | None = "https://images.genius.com/example-cover.jpg",
    genius_url: str | None = "https://genius.com/Die-erfundenen-nachtlicht-lyrics",
    lyrics: str = SAMPLE_LYRICS,
) -> Article:
    """Creates a kind="song" article plus its songs row. There's no service for this yet
    (phase 3), so tests build it directly; the relationship fills in article_id/user_id."""
    article = Article(user_id=user.id, kind="song", title=title, original_text=lyrics)
    article.song = Song(
        genius_song_id=genius_song_id,
        title=title,
        primary_artist=primary_artist,
        album=album,
        release_date=release_date,
        release_date_display=release_date_display,
        cover_url=cover_url,
        genius_url=genius_url,
        metadata_fetched_at=datetime.now(UTC) if genius_song_id is not None else None,
    )
    db_session.add(article)
    db_session.flush()
    return article

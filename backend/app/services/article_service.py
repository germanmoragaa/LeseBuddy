import unicodedata
import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Article, Song, User
from app.schemas.article import ArticleCreate

ArticleSort = Literal["created", "recent"]


def create_article(
    db: Session, user: User, data: ArticleCreate, *, song: Song | None = None
) -> Article:
    """Creates a "text" article, or a "song" article when `song` (its metadata row) is given.
    A song that violates the per-user Genius-id uniqueness raises IntegrityError on commit;
    rolling back and resolving that is the caller's job (see songs.library.save_genius_song)."""
    article = Article(
        user_id=user.id,
        kind="song" if song is not None else "text",
        title=data.title,
        source_url=data.source_url,
        # NFC-normalize once, here, so every downstream consumer (NLP offsets, future
        # diffing) can rely on original_text already being in a single canonical form.
        original_text=unicodedata.normalize("NFC", data.original_text),
        language=data.language,
    )
    if song is not None:
        # The relationship copies article_id/user_id into the song row on flush.
        article.song = song
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def get_article_for_user(db: Session, user: User, article_id: uuid.UUID) -> Article | None:
    return db.scalar(
        select(Article)
        .options(joinedload(Article.song))
        .where(Article.id == article_id, Article.user_id == user.id)
    )


def list_articles_for_user(
    db: Session, user: User, *, page: int = 1, page_size: int = 20, sort: ArticleSort = "created"
) -> list[tuple[Article, float | None]]:
    # progress_percent is computed in SQL (rather than from the already-loaded
    # original_text in Python) so it stays next to the ORDER BY it informs and is trivial
    # to extend to a server-side progress filter later.
    progress_percent = case(
        (Article.reading_position.is_(None), None),
        else_=Article.reading_position * 100.0 / func.char_length(Article.original_text),
    ).label("progress_percent")
    order_by = (
        func.coalesce(Article.last_opened_at, Article.created_at).desc()
        if sort == "recent"
        else Article.created_at.desc()
    )

    rows = db.execute(
        select(Article, progress_percent)
        # One LEFT OUTER JOIN for the whole page instead of a lazy load per song article.
        .options(joinedload(Article.song))
        .where(Article.user_id == user.id)
        .order_by(order_by)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return [(article, percent) for article, percent in rows]


def count_articles_for_user(db: Session, user: User) -> int:
    return db.scalar(select(func.count()).select_from(Article).where(Article.user_id == user.id))


def update_article(db: Session, article: Article, title: str) -> Article:
    article.title = title
    db.commit()
    db.refresh(article)
    return article


def open_article(db: Session, article: Article) -> Article:
    article.last_opened_at = datetime.now(UTC)
    db.commit()
    db.refresh(article)
    return article


def set_reading_position(db: Session, article: Article, offset: int) -> Article:
    article.reading_position = offset
    db.commit()
    db.refresh(article)
    return article


def delete_article(db: Session, article: Article) -> None:
    """Deletes the article. Cascades (via FK ondelete="CASCADE") to its article_analyses and
    article_vocabulary rows only — vocabulary_items have no FK to articles and are
    untouched, per docs/blueprint.md section 7's deletion policy."""
    db.delete(article)
    db.commit()

import unicodedata
import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import Article, User
from app.schemas.article import ArticleCreate

ArticleSort = Literal["created", "recent"]


def create_article(db: Session, user: User, data: ArticleCreate) -> Article:
    article = Article(
        user_id=user.id,
        title=data.title,
        source_url=data.source_url,
        # NFC-normalize once, here, so every downstream consumer (NLP offsets, future
        # diffing) can rely on original_text already being in a single canonical form.
        original_text=unicodedata.normalize("NFC", data.original_text),
        language=data.language,
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


def get_article_for_user(db: Session, user: User, article_id: uuid.UUID) -> Article | None:
    return db.scalar(select(Article).where(Article.id == article_id, Article.user_id == user.id))


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

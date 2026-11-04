import unicodedata
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Article, User
from app.schemas.article import ArticleCreate


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


def list_articles_for_user(db: Session, user: User) -> list[Article]:
    return list(
        db.scalars(
            select(Article).where(Article.user_id == user.id).order_by(Article.created_at.desc())
        )
    )

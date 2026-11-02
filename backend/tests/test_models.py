import pytest
from factories import make_user
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Article, User


def test_create_user_and_article(db_session: Session) -> None:
    user = make_user(db_session, email="learner@example.com", username="learner")

    article = Article(user_id=user.id, original_text="Der Hund läuft im Park.")
    db_session.add(article)
    db_session.commit()

    stored = db_session.scalar(select(Article).where(Article.id == article.id))
    assert stored is not None
    assert stored.user_id == user.id
    assert stored.language == "de"
    assert stored.title is None
    assert stored.created_at is not None
    assert stored.updated_at is not None


def test_unique_email_constraint(db_session: Session) -> None:
    make_user(db_session, email="duplicate@example.com", username="dup_one")

    db_session.add(User(username="dup_two", email="duplicate@example.com", password_hash="x"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_article_deleted_when_user_deleted(db_session: Session) -> None:
    user = make_user(db_session, email="to-delete@example.com", username="to_delete")

    article = Article(user_id=user.id, original_text="Ein Beispieltext.")
    db_session.add(article)
    db_session.commit()
    article_id = article.id

    db_session.execute(delete(User).where(User.id == user.id))
    db_session.commit()

    remaining = db_session.scalar(select(Article).where(Article.id == article_id))
    assert remaining is None

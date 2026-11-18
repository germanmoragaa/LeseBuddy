"""Database-level guarantees of the songs data model (ADR 0006, phase 1).

Constraint tests insert through Core rather than the ORM relationship on purpose: the
relationship always copies article_id/user_id from the parent article, so it can't express
the invalid rows the database itself must reject. Each rejection asserts the specific
constraint name, so a test can't pass because some unrelated constraint fired instead.
"""

import uuid

import pytest
from factories import make_article, make_song, make_user
from sqlalchemy import func, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Article, Song, User


def _violated_constraint(exc: pytest.ExceptionInfo[IntegrityError]) -> str | None:
    return exc.value.orig.diag.constraint_name  # type: ignore[union-attr]


def _insert_song(
    db_session: Session,
    *,
    article_id: uuid.UUID,
    user_id: uuid.UUID,
    genius_song_id: int | None = None,
) -> None:
    db_session.execute(
        insert(Song).values(
            article_id=article_id,
            user_id=user_id,
            genius_song_id=genius_song_id,
            title="Nachtlicht",
            primary_artist="Die Erfundenen",
        )
    )


def _song_article(db_session: Session, user: User) -> Article:
    return make_article(db_session, user, original_text="Ich lauf' durch die Nacht")


class TestArticleKind:
    def test_orm_default_is_text(self, db_session: Session) -> None:
        user = make_user(db_session, email="a@example.com", username="a")

        article = make_article(db_session, user)
        db_session.expire(article)

        assert article.kind == "text"

    def test_server_default_is_text_for_rows_inserted_without_kind(
        self, db_session: Session
    ) -> None:
        # The migration relies on this server default to backfill pre-existing rows.
        user = make_user(db_session, email="a@example.com", username="a")

        kind = db_session.execute(
            text(
                "INSERT INTO articles (user_id, original_text) VALUES (:user_id, 'Hallo.') "
                "RETURNING kind"
            ),
            {"user_id": user.id},
        ).scalar_one()

        assert kind == "text"

    def test_accepts_song(self, db_session: Session) -> None:
        user = make_user(db_session, email="a@example.com", username="a")

        article = make_song(db_session, user)

        assert db_session.scalar(select(Article.kind).where(Article.id == article.id)) == "song"

    def test_rejects_other_values(self, db_session: Session) -> None:
        user = make_user(db_session, email="a@example.com", username="a")
        db_session.add(Article(user_id=user.id, original_text="Hallo.", kind="podcast"))

        with pytest.raises(IntegrityError) as exc:
            db_session.flush()

        assert _violated_constraint(exc) == "ck_articles_kind"


class TestSongArticleRelationship:
    def test_relationship_loads_song_and_back(self, db_session: Session) -> None:
        user = make_user(db_session, email="a@example.com", username="a")
        article = make_song(db_session, user)
        db_session.expire_all()

        stored = db_session.get(Article, article.id)

        assert stored is not None
        assert stored.song is not None
        assert stored.song.user_id == user.id
        assert stored.song.primary_artist == "Die Erfundenen"
        assert stored.song.article is stored

    def test_text_article_has_no_song(self, db_session: Session) -> None:
        user = make_user(db_session, email="a@example.com", username="a")
        article = make_article(db_session, user)
        db_session.expire_all()

        assert db_session.get(Article, article.id).song is None  # type: ignore[union-attr]

    def test_at_most_one_song_per_article(self, db_session: Session) -> None:
        user = make_user(db_session, email="a@example.com", username="a")
        article = _song_article(db_session, user)
        _insert_song(db_session, article_id=article.id, user_id=user.id)

        with pytest.raises(IntegrityError) as exc:
            _insert_song(db_session, article_id=article.id, user_id=user.id)

        assert _violated_constraint(exc) == "pk_songs"

    def test_deleting_article_through_orm_deletes_song(self, db_session: Session) -> None:
        user = make_user(db_session, email="a@example.com", username="a")
        article = make_song(db_session, user)
        article_id = article.id

        db_session.delete(article)
        db_session.flush()

        remaining = db_session.scalar(
            select(func.count()).select_from(Song).where(Song.article_id == article_id)
        )
        assert remaining == 0

    def test_deleting_article_in_sql_cascades_to_song(self, db_session: Session) -> None:
        # Bypasses the ORM entirely, so this proves the database's ON DELETE CASCADE,
        # not just the relationship's cascade setting.
        user = make_user(db_session, email="a@example.com", username="a")
        article = _song_article(db_session, user)
        _insert_song(db_session, article_id=article.id, user_id=user.id)

        db_session.execute(text("DELETE FROM articles WHERE id = :id"), {"id": article.id})

        remaining = db_session.scalar(
            select(func.count()).select_from(Song).where(Song.article_id == article.id)
        )
        assert remaining == 0

    def test_deleting_user_cascades_through_article_to_song(self, db_session: Session) -> None:
        user = make_user(db_session, email="a@example.com", username="a")
        article = make_song(db_session, user)
        article_id = article.id

        db_session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user.id})

        remaining = db_session.scalar(
            select(func.count()).select_from(Song).where(Song.article_id == article_id)
        )
        assert remaining == 0


class TestSongOwnership:
    def test_rejects_song_whose_user_differs_from_its_articles(self, db_session: Session) -> None:
        owner = make_user(db_session, email="owner@example.com", username="owner")
        other = make_user(db_session, email="other@example.com", username="other")
        article = _song_article(db_session, owner)

        with pytest.raises(IntegrityError) as exc:
            _insert_song(db_session, article_id=article.id, user_id=other.id)

        assert _violated_constraint(exc) == "fk_songs_article_id_articles"

    def test_rejects_song_for_nonexistent_article(self, db_session: Session) -> None:
        user = make_user(db_session, email="a@example.com", username="a")

        with pytest.raises(IntegrityError) as exc:
            _insert_song(db_session, article_id=uuid.uuid4(), user_id=user.id)

        assert _violated_constraint(exc) == "fk_songs_article_id_articles"


class TestGeniusSongIdUniqueness:
    def test_same_user_cannot_save_same_genius_song_twice(self, db_session: Session) -> None:
        user = make_user(db_session, email="a@example.com", username="a")
        first = _song_article(db_session, user)
        second = _song_article(db_session, user)
        _insert_song(db_session, article_id=first.id, user_id=user.id, genius_song_id=42)

        with pytest.raises(IntegrityError) as exc:
            _insert_song(db_session, article_id=second.id, user_id=user.id, genius_song_id=42)

        assert _violated_constraint(exc) == "ix_songs_user_id_genius_song_id"

    def test_different_users_can_save_same_genius_song(self, db_session: Session) -> None:
        alice = make_user(db_session, email="alice@example.com", username="alice")
        bob = make_user(db_session, email="bob@example.com", username="bob")

        make_song(db_session, alice, genius_song_id=42)
        make_song(db_session, bob, genius_song_id=42)

        count = db_session.scalar(
            select(func.count()).select_from(Song).where(Song.genius_song_id == 42)
        )
        assert count == 2

    def test_same_user_can_save_several_songs_without_genius_id(self, db_session: Session) -> None:
        user = make_user(db_session, email="a@example.com", username="a")

        for _ in range(3):
            make_song(db_session, user, genius_song_id=None)

        count = db_session.scalar(
            select(func.count())
            .select_from(Song)
            .where(Song.user_id == user.id, Song.genius_song_id.is_(None))
        )
        assert count == 3

    def test_same_user_can_save_different_genius_songs(self, db_session: Session) -> None:
        user = make_user(db_session, email="a@example.com", username="a")

        make_song(db_session, user, genius_song_id=1)
        make_song(db_session, user, genius_song_id=2)

        count = db_session.scalar(
            select(func.count()).select_from(Song).where(Song.user_id == user.id)
        )
        assert count == 2

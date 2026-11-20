"""Song cover URLs (Genius payload mapping, save, backfill), song list excerpts, and the
lyrics-page cleanup (on save and for existing songs). FakeSongProvider / MockTransport only -
no network. All lyrics are invented lyric-style lines (ADR 0006)."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from factories import make_song, make_user
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Article, ArticleAnalysis, ArticleVocabulary, Song, User, VocabularyItem
from app.scripts.backfill_song_covers import backfill_song_covers
from app.scripts.clean_song_lyrics import clean_song_lyrics
from app.services.lyrics_cleanup import clean_pasted_lyrics
from app.services.songs.cache import TTLCache
from app.services.songs.fake_provider import FakeSongProvider
from app.services.songs.genius_provider import GeniusSongProvider, cover_urls

FIXTURES = Path(__file__).parent / "fixtures" / "genius"
VALID_PASSWORD = "correct horse battery staple"

ART = "https://images.example.test/nachtlicht-1000x1000.jpg"
ART_THUMB = "https://images.example.test/nachtlicht-300x300.jpg"
HEADER_THUMB = "https://images.example.test/nachtlicht-header-300x300.jpg"


def _song_fixture() -> dict[str, Any]:
    return json.loads((FIXTURES / "song.json").read_text(encoding="utf-8"))


def _login_as(client: TestClient, db_session: Session) -> User:
    user = make_user(
        db_session,
        email="alex@example.com",
        username="alex_morgan",
        password=VALID_PASSWORD,
        email_verified=True,
    )
    response = client.post(
        "/api/v1/auth/login", json={"identifier": "alex_morgan", "password": VALID_PASSWORD}
    )
    assert response.status_code == 200
    return user


class TestCoverUrlMapping:
    def test_fixture_payload_has_full_art_and_thumbnail(self) -> None:
        song = _song_fixture()["response"]["song"]

        assert cover_urls(song) == (ART, ART_THUMB)

    def test_get_song_parses_both_urls(self) -> None:
        body = _song_fixture()
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))

        song = GeniusSongProvider("test-token", transport=transport).get_song(900001)

        assert song.cover_url == ART
        assert song.cover_thumbnail_url == ART_THUMB

    @pytest.mark.parametrize(
        ("overrides", "expected"),
        [
            # No full art: the cover falls back to the song-art thumbnail.
            ({"song_art_image_url": None}, (ART_THUMB, ART_THUMB)),
            # No song art at all: the header thumbnail is both.
            (
                {"song_art_image_url": "", "song_art_image_thumbnail_url": None},
                (HEADER_THUMB, HEADER_THUMB),
            ),
            # Only full art: the thumbnail falls back to it.
            (
                {"song_art_image_thumbnail_url": None, "header_image_thumbnail_url": None},
                (ART, ART),
            ),
            (
                {
                    "song_art_image_url": None,
                    "song_art_image_thumbnail_url": None,
                    "header_image_thumbnail_url": None,
                },
                (None, None),
            ),
        ],
    )
    def test_fallbacks(self, overrides: dict[str, Any], expected: tuple) -> None:
        song = {**_song_fixture()["response"]["song"], **overrides}

        assert cover_urls(song) == expected


class TestSaveStoresCoverAndCleansLyrics:
    def test_save_stores_cover_and_thumbnail(self, client: TestClient, db_session: Session) -> None:
        user = _login_as(client, db_session)

        response = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": "Zeile eins"}
        )

        assert response.status_code == 201
        song = db_session.scalar(select(Song).where(Song.user_id == user.id))
        assert (song.cover_url, song.cover_thumbnail_url) == (ART, ART_THUMB)

    def test_save_removes_page_leftovers(self, client: TestClient, db_session: Session) -> None:
        _login_as(client, db_session)
        pasted = (
            "12 ContributorsTranslationsEnglish\n"
            "Nachtlicht Lyrics\n"
            "[Intro]\n"
            "Ich lauf' durch die Nacht\n"
            "You might also like\n"
            "Und die Stadt ist noch wach3Embed"
        )

        response = client.post(
            "/api/v1/songs", json={"genius_song_id": 900001, "lyrics_text": pasted}
        )

        assert response.status_code == 201
        assert response.json()["original_text"] == (
            "[Intro]\nIch lauf' durch die Nacht\nUnd die Stadt ist noch wach"
        )

    def test_only_leftovers_is_a_422_and_creates_nothing(
        self, client: TestClient, db_session: Session
    ) -> None:
        _login_as(client, db_session)

        response = client.post(
            "/api/v1/songs",
            json={"genius_song_id": 900001, "lyrics_text": "Songtext\n5 Contributors\nEmbed"},
        )

        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "lyrics_empty"
        assert db_session.scalar(select(Article)) is None


class TestExcerpt:
    def test_song_excerpt_starts_at_the_first_lyric_line(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _login_as(client, db_session)
        make_song(
            db_session,
            user,
            lyrics="[Intro: Die Erfundenen]\n\n[Hook]\nIch lauf' durch die Nacht\n"
            "[Strophe 1]\nUnd die Stadt ist noch wach",
        )

        item = client.get("/api/v1/articles").json()["items"][0]

        assert item["excerpt"] == "Ich lauf' durch die Nacht / Und die Stadt ist noch wach"

    def test_song_list_item_includes_thumbnail(
        self, client: TestClient, db_session: Session
    ) -> None:
        user = _login_as(client, db_session)
        make_song(db_session, user)

        song = client.get("/api/v1/articles").json()["items"][0]["song"]

        assert song["cover_thumbnail_url"] == "https://images.genius.com/example-cover-300x300.jpg"


class TestCleanPastedLyrics:
    @pytest.mark.parametrize(
        "leftover",
        [
            "[Songtext zu „Nachtlicht“]",
            '[Songtext zu "Nachtlicht"]',
            "Songtext",
            "Lyrics",
            "12 Contributors",
            "1 Contributor",
            "3 ContributorsTranslationsEnglishNachtlicht Lyrics",
            "Translations",
            "Übersetzungen",
            "Embed",
            "24Embed",
            "You might also like",
            "Das könnte dir auch gefallen",
        ],
    )
    def test_removes_leftover_lines(self, leftover: str) -> None:
        text = f"{leftover}\nIch lauf' durch die Nacht\n{leftover}\nUnd die Stadt ist noch wach"

        assert clean_pasted_lyrics(text) == "Ich lauf' durch die Nacht\nUnd die Stadt ist noch wach"

    def test_removes_title_heading_only_before_the_first_lyric_line(self) -> None:
        text = "Nachtlicht Lyrics\n\nZeile eins\nSo heißen meine Lyrics"

        assert clean_pasted_lyrics(text) == "Zeile eins\nSo heißen meine Lyrics"

    def test_unglues_leftovers_from_lyric_lines(self) -> None:
        text = "Zeile eins\nYou might also likeZeile zwei\nZeile drei42Embed"

        assert clean_pasted_lyrics(text) == "Zeile eins\nZeile zwei\nZeile drei"

    def test_keeps_section_lines_and_blank_lines(self) -> None:
        text = "[Hook]\nZeile eins\n\n[Strophe 1: Die Erfundenen]\nZeile zwei\nEmbed"

        assert clean_pasted_lyrics(text) == (
            "[Hook]\nZeile eins\n\n[Strophe 1: Die Erfundenen]\nZeile zwei"
        )

    @pytest.mark.parametrize(
        "clean",
        [
            "Zeile eins\nZeile zwei\n",
            "  Einrückung bleibt\r\nAuch Windows-Zeilen\n\n\n",
            "Ich sing' ein Lied\nDas Wort Embed steht mitten drin",
        ],
    )
    def test_clean_text_is_returned_unchanged(self, clean: str) -> None:
        assert clean_pasted_lyrics(clean) == clean

    def test_is_idempotent(self) -> None:
        once = clean_pasted_lyrics("5 Contributors\nZeile eins\nZeile zwei7Embed")

        assert clean_pasted_lyrics(once) == once


class TestBackfillSongCovers:
    def test_fills_missing_covers_and_is_idempotent(
        self, db_session: Session, fake_song_provider: FakeSongProvider, song_cache: TTLCache
    ) -> None:
        user = make_user(db_session, email="alex@example.com")
        missing = make_song(
            db_session, user, genius_song_id=900001, cover_url=None, cover_thumbnail_url=None
        )
        manual = make_song(
            db_session,
            user,
            title="Ohne Genius",
            genius_song_id=None,
            cover_url=None,
            cover_thumbnail_url=None,
        )
        no_art = make_song(
            db_session,
            user,
            title="Nachtzug",
            genius_song_id=900003,
            cover_url=None,
            cover_thumbnail_url=None,
        )
        unknown = make_song(
            db_session,
            user,
            title="Verschollen",
            genius_song_id=999999,
            cover_url=None,
            cover_thumbnail_url=None,
        )

        first = backfill_song_covers(db_session, fake_song_provider, song_cache)

        assert (first.songs_missing_cover, first.covers_filled, first.thumbnails_filled) == (
            3,
            1,
            1,
        )
        assert (first.still_without_cover, first.provider_errors) == (2, 1)
        assert (missing.song.cover_url, missing.song.cover_thumbnail_url) == (ART, ART_THUMB)
        assert manual.song.cover_url is None
        assert no_art.song.cover_url is None
        assert unknown.song.cover_url is None
        assert sorted(fake_song_provider.get_song_calls) == [900001, 900003, 999999]

        calls_before = len(fake_song_provider.get_song_calls)
        second = backfill_song_covers(db_session, fake_song_provider, song_cache)

        assert second.covers_filled == 0
        assert second.thumbnails_filled == 0
        # 900003 is served from the cache; only the failing id is asked again.
        assert fake_song_provider.get_song_calls[calls_before:] == [999999]


def _save_occurrence(db_session: Session, article: Article, start: int, end: int) -> None:
    item = VocabularyItem(
        user_id=article.user_id,
        lemma=article.original_text[start:end],
        display_form=article.original_text[start:end],
        part_of_speech="NOUN",
    )
    db_session.add(item)
    db_session.flush()
    db_session.add(
        ArticleVocabulary(
            article_id=article.id,
            vocabulary_item_id=item.id,
            start_offset=start,
            end_offset=end,
            context_sentence="-",
        )
    )
    db_session.flush()


class TestCleanExistingSongs:
    def test_cleans_songs_without_vocabulary_and_drops_their_analysis(
        self, db_session: Session
    ) -> None:
        user = make_user(db_session, email="alex@example.com")
        article = make_song(db_session, user, lyrics="7 Contributors\nZeile eins\nZeile zwei")
        db_session.add(ArticleAnalysis(article_id=article.id, analysis_version=1, results={}))
        article.reading_position = 20
        db_session.flush()

        stats = clean_song_lyrics(db_session)

        assert (stats.songs_checked, stats.cleaned, stats.skipped_article_ids) == (1, 1, [])
        db_session.refresh(article)
        assert article.original_text == "Zeile eins\nZeile zwei"
        assert article.reading_position is None
        assert db_session.scalar(select(ArticleAnalysis)) is None

    def test_cleans_when_saved_words_are_before_the_removed_text(self, db_session: Session) -> None:
        user = make_user(db_session, email="alex@example.com")
        article = make_song(db_session, user, lyrics="Zeile eins\nZeile zwei\nYou might also like")
        _save_occurrence(db_session, article, 0, 5)

        stats = clean_song_lyrics(db_session)

        assert stats.cleaned == 1
        db_session.refresh(article)
        assert article.original_text == "Zeile eins\nZeile zwei"
        occurrence = db_session.scalar(select(ArticleVocabulary))
        assert article.original_text[occurrence.start_offset : occurrence.end_offset] == "Zeile"

    def test_skips_songs_whose_saved_offsets_would_move(self, db_session: Session) -> None:
        user = make_user(db_session, email="alex@example.com")
        lyrics = "Nachtlicht Lyrics\nZeile eins\nZeile zwei"
        article = make_song(db_session, user, lyrics=lyrics)
        _save_occurrence(db_session, article, 18, 23)

        stats = clean_song_lyrics(db_session)

        assert (stats.cleaned, stats.skipped_article_ids) == (0, [article.id])
        db_session.refresh(article)
        assert article.original_text == lyrics

    def test_leaves_clean_songs_and_texts_alone(self, db_session: Session) -> None:
        user = make_user(db_session, email="alex@example.com")
        make_song(db_session, user, lyrics="[Hook]\nZeile eins")
        db_session.add(Article(user_id=user.id, original_text="Songtext\nKein Song, nur Text."))
        db_session.flush()

        stats = clean_song_lyrics(db_session)

        assert (stats.songs_checked, stats.already_clean, stats.cleaned) == (1, 1, 0)

    def test_dry_run_changes_nothing(self, db_session: Session) -> None:
        user = make_user(db_session, email="alex@example.com")
        article = make_song(db_session, user, lyrics="Embed\nZeile eins")

        stats = clean_song_lyrics(db_session, dry_run=True)

        assert stats.cleaned == 1
        assert db_session.get(Article, article.id).original_text == "Embed\nZeile eins"

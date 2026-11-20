"""One-off: remove lyrics-page leftovers from already-saved song texts.

    uv run python -m app.scripts.clean_song_lyrics [--dry-run]

Applies the same cleanup new song saves get (app/services/lyrics_cleanup.py). Saved vocabulary
occurrences point into original_text by code-point offset, so an article is only rewritten when
every occurrence lies entirely inside the unchanged prefix of the text - i.e. the cleanup only
removes text after the last saved word. Any other article is skipped and reported, never
rewritten. Rewritten articles drop their stored NLP analysis (recomputed on next open); a
reading position past the unchanged prefix is cleared. Re-running is a no-op.
"""

import argparse
import uuid
from dataclasses import dataclass, field

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.db import UntimedSessionLocal
from app.models import Article, ArticleAnalysis, ArticleVocabulary
from app.services.lyrics_cleanup import clean_pasted_lyrics


@dataclass
class CleanupStats:
    songs_checked: int = 0
    already_clean: int = 0
    cleaned: int = 0
    characters_removed: int = 0
    reading_positions_cleared: int = 0
    # Articles left untouched because cleaning would move a saved occurrence's offsets.
    skipped_article_ids: list[uuid.UUID] = field(default_factory=list)


def common_prefix_length(a: str, b: str) -> int:
    limit = min(len(a), len(b))
    for index in range(limit):
        if a[index] != b[index]:
            return index
    return limit


def clean_song_lyrics(db: Session, *, dry_run: bool = False) -> CleanupStats:
    stats = CleanupStats()
    articles = db.scalars(
        select(Article).where(Article.kind == "song").order_by(Article.created_at)
    ).all()
    for article in articles:
        stats.songs_checked += 1
        original = article.original_text
        cleaned = clean_pasted_lyrics(original)
        if cleaned == original:
            stats.already_clean += 1
            continue
        if not cleaned.strip():
            stats.skipped_article_ids.append(article.id)
            continue

        unchanged_prefix = common_prefix_length(original, cleaned)
        last_saved_end = db.scalar(
            select(func.max(ArticleVocabulary.end_offset)).where(
                ArticleVocabulary.article_id == article.id
            )
        )
        if last_saved_end is not None and last_saved_end > unchanged_prefix:
            stats.skipped_article_ids.append(article.id)
            continue

        stats.cleaned += 1
        stats.characters_removed += len(original) - len(cleaned)
        if dry_run:
            continue
        article.original_text = cleaned
        if article.reading_position is not None and article.reading_position > unchanged_prefix:
            article.reading_position = None
            stats.reading_positions_cleared += 1
        # Token offsets in the stored analysis no longer match the text.
        db.execute(delete(ArticleAnalysis).where(ArticleAnalysis.article_id == article.id))

    if not dry_run:
        db.commit()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report only, change nothing.")
    args = parser.parse_args()

    session = UntimedSessionLocal()
    try:
        stats = clean_song_lyrics(session, dry_run=args.dry_run)
    finally:
        session.close()
    for name, value in vars(stats).items():
        if name == "skipped_article_ids":
            print(f"skipped (would move saved vocabulary offsets or empty the text): {len(value)}")
            for article_id in value:
                print(f"  - {article_id}")
        else:
            print(f"{name}: {value}")


if __name__ == "__main__":
    main()

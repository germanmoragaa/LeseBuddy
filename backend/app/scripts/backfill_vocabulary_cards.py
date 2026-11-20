"""One-off, idempotent backfill for the Anki-style card fields on vocabulary saved before
they existed:

    uv run python -m app.scripts.backfill_vocabulary_cards [--no-translate]

- article_vocabulary.context_line: re-derived from the stored article text and offsets (the
  lyric line for songs, the sentence for texts), falling back to the stored context_sentence
  if the offsets no longer resolve.
- vocabulary_items.example_occurrence_id: the first occurrence saved.
- vocabulary_items.meanings: the stored contextual translation (if any) first, then the
  dictionary's translations in the owner's translation language. Run it after the dictionary
  import that brought in dictionary_translations.
- article_vocabulary.context_translation: the line via DeepL (cached, rate-limited per owner,
  so a re-run reuses every translation it already paid for). Skipped with --no-translate.

Only ever fills NULL/empty values, never overwrites one, so a re-run changes nothing except
retrying line translations that failed before. Prints the DeepL characters it billed.
"""

import argparse
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_translation_provider
from app.core.db import UntimedSessionLocal
from app.models import Article, ArticleVocabulary, User, VocabularyItem
from app.services import dictionary_service
from app.services.selection import SelectionError
from app.services.translation.provider import TranslationProvider, UsageSnapshot
from app.services.translation_service import (
    RETRYABLE_TRANSLATION_ERRORS,
    context_translation_request,
    translate_text,
)
from app.services.vocabulary_service import (
    MACHINE,
    merge_meanings,
    resolve_occurrence_selection,
)


class CountingProvider:
    """Wraps the real provider to count characters actually sent to it (cache hits never
    reach the provider, so this is exactly what gets billed)."""

    def __init__(self, inner: TranslationProvider) -> None:
        self.inner = inner
        self.characters = 0
        self.calls = 0

    def translate(self, text: str, *, context: str | None, target_lang: str) -> str:
        result = self.inner.translate(text, context=context, target_lang=target_lang)
        self.characters += len(text)
        self.calls += 1
        return result

    def get_usage(self) -> UsageSnapshot:
        return self.inner.get_usage()


@dataclass
class BackfillStats:
    occurrences_checked: int = 0
    context_lines_filled: int = 0
    context_lines_fallback: int = 0
    context_translations_filled: int = 0
    context_translations_failed: int = 0
    items_checked: int = 0
    meanings_filled: int = 0
    examples_filled: int = 0
    deepl_calls: int = 0
    deepl_characters: int = 0


def backfill(
    session: Session, provider: TranslationProvider | None, stats: BackfillStats | None = None
) -> BackfillStats:
    stats = stats or BackfillStats()
    counting = CountingProvider(provider) if provider is not None else None
    users: dict = {}
    articles: dict = {}

    def owner(item: VocabularyItem) -> User:
        if item.user_id not in users:
            users[item.user_id] = session.get(User, item.user_id)
        return users[item.user_id]

    def article_for(occurrence: ArticleVocabulary) -> Article:
        if occurrence.article_id not in articles:
            articles[occurrence.article_id] = session.get(Article, occurrence.article_id)
        return articles[occurrence.article_id]

    items = session.scalars(select(VocabularyItem).order_by(VocabularyItem.created_at)).all()
    for item in items:
        stats.items_checked += 1
        occurrences = session.scalars(
            select(ArticleVocabulary)
            .where(ArticleVocabulary.vocabulary_item_id == item.id)
            .order_by(ArticleVocabulary.created_at, ArticleVocabulary.id)
        ).all()

        first_selection = None
        for occurrence in occurrences:
            stats.occurrences_checked += 1
            article = article_for(occurrence)
            try:
                selection = resolve_occurrence_selection(session, article, occurrence)
            except SelectionError:
                selection = None
            if first_selection is None and selection is not None:
                first_selection = selection

            if occurrence.context_line is None:
                if selection is not None:
                    occurrence.context_line = selection.context_text(article.original_text)
                    stats.context_lines_filled += 1
                else:
                    occurrence.context_line = occurrence.context_sentence
                    stats.context_lines_fallback += 1
                session.commit()

            if occurrence.context_translation is None and counting is not None:
                if selection is not None:
                    source_text, context = context_translation_request(
                        selection, article.original_text
                    )
                else:
                    source_text, context = occurrence.context_line, None
                try:
                    translation = translate_text(
                        session, counting, owner(item), source_text=source_text, context=context
                    )
                except RETRYABLE_TRANSLATION_ERRORS:
                    stats.context_translations_failed += 1
                else:
                    session.refresh(occurrence)
                    occurrence.context_translation = translation
                    session.commit()
                    stats.context_translations_filled += 1

        if item.example_occurrence_id is None and occurrences:
            item.example_occurrence_id = occurrences[0].id
            stats.examples_filled += 1

        if not item.meanings:
            if first_selection is not None:
                entry = dictionary_service.resolve_dictionary_entry(session, first_selection)
            else:
                entry = dictionary_service.lookup(session, item.lemma, item.part_of_speech)
            meanings = merge_meanings(
                [{"text": item.translation, "source": MACHINE}] if item.translation else [],
                dictionary_service.dictionary_meanings(
                    session, entry, owner(item).translation_language
                ),
            )
            if meanings:
                item.meanings = meanings
                stats.meanings_filled += 1
        session.commit()

    if counting is not None:
        stats.deepl_calls = counting.calls
        stats.deepl_characters = counting.characters
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-translate", action="store_true", help="Skip the DeepL line translations."
    )
    args = parser.parse_args()

    provider = None if args.no_translate else get_translation_provider()
    session = UntimedSessionLocal()
    try:
        stats = backfill(session, provider)
    finally:
        session.close()
    for field, value in vars(stats).items():
        print(f"{field}: {value}")


if __name__ == "__main__":
    main()

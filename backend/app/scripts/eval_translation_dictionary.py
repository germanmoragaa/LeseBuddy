"""Manual quality/coverage spot-check for the DeepL + Wiktionary pipeline.

    uv run python -m app.scripts.eval_translation_dictionary

NOT run in CI — this hits the real DeepL API (consuming real quota) and expects the real
dictionary to already be imported (see app/scripts/import_dictionary.py). It runs ~15 real
selections from the seeded homeoffice_debatte.txt article (including a separable verb, a
compound noun, and the idiom "vor allem") through the actual production code paths
(resolve_selection, dictionary_service, translation_service) — not a reimplementation of
them — and writes a markdown report for human review. A throwaway user and article are
created in the DB to drive those code paths, then deleted at the end.
"""

import time
from dataclasses import dataclass
from pathlib import Path

import deepl

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import Article, User
from app.schemas.article import ArticleCreate
from app.services.analysis_service import get_or_create_analysis
from app.services.article_service import create_article, delete_article
from app.services.dictionary_service import resolve_dictionary_entry
from app.services.selection import SelectionError, resolve_selection
from app.services.translation.deepl_provider import DeepLTranslationProvider
from app.services.translation.provider import TranslationProvider, TranslationProviderError
from app.services.translation_service import translate_selection

SEED_ARTICLE_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "seed_data" / "homeoffice_debatte.txt"
)
REPORT_PATH = (
    Path(__file__).resolve().parents[2] / "eval_reports" / "translation_dictionary_eval.md"
)

EVAL_USER_EMAIL = "eval-script@lesebuddy.internal"


@dataclass
class EvalTerm:
    surface_text: str
    category: str  # noun | compound-noun | verb | separable-verb | adjective | idiom
    note: str = ""


# Surface forms exactly as they appear in homeoffice_debatte.txt. The separable verb
# ("einschalten") is split in the text as "schalten ... ein" — located via the analysis's
# separable_verbs list, not a plain substring search (see _locate_span below).
EVAL_TERMS = [
    EvalTerm("Homeoffice", "noun"),
    EvalTerm("Pandemie", "noun"),
    EvalTerm("Selbstverständlichkeit", "compound-noun"),
    EvalTerm("vor allem", "idiom", note="also gets a sentence translation, as a demo"),
    EvalTerm("Zeitersparnis", "compound-noun"),
    EvalTerm("pendeln", "verb"),
    EvalTerm("Kolleginnen", "noun"),
    EvalTerm("Vertrauen", "noun"),
    EvalTerm("Vorgesetzten", "noun"),
    EvalTerm("einschalten", "separable-verb", note="split in text as 'schalten ... ein'"),
    EvalTerm("Arbeitsplatz", "compound-noun"),
    EvalTerm("Mittelweg", "compound-noun"),
    EvalTerm("Zusammenhalt", "noun"),
    EvalTerm("isoliert", "adjective"),
    EvalTerm("Erreichbarkeit", "noun"),
]


@dataclass
class EvalResult:
    term: EvalTerm
    lemma: str | None = None
    dictionary_found: bool = False
    dictionary_gender: str | None = None
    dictionary_plural: str | None = None
    dictionary_glosses: list[str] | None = None
    translation: str | None = None
    sentence_translation: str | None = None
    latency_ms: float | None = None
    error: str | None = None


def _get_or_create_eval_user(db) -> User:
    from sqlalchemy import select

    existing = db.scalar(select(User).where(User.email == EVAL_USER_EMAIL))
    if existing is not None:
        return existing

    from datetime import UTC, datetime

    user = User(
        username="eval_script_user",
        email=EVAL_USER_EMAIL,
        password_hash=hash_password("not-a-real-password-eval-only"),
        email_verified_at=datetime.now(UTC),
        translation_language="EN-US",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _locate_span(analysis, original_text: str, term: EvalTerm) -> tuple[int, int] | None:
    """Finds {start, end} offsets for a term's surface text within the article, aligned to
    real token boundaries — mirrors how the frontend derives offsets from a user's click."""
    if term.category == "separable-verb":
        verb = next((v for v in analysis.separable_verbs if v.lemma == term.surface_text), None)
        if verb is None:
            return None
        verb_token = analysis.tokens[verb.verb_token_index]
        particle_token = analysis.tokens[verb.particle_token_index]
        return (
            min(verb_token.start, particle_token.start),
            max(verb_token.end, particle_token.end),
        )

    start = original_text.find(term.surface_text)
    if start == -1:
        return None
    return start, start + len(term.surface_text)


def _run_eval(db, user: User, article: Article, provider: TranslationProvider) -> list[EvalResult]:
    analysis = get_or_create_analysis(db, article)
    results: list[EvalResult] = []

    for term in EVAL_TERMS:
        result = EvalResult(term=term)
        span = _locate_span(analysis, article.original_text, term)
        if span is None:
            result.error = "Could not locate this term in the seed article."
            results.append(result)
            continue
        start, end = span

        try:
            selection = resolve_selection(analysis, article.original_text, start, end)
        except SelectionError as exc:
            result.error = f"Selection did not resolve: {exc}"
            results.append(result)
            continue
        result.lemma = selection.lemma

        entry = resolve_dictionary_entry(db, selection)
        if entry is not None:
            result.dictionary_found = True
            result.dictionary_gender = entry.gender
            result.dictionary_plural = entry.plural
            result.dictionary_glosses = entry.glosses

        include_sentence = term.category == "idiom"
        started = time.perf_counter()
        try:
            translation = translate_selection(
                db, provider, user, article, start, end, include_sentence
            )
            result.translation = translation.selection_translation
            result.sentence_translation = translation.sentence_translation
        except TranslationProviderError as exc:
            result.error = f"Translation failed: {exc}"
        result.latency_ms = (time.perf_counter() - started) * 1000

        results.append(result)

    return results


def _render_report(results: list[EvalResult], characters_used: int) -> str:
    lines = [
        "# DeepL + Wiktionary eval report",
        "",
        f"Terms evaluated: {len(results)}. DeepL characters consumed this run: {characters_used}.",
        "",
        "| Term | Category | Lemma | Dictionary | Gender | Plural | Glosses | Translation "
        "| Latency (ms) | Error |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for result in results:
        glosses = "; ".join(result.dictionary_glosses or []) or "—"
        lines.append(
            "| {term} | {category} | {lemma} | {found} | {gender} | {plural} | {glosses} | "
            "{translation} | {latency} | {error} |".format(
                term=result.term.surface_text,
                category=result.term.category,
                lemma=result.lemma or "—",
                found="yes" if result.dictionary_found else "no",
                gender=result.dictionary_gender or "—",
                plural=result.dictionary_plural or "—",
                glosses=glosses,
                translation=result.translation or "—",
                latency=f"{result.latency_ms:.0f}" if result.latency_ms is not None else "—",
                error=result.error or "—",
            )
        )

    idiom_result = next((r for r in results if r.term.category == "idiom"), None)
    if idiom_result and idiom_result.sentence_translation:
        lines += [
            "",
            "## Sentence translation demo (idiom term)",
            "",
            f"> {idiom_result.sentence_translation}",
        ]

    found_count = sum(1 for r in results if r.dictionary_found)
    error_count = sum(1 for r in results if r.error)
    lines += [
        "",
        "## Summary",
        "",
        f"- Dictionary coverage: {found_count}/{len(results)} terms found an entry.",
        f"- Errors: {error_count}/{len(results)}.",
        f"- DeepL characters used this run: {characters_used}.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    settings = get_settings()
    if not settings.deepl_api_key:
        raise SystemExit("DEEPL_API_KEY is not set — this script requires the real provider.")

    usage_client = deepl.DeepLClient(settings.deepl_api_key)
    characters_before = usage_client.get_usage().character.count

    db = SessionLocal()
    provider = DeepLTranslationProvider(settings)
    article: Article | None = None
    try:
        user = _get_or_create_eval_user(db)
        original_text = SEED_ARTICLE_PATH.read_text(encoding="utf-8")
        article = create_article(
            db,
            user,
            ArticleCreate(title="Eval: Homeoffice-Debatte", original_text=original_text),
        )

        print(f"Running {len(EVAL_TERMS)} term lookups against the real DeepL + dictionary...")
        results = _run_eval(db, user, article, provider)

        characters_after = usage_client.get_usage().character.count
        characters_used = characters_after - characters_before

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(_render_report(results, characters_used), encoding="utf-8")
        print(f"Report written to {REPORT_PATH}")
        print(f"DeepL characters used this run: {characters_used}")
        found_count = sum(1 for r in results if r.dictionary_found)
        print(f"Dictionary coverage: {found_count}/{len(results)}")
    finally:
        if article is not None:
            delete_article(db, article)
        db.close()


if __name__ == "__main__":
    main()

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_translation_provider
from app.core.db import get_db
from app.models import Article, User
from app.schemas.analysis import ArticleAnalysisResult
from app.schemas.article import (
    ArticleCreate,
    ArticleListItem,
    ArticleListResponse,
    ArticleRead,
    ArticleUpdate,
)
from app.schemas.dictionary import DictionaryEntryRead, DictionaryLookupResponse
from app.schemas.translation import TranslateRequest, TranslateResponse
from app.schemas.vocabulary import VocabularyOccurrenceSummary
from app.services.analysis_service import get_or_create_analysis
from app.services.article_service import (
    count_articles_for_user,
    create_article,
    delete_article,
    get_article_for_user,
    list_articles_for_user,
    update_article,
)
from app.services.dictionary_service import resolve_dictionary_entry
from app.services.selection import SelectionError, resolve_selection
from app.services.translation.provider import (
    TranslationNotConfiguredError,
    TranslationProvider,
    TranslationProviderError,
    TranslationQuotaExceededError,
    TranslationTimeoutError,
)
from app.services.translation_service import TranslationRateLimitedError, translate_selection
from app.services.vocabulary_service import list_occurrences_for_article

router = APIRouter(prefix="/api/v1/articles", tags=["articles"])

EXCERPT_MAX_LENGTH = 160


def _word_count(text: str) -> int:
    return len(text.split())


def _excerpt(text: str) -> str | None:
    collapsed = " ".join(text.split())
    if not collapsed:
        return None
    if len(collapsed) <= EXCERPT_MAX_LENGTH:
        return collapsed
    return collapsed[:EXCERPT_MAX_LENGTH].rstrip() + "…"


def _to_list_item(article: Article) -> ArticleListItem:
    return ArticleListItem(
        id=article.id,
        title=article.title,
        source_url=article.source_url,
        language=article.language,
        created_at=article.created_at,
        updated_at=article.updated_at,
        word_count=_word_count(article.original_text),
        excerpt=_excerpt(article.original_text),
    )


def _to_read(article: Article) -> ArticleRead:
    return ArticleRead(**_to_list_item(article).model_dump(), original_text=article.original_text)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ArticleRead)
def create(
    data: ArticleCreate,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> ArticleRead:
    article = create_article(db, user, data)
    return _to_read(article)


@router.get("", response_model=ArticleListResponse)
def list_articles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> ArticleListResponse:
    articles = list_articles_for_user(db, user, page=page, page_size=page_size)
    total = count_articles_for_user(db, user)
    return ArticleListResponse(
        items=[_to_list_item(article) for article in articles],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(
    article_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> ArticleRead:
    article = get_article_for_user(db, user, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return _to_read(article)


@router.patch("/{article_id}", response_model=ArticleRead)
def update(
    article_id: uuid.UUID,
    data: ArticleUpdate,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> ArticleRead:
    article = get_article_for_user(db, user, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    article = update_article(db, article, data.title)
    return _to_read(article)


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    article_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> None:
    article = get_article_for_user(db, user, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    # Cascades to article_analyses and article_vocabulary only — vocabulary_items (no FK to
    # articles) are untouched. See docs/blueprint.md section 7's deletion policy.
    delete_article(db, article)


@router.get("/{article_id}/analysis", response_model=ArticleAnalysisResult)
def get_analysis(
    article_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> ArticleAnalysisResult:
    article = get_article_for_user(db, user, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return get_or_create_analysis(db, article)


@router.get("/{article_id}/dictionary", response_model=DictionaryLookupResponse)
def get_dictionary_entry(
    article_id: uuid.UUID,
    start: int = Query(..., ge=0),
    end: int = Query(..., gt=0),
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> DictionaryLookupResponse:
    article = get_article_for_user(db, user, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    analysis = get_or_create_analysis(db, article)
    try:
        selection = resolve_selection(analysis, article.original_text, start, end)
    except SelectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from None

    entry = resolve_dictionary_entry(db, selection)
    return DictionaryLookupResponse(
        lemma=selection.lemma,
        pos_detected=selection.pos,
        is_separable_verb=selection.is_separable_verb,
        entry=DictionaryEntryRead.model_validate(entry) if entry is not None else None,
    )


@router.get(
    "/{article_id}/vocabulary-occurrences", response_model=list[VocabularyOccurrenceSummary]
)
def get_vocabulary_occurrences(
    article_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> list[VocabularyOccurrenceSummary]:
    """Used to highlight words already in the user's vocabulary while reading — kept
    separate from /analysis, which is cached per-article-version independent of any user."""
    article = get_article_for_user(db, user, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    occurrences = list_occurrences_for_article(db, article.id)
    return [VocabularyOccurrenceSummary.model_validate(occurrence) for occurrence in occurrences]


@router.post("/{article_id}/translate", response_model=TranslateResponse)
def translate(
    article_id: uuid.UUID,
    data: TranslateRequest,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    provider: TranslationProvider = Depends(get_translation_provider),
) -> TranslateResponse:
    article = get_article_for_user(db, user, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    try:
        result = translate_selection(
            db, provider, user, article, data.start, data.end, data.include_sentence
        )
    except SelectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from None
    except TranslationNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "translation_not_configured",
                "message": "Translations aren't configured yet.",
            },
        ) from None
    except TranslationRateLimitedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "translation_rate_limited",
                "message": "Too many translation requests. Please try again later.",
                "retry_after": exc.retry_after,
            },
            headers={"Retry-After": str(exc.retry_after)},
        ) from None
    except TranslationQuotaExceededError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "translation_quota_exceeded",
                "message": "The monthly translation quota has been used up.",
            },
        ) from None
    except TranslationTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "code": "translation_timeout",
                "message": "The translation service timed out. Please try again.",
            },
        ) from None
    except TranslationProviderError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "translation_provider_error",
                "message": "The translation service is unavailable right now.",
            },
        ) from None

    return TranslateResponse(
        selection_translation=result.selection_translation,
        sentence_translation=result.sentence_translation,
        quota_warning=result.quota_warning,
    )

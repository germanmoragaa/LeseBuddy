import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user, get_translation_provider
from app.api.errors import selection_error_response, translation_error_response
from app.core.db import get_db
from app.models import User
from app.schemas.vocabulary import (
    OccurrencePatchRequest,
    OccurrenceRead,
    VocabularyItemDetail,
    VocabularyItemListItem,
    VocabularyListResponse,
    VocabularyPatchRequest,
    VocabularySaveRequest,
    VocabularySaveResponse,
)
from app.services.article_service import get_article_for_user
from app.services.deck_service import get_deck_for_user
from app.services.selection import SelectionError
from app.services.translation.provider import TranslationProvider
from app.services.translation_service import RETRYABLE_TRANSLATION_ERRORS
from app.services.vocabulary_service import (
    MACHINE,
    InvalidExampleOccurrenceError,
    delete_item,
    get_item_for_user,
    get_occurrence_for_user,
    get_occurrences,
    list_items_for_user,
    patch_item,
    patch_occurrence,
    retry_occurrence_translation,
    save_occurrence,
)

router = APIRouter(prefix="/api/v1/vocabulary", tags=["vocabulary"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=VocabularySaveResponse)
def save(
    data: VocabularySaveRequest,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    provider: TranslationProvider = Depends(get_translation_provider),
) -> VocabularySaveResponse:
    article = get_article_for_user(db, user, data.article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    try:
        item, occurrence, already_saved = save_occurrence(
            db, user, article, data.start, data.end, deck_ids=data.deck_ids, provider=provider
        )
    except SelectionError as exc:
        raise selection_error_response(exc) from None

    has_machine_meaning = any(m.get("source") == MACHINE for m in item.meanings or [])
    return VocabularySaveResponse(
        item=VocabularyItemListItem.model_validate(item),
        already_saved=already_saved,
        translation_pending=occurrence.needs_translation or not has_machine_meaning,
        occurrence_id=occurrence.id,
    )


@router.get("", response_model=VocabularyListResponse)
def list_vocabulary(
    search: str | None = Query(default=None),
    pos: str | None = Query(default=None),
    deck_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> VocabularyListResponse:
    if deck_id is not None and get_deck_for_user(db, user, deck_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")

    items, total = list_items_for_user(
        db, user, search=search, part_of_speech=pos, deck_id=deck_id, page=page, page_size=page_size
    )
    return VocabularyListResponse(
        items=[VocabularyItemListItem.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


def _occurrence_or_404(db: Session, user: User, occurrence_id: uuid.UUID):
    occurrence = get_occurrence_for_user(db, user, occurrence_id)
    if occurrence is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Occurrence not found")
    return occurrence


@router.post("/occurrences/{occurrence_id}/retry-translation", response_model=OccurrenceRead)
def retry_translation(
    occurrence_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    provider: TranslationProvider = Depends(get_translation_provider),
) -> OccurrenceRead:
    """Retries a context translation (and the item's contextual meaning) that DeepL failed
    to produce at save time. Translation failures map to the same codes as /translate."""
    occurrence = _occurrence_or_404(db, user, occurrence_id)
    try:
        occurrence = retry_occurrence_translation(db, provider, user, occurrence)
    except SelectionError as exc:
        raise selection_error_response(exc) from None
    except RETRYABLE_TRANSLATION_ERRORS as exc:
        raise translation_error_response(exc) from None
    return OccurrenceRead.model_validate(occurrence)


@router.patch("/occurrences/{occurrence_id}", response_model=OccurrenceRead)
def patch_vocabulary_occurrence(
    occurrence_id: uuid.UUID,
    data: OccurrencePatchRequest,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> OccurrenceRead:
    occurrence = _occurrence_or_404(db, user, occurrence_id)
    updates = data.model_dump(exclude_unset=True)
    if "context_translation" in updates and updates["context_translation"] is not None:
        updates["context_translation"] = updates["context_translation"].strip() or None
    occurrence = patch_occurrence(db, occurrence, updates)
    return OccurrenceRead.model_validate(occurrence)


@router.get("/{item_id}", response_model=VocabularyItemDetail)
def get_vocabulary_item(
    item_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> VocabularyItemDetail:
    item = get_item_for_user(db, user, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found"
        )

    occurrences = get_occurrences(db, item.id)
    return VocabularyItemDetail(
        **VocabularyItemListItem.model_validate(item).model_dump(),
        occurrences=[OccurrenceRead.model_validate(occurrence) for occurrence in occurrences],
    )


@router.patch("/{item_id}", response_model=VocabularyItemListItem)
def patch_vocabulary_item(
    item_id: uuid.UUID,
    data: VocabularyPatchRequest,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> VocabularyItemListItem:
    item = get_item_for_user(db, user, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found"
        )

    updates = data.model_dump(exclude_unset=True, exclude_none=False)
    if "meanings" in updates and updates["meanings"] is not None:
        updates["meanings"] = [
            {key: value for key, value in meaning.items() if value is not None}
            for meaning in updates["meanings"]
        ]
    if "meanings" in updates and updates["meanings"] is None:
        updates["meanings"] = []
    try:
        updated = patch_item(db, item, updates)
    except InvalidExampleOccurrenceError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "invalid_example_occurrence",
                "message": "That example isn't one of this word's occurrences.",
            },
        ) from None
    return VocabularyItemListItem.model_validate(updated)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vocabulary_item(
    item_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> None:
    item = get_item_for_user(db, user, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found"
        )
    delete_item(db, item)

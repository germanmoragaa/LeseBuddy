import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user
from app.core.db import get_db
from app.models import User
from app.schemas.vocabulary import (
    OccurrenceRead,
    VocabularyItemDetail,
    VocabularyItemListItem,
    VocabularyListResponse,
    VocabularyPatchRequest,
    VocabularySaveRequest,
    VocabularySaveResponse,
)
from app.services.article_service import get_article_for_user
from app.services.selection import SelectionError
from app.services.vocabulary_service import (
    delete_item,
    get_item_for_user,
    get_occurrences,
    list_items_for_user,
    patch_item,
    save_occurrence,
)

router = APIRouter(prefix="/api/v1/vocabulary", tags=["vocabulary"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=VocabularySaveResponse)
def save(
    data: VocabularySaveRequest,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> VocabularySaveResponse:
    article = get_article_for_user(db, user, data.article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    try:
        item, already_saved = save_occurrence(db, user, article, data.start, data.end)
    except SelectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from None

    return VocabularySaveResponse(
        item=VocabularyItemListItem.model_validate(item), already_saved=already_saved
    )


@router.get("", response_model=VocabularyListResponse)
def list_vocabulary(
    search: str | None = Query(default=None),
    pos: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> VocabularyListResponse:
    items, total = list_items_for_user(
        db, user, search=search, part_of_speech=pos, page=page, page_size=page_size
    )
    return VocabularyListResponse(
        items=[VocabularyItemListItem.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


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

    updated = patch_item(db, item, data.model_dump(exclude_unset=True))
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

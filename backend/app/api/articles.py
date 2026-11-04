import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_verified_user
from app.core.db import get_db
from app.models import User
from app.schemas.analysis import ArticleAnalysisResult
from app.schemas.article import ArticleCreate, ArticleListItem, ArticleRead
from app.services.analysis_service import get_or_create_analysis
from app.services.article_service import (
    create_article,
    get_article_for_user,
    list_articles_for_user,
)

router = APIRouter(prefix="/api/v1/articles", tags=["articles"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ArticleRead)
def create(
    data: ArticleCreate,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> ArticleRead:
    article = create_article(db, user, data)
    return ArticleRead.model_validate(article)


@router.get("", response_model=list[ArticleListItem])
def list_articles(
    user: User = Depends(get_current_verified_user), db: Session = Depends(get_db)
) -> list[ArticleListItem]:
    articles = list_articles_for_user(db, user)
    return [ArticleListItem.model_validate(article) for article in articles]


@router.get("/{article_id}", response_model=ArticleRead)
def get_article(
    article_id: uuid.UUID,
    user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
) -> ArticleRead:
    article = get_article_for_user(db, user, article_id)
    if article is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return ArticleRead.model_validate(article)


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

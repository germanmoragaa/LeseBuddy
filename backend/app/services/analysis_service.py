from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Article, ArticleAnalysis
from app.schemas.analysis import ArticleAnalysisResult
from app.services.nlp.analyze import analyze_text
from app.services.nlp.types import AnalysisResult

# Bump by hand whenever the NLP pipeline logic or model changes — existing rows for the old
# version are left alone (history, not silently overwritten) and a fresh row is computed and
# stored under the new version the next time that article's analysis is requested.
CURRENT_ANALYSIS_VERSION = 1


def _to_result(row: ArticleAnalysis) -> ArticleAnalysisResult:
    analysis = AnalysisResult.model_validate(row.results)
    return ArticleAnalysisResult(
        **analysis.model_dump(),
        analysis_version=row.analysis_version,
        difficulty_estimate=row.difficulty_estimate,
    )


def get_or_create_analysis(db: Session, article: Article) -> ArticleAnalysisResult:
    existing = db.scalar(
        select(ArticleAnalysis).where(
            ArticleAnalysis.article_id == article.id,
            ArticleAnalysis.analysis_version == CURRENT_ANALYSIS_VERSION,
        )
    )
    if existing is not None:
        return _to_result(existing)

    # Compute off-DB (CPU-bound, no open transaction) before attempting the insert.
    analysis = analyze_text(article.original_text)

    row = ArticleAnalysis(
        article_id=article.id,
        analysis_version=CURRENT_ANALYSIS_VERSION,
        results=analysis.model_dump(mode="json"),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent request computed and stored the same version first — use its result
        # rather than erroring, mirroring auth_service.register_user's race handling.
        db.rollback()
        existing = db.scalar(
            select(ArticleAnalysis).where(
                ArticleAnalysis.article_id == article.id,
                ArticleAnalysis.analysis_version == CURRENT_ANALYSIS_VERSION,
            )
        )
        assert existing is not None
        return _to_result(existing)

    db.refresh(row)
    return _to_result(row)

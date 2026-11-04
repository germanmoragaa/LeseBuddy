import uuid

from sqlalchemy import Float, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ArticleAnalysis(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "article_analyses"

    article_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"), nullable=False
    )
    analysis_version: Mapped[int] = mapped_column(Integer, nullable=False)
    # The NLP pipeline's AnalysisResult (tokens/sentences/separable_verbs), round-tripped
    # through app.schemas.analysis.ArticleAnalysisResult — see that module for why there's
    # only one schema for both directions.
    results: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Reserved for the difficulty-estimation step (docs/blueprint.md section 8); always NULL
    # until that step lands — never faked.
    difficulty_estimate: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index(
            "ix_article_analyses_article_id_version",
            "article_id",
            "analysis_version",
            unique=True,
        ),
    )

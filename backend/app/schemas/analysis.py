from app.services.nlp.types import AnalysisResult


class ArticleAnalysisResult(AnalysisResult):
    """The single round-trip contract for an article's analysis.

    NLP output (AnalysisResult) -> this schema -> `.model_dump(mode="json")` into the
    `results` JSONB column on write -> re-validated through this same schema on read. Keeping
    one schema for both directions means the stored shape and the API response shape can
    never silently drift from each other.
    """

    analysis_version: int
    # Deliberately null: the difficulty heuristic is a separate, future step (see
    # docs/blueprint.md section 8) — never faked here.
    difficulty_estimate: float | None = None

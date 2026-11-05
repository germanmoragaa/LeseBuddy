from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    include_sentence: bool = False


class TranslateResponse(BaseModel):
    selection_translation: str
    sentence_translation: str | None = None
    quota_warning: str | None = None
    source: str = "machine_translation"

from __future__ import annotations

from pydantic import BaseModel, Field


class TextBlock(BaseModel):
    id: int
    bounding_box: list[int] = Field(
        description="[x_min, y_min, x_max, y_max] in source image pixels."
    )
    confidence: float
    class_name: str
    text: str


class MangaOcrResponse(BaseModel):
    filename: str
    width: int
    height: int
    blocks: list[TextBlock]


class TranslationJobPage(BaseModel):
    page: int
    url: str


class TranslationJobStatusResponse(BaseModel):
    job_id: str
    status: str
    total_pages: int
    completed_pages: int
    target_language: str
    created_at: str
    updated_at: str
    error: str | None = None
    pages: list[TranslationJobPage] = Field(default_factory=list)
    result_zip_url: str | None = None

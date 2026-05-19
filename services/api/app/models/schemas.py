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

"""PDF 提取结果与可追溯的原文事实。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Fact(Model):
    value: str | None = None
    normalized_value: str | None = None
    source_ids: list[str] = Field(default_factory=list)


class Block(Model):
    id: str
    page: int = Field(ge=1)
    text: str
    bbox: list[float] | None = None


class Page(Model):
    number: int = Field(ge=1)
    width: float
    height: float
    status: Literal["text", "needs_ocr"]
    layout: Literal["single_column", "two_columns", "unknown"]


class Source(Model):
    schema_version: Literal["1.0.0"] = "1.0.0"
    file_name: str
    sha256: str
    page_count: int = Field(ge=1)
    pages: list[Page]
    blocks: list[Block]

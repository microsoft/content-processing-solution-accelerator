# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Pydantic response models for Azure Content Understanding analysis results.

Maps the JSON payload returned by the Content Understanding API into
typed Python objects used downstream by pipeline handlers.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class Span(BaseModel):
    offset: int
    length: int


class Word(BaseModel):
    content: str
    span: Span
    confidence: float
    source: str
    polygon: Optional[List[float]] = None

    @field_validator("polygon", mode="after")
    @classmethod
    def parse_polygon(cls, value, info: ValidationInfo):
        """Extract polygon coordinates from the ``source`` field.

        Provides compatibility with Azure Document Intelligence API results
        by parsing the ``D(page, x1, y1, ...)`` source format.

        Args:
            value: The raw polygon value (may be None).
            info: Pydantic validation context carrying sibling field data.

        Returns:
            List of float coordinates, or an empty list.
        """
        source_str = info.data.get("source", "")
        if source_str.startswith("D(") and source_str.endswith(")"):
            inside = source_str[2:-1]
            parts = inside.split(",")
            if len(parts) > 1:
                return [float(x.strip()) for x in parts[1:]]
        return []

    class Config:
        validate_default = True
        arbitary_types_allowed = True


class Line(BaseModel):
    content: str
    source: str
    span: Span
    polygon: Optional[List[float]] = None

    @field_validator("polygon", mode="after")
    @classmethod
    def parse_polygon(cls, value, info: ValidationInfo):
        """Extract polygon coordinates from the ``source`` field."""
        source_str = info.data.get("source", "")
        if source_str.startswith("D(") and source_str.endswith(")"):
            inside = source_str[2:-1]
            parts = inside.split(",")
            if len(parts) > 1:
                return [float(x.strip()) for x in parts[1:]]
        return []

    class Config:
        validate_default = True
        arbitary_types_allowed = True


class Paragraph(BaseModel):
    content: str
    source: str
    span: Span
    polygon: Optional[List[float]] = None

    @field_validator("polygon", mode="after")
    @classmethod
    def parse_polygon(cls, value, info: ValidationInfo):
        """Extract polygon coordinates from the ``source`` field."""
        source_str = info.data.get("source", "")
        if source_str.startswith("D(") and source_str.endswith(")"):
            inside = source_str[2:-1]
            parts = inside.split(",")
            if len(parts) > 1:
                return [float(x.strip()) for x in parts[1:]]
        return []

    class Config:
        validate_default = True
        arbitary_types_allowed = True


class Page(BaseModel):
    pageNumber: int
    angle: Optional[float] = None
    width: float
    height: float
    spans: List[Span] = Field(default_factory=list)
    words: List[Word] = Field(default_factory=list)
    lines: Optional[List[Line]] = []
    paragraphs: Optional[List[Paragraph]] = []


class DocumentContent(BaseModel):
    markdown: str
    kind: str
    startPageNumber: int
    endPageNumber: int
    unit: str
    pages: List[Page]
    paragraphs: List[Paragraph] = Field(default_factory=list)


class Warning(BaseModel):
    """Mirrors the Azure.Core.Foundations.Error shape returned in
    ``ResultData.warnings`` by the Content Understanding GA API.

    The API now emits structured warning objects (with ``code`` / ``message``
    plus optional ``target`` / ``details``) instead of plain strings, so this
    model accepts arbitrary nested error payloads via ``model_config``.
    """

    code: str
    message: str
    target: Optional[str] = None

    model_config = {"extra": "allow"}


class ResultData(BaseModel):
    analyzerId: str
    apiVersion: str
    createdAt: str
    warnings: List[Warning] = Field(default_factory=list)
    contents: List[DocumentContent]


class AnalyzedResult(BaseModel):
    id: str
    status: str
    result: ResultData

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from typing import List, Optional

from pydantic import BaseModel, ValidationInfo, field_validator


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
    def parse_polygon(self, value, info: ValidationInfo):
        """
        Providing comparability with Azure Documenent Document Intelligence Service API result.

        Args:
            value (_type_): _description_
            info (ValidationInfo): _description_

        Returns:
            Parsed Polygon Information with metadata
        """
        source_str = info.data.get("source", "")
        if source_str.startswith("D(") and source_str.endswith(")"):
            inside = source_str[2:-1]  # remove "D(" and ")"
            parts = inside.split(",")
            # skip the first item (like the "1") and parse the rest
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
    def parse_polygon(self, value, info: ValidationInfo):
        source_str = info.data.get("source", "")
        if source_str.startswith("D(") and source_str.endswith(")"):
            inside = source_str[2:-1]  # remove "D(" and ")"
            parts = inside.split(",")
            # skip the first item (like the "1") and parse the rest
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
    def parse_polygon(self, value, info: ValidationInfo):
        source_str = info.data.get("source", "")
        if source_str.startswith("D(") and source_str.endswith(")"):
            inside = source_str[2:-1]  # remove "D(" and ")"
            parts = inside.split(",")
            # skip the first item (like the "1") and parse the rest
            if len(parts) > 1:
                return [float(x.strip()) for x in parts[1:]]
        return []

    class Config:
        validate_default = True
        arbitary_types_allowed = True


class Page(BaseModel):
    pageNumber: int
    angle: float
    width: float
    height: float
    spans: List[Span]
    words: List[Word]
    lines: Optional[List[Line]] = []
    paragraphs: Optional[List[Paragraph]] = []


class DocumentContent(BaseModel):
    markdown: str
    kind: str
    startPageNumber: int
    endPageNumber: int
    unit: str
    pages: List[Page]


class ResultData(BaseModel):
    analyzerId: str
    apiVersion: str
    createdAt: str
    warnings: List[str]
    contents: List[DocumentContent]


class AnalyzedResult(BaseModel):
    id: str
    status: str
    result: ResultData

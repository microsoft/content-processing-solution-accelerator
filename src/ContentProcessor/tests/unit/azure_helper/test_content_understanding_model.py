# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.azure_helper.model.content_understanding (API response models)."""

from __future__ import annotations

from libs.azure_helper.model.content_understanding import (
    AnalyzedResult,
    DocumentContent,
    Line,
    Page,
    Paragraph,
    ResultData,
    Span,
    Word,
)

# ── TestSpan ────────────────────────────────────────────────────────────


class TestSpan:
    """Basic offset/length span model."""

    def test_construction(self):
        span = Span(offset=0, length=10)
        assert span.offset == 0
        assert span.length == 10


# ── TestWord ────────────────────────────────────────────────────────────


class TestWord:
    """Word model with polygon extraction from source field."""

    def test_construction(self):
        word = Word(
            content="hello",
            span=Span(offset=0, length=5),
            confidence=0.99,
            source="D(1, 1.0, 2.0, 3.0, 4.0)",
        )
        assert word.content == "hello"
        assert word.confidence == 0.99

    def test_polygon_parsed_from_source(self):
        word = Word(
            content="test",
            span=Span(offset=0, length=4),
            confidence=0.95,
            source="D(1, 10.5, 20.3, 30.1, 40.2)",
        )
        assert word.polygon == [10.5, 20.3, 30.1, 40.2]

    def test_polygon_empty_for_non_d_source(self):
        word = Word(
            content="test",
            span=Span(offset=0, length=4),
            confidence=0.95,
            source="other-source",
        )
        assert word.polygon == []


# ── TestLine ────────────────────────────────────────────────────────────


class TestLine:
    """Line model with polygon parsing."""

    def test_construction_with_polygon(self):
        line = Line(
            content="Hello world",
            source="D(1, 1.0, 2.0, 3.0, 4.0)",
            span=Span(offset=0, length=11),
        )
        assert line.content == "Hello world"
        assert line.polygon == [1.0, 2.0, 3.0, 4.0]


# ── TestParagraph ───────────────────────────────────────────────────────


class TestParagraph:
    """Paragraph model with polygon parsing."""

    def test_construction(self):
        para = Paragraph(
            content="A paragraph.",
            source="D(1, 5.0, 10.0)",
            span=Span(offset=0, length=12),
        )
        assert para.content == "A paragraph."
        assert para.polygon == [5.0, 10.0]


# ── TestPage ────────────────────────────────────────────────────────────


class TestPage:
    """Page container with words, lines, and paragraphs."""

    def test_construction(self):
        page = Page(
            pageNumber=1,
            angle=0.0,
            width=8.5,
            height=11.0,
            spans=[Span(offset=0, length=100)],
            words=[
                Word(
                    content="word",
                    span=Span(offset=0, length=4),
                    confidence=0.9,
                    source="plain",
                )
            ],
        )
        assert page.pageNumber == 1
        assert len(page.words) == 1
        assert page.lines == []
        assert page.paragraphs == []


# ── TestDocumentContent ─────────────────────────────────────────────────


class TestDocumentContent:
    """Document content container with pages."""

    def test_construction(self):
        doc = DocumentContent(
            markdown="# Title",
            kind="document",
            startPageNumber=1,
            endPageNumber=1,
            unit="inch",
            pages=[
                Page(
                    pageNumber=1,
                    angle=0.0,
                    width=8.5,
                    height=11.0,
                    spans=[Span(offset=0, length=7)],
                    words=[],
                )
            ],
        )
        assert doc.markdown == "# Title"
        assert len(doc.pages) == 1


# ── TestAnalyzedResult ──────────────────────────────────────────────────


class TestAnalyzedResult:
    """Top-level API response model."""

    def test_construction(self):
        result = AnalyzedResult(
            id="r-1",
            status="succeeded",
            result=ResultData(
                analyzerId="prebuilt",
                apiVersion="2024-01-01",
                createdAt="2024-01-01T00:00:00Z",
                warnings=[],
                contents=[],
            ),
        )
        assert result.id == "r-1"
        assert result.status == "succeeded"
        assert result.result.contents == []

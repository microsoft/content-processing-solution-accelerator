# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.entities.mime_types (MIME detection and constants)."""

from __future__ import annotations

import pytest

from libs.pipeline.entities.mime_types import (
    FileExtensions,
    MimeTypeException,
    MimeTypes,
    MimeTypesDetection,
)

# ── TestMimeTypeConstants ───────────────────────────────────────────────


class TestMimeTypeConstants:
    """Spot-check that MIME type string constants are well-formed."""

    def test_pdf_value(self):
        assert MimeTypes.Pdf == "application/pdf"

    def test_json_value(self):
        assert MimeTypes.Json == "application/json"

    def test_plain_text_value(self):
        assert MimeTypes.PlainText == "text/plain"

    def test_markdown_value(self):
        assert MimeTypes.MarkDown == "text/markdown"


# ── TestFileExtensionConstants ──────────────────────────────────────────


class TestFileExtensionConstants:
    """Spot-check that file extension constants start with a dot."""

    def test_pdf_extension(self):
        assert FileExtensions.Pdf == ".pdf"

    def test_json_extension(self):
        assert FileExtensions.Json == ".json"

    def test_docx_extension(self):
        assert FileExtensions.MsWordX == ".docx"


# ── TestMimeTypeException ──────────────────────────────────────────────


class TestMimeTypeException:
    """Custom exception carries an is_transient flag."""

    def test_exception_attributes(self):
        exc = MimeTypeException("bad type", is_transient=True)
        assert str(exc) == "bad type"
        assert exc.is_transient is True

    def test_non_transient(self):
        exc = MimeTypeException("permanent", is_transient=False)
        assert exc.is_transient is False


# ── TestMimeTypesDetection ─────────────────────────────────────────────


class TestMimeTypesDetection:
    """Extension-based MIME type resolution."""

    def test_get_file_type_pdf(self):
        assert MimeTypesDetection.get_file_type("report.pdf") == MimeTypes.Pdf

    def test_get_file_type_json(self):
        assert MimeTypesDetection.get_file_type("data.json") == MimeTypes.Json

    def test_get_file_type_docx(self):
        assert MimeTypesDetection.get_file_type("file.docx") == MimeTypes.MsWordX

    def test_get_file_type_png(self):
        assert MimeTypesDetection.get_file_type("image.png") == MimeTypes.ImagePng

    def test_get_file_type_csv(self):
        assert MimeTypesDetection.get_file_type("data.csv") == MimeTypes.CSVData

    def test_get_file_type_unsupported_raises(self):
        with pytest.raises(MimeTypeException, match="File type not supported"):
            MimeTypesDetection.get_file_type("archive.xyz")

    def test_try_get_file_type_known(self):
        assert MimeTypesDetection.try_get_file_type("page.html") == MimeTypes.Html

    def test_try_get_file_type_unknown_returns_none(self):
        assert MimeTypesDetection.try_get_file_type("archive.xyz") is None

    def test_jpg_and_jpeg_both_resolve_to_jpeg(self):
        assert MimeTypesDetection.get_file_type("photo.jpg") == MimeTypes.ImageJpeg
        assert MimeTypesDetection.get_file_type("photo.jpeg") == MimeTypes.ImageJpeg

    def test_tiff_variants(self):
        assert MimeTypesDetection.get_file_type("scan.tiff") == MimeTypes.ImageTiff
        assert MimeTypesDetection.get_file_type("scan.tif") == MimeTypes.ImageTiff

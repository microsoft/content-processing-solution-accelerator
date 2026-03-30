# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for MimeTypes, FileExtensions, MimeTypesDetection, and MimeTypeException."""

from __future__ import annotations

import pytest

from app.utils.mime_types import (
    MimeTypeException,
    MimeTypes,
    MimeTypesDetection,
)


class TestMimeTypesDetection:
    def test_get_file_type_pdf(self):
        assert MimeTypesDetection.get_file_type("report.pdf") == MimeTypes.Pdf

    def test_get_file_type_jpeg(self):
        assert MimeTypesDetection.get_file_type("photo.jpeg") == MimeTypes.ImageJpeg

    def test_get_file_type_jpg(self):
        assert MimeTypesDetection.get_file_type("photo.jpg") == MimeTypes.ImageJpeg

    def test_get_file_type_png(self):
        assert MimeTypesDetection.get_file_type("image.png") == MimeTypes.ImagePng

    def test_get_file_type_docx(self):
        assert MimeTypesDetection.get_file_type("doc.docx") == MimeTypes.MsWordX

    def test_get_file_type_unsupported_raises(self):
        with pytest.raises(MimeTypeException, match="File type not supported"):
            MimeTypesDetection.get_file_type("data.xyz")

    def test_try_get_file_type_known(self):
        assert MimeTypesDetection.try_get_file_type("sheet.xlsx") == MimeTypes.MsExcelX

    def test_try_get_file_type_unknown_returns_none(self):
        assert MimeTypesDetection.try_get_file_type("file.unknown") is None


class TestMimeTypeException:
    def test_exception_message(self):
        exc = MimeTypeException("test error", is_transient=False)
        assert str(exc) == "test error"
        assert exc.is_transient is False

    def test_transient_exception(self):
        exc = MimeTypeException("transient error", is_transient=True)
        assert exc.is_transient is True

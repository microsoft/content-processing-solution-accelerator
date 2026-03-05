# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for upload_validation utilities."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.utils.upload_validation import (
    get_upload_size_bytes,
    sanitize_filename,
    sniff_mime_type_from_magic,
    validate_upload_for_processing,
)

# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------


class TestSanitizeFilename:
    def test_returns_file_for_none(self):
        assert sanitize_filename(None) == "file"

    def test_returns_file_for_empty(self):
        assert sanitize_filename("") == "file"

    def test_strips_windows_path(self):
        assert sanitize_filename("C:\\\\fakepath\\\\report.pdf") == "report.pdf"

    def test_strips_unix_path(self):
        assert sanitize_filename("/home/user/docs/report.pdf") == "report.pdf"

    def test_replaces_unsafe_characters(self):
        result = sanitize_filename("hello@world#$.pdf")
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result
        assert result.endswith(".pdf")

    def test_dot_only_names(self):
        assert sanitize_filename(".") == "file"
        assert sanitize_filename("..") == "file"

    def test_control_chars_removed(self):
        result = sanitize_filename("test\x00\x01\x02.pdf")
        assert "\x00" not in result
        assert result.endswith(".pdf")

    def test_too_long_filename_raises(self):
        long_name = "a" * 1100 + ".pdf"
        with pytest.raises(ValueError, match="too long"):
            sanitize_filename(long_name)

    def test_truncates_long_stem(self):
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert len(result) <= 255
        assert result.endswith(".pdf")

    def test_unicode_normalization(self):
        result = sanitize_filename("\u00e9l\u00e8ve.pdf")
        assert result.endswith(".pdf")

    def test_all_unsafe_chars_in_stem(self):
        result = sanitize_filename("@@@.pdf")
        assert result.endswith(".pdf")
        assert "@" not in result

    def test_trailing_dot_removed(self):
        result = sanitize_filename("test.pdf.")
        assert not result.endswith(".")


# ---------------------------------------------------------------------------
# get_upload_size_bytes
# ---------------------------------------------------------------------------


class TestGetUploadSizeBytes:
    def test_returns_size_attribute(self):
        upload = MagicMock()
        upload.size = 1024
        assert get_upload_size_bytes(upload) == 1024

    def test_falls_back_to_seek(self):
        upload = MagicMock()
        upload.size = None
        file_obj = BytesIO(b"x" * 100)
        upload.file = file_obj
        assert get_upload_size_bytes(upload) == 100

    def test_returns_none_no_file(self):
        upload = MagicMock()
        upload.size = None
        upload.file = None
        assert get_upload_size_bytes(upload) is None

    def test_returns_none_on_seek_error(self):
        upload = MagicMock()
        upload.size = None
        upload.file = MagicMock()
        upload.file.tell.side_effect = OSError("unseekable")
        assert get_upload_size_bytes(upload) is None


# ---------------------------------------------------------------------------
# sniff_mime_type_from_magic
# ---------------------------------------------------------------------------


class TestSniffMimeType:
    def test_pdf(self):
        assert sniff_mime_type_from_magic(b"%PDF-1.7\n") == "application/pdf"

    def test_jpeg(self):
        assert (
            sniff_mime_type_from_magic(b"\xff\xd8\xff\xe0" + b"\x00" * 12)
            == "image/jpeg"
        )

    def test_png(self):
        assert (
            sniff_mime_type_from_magic(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
            == "image/png"
        )

    def test_unknown_returns_none(self):
        assert sniff_mime_type_from_magic(b"\x00\x00\x00\x00") is None


# ---------------------------------------------------------------------------
# validate_upload_for_processing
# ---------------------------------------------------------------------------


class TestValidateUploadForProcessing:
    @pytest.mark.asyncio
    async def test_missing_filename(self):
        upload = MagicMock()
        upload.filename = ""
        result = await validate_upload_for_processing(upload=upload, max_filesize_mb=20)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_too_long_filename(self):
        upload = MagicMock()
        upload.filename = "a" * 1100 + ".pdf"
        result = await validate_upload_for_processing(upload=upload, max_filesize_mb=20)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_unsupported_extension(self):
        upload = MagicMock()
        upload.filename = "test.exe"
        upload.read = AsyncMock(return_value=b"MZ" + b"\x00" * 14)
        upload.seek = AsyncMock()
        result = await validate_upload_for_processing(upload=upload, max_filesize_mb=20)
        assert result.status_code == 415

    @pytest.mark.asyncio
    async def test_magic_mismatch(self):
        upload = MagicMock()
        upload.filename = "test.pdf"
        upload.content_type = "application/pdf"
        upload.read = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
        upload.seek = AsyncMock()
        result = await validate_upload_for_processing(upload=upload, max_filesize_mb=20)
        assert result.status_code == 415

    @pytest.mark.asyncio
    async def test_wrong_content_type(self):
        upload = MagicMock()
        upload.filename = "test.pdf"
        upload.content_type = "text/plain"
        upload.size = 100
        upload.read = AsyncMock(return_value=b"%PDF-1.7\n" + b"\x00" * 7)
        upload.seek = AsyncMock()
        result = await validate_upload_for_processing(upload=upload, max_filesize_mb=20)
        assert result.status_code == 415

    @pytest.mark.asyncio
    async def test_octet_stream_content_type_accepted(self):
        upload = MagicMock()
        upload.filename = "test.pdf"
        upload.content_type = "application/octet-stream"
        upload.size = 100
        upload.read = AsyncMock(return_value=b"%PDF-1.7\n" + b"\x00" * 7)
        upload.seek = AsyncMock()
        result = await validate_upload_for_processing(upload=upload, max_filesize_mb=20)
        assert isinstance(result, tuple)
        assert result[0] == "test.pdf"
        assert result[1] == "application/pdf"

    @pytest.mark.asyncio
    async def test_size_unknown(self):
        upload = MagicMock()
        upload.filename = "test.pdf"
        upload.content_type = "application/pdf"
        upload.size = None
        upload.file = None
        upload.read = AsyncMock(return_value=b"%PDF-1.7\n" + b"\x00" * 7)
        upload.seek = AsyncMock()
        result = await validate_upload_for_processing(upload=upload, max_filesize_mb=20)
        assert result.status_code == 400

    @pytest.mark.asyncio
    async def test_file_too_large(self):
        upload = MagicMock()
        upload.filename = "test.pdf"
        upload.content_type = "application/pdf"
        upload.size = 25 * 1024 * 1024  # 25 MB
        upload.read = AsyncMock(return_value=b"%PDF-1.7\n" + b"\x00" * 7)
        upload.seek = AsyncMock()
        result = await validate_upload_for_processing(upload=upload, max_filesize_mb=20)
        assert result.status_code == 413

    @pytest.mark.asyncio
    async def test_valid_pdf(self):
        upload = MagicMock()
        upload.filename = "report.pdf"
        upload.content_type = "application/pdf"
        upload.size = 5000
        upload.read = AsyncMock(return_value=b"%PDF-1.7\n" + b"\x00" * 7)
        upload.seek = AsyncMock()
        result = await validate_upload_for_processing(upload=upload, max_filesize_mb=20)
        assert isinstance(result, tuple)
        safe_name, mime, size = result
        assert safe_name == "report.pdf"
        assert mime == "application/pdf"
        assert size == 5000

    @pytest.mark.asyncio
    async def test_valid_jpeg(self):
        upload = MagicMock()
        upload.filename = "photo.jpg"
        upload.content_type = "image/jpeg"
        upload.size = 2000
        upload.read = AsyncMock(return_value=b"\xff\xd8\xff\xe0" + b"\x00" * 12)
        upload.seek = AsyncMock()
        result = await validate_upload_for_processing(upload=upload, max_filesize_mb=20)
        assert isinstance(result, tuple)
        assert result[0] == "photo.jpg"
        assert result[1] == "image/jpeg"

    @pytest.mark.asyncio
    async def test_valid_png(self):
        upload = MagicMock()
        upload.filename = "image.png"
        upload.content_type = "image/png"
        upload.size = 3000
        upload.read = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
        upload.seek = AsyncMock()
        result = await validate_upload_for_processing(upload=upload, max_filesize_mb=20)
        assert isinstance(result, tuple)
        assert result[0] == "image.png"
        assert result[1] == "image/png"

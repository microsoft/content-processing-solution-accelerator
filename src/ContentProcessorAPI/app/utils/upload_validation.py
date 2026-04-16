# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Upload validation utilities: filename sanitization, MIME sniffing, and size checks."""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Optional, cast

from fastapi import UploadFile
from fastapi.responses import JSONResponse

from app.utils.mime_types import MimeTypes

_DEFAULT_MAX_FILENAME_CHARS = 255
_DEFAULT_MAX_FILENAME_UTF8_BYTES = 1024


_SAFE_FILENAME_CHARS_RE = re.compile(r"[^A-Za-z0-9 ._()\-]+")


def sanitize_filename(
    filename: Optional[str],
    *,
    max_chars: int = _DEFAULT_MAX_FILENAME_CHARS,
    max_utf8_bytes: int = _DEFAULT_MAX_FILENAME_UTF8_BYTES,
) -> str:
    """Return a conservative, storage-safe filename.

    - Drops any path components (both '\\' and '/')
    - Unicode normalizes to NFKC
    - Removes control characters
    - Replaces unsafe characters with '_'
    - Enforces length limits (chars and UTF-8 bytes)

    This is intended for blob/object names, not as a UI display name.
    """

    if not filename:
        return "file"

    # Some clients send a full path like C:\\fakepath\\file.pdf
    normalized = filename.replace("\\\\", "/")
    normalized = normalized.split("/")[-1].strip()

    normalized = unicodedata.normalize("NFKC", normalized)

    # Reject extremely large filenames early to avoid odd edge cases.
    try:
        utf8_bytes = normalized.encode("utf-8", "strict")
    except UnicodeEncodeError:
        # Replace undecodable sequences conservatively
        normalized = normalized.encode("utf-8", "replace").decode("utf-8", "replace")
        utf8_bytes = normalized.encode("utf-8", "strict")

    if len(utf8_bytes) > max_utf8_bytes:
        raise ValueError("Filename is too long")

    # Remove NULs and ASCII control chars (including CR/LF/TAB)
    normalized = "".join(ch for ch in normalized if ch >= " " and ch not in "\x7f")

    # Prevent empty / dot-only names
    if normalized in {"", ".", ".."}:
        normalized = "file"

    # Keep extension but sanitize stem
    stem, ext = os.path.splitext(normalized)
    ext = ext[:16]  # avoid pathological long extensions

    safe_stem = _SAFE_FILENAME_CHARS_RE.sub("_", stem).strip(" .")
    safe_ext = _SAFE_FILENAME_CHARS_RE.sub("_", ext)

    if not safe_stem:
        safe_stem = "file"

    # Enforce max chars while preserving extension
    if len(safe_stem) + len(safe_ext) > max_chars:
        safe_stem = safe_stem[: max(1, max_chars - len(safe_ext))]

    candidate = f"{safe_stem}{safe_ext}"

    # Avoid blob names that end with '.' which causes Windows download issues
    candidate = candidate.rstrip(" .")
    if candidate in {"", ".", ".."}:
        candidate = "file"

    return candidate


def get_upload_size_bytes(upload: UploadFile) -> Optional[int]:
    """Best-effort size retrieval.

    Starlette's UploadFile may or may not provide `.size` depending on version/parser.
    """

    size = getattr(upload, "size", None)
    if isinstance(size, int) and size >= 0:
        return size

    file_obj = getattr(upload, "file", None)
    if file_obj is None:
        return None

    try:
        current = file_obj.tell()
        file_obj.seek(0, os.SEEK_END)
        end = file_obj.tell()
        file_obj.seek(current)
        return end
    except Exception:
        return None


def sniff_mime_type_from_magic(header: bytes) -> Optional[str]:
    """Very small, deterministic magic-byte sniffing for supported types."""

    if header.startswith(b"%PDF-"):
        return "application/pdf"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return None


async def validate_upload_for_processing(
    *,
    upload: UploadFile,
    max_filesize_mb: int,
) -> tuple[str, str, int] | JSONResponse:
    """Validate an uploaded file for ContentProcessor endpoints.

    Performs:
    - filename sanitization
    - extension + magic-byte MIME sniff validation
    - Content-Type validation (allows application/octet-stream)
    - max file size validation

    Returns:
        (safe_filename, expected_mime_type, size_bytes) on success, otherwise a JSONResponse
        with an appropriate HTTP status code.
    """

    if not upload.filename:
        return JSONResponse(
            status_code=400,
            content={"message": "Missing filename."},
        )

    # Industry-standard hardening: treat client filename/content-type as untrusted.
    try:
        safe_filename = sanitize_filename(upload.filename)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"message": "Filename is too long."},
        )

    extension = os.path.splitext(safe_filename)[1].lower()

    # Read a small header for magic-byte sniffing (then rewind for downstream consumers).
    header = await upload.read(16)
    await upload.seek(0)

    sniffed = sniff_mime_type_from_magic(header)
    allowed_by_ext = {
        ".pdf": MimeTypes.Pdf,
        ".jpg": MimeTypes.ImageJpeg,
        ".jpeg": MimeTypes.ImageJpeg,
        ".png": MimeTypes.ImagePng,
    }

    expected_for_ext = allowed_by_ext.get(extension)
    if expected_for_ext is None or sniffed != expected_for_ext:
        return JSONResponse(
            status_code=415,
            content={
                "message": "Unsupported or mismatched file type. Only PDF, JPEG, JPG, and PNG are supported.",
                "file_name": safe_filename,
            },
        )

    # Some clients may send application/octet-stream; accept if magic bytes+extension validate.
    if upload.content_type not in {expected_for_ext, "application/octet-stream"}:
        return JSONResponse(
            status_code=415,
            content={
                "message": f"Unsupported Content-Type: {upload.content_type}. Expected {expected_for_ext}.",
                "file_name": safe_filename,
            },
        )

    size_bytes = get_upload_size_bytes(upload)
    if size_bytes is None:
        return JSONResponse(
            status_code=400,
            content={
                "message": "Unable to determine upload size.",
                "file_name": safe_filename,
            },
        )

    if size_bytes > max_filesize_mb * 1024 * 1024:
        return JSONResponse(
            status_code=413,
            content={
                "message": f"File size exceeds the limit of {max_filesize_mb} MB. Current size: {size_bytes / (1024 * 1024):.2f} MB.",
                "file_name": safe_filename,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
            },
        )

    return safe_filename, cast(str, expected_for_ext), size_bytes

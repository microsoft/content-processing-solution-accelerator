# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.utils.base64_util (Base64 validation)."""

from __future__ import annotations

import base64

from libs.utils.base64_util import is_base64_encoded

# ── TestIsBase64Encoded ─────────────────────────────────────────────────


class TestIsBase64Encoded:
    """Base64 encoding detection with edge cases."""

    def test_valid_base64(self):
        valid = base64.b64encode(b"test data").decode("utf-8")
        assert is_base64_encoded(valid) is True

    def test_invalid_string(self):
        assert is_base64_encoded("invalid_base64_string") is False

    def test_empty_string(self):
        assert is_base64_encoded(" ") is False

    def test_special_characters(self):
        assert is_base64_encoded("!@#$%^&*()") is False

    def test_partial_base64(self):
        partial = base64.b64encode(b"test").decode("utf-8")[:5]
        assert is_base64_encoded(partial) is False

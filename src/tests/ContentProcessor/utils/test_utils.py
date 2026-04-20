# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.utils.utils (CustomEncoder, flatten_dict, value helpers)."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from libs.utils.utils import CustomEncoder, flatten_dict, value_contains, value_match

# ── TestCustomEncoder ───────────────────────────────────────────────────


class TestCustomEncoder:
    """JSON encoding fallback for objects with to_dict()."""

    def test_to_dict(self):
        obj = Mock()
        obj.to_dict.return_value = {"key": "value"}
        encoder = CustomEncoder()
        assert encoder.default(obj) == {"key": "value"}

    def test_unsupported_type_raises(self):
        class _Unserializable:
            pass

        encoder = CustomEncoder()
        with pytest.raises(TypeError):
            encoder.default(_Unserializable())


# ── TestFlattenDict ─────────────────────────────────────────────────────


class TestFlattenDict:
    """Recursive dict / list flattening with underscore-joined keys."""

    def test_nested_dict(self):
        data = {"a": 1, "b": {"c": 2, "d": {"e": 3}}, "f": [4, 5, {"g": 6}]}
        expected = {"a": 1, "b_c": 2, "b_d_e": 3, "f_0": 4, "f_1": 5, "f_2_g": 6}
        assert flatten_dict(data) == expected


# ── TestValueMatch ──────────────────────────────────────────────────────


class TestValueMatch:
    """Case-insensitive equality for strings, lists, and dicts."""

    def test_strings_match(self):
        assert value_match("Hello", "hello") is True

    def test_strings_mismatch(self):
        assert value_match("Hello", "world") is False

    def test_lists_match(self):
        assert value_match([1, 2, 3], [1, 2, 3]) is True

    def test_lists_mismatch(self):
        assert value_match([1, 2, 3], [1, 2, 4]) is False

    def test_dicts_match(self):
        assert value_match({"a": 1, "b": 2}, {"a": 1, "b": 2}) is True

    def test_dicts_mismatch(self):
        assert value_match({"a": 1, "b": 2}, {"a": 1, "b": 3}) is False


# ── TestValueContains ───────────────────────────────────────────────────


class TestValueContains:
    """Substring / element containment checks."""

    def test_string_contains(self):
        assert value_contains("hello", "Hello world") is True
        assert value_contains("world", "Hello world") is True
        assert value_contains("test", "Hello world") is False

    def test_list_not_contains(self):
        assert value_contains([4], [1, 2, 3]) is False

    def test_dict_not_contains(self):
        assert value_contains({"c": 3}, {"a": 1, "b": 2}) is False

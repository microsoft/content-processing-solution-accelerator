# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for HTTP request utilities."""

import pytest

from utils.http_request import _join_url, _parse_retry_after_seconds


@pytest.mark.parametrize(
    "base,url,expected",
    [
        (None, "https://example.com/a", "https://example.com/a"),
        ("https://example.com", "/a", "https://example.com/a"),
        ("https://example.com/", "a", "https://example.com/a"),
        ("https://example.com/api", "v1/items", "https://example.com/api/v1/items"),
    ],
)
def test_join_url(base, url, expected):
    assert _join_url(base, url) == expected


def test_parse_retry_after_seconds_numeric():
    assert _parse_retry_after_seconds({"Retry-After": "5"}) == 5.0


def test_parse_retry_after_seconds_missing():
    assert _parse_retry_after_seconds({"X": "1"}) is None

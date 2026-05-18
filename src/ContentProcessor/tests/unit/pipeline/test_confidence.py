# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.handlers.logics.evaluate_handler.confidence (score merging)."""

from __future__ import annotations

from libs.pipeline.handlers.logics.evaluate_handler.confidence import (
    find_keys_with_min_confidence,
    get_confidence_values,
    merge_confidence_values,
)

# ── TestGetConfidenceValues ─────────────────────────────────────────────


class TestGetConfidenceValues:
    """Recursive extraction of confidence scores from nested data."""

    def test_flat_dict(self):
        data = {"field": {"confidence": 0.9, "value": "x"}}
        assert get_confidence_values(data) == [0.9]

    def test_nested_dict(self):
        data = {
            "a": {"confidence": 0.8, "value": "x"},
            "b": {"confidence": 0.95, "value": "y"},
        }
        values = get_confidence_values(data)
        assert sorted(values) == [0.8, 0.95]

    def test_skips_zero_and_none(self):
        data = {
            "a": {"confidence": 0, "value": "x"},
            "b": {"confidence": None, "value": "y"},
            "c": {"confidence": 0.5, "value": "z"},
        }
        assert get_confidence_values(data) == [0.5]

    def test_list_nesting(self):
        data = [
            {"confidence": 0.7, "value": "x"},
            {"confidence": 0.6, "value": "y"},
        ]
        assert sorted(get_confidence_values(data)) == [0.6, 0.7]

    def test_empty_dict(self):
        assert get_confidence_values({}) == []

    def test_skips_boolean_confidence(self):
        data = {"field": {"confidence": True, "value": "x"}}
        assert get_confidence_values(data) == []


# ── TestFindKeysWithMinConfidence ───────────────────────────────────────


class TestFindKeysWithMinConfidence:
    """Locate fields matching a specific confidence threshold."""

    def test_finds_matching_keys(self):
        data = {
            "a": {"confidence": 0.5, "value": "x"},
            "b": {"confidence": 0.8, "value": "y"},
        }
        result = find_keys_with_min_confidence(data, 0.5)
        assert "a" in result
        assert "b" not in result

    def test_no_matches(self):
        data = {"a": {"confidence": 0.9, "value": "x"}}
        assert find_keys_with_min_confidence(data, 0.1) == []


# ── TestMergeConfidenceValues ───────────────────────────────────────────


class TestMergeConfidenceValues:
    """Merge two confidence evaluations by taking the min score per field."""

    def test_basic_merge(self):
        a = {"field1": {"confidence": 0.9, "value": "x"}}
        b = {"field1": {"confidence": 0.7, "value": "x"}}
        result = merge_confidence_values(a, b)
        assert result["field1"]["confidence"] == 0.7

    def test_merge_preserves_value_from_first(self):
        a = {"f": {"confidence": 0.8, "value": "hello"}}
        b = {"f": {"confidence": 0.6, "value": "world"}}
        result = merge_confidence_values(a, b)
        assert result["f"]["value"] == "hello"

    def test_merge_adds_summary_fields(self):
        a = {
            "f1": {"confidence": 0.8, "value": "x"},
            "f2": {"confidence": 0.6, "value": "y"},
        }
        b = {
            "f1": {"confidence": 0.9, "value": "x"},
            "f2": {"confidence": 0.5, "value": "y"},
        }
        result = merge_confidence_values(a, b)
        assert "overall_confidence" in result
        assert "total_evaluated_fields_count" in result
        assert result["total_evaluated_fields_count"] == 2
        assert "min_extracted_field_confidence" in result

    def test_merge_empty_dicts(self):
        result = merge_confidence_values({}, {})
        assert result["overall_confidence"] == 0.0
        assert result["total_evaluated_fields_count"] == 0

    def test_merge_with_list_fields(self):
        a = {
            "items": [
                {"confidence": 0.9, "value": "a"},
                {"confidence": 0.8, "value": "b"},
            ]
        }
        b = {
            "items": [
                {"confidence": 0.7, "value": "a"},
                {"confidence": 0.6, "value": "b"},
            ]
        }
        result = merge_confidence_values(a, b)
        assert result["items"][0]["confidence"] == 0.7
        assert result["items"][1]["confidence"] == 0.6

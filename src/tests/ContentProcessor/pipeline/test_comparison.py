# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.handlers.logics.evaluate_handler.comparison (extraction comparison)."""

from __future__ import annotations

from libs.pipeline.handlers.logics.evaluate_handler.comparison import (
    ExtractionComparisonData,
    ExtractionComparisonItem,
    get_extraction_comparison_data,
)

# ── TestExtractionComparisonItem ────────────────────────────────────────


class TestExtractionComparisonItem:
    """Single comparison row serialisation."""

    def test_construction(self):
        item = ExtractionComparisonItem(
            Field="name",
            Extracted="John",
            Confidence="95.00%",
            IsAboveThreshold=True,
        )
        assert item.Field == "name"
        assert item.Extracted == "John"

    def test_to_dict(self):
        item = ExtractionComparisonItem(
            Field="age", Extracted=30, Confidence="88.00%", IsAboveThreshold=True
        )
        d = item.to_dict()
        assert d["Field"] == "age"
        assert d["Extracted"] == 30

    def test_to_json(self):
        item = ExtractionComparisonItem(
            Field="x", Extracted="y", Confidence="100.00%", IsAboveThreshold=True
        )
        json_str = item.to_json()
        assert '"Field"' in json_str


# ── TestExtractionComparisonData ────────────────────────────────────────


class TestExtractionComparisonData:
    """Collection of comparison items with serialisation."""

    def test_construction(self):
        items = [
            ExtractionComparisonItem(
                Field="f1",
                Extracted="v1",
                Confidence="90.00%",
                IsAboveThreshold=True,
            )
        ]
        data = ExtractionComparisonData(items=items)
        assert len(data.items) == 1

    def test_to_dict(self):
        data = ExtractionComparisonData(items=[])
        d = data.to_dict()
        assert d["items"] == []


# ── TestGetExtractionComparisonData ─────────────────────────────────────


class TestGetExtractionComparisonData:
    """Build comparison rows from actual results and confidence scores."""

    def test_basic_comparison(self):
        actual = {"name": "John", "age": 30}
        confidence = {"name_confidence": 0.95, "age_confidence": 0.8}
        result = get_extraction_comparison_data(actual, confidence, 0.9)
        assert len(result.items) == 2
        fields = {item.Field for item in result.items}
        assert "name" in fields
        assert "age" in fields

    def test_above_threshold_flag(self):
        actual = {"score": 100}
        confidence = {"score_confidence": 0.95}
        result = get_extraction_comparison_data(actual, confidence, 0.9)
        item = result.items[0]
        assert item.Confidence == "95.00%"
        assert item.IsAboveThreshold is True

    def test_below_threshold_flag(self):
        actual = {"score": 100}
        confidence = {"score_confidence": 0.5}
        result = get_extraction_comparison_data(actual, confidence, 0.9)
        item = result.items[0]
        assert item.IsAboveThreshold is False

    def test_nested_input(self):
        actual = {"address": {"city": "Seattle", "zip": "98101"}}
        confidence = {
            "address_city_confidence": 0.99,
            "address_zip_confidence": 0.85,
        }
        result = get_extraction_comparison_data(actual, confidence, 0.9)
        assert len(result.items) == 2

    def test_missing_confidence_defaults_to_zero(self):
        actual = {"field_a": "value"}
        confidence = {}
        result = get_extraction_comparison_data(actual, confidence, 0.5)
        assert result.items[0].Confidence == "0.00%"

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for ``SaveHandler._derive_aggregate_scores``.

Covers the score-derivation contract:
- probabilistic confidence flows through verbatim when available
- structural completeness fallback fires for Completed runs without logprobs
  (e.g. reasoning models / image-only flow) instead of emitting a misleading 0%
- a genuine zero is preserved as ``0.0``
- failed/empty runs return ``0.0``
"""

from __future__ import annotations

from libs.pipeline.handlers.logics.evaluate_handler.comparison import (
    ExtractionComparisonData,
    ExtractionComparisonItem,
)
from libs.pipeline.handlers.logics.evaluate_handler.model import DataExtractionResult
from libs.pipeline.handlers.save_handler import SaveHandler


def _make_result(
    *,
    items: list[ExtractionComparisonItem],
    confidence: dict,
) -> DataExtractionResult:
    return DataExtractionResult(
        extracted_result={},
        confidence=confidence,
        comparison_result=ExtractionComparisonData(items=items),
        prompt_tokens=0,
        completion_tokens=0,
        execution_time=0,
    )


class TestProbabilisticPath:
    def test_valid_scores_flow_through(self):
        """A normal evaluate-step result must produce numeric scores."""
        items = [
            ExtractionComparisonItem(
                Field="a", Extracted="x", Confidence="90.00%", IsAboveThreshold="True"
            ),
            ExtractionComparisonItem(
                Field="b", Extracted="y", Confidence="80.00%", IsAboveThreshold="True"
            ),
            ExtractionComparisonItem(
                Field="c", Extracted="z", Confidence="0.00%", IsAboveThreshold="False"
            ),
        ]
        confidence = {
            "total_evaluated_fields_count": 3,
            "overall_confidence": 0.567,
            "min_extracted_field_confidence": 0.0,
            "zero_confidence_fields_count": 1,
        }
        entity, schema, min_score = SaveHandler._derive_aggregate_scores(
            _make_result(items=items, confidence=confidence)
        )
        assert entity == 0.567
        # 2 of 3 fields above threshold → 0.667
        assert schema == round(2 / 3, 3)
        assert min_score == 0.0

    def test_all_fields_above_threshold(self):
        items = [
            ExtractionComparisonItem(
                Field="a", Extracted="x", Confidence="95.00%", IsAboveThreshold="True"
            ),
            ExtractionComparisonItem(
                Field="b", Extracted="y", Confidence="90.00%", IsAboveThreshold="True"
            ),
        ]
        confidence = {
            "total_evaluated_fields_count": 2,
            "overall_confidence": 0.925,
            "min_extracted_field_confidence": 0.9,
            "zero_confidence_fields_count": 0,
        }
        entity, schema, min_score = SaveHandler._derive_aggregate_scores(
            _make_result(items=items, confidence=confidence)
        )
        assert entity == 0.925
        assert schema == 1.0
        assert min_score == 0.9


class TestStructuralFallback:
    """When logprobs are unavailable (reasoning model / image-only) but
    extraction succeeded, the Completed file must still get a meaningful
    numeric score based on schema completeness."""

    def test_all_fields_filled_yields_one(self):
        items = [
            ExtractionComparisonItem(
                Field="a", Extracted="x", Confidence="0.00%", IsAboveThreshold="False"
            ),
            ExtractionComparisonItem(
                Field="b", Extracted="y", Confidence="0.00%", IsAboveThreshold="False"
            ),
            ExtractionComparisonItem(
                Field="c", Extracted=42, Confidence="0.00%", IsAboveThreshold="False"
            ),
        ]
        # No probabilistic signal: total_evaluated_fields_count == 0
        confidence = {
            "total_evaluated_fields_count": 0,
            "overall_confidence": 0.0,
            "min_extracted_field_confidence": 0.0,
            "zero_confidence_fields_count": 0,
        }
        entity, schema, min_score = SaveHandler._derive_aggregate_scores(
            _make_result(items=items, confidence=confidence)
        )
        assert entity == 1.0
        assert schema == 1.0
        assert min_score == 1.0

    def test_partial_fill_yields_ratio(self):
        items = [
            ExtractionComparisonItem(
                Field="a", Extracted="x", Confidence="0.00%", IsAboveThreshold="False"
            ),
            ExtractionComparisonItem(
                Field="b", Extracted=None, Confidence="0.00%", IsAboveThreshold="False"
            ),
            ExtractionComparisonItem(
                Field="c", Extracted="", Confidence="0.00%", IsAboveThreshold="False"
            ),
            ExtractionComparisonItem(
                Field="d", Extracted="z", Confidence="0.00%", IsAboveThreshold="False"
            ),
        ]
        confidence = {"total_evaluated_fields_count": 0}
        entity, schema, min_score = SaveHandler._derive_aggregate_scores(
            _make_result(items=items, confidence=confidence)
        )
        # 2 of 4 fields actually filled → 0.5
        assert entity == 0.5
        assert schema == 0.5
        assert min_score == 0.5

    def test_all_fields_empty_yields_zero(self):
        """Genuine-empty extraction: structural fallback collapses to ``0.0``."""
        items = [
            ExtractionComparisonItem(
                Field="a", Extracted=None, Confidence="0.00%", IsAboveThreshold="False"
            ),
            ExtractionComparisonItem(
                Field="b", Extracted="", Confidence="0.00%", IsAboveThreshold="False"
            ),
            ExtractionComparisonItem(
                Field="c", Extracted="   ", Confidence="0.00%", IsAboveThreshold="False"
            ),
        ]
        confidence = {"total_evaluated_fields_count": 0}
        entity, schema, min_score = SaveHandler._derive_aggregate_scores(
            _make_result(items=items, confidence=confidence)
        )
        assert entity == 0.0
        assert schema == 0.0
        assert min_score == 0.0


class TestZeroPath:
    def test_no_comparison_items_returns_zero(self):
        """No extraction data at all (failed pipeline) → ``0.0``."""
        confidence = {
            "total_evaluated_fields_count": 0,
            "overall_confidence": 0.0,
            "min_extracted_field_confidence": 0.0,
            "zero_confidence_fields_count": 0,
        }
        entity, schema, min_score = SaveHandler._derive_aggregate_scores(
            _make_result(items=[], confidence=confidence)
        )
        assert entity == 0.0
        assert schema == 0.0
        assert min_score == 0.0

    def test_genuine_zero_probabilistic_score_preserved(self):
        """A real ``0`` confidence (every field below threshold) must NOT be
        replaced by the structural fallback — it's genuinely 0%."""
        items = [
            ExtractionComparisonItem(
                Field="a", Extracted="x", Confidence="0.00%", IsAboveThreshold="False"
            ),
        ]
        confidence = {
            "total_evaluated_fields_count": 1,
            "overall_confidence": 0.0,
            "min_extracted_field_confidence": 0.0,
            "zero_confidence_fields_count": 1,
        }
        entity, schema, min_score = SaveHandler._derive_aggregate_scores(
            _make_result(items=items, confidence=confidence)
        )
        assert entity == 0.0
        assert schema == 0.0
        assert min_score == 0.0


class TestIsFilledValue:
    """Coverage for the ``_is_filled_value`` helper used by the structural fallback."""

    def test_none_is_empty(self):
        assert SaveHandler._is_filled_value(None) is False

    def test_empty_string_is_empty(self):
        assert SaveHandler._is_filled_value("") is False
        assert SaveHandler._is_filled_value("   ") is False

    def test_non_empty_string_is_filled(self):
        assert SaveHandler._is_filled_value("x") is True

    def test_zero_int_is_filled(self):
        # A literal ``0`` is a valid extracted value (e.g. count fields).
        assert SaveHandler._is_filled_value(0) is True

    def test_bool_is_filled(self):
        assert SaveHandler._is_filled_value(False) is True
        assert SaveHandler._is_filled_value(True) is True

    def test_empty_container_is_empty(self):
        assert SaveHandler._is_filled_value([]) is False
        assert SaveHandler._is_filled_value({}) is False

    def test_nested_all_null_is_empty(self):
        assert SaveHandler._is_filled_value({"a": None, "b": ""}) is False
        assert SaveHandler._is_filled_value([None, "", {"c": None}]) is False

    def test_nested_with_value_is_filled(self):
        assert SaveHandler._is_filled_value({"a": None, "b": "x"}) is True
        assert SaveHandler._is_filled_value([None, "x"]) is True


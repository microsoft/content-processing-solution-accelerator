# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for ``SaveHandler._derive_aggregate_scores``.

Covers the score-availability semantics:
- valid scores flow through verbatim
- missing per-field signal yields ``None`` (rendered as "N/A" in the UI)
- a genuine zero is preserved as ``0`` (rendered as "0%")
- failed processing (no comparison items) yields ``None``
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


class TestDeriveAggregateScores:
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

    def test_missing_per_field_signal_returns_none(self):
        """Reasoning-model / image-only flow: no signal → ``None`` everywhere."""
        items: list[ExtractionComparisonItem] = []
        confidence = {
            "total_evaluated_fields_count": 0,
            "overall_confidence": 0.0,
            "min_extracted_field_confidence": 0.0,
            "zero_confidence_fields_count": 0,
        }
        entity, schema, min_score = SaveHandler._derive_aggregate_scores(
            _make_result(items=items, confidence=confidence)
        )
        assert entity is None
        assert schema is None
        assert min_score is None

    def test_no_comparison_items_returns_none(self):
        """Even if confidence claims fields exist, an empty comparison list is unknown."""
        confidence = {
            "total_evaluated_fields_count": 5,
            "overall_confidence": 0.9,
            "min_extracted_field_confidence": 0.5,
            "zero_confidence_fields_count": 0,
        }
        entity, schema, min_score = SaveHandler._derive_aggregate_scores(
            _make_result(items=[], confidence=confidence)
        )
        assert entity is None
        assert schema is None
        assert min_score is None

    def test_genuine_zero_score_preserved(self):
        """A real ``0`` confidence (e.g. all fields below threshold) must NOT become ``None``."""
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

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.handlers.logics.evaluate_handler.model (result containers)."""

from __future__ import annotations

from libs.pipeline.handlers.logics.evaluate_handler.comparison import (
    ExtractionComparisonData,
)
from libs.pipeline.handlers.logics.evaluate_handler.model import (
    DataClassificationResult,
    DataExtractionResult,
)

# ── TestDataExtractionResult ────────────────────────────────────────────


class TestDataExtractionResult:
    """Pydantic model for extraction results with serialisation."""

    def _make_result(self):
        return DataExtractionResult(
            extracted_result={"name": "Alice"},
            confidence={"name_confidence": 0.9},
            comparison_result=ExtractionComparisonData(items=[]),
            prompt_tokens=100,
            completion_tokens=50,
            execution_time=3,
        )

    def test_construction(self):
        result = self._make_result()
        assert result.extracted_result == {"name": "Alice"}
        assert result.prompt_tokens == 100

    def test_to_json(self):
        result = self._make_result()
        json_str = result.to_json()
        assert '"extracted_result"' in json_str
        assert '"Alice"' in json_str

    def test_to_dict(self):
        result = self._make_result()
        d = result.to_dict()
        assert d["prompt_tokens"] == 100
        assert d["completion_tokens"] == 50


# ── TestDataClassificationResult ────────────────────────────────────────


class TestDataClassificationResult:
    """Plain class for classification results."""

    def test_construction(self):
        result = DataClassificationResult(
            classification={"category": "invoice"},
            accuracy=0.95,
            execution_time=1.5,
        )
        assert result.classification == {"category": "invoice"}
        assert result.accuracy == 0.95

    def test_to_dict(self):
        result = DataClassificationResult(
            classification={"type": "receipt"}, accuracy=0.88, execution_time=2.0
        )
        d = result.to_dict()
        assert d["classification"] == {"type": "receipt"}
        assert d["accuracy"] == 0.88
        assert d["execution_time"] == 2.0

    def test_to_json(self):
        result = DataClassificationResult(
            classification={"type": "form"}, accuracy=0.75, execution_time=1.0
        )
        json_str = result.to_json()
        assert '"classification"' in json_str

    def test_none_values(self):
        result = DataClassificationResult(
            classification=None, accuracy=None, execution_time=None
        )
        d = result.to_dict()
        assert d["classification"] is None

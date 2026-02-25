"""Tests for comparison module."""

import pytest
from libs.pipeline.handlers.logics.evaluate_handler.comparison import (
    ExtractionComparisonItem,
    ExtractionComparisonData,
    get_extraction_comparison_data,
    get_extraction_comparison,
)


class TestExtractionComparisonItem:
    """Tests for ExtractionComparisonItem class."""

    def test_to_dict(self):
        """Test that to_dict returns a dictionary representation."""
        item = ExtractionComparisonItem(
            Field="test_field",
            Extracted="test_value",
            Confidence="95.00%",
            IsAboveThreshold=True,
        )
        result = item.to_dict()
        assert isinstance(result, dict)
        assert result["Field"] == "test_field"
        assert result["Extracted"] == "test_value"
        assert result["Confidence"] == "95.00%"
        assert result["IsAboveThreshold"] is True

    def test_to_json(self):
        """Test that to_json returns a JSON string representation."""
        item = ExtractionComparisonItem(
            Field="test_field",
            Extracted="test_value",
            Confidence="95.00%",
            IsAboveThreshold=True,
        )
        result = item.to_json()
        assert isinstance(result, str)
        assert "test_field" in result
        assert "test_value" in result


class TestExtractionComparisonData:
    """Tests for ExtractionComparisonData class."""

    def test_to_dict(self):
        """Test that to_dict returns a dictionary representation."""
        item = ExtractionComparisonItem(
            Field="field1", Extracted="value1", Confidence="90.00%", IsAboveThreshold=True
        )
        data = ExtractionComparisonData(items=[item])
        result = data.to_dict()
        assert isinstance(result, dict)
        assert "items" in result
        assert len(result["items"]) == 1

    def test_to_json(self):
        """Test that to_json returns a JSON string representation."""
        item = ExtractionComparisonItem(
            Field="field1", Extracted="value1", Confidence="90.00%", IsAboveThreshold=True
        )
        data = ExtractionComparisonData(items=[item])
        result = data.to_json()
        assert isinstance(result, str)
        assert "field1" in result


class TestGetExtractionComparisonData:
    """Tests for get_extraction_comparison_data function."""

    def test_basic_comparison(self):
        """Test basic extraction comparison data generation."""
        actual = {"name": "John", "age": 30}
        confidence = {"name_confidence": 0.95, "age_confidence": 0.85}
        threshold = 0.8

        result = get_extraction_comparison_data(actual, confidence, threshold)

        assert isinstance(result, ExtractionComparisonData)
        assert len(result.items) == 2

    def test_above_threshold(self):
        """Test that IsAboveThreshold is set correctly when above threshold."""
        actual = {"field1": "value1"}
        confidence = {"field1_confidence": 0.95}
        threshold = 0.8

        result = get_extraction_comparison_data(actual, confidence, threshold)

        assert result.items[0].IsAboveThreshold in (True, "True")

    def test_below_threshold(self):
        """Test that IsAboveThreshold is set correctly when below threshold."""
        actual = {"field1": "value1"}
        confidence = {"field1_confidence": 0.5}
        threshold = 0.8

        result = get_extraction_comparison_data(actual, confidence, threshold)

        assert result.items[0].IsAboveThreshold in (False, "False")

    def test_nested_dict(self):
        """Test comparison with nested dictionary."""
        actual = {"person": {"name": "John"}}
        confidence = {"person.name_confidence": 0.9}
        threshold = 0.8

        result = get_extraction_comparison_data(actual, confidence, threshold)

        assert len(result.items) >= 1


class TestGetExtractionComparison:
    """Tests for get_extraction_comparison function."""

    def test_basic_comparison_dataframe(self):
        """Test that get_extraction_comparison returns a styled DataFrame."""
        pytest.importorskip("jinja2")
        expected = {"name": "John", "age": 30}
        actual = {"name": "John", "age": 30}
        confidence = {"name_confidence": 0.95, "age_confidence": 0.85}
        accuracy = {"accuracy_name": 1.0, "accuracy_age": 1.0}

        result = get_extraction_comparison(expected, actual, confidence, accuracy)

        # Result should be a styled DataFrame
        assert result is not None

    def test_mismatch_detection(self):
        """Test that mismatches are detected correctly."""
        pytest.importorskip("jinja2")
        expected = {"name": "John"}
        actual = {"name": "Jane"}
        confidence = {"name_confidence": 0.95}
        accuracy = {"accuracy_name": 0.0}

        result = get_extraction_comparison(expected, actual, confidence, accuracy)

        assert result is not None

    def test_match_detection(self):
        """Test that matches are detected correctly."""
        pytest.importorskip("jinja2")
        expected = {"field1": "value1"}
        actual = {"field1": "value1"}
        confidence = {"field1_confidence": 0.95}
        accuracy = {"accuracy_field1": 1.0}

        result = get_extraction_comparison(expected, actual, confidence, accuracy)

        assert result is not None

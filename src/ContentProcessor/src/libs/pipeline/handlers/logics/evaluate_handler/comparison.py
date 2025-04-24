from typing import Any, List, Optional

import pandas as pd
from pydantic import BaseModel

from libs.utils.utils import flatten_dict


class ExtractionComparisonItem(BaseModel):
    Field: Optional[str]
    Extracted: Optional[Any]
    Confidence: Optional[str]
    IsAboveThreshold: Optional[bool]

    def to_dict(self) -> dict:
        return self.model_dump()

    def to_json(self) -> str:
        return self.model_dump_json(indent=4)


class ExtractionComparisonData(BaseModel):
    items: List[ExtractionComparisonItem]

    def to_dict(self) -> dict:
        return self.model_dump()

    def to_json(self) -> str:
        return self.model_dump_json(indent=4)


def get_extraction_comparison_data(
    actual: dict, confidence: dict, threads_hold: float
) -> ExtractionComparisonData:
    """
    Generate a JSON object comparing the extracted fields with the expected fields.

    Args:
        actual: The extracted fields.
        confidence: The confidence values for the extracted fields.

    Returns:
        ExtractionComparisonData: The JSON object comparing the extracted fields with the expected fields.
    """

    # expected_flat = flatten_dict(expected)
    extracted_flat = flatten_dict(actual)
    confidence_flat = flatten_dict(confidence)
    # accuracy_flat = flatten_dict(accuracy)

    all_keys = sorted(set(extracted_flat.keys()))

    items = []
    for key in all_keys:
        items.append(
            ExtractionComparisonItem(
                Field=key,
                Extracted=extracted_flat.get(key),
                Confidence=f"{confidence_flat.get(f'{key}_confidence', 0.0) * 100:.2f}%",
                IsAboveThreshold=f"{True if confidence_flat.get(f'{key}_confidence', 0.0) > threads_hold else False}",
            )
        )

    return ExtractionComparisonData(items=items)


def get_extraction_comparison(
    expected: dict, actual: dict, confidence: dict, accuracy: dict
):
    """
    Generate a pandas DataFrame comparing the extracted fields with the expected fields.
    If a match is found, the row is highlighted in green. If a mismatch is found, the row is highlighted in red.

    Args:
        expected: The expected fields.
        actual: The extracted fields.
        confidence: The confidence values for the extracted fields.
        accuracy: The accuracy values for the extracted fields.

    Returns:
        pd.DataFrame: The DataFrame comparing the extracted fields with the expected fields.
    """

    expected_flat = flatten_dict(expected)
    extracted_flat = flatten_dict(actual)
    confidence_flat = flatten_dict(confidence)
    accuracy_flat = flatten_dict(accuracy)

    all_keys = sorted(set(expected_flat.keys()) | set(extracted_flat.keys()))

    rows = []
    for key in all_keys:
        rows.append(
            {
                "Field": key,
                "Expected": expected_flat.get(key),
                "Extracted": extracted_flat.get(key),
                "Confidence": f"{confidence_flat.get(f'{key}_confidence', 0.0) * 100:.2f}%",
                "Accuracy": f"{'Match' if accuracy_flat.get(f'accuracy_{key}', 0.0) == 1.0 else 'Mismatch'}",
            }
        )
    df = pd.DataFrame(rows)

    def highlight_row(row):
        return [
            "background-color: #66ff33"
            if row.Accuracy == "Match"
            else "background-color: #ff9999"
        ] * len(row)

    df = df.style.apply(highlight_row, axis=1)
    return df

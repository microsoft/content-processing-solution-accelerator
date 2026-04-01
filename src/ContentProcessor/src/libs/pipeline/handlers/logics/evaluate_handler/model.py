# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Result container models for extraction and classification.

Used by the evaluate and save handlers to bundle extracted data,
confidence scores, comparison results, and token usage into a
single serializable object.
"""

from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel

from libs.pipeline.handlers.logics.evaluate_handler.comparison import (
    ExtractionComparisonData,
)
from libs.utils.utils import CustomEncoder


class DataExtractionResult(BaseModel):
    """
    A class representing the result of data extraction.

    Attributes:
        extract_result: The extracted data.
        confidence: The confidence of the extracted data.
        accuracy: The accuracy of the extracted data.
        prompt_tokens: The number of tokens in the prompt.
        completion_tokens: The number of tokens in the completion.
        execution_time: The execution time of the data extraction.
    """

    extracted_result: dict
    confidence: dict
    comparison_result: ExtractionComparisonData
    prompt_tokens: int
    completion_tokens: int
    execution_time: int

    def to_json(self, indent: Optional[int] = 4) -> str:
        """
        Converts the DataExtractionResult object to a JSON string using a CustomEncoder for serializing objects with 'to_dict' and 'as_dict' methods.

        Args:
            indent: The number of spaces to indent the JSON string.

        Returns:
            str: The DataExtractionResult object as a JSON string.
        """

        # return json.dumps(self.to_dict(), indent=indent, cls=CustomEncoder)
        return self.model_dump_json(indent=indent)

    def to_dict(self) -> dict:
        """
        Converts the DataExtractionResult object to a dictionary.

        Returns:
            dict: The DataExtractionResult object as a dictionary.
        """
        return self.model_dump()


class DataClassificationResult:
    """
    A class representing the result of data classification.

    Attributes:
        classification: The classification of the data.
        accuracy: The accuracy of the classification.
        execution_time: The execution time of the data classification.
    """

    def __init__(
        self,
        classification: Optional[dict],
        accuracy: Optional[float],
        execution_time: Optional[float],
    ):
        """
        Initializes a new instance of the DataClassificationResult class.

        Args:
            classification: The classification of the data.
            accuracy: The accuracy of the classification.
            execution_time: The execution time of the data classification.
        """

        self.classification = classification
        self.accuracy = accuracy
        self.execution_time = execution_time

    def to_json(self, indent: Optional[int] = 4) -> str:
        """
        Converts the DataClassificationResult object to a JSON string using a CustomEncoder for serializing objects with 'to_dict' and 'as_dict' methods.

        Args:
            indent: The number of spaces to indent the JSON string.

        Returns:
            str: The DataClassificationResult object as a JSON string.
        """

        return json.dumps(self.to_dict(), indent=indent, cls=CustomEncoder)

    def to_dict(self) -> dict:
        """
        Converts the DataClassificationResult object to a dictionary.

        Returns:
            dict: The DataClassificationResult object as a dictionary.
        """

        return {
            "classification": self.classification,
            "accuracy": self.accuracy,
            "execution_time": self.execution_time,
        }

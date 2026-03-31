# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Confidence scoring against Azure Content Understanding OCR results.

Cross-references extracted field values with OCR lines to derive
per-field confidence based on word-level recognition scores.
"""

import copy
from typing import Iterable, Optional

from pydantic import Field

from libs.azure_helper.model.content_understanding import (
    DocumentContent,
    Line,
    Page,
    Word,
)
from libs.pipeline.handlers.logics.evaluate_handler.confidence import (
    get_confidence_values,
)
from libs.utils.utils import value_contains, value_match


class DIDocumentLine(Line):
    """
    A class representing a line in a document extracted by Azure AI Document Intelligence with additional attributes.

    Attributes:
        normalized_polygon (Optional[list[dict[str, int]]]): The normalized polygon coordinates of the document line.
        confidence (float): The confidence score of the document line.
        page_number (int): The page number where the document line is located.
        contained_words (list[DocumentWord]): The list of words contained in the document line.
    """

    normalized_polygon: Optional[list[dict[str, int]]] = Field(default=None)
    confidence: Optional[float] = Field(default=None)
    page_number: Optional[int] = Field(default=None)
    contained_words: Optional[list[Word]] = Field(default=None)

    def to_dict(self):
        """
        Converts the DIDocumentLine instance to a dictionary.

        Returns:
            dict: The dictionary representation of the DIDocumentLine instance including the base DocumentLine attributes.
        """

        as_dict = self.as_dict()
        as_dict["normalized_polygon"] = self.normalized_polygon
        as_dict["confidence"] = self.confidence
        as_dict["page_number"] = self.page_number
        as_dict["contained_words"] = self.contained_words

        return as_dict


class DIDocumentWord(Word):
    """
    A class representing a document word extracted by Azure AI Document Intelligence with additional attributes.

    Attributes:
        normalized_polygon (Optional[list[dict[str, int]]]): The normalized polygon coordinates of the document word.
        page_number (int): The page number where the document word is located.
        content_type (str): The content type of the document word.
    """

    normalized_polygon: Optional[list[dict[str, int]]]
    page_number: int

    def to_dict(self):
        """
        Converts the DIDocumentWord instance to a dictionary.

        Returns:
            dict: The dictionary representation of the DIDocumentWord instance including the base DocumentWord attributes.
        """

        as_dict = self.as_dict()
        as_dict["normalized_polygon"] = self.normalized_polygon
        as_dict["page_number"] = self.page_number

        return as_dict


def normalize_polygon(page: Page, polygon: list[float]) -> list[dict[str, int]]:
    """
    Normalize a polygon's coordinates to page dimensions.
    The polygon is represented as a list of x, y coordinates starting from the top-left corner of the page and moving clockwise.

    Args:
        page: The page to normalize the polygon to.
        polygon: The polygon coordinates on the page to normalize.

    Returns:
        list: The normalized polygon coordinates as a list of dictionaries with 'x' and 'y' keys.
    """

    result = list()

    for i in range(0, len(polygon), 2):
        x = polygon[i]
        y = polygon[i + 1]

        # Normalize the coordinates to the page dimensions
        x = round(x / page.width, 3)
        y = round(y / page.height, 3)

        result.append({"x": x, "y": y})

    return result


def extract_lines(
    analyze_result: DocumentContent, multiple_score_resolver: callable = min
) -> list[DIDocumentLine]:
    """
    Extract lines from the  Content Understanding Service result, enriching with confidence, contained words, and normalized polygons.

    Args:
        result: The  Content Understanding Service result to extract lines from.
        multiple_score_resolver: The function to resolve multiple confidence scores of contained words.

    Returns:
        list: The list of DIDocumentLine instances extracted from the analysis result.
    """

    di_lines = list()
    for page_number, page in enumerate(analyze_result.pages):
        for line in page.lines:
            line_copy = copy.copy(line)
            contained_words = list()
            # for span in line_copy.spans:
            # Find words in the page that are fully contained within the span
            span = line_copy.span
            span_offset_start = span.offset
            span_offset_end = span_offset_start + span.length
            words_contained = [
                word
                for word in page.words
                if word.span.offset >= span_offset_start
                and word.span.offset + word.span.length <= span_offset_end
            ]
            contained_words.extend(words_contained)

            contained_words_conf_scores = [word.confidence for word in contained_words]

            di_line = DIDocumentLine(**line_copy.model_dump())
            di_line.contained_words = contained_words
            di_line.page_number = page_number
            di_line.confidence = multiple_score_resolver(contained_words_conf_scores)
            di_line.normalized_polygon = normalize_polygon(page, line_copy.polygon)

            di_lines.append(di_line)
    return di_lines


def find_matching_lines(
    value: str,
    analyze_result: DocumentContent,
    value_matcher: callable = value_match,
    multiple_score_resolver: callable = min,
) -> list[DIDocumentLine]:
    """
    Find lines in the  Content Understanding Service result that match a given value.

    Args:
        value: The value to match.
        analyze_result: The  Content Understanding Service result to search for matching lines.
        value_matcher: The function to use for matching values.
        multiple_score_resolver: The function to resolve multiple confidence scores of contained words.

    Returns:
        list: The list of DIDocumentLine instances that match the given value.
    """

    if not value:
        return list()

    if not isinstance(value, str):
        value = str(value)

    di_lines = extract_lines(analyze_result, multiple_score_resolver)

    matching_lines = [line for line in di_lines if value_matcher(value, line.content)]

    return matching_lines


def get_field_confidence_score(
    scores: Iterable[float],
    default_score: Optional[float | int] = None,
    multiple_score_resolver: callable = min,
) -> float:
    """
    Determines the field confidence score based on potentially multiple scores.

    Args:
        scores: The confidence scores for the field.
        default_score: The default confidence score to return if no scores are provided.
        multiple_score_resolver: The function to resolve multiple confidence scores.

    Returns:
        float: The field confidence score.
    """

    if len(scores) == 1:
        return scores[0]
    if len(scores) == 0:
        return default_score
    return multiple_score_resolver(scores)


def evaluate_confidence(extract_result: dict, analyze_result: DocumentContent):
    """
    Evaluate the confidence of extracted fields based on the  Content Understanding Service result.

    Args:
        extract_result: The extracted fields to evaluate.
        analyze_result: The  Content Understanding Service result to evaluate against.

    Returns:
        dict: The confidence evaluation of the extracted fields.
    """

    def evaluate_field_value_confidence(
        value: any,
    ) -> dict[str, any]:
        """
        Evaluate the confidence of a field value based on the  Content Understanding Service result.

        Args:
            value: The field value to evaluate.

        Returns:
            dict: The confidence evaluation of the field value.
        """

        if isinstance(value, dict):
            # Recursively evaluate confidence for nested values
            return {
                key: evaluate_field_value_confidence(val) for key, val in value.items()
            }
        elif isinstance(value, list):
            # Evaluate confidence for each item in the list
            return [evaluate_field_value_confidence(item) for item in value]
        else:
            # Find lines that match the value exactly or contain the value
            matching_lines = find_matching_lines(
                value, analyze_result, value_matcher=value_match
            )
            if not matching_lines:
                matching_lines = find_matching_lines(
                    value, analyze_result, value_matcher=value_contains
                )

            # Calculate the confidence score based on the matching lines
            field_confidence_score = get_field_confidence_score(
                scores=[match.confidence for match in matching_lines],
                default_score=0.0,
                multiple_score_resolver=min,
            )

            normalized_polygons = [line.normalized_polygon for line in matching_lines]

            return {
                "confidence": field_confidence_score,
                "matching_lines": matching_lines,
                "normalized_polygons": normalized_polygons,
                "value": value,
            }

    confidence = dict()

    for field, value in extract_result.items():
        confidence[field] = evaluate_field_value_confidence(value)

    confidence_scores = get_confidence_values(confidence)

    if confidence_scores:
        confidence["_overall"] = sum(confidence_scores) / len(confidence_scores)
    else:
        confidence["_overall"] = 0.0

    return confidence

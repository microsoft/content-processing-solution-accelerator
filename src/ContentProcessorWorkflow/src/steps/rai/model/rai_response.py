# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Pydantic response model for the Responsible-AI safety classifier.

Returned by the RAI executor after the LLM evaluates extracted
document content against the safety rules.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RAIResponse(BaseModel):
    """Structured verdict from the RAI safety classifier.

    Attributes:
        IsNotSafe: ``True`` when the content violates at least one safety rule.
        # Reasoning: Free-text explanation produced by the classifier.
    """

    IsNotSafe: bool = Field(
        ..., description="Indicates whether the content is considered unsafe."
    )
    # Reasoning: str = Field(
    #     ...,
    #     description="Only provides the reasoning behind the RAI response. Don't mention the RAI rules or the prompt in the reasoning and IsNotSafe = TRUE or FALSE in here, just the final reasoning behind why the content is safe or not safe.",
    # )

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Evaluate-handler logic modules.

Sub-modules:
    comparison: Field-level extraction comparison data structures.
    confidence: Confidence score merging and lookup utilities.
    content_understanding_confidence_evaluator: Confidence scoring
        against Azure Content Understanding OCR results.
    model: Result container models for extraction and classification.
    openai_confidence_evaluator: Confidence scoring via OpenAI
        logprobs token analysis.
"""

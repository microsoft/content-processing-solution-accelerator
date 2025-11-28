# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import math

import tiktoken

from libs.pipeline.handlers.logics.evaluate_handler.confidence import (
    get_confidence_values,
)


def evaluate_confidence(extract_result: dict, choice: dict, model: str = "gpt-4o"):
    """
    Evaluate confidence for each field value in the extracted result based on the logprobs of the response from Azure AI Foundry.

    Args:
        extract_result: The extraction result.
        choice: The choice dictionary from the Azure AI Foundry response.
        model: The model used for the response.

    Returns:
        dict: The confidence evaluation of the extraction result.
    """

    confidence = dict()

    # Retrieves the specific encoding used for the OpenAI model that generated the response.
    encoding = tiktoken.encoding_for_model(model)

    # To perform the confidence evaluation, we need the original text from the response, not just the object result.
    generated_text = choice["message"]["content"]

    if choice.get("logprobs") is None:
        confidence["_overall"] = 0.0
        return confidence

    logprobs = choice["logprobs"]["content"]

    tokens = [token_logprob["token"] for token_logprob in logprobs]
    token_logprobs = [token_logprob["logprob"] for token_logprob in logprobs]

    # Encode the entire generated text to map tokens to character positions
    token_offsets = []
    current_pos = 0
    for token in tokens:
        token_bytes = encoding.encode(token, disallowed_special=())
        token_str = encoding.decode(token_bytes)
        token_length = len(token_str)
        token_offsets.append((current_pos, current_pos + token_length))
        current_pos += token_length

    substr_offset = 0

    def find_token_indices(substring: str, start_char: int):
        """
        Find the indices of tokens that contain a given substring.

        Args:
            substring: The substring to search for.
            start_char: The starting character position of the substring.

        Returns:
            list: The list of token indices that contain the substring.
        """

        substring_length = len(substring)
        end_char = start_char + substring_length
        indices = []
        for idx, (start, end) in enumerate(token_offsets):
            if start >= end_char:
                break
            if end > start_char:
                indices.append(idx)
        return indices

    def evaluate_field_value_confidence(value: any):
        """
        Evaluate confidence for a field value based on the logprobs of the response.

        Args:
            value: The value to evaluate.

        Returns:
            tuple: The confidence evaluation of the value and the updated substr_offset.
        """

        nonlocal substr_offset

        if isinstance(value, dict):
            # Recursively evaluate confidence for nested values
            return {
                key: evaluate_field_value_confidence(val) for key, val in value.items()
            }
        elif isinstance(value, list):
            # Evaluate confidence for each item in the list
            return [evaluate_field_value_confidence(item) for item in value]
        else:
            value_str = str(value)

            try:
                # Find the start index of the value in the generated text
                start_index = generated_text.index(value_str, substr_offset)
                substr_offset = start_index + len(value_str)
            except ValueError:
                return {"confidence": 0.0, "value": value}

            # Find all the token indices that cover the value string
            token_indices = find_token_indices(value_str, start_index)

            if not token_indices:
                return {"confidence": 0.0, "value": value}

            # Get the logprobs for the tokens that cover the value string
            value_logprobs = []
            for idx in token_indices:
                logprob = token_logprobs[idx]
                if logprob is not None:
                    value_logprobs.append(logprob)

            if not value_logprobs:
                return {"confidence": 0.0, "value": value}

            # Ensure that only likely tokens are considered for confidence calculation
            filtered_logprobs = [
                logprob for logprob in value_logprobs if logprob > -9999.0
            ]

            if not filtered_logprobs:
                return {"confidence": 0.0, "value": value}

            # Calculate the average log probability of the likely tokens
            avg_logprob = sum(filtered_logprobs) / len(filtered_logprobs)

            # Convert the average log probability to a confidence score
            confidence = math.exp(avg_logprob)

            # Clamp the confidence score to the range [0.0, 1.0]
            confidence = min(max(confidence, 0.0), 1.0)

            return {"confidence": confidence, "value": value}

    for field, value in extract_result.items():
        confidence[field] = evaluate_field_value_confidence(value)

    confidence_scores = get_confidence_values(confidence)

    if confidence_scores:
        confidence["_overall"] = sum(confidence_scores) / len(confidence_scores)
    else:
        confidence["_overall"] = 0.0

    return confidence

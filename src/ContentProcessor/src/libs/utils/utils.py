# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""General-purpose JSON encoding, dict flattening, and value comparison.

Provides helpers shared across pipeline handlers and evaluation logic.
"""

import json


class CustomEncoder(json.JSONEncoder):
    """
    A class representing a custom JSON encoder for serializing objects with custom dictionary representations.
    """

    def default(self, obj):
        """
        Serializes the object to a JSON-compatible format.
        Checks if the object has a 'to_dict', 'as_dict', or 'model_dump' method and calls it to get the dictionary representation.

        Args:
            obj: The object to serialize.

        Returns:
            str: The serialized object as a JSON-compatible format.
        """

        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "as_dict"):
            return obj.as_dict()
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return super().default(obj)


def flatten_dict(data, parent_key="", sep="_"):
    """
    Flatten a nested dictionary.

    Args:
        data: The dictionary to flatten.
        parent_key: The parent key.
        sep: The separator to use between keys.

    Returns:
        dict: The flattened dictionary with keys separated by the separator.
    """

    items = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                items.extend(
                    flatten_dict({f"{new_key}_{i}": item}, "", sep=sep).items()
                )
        else:
            items.append((new_key, v))
    return dict(items)


def value_match(value_a: any, value_b: any) -> bool:
    """
    Check if two values match.
    For strings, the comparison is case-insensitive.
    For lists and dictionaries, the comparison is recursive, and all elements must match.

    Args:
        value_a: The first value to compare.
        value_b: The second value to compare.

    Returns:
        bool: True if the values match, False otherwise.
    """

    if isinstance(value_a, str) and isinstance(value_b, str):
        return value_a.lower() == value_b.lower()

    if isinstance(value_a, list) and isinstance(value_b, list):
        for v, c in zip(value_a, value_b):
            if not value_match(v, c):
                return False

    if isinstance(value_a, dict) and isinstance(value_b, dict):
        for key in value_a:
            if key not in value_b:
                return False
            if not value_match(value_a[key], value_b[key]):
                return False

    return value_a == value_b


def value_contains(value_a: any, value_b: any) -> bool:
    """
    Check if a value contains another value.

    For strings, the comparison is case-insensitive.
    For lists and dictionaries, the comparison is recursive, and all elements must match.
    Other types are compared using the value_match function.

    Args:
        value_a: The value to check if it contains the other value.
        value_b: The value to check if it is contained in the other value.

    Returns:
        bool: True if the value contains the other value, False otherwise.
    """

    if isinstance(value_a, str) and isinstance(value_b, str):
        return value_a.replace(" ", "").lower() in value_b.replace(" ", "").lower()

    if isinstance(value_a, list) and isinstance(value_b, list):
        for v in value_a:
            if not any(value_contains(v, c) for c in value_b):
                return False

    if isinstance(value_a, dict) and isinstance(value_b, dict):
        for key in value_a:
            if key not in value_b:
                return False
            if not value_contains(value_a[key], value_b[key]):
                return False

    return value_match(value_a, value_b)

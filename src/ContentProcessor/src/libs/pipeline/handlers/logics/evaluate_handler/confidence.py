# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Confidence score merging and lookup utilities.

Provides recursive traversal of nested confidence dictionaries to
extract, merge, and summarize per-field confidence values.
"""


def get_confidence_values(data, key="confidence"):
    """
    Finds all of the confidence values in a nested dictionary or list.

    Args:
        data: The nested dictionary or list to search for confidence values.
        key: The key to search for in the dictionary.

    Returns:
        list: The list of confidence values found in the nested dictionary or list.
    """

    confidence_values = []

    def recursive_search(d):
        if isinstance(d, dict):
            for k, v in d.items():
                if k == key and (v is not None and v != 0):
                    # Only treat numeric values as confidence scores.
                    # Some schemas include a nested field literally named "confidence".
                    if isinstance(v, (int, float)) and not isinstance(v, bool):
                        confidence_values.append(v)
                if isinstance(v, (dict, list)):
                    recursive_search(v)
        elif isinstance(d, list):
            for item in d:
                recursive_search(item)

    recursive_search(data)
    return confidence_values


def find_keys_with_min_confidence(data, min_confidence, key="confidence"):
    """
    Finds all keys with the minimum confidence value in a nested dictionary or list.

    Args:
        data: The nested dictionary or list to search for keys with the minimum confidence value.
        min_confidence: The minimum confidence value to search for.
        key: The key to search for the confidence value in the dictionary.

    Returns:
        list: The list of keys with the minimum confidence value.
    """

    keys_with_min_confidence = []

    def recursive_search(d, parent_key=""):
        if isinstance(d, dict):
            for k, v in d.items():
                new_key = f"{parent_key}.{k}" if parent_key else k
                if (
                    k == key
                    and isinstance(v, (int, float))
                    and not isinstance(v, bool)
                    and v == min_confidence
                ):
                    keys_with_min_confidence.append(parent_key)
                if isinstance(v, (dict, list)):
                    recursive_search(v, new_key)
        elif isinstance(d, list):
            for idx, item in enumerate(d):
                new_key = f"{parent_key}[{idx}]"
                recursive_search(item, new_key)

    recursive_search(data)
    return keys_with_min_confidence


def merge_confidence_values(confidence_a: dict, confidence_b: dict):
    """
    Merges to evaluations of confidence for the same set of fields as one.
    This is achieved by summing the confidence values and averaging the scores.

    Args:
        confidence_a: The first confidence evaluation.
        confidence_b: The second confidence evaluation.

    Returns:
        dict: The merged confidence evaluation.
    """

    def _is_leaf_confidence_node(node: any) -> bool:
        if not isinstance(node, dict):
            return False
        # Leaf nodes are expected to look like: {"confidence": <number>, "value": <any>}
        # If a domain schema includes a nested field named "confidence", the parent object
        # should NOT be treated as a leaf just because it has a "confidence" key.
        allowed_keys = {"confidence", "value"}
        return "confidence" in node and set(node.keys()).issubset(allowed_keys)

    def merge_field_confidence_value(
        field_a: any, field_b: any, score_resolver: callable = min
    ) -> any:
        """
        Merges two field confidence values.
        If the field is a dictionary or list, the function is called recursively.

        Args:
            field_a: The first field confidence value.
            field_b: The second field confidence value.

        Returns:
            dict: The merged field confidence value.
        """

        CONFIDENT_SCORE_ROUNDING = 3

        # Dict merge
        if isinstance(field_a, dict):
            if not isinstance(field_b, dict):
                return field_a

            # Leaf merge: {confidence, value}
            if _is_leaf_confidence_node(field_a) and _is_leaf_confidence_node(field_b):
                a_conf = field_a.get("confidence")
                b_conf = field_b.get("confidence")

                valid_confidences = [
                    conf
                    for conf in [a_conf, b_conf]
                    if isinstance(conf, (int, float))
                    and not isinstance(conf, bool)
                    and conf not in (None, 0)
                ]

                merged_confidence = (
                    score_resolver(valid_confidences) if valid_confidences else 0.0
                )
                return {
                    "confidence": round(merged_confidence, CONFIDENT_SCORE_ROUNDING),
                    "value": field_a.get("value"),
                }

            # Nested object merge
            result = {}
            all_keys = set(field_a.keys()) | set(field_b.keys())
            for key in all_keys:
                if key.startswith("_"):
                    continue
                if key in field_a and key in field_b:
                    result[key] = merge_field_confidence_value(
                        field_a[key], field_b[key]
                    )
                elif key in field_a:
                    result[key] = field_a[key]
                else:
                    result[key] = field_b[key]
            return result

        # List merge
        if isinstance(field_a, list):
            if not isinstance(field_b, list):
                return field_a

            merged = [
                merge_field_confidence_value(a, b) for a, b in zip(field_a, field_b)
            ]
            if len(field_a) > len(field_b):
                merged.extend(field_a[len(field_b) :])
            elif len(field_b) > len(field_a):
                merged.extend(field_b[len(field_a) :])
            return merged

        # Scalar fallback (including bool)
        return field_a if field_a is not None else field_b

    merged_confidence = merge_field_confidence_value(confidence_a, confidence_b)
    confidence_scores = get_confidence_values(merged_confidence)

    if confidence_scores and len(confidence_scores) > 0:
        merged_confidence["total_evaluated_fields_count"] = len(confidence_scores)
        merged_confidence["overall_confidence"] = round(
            sum(confidence_scores) / merged_confidence["total_evaluated_fields_count"],
            3,
        )
        merged_confidence["min_extracted_field_confidence"] = min(confidence_scores)
        # find all the keys which has min_extracted_field_confidence value
        merged_confidence["min_extracted_field_confidence_field"] = (
            find_keys_with_min_confidence(
                merged_confidence, merged_confidence["min_extracted_field_confidence"]
            )
        )
        merged_confidence["zero_confidence_fields"] = find_keys_with_min_confidence(
            merged_confidence, 0
        )
        merged_confidence["zero_confidence_fields_count"] = len(
            merged_confidence["zero_confidence_fields"]
        )
    else:
        merged_confidence["overall"] = 0.0
        merged_confidence["total_evaluated_fields_count"] = 0
        merged_confidence["overall_confidence"] = 0.0
        merged_confidence["min_extracted_field_confidence"] = 0.0
        merged_confidence["zero_confidence_fields"] = []
        merged_confidence["zero_confidence_fields_count"] = 0

    return merged_confidence

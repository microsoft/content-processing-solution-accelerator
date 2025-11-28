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
                if k == key and v == min_confidence:
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

    def merge_field_confidence_value(
        field_a: any, field_b: any, score_resolver: callable = min
    ) -> dict:
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

        if isinstance(field_a, dict) and "confidence" not in field_a:
            result = {}
            all_keys = set(field_a.keys()) | set(field_b.keys())
            for key in all_keys:
                if key.startswith("_"):
                    continue
                if key in field_a and key in field_b:
                    result[key] = merge_field_confidence_value(field_a[key], field_b[key])
                elif key in field_a:
                    result[key] = field_a[key]
                elif key in field_b:
                    result[key] = field_b[key]
            return result
        elif isinstance(field_a, list):
            return [
                merge_field_confidence_value(field_a[i], field_b[i])
                for i in range(len(field_a))
            ]
        else:
            valid_confidences = [
                conf
                for conf in [field_a["confidence"], field_b["confidence"]]
                if conf not in (None, 0)
            ]

            merged_confidence = (
                score_resolver(valid_confidences) if valid_confidences else 0.0
            )
            return {
                "confidence": round(merged_confidence, CONFIDENT_SCORE_ROUNDING),
                "value": field_a["value"] if "value" in field_a else None,
            }

            # return {
            #     "confidence": score_resolver(valid_confidences)
            #     if valid_confidences
            #     else 0.0,
            #     #"value": field_a["value"] if "field" in field_a else None,
            #     "value": field_a["value"] if "value" in field_a else None
            #     #"normalized_polygons": field_a["normalized_polygons"]
            # }

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
        # merged_confidence["overall_hit_rate"] = round(
        #     (
        #         merged_confidence["total_evaluated_fields_count"]
        #         - merged_confidence["missed_fields_count"]
        #     )
        #     / merged_confidence["total_evaluated_fields_count"],
        #     3,
        # )
    else:
        merged_confidence["overall"] = 0.0
        merged_confidence["total_evaluated_fields_count"] = 0
        merged_confidence["overall_confidence"] = 0.0
        merged_confidence["min_extracted_field_confidence"] = 0.0
        merged_confidence["zero_confidence_fields"] = []
        merged_confidence["zero_confidence_fields_count"] = 0

    return merged_confidence

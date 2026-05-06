# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Validate uploaded JSON Schema descriptors used by the content-processing pipeline.

A JSON schema descriptor is treated as **data**: it is parsed (never
executed), checked against the JSON Schema Draft 2020-12 meta-schema, and
required to use only a small set of project-specific custom keywords.

This module is intentionally side-effect free; it does not touch storage
or Cosmos. The router is responsible for calling :func:`validate_json_schema`
and acting on the returned errors.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

#: Maximum size in bytes for an uploaded JSON schema. Schemas are config
#: artefacts; a generous cap of 1 MB matches the legacy ``.py`` limit.
MAX_SCHEMA_BYTES: int = 1 * 1024 * 1024

#: Allowlisted project-specific custom keywords. Any other ``x-cps-*`` or
#: ``x-`` keyword in the uploaded schema is rejected so unknown extension
#: points cannot be smuggled in.
ALLOWED_CPS_KEYWORDS: frozenset[str] = frozenset({
    "x-cps-extract-prompt",
    "x-cps-required-on-save",
})


class SchemaValidationError(ValueError):
    """Raised when an uploaded JSON schema fails validation.

    Attributes:
        errors: Human-readable list of violations.
    """

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors) if errors else "Invalid JSON schema")


def validate_json_schema(raw_bytes: bytes) -> dict[str, Any]:
    """Validate the bytes of an uploaded JSON Schema descriptor.

    Args:
        raw_bytes: Uploaded file contents.

    Returns:
        The parsed schema document as a ``dict`` (only on success).

    Raises:
        SchemaValidationError: If the bytes are too large, are not valid
            JSON, do not conform to JSON Schema Draft 2020-12, or use
            disallowed custom extension keywords.
    """
    errors: list[str] = []

    if raw_bytes is None:
        raise SchemaValidationError(["Empty schema upload."])

    if len(raw_bytes) > MAX_SCHEMA_BYTES:
        raise SchemaValidationError([
            f"Schema is too large ({len(raw_bytes)} bytes; max {MAX_SCHEMA_BYTES})."
        ])

    try:
        document = json.loads(raw_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise SchemaValidationError([f"Schema must be UTF-8 encoded: {exc}"]) from exc
    except json.JSONDecodeError as exc:
        raise SchemaValidationError([f"Schema is not valid JSON: {exc.msg}"]) from exc

    if not isinstance(document, dict):
        raise SchemaValidationError([
            "Schema root must be a JSON object describing the model."
        ])

    # Reject schemas without a usable type. We only support object roots
    # because the pipeline materialises a Pydantic model from them.
    root_type = document.get("type")
    if root_type != "object":
        errors.append(
            "Schema root must declare 'type': 'object' "
            "(got %r)." % (root_type,)
        )

    if "properties" not in document or not isinstance(
        document.get("properties"), dict
    ):
        errors.append("Schema root must declare a 'properties' object.")

    # Validate the document itself is a syntactically valid Draft 2020-12 schema.
    try:
        Draft202012Validator.check_schema(document)
    except SchemaError as exc:
        errors.append(f"Not a valid JSON Schema (Draft 2020-12): {exc.message}")

    # Walk the document and reject unknown ``x-`` extension keywords.
    for path, key in _walk_extension_keywords(document):
        if key not in ALLOWED_CPS_KEYWORDS:
            errors.append(
                f"Unsupported extension keyword '{key}' at {path or '<root>'}. "
                f"Allowed: {sorted(ALLOWED_CPS_KEYWORDS)}."
            )

    # Reject unsupported $ref values. The runtime loader only supports local
    # references of the form ``#/$defs/...`` or ``#/definitions/...``.
    for path, ref in _walk_refs(document):
        if not (ref.startswith("#/$defs/") or ref.startswith("#/definitions/")):
            errors.append(
                f"Unsupported $ref '{ref}' at {path or '<root>'}. "
                "Only '#/$defs/...' and '#/definitions/...' references are supported."
            )

    if errors:
        raise SchemaValidationError(errors)

    return document


def derive_class_name(document: dict[str, Any], fallback: str) -> str:
    """Derive a stable class name for the schema document.

    The schema's ``title`` is preferred (matches Pydantic conventions);
    otherwise the supplied filename stem is used. Any non-identifier
    characters in the fallback are replaced with underscores so the
    result is always a valid Python identifier.

    Args:
        document: Parsed JSON schema document.
        fallback: Filename stem (without extension) to use if no title.

    Returns:
        A non-empty string suitable for use as a Pydantic model name.
    """
    title = document.get("title")
    if isinstance(title, str) and title.strip():
        candidate = title.strip()
    else:
        candidate = fallback

    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in candidate)
    if not cleaned or not (cleaned[0].isalpha() or cleaned[0] == "_"):
        cleaned = "Schema_" + cleaned
    return cleaned


def _walk_extension_keywords(
    node: Any, path: str = ""
) -> Iterable[tuple[str, str]]:
    """Yield every ``(path, key)`` for keys starting with ``x-`` anywhere in *node*."""
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and key.startswith("x-"):
                yield path, key
            child_path = f"{path}.{key}" if path else str(key)
            yield from _walk_extension_keywords(value, child_path)
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            yield from _walk_extension_keywords(item, f"{path}[{idx}]")


def _walk_refs(
    node: Any, path: str = ""
) -> Iterable[tuple[str, str]]:
    """Yield every ``(path, ref_value)`` for ``$ref`` keys anywhere in *node*."""
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            yield path, node["$ref"]
        for key, value in node.items():
            child_path = f"{path}.{key}" if path else str(key)
            yield from _walk_refs(value, child_path)
    elif isinstance(node, list):
        for idx, item in enumerate(node):
            yield from _walk_refs(item, f"{path}[{idx}]")

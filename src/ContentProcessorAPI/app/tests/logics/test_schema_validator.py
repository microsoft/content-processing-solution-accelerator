# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the JSON Schema validator used by the schema vault upload routes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.routers.logics.schema_validator import (
    ALLOWED_CPS_KEYWORDS,
    SchemaValidationError,
    derive_class_name,
    validate_json_schema,
)


SAMPLES_DIR = (
    Path(__file__).resolve().parents[3] / "samples" / "schemas"
)


def _minimal_object_schema(**extra) -> dict:
    base = {
        "type": "object",
        "title": "Minimal",
        "properties": {"name": {"type": "string"}},
    }
    base.update(extra)
    return base


def _bytes(doc) -> bytes:
    return json.dumps(doc).encode("utf-8")


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_validate_accepts_minimal_object_schema():
    document = validate_json_schema(_bytes(_minimal_object_schema()))
    assert document["title"] == "Minimal"


def test_validate_accepts_autoclaim_golden():
    raw = (SAMPLES_DIR / "autoclaim.json").read_bytes()
    document = validate_json_schema(raw)
    assert document["title"] == "AutoInsuranceClaimForm"
    assert document["type"] == "object"


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_validate_rejects_non_utf8_bytes():
    with pytest.raises(SchemaValidationError) as exc:
        validate_json_schema(b"\xff\xfe\x00not utf-8")
    assert "UTF-8" in str(exc.value)


def test_validate_rejects_non_json():
    with pytest.raises(SchemaValidationError) as exc:
        validate_json_schema(b"not json at all")
    assert "not valid JSON" in str(exc.value)


def test_validate_rejects_non_object_root():
    with pytest.raises(SchemaValidationError):
        validate_json_schema(_bytes([1, 2, 3]))


def test_validate_rejects_missing_type_object():
    schema = {"title": "X", "properties": {"a": {"type": "string"}}}
    with pytest.raises(SchemaValidationError) as exc:
        validate_json_schema(_bytes(schema))
    assert "type" in str(exc.value)


def test_validate_rejects_missing_properties():
    schema = {"title": "X", "type": "object"}
    with pytest.raises(SchemaValidationError) as exc:
        validate_json_schema(_bytes(schema))
    assert "properties" in str(exc.value)


def test_validate_rejects_invalid_dialect():
    schema = _minimal_object_schema()
    # ``type`` must be a string or array; this is a meta-schema violation.
    schema["properties"]["name"] = {"type": "banana"}
    with pytest.raises(SchemaValidationError) as exc:
        validate_json_schema(_bytes(schema))
    assert "JSON Schema" in str(exc.value)


def test_validate_rejects_unknown_x_keyword():
    schema = _minimal_object_schema()
    schema["x-evil-side-channel"] = "haha"
    with pytest.raises(SchemaValidationError) as exc:
        validate_json_schema(_bytes(schema))
    assert "x-evil-side-channel" in str(exc.value)


def test_validate_rejects_unknown_x_keyword_in_nested_property():
    schema = _minimal_object_schema()
    schema["properties"]["name"]["x-cps-malicious"] = True
    with pytest.raises(SchemaValidationError):
        validate_json_schema(_bytes(schema))


def test_validate_rejects_oversized_payload():
    big = "x" * (2 * 1024 * 1024)
    schema = _minimal_object_schema(description=big)
    with pytest.raises(SchemaValidationError) as exc:
        validate_json_schema(_bytes(schema))
    assert "too large" in str(exc.value)


# ---------------------------------------------------------------------------
# derive_class_name
# ---------------------------------------------------------------------------


def test_derive_class_name_uses_title():
    assert derive_class_name({"title": "InvoiceSchema"}, fallback="x") == "InvoiceSchema"


def test_derive_class_name_falls_back_to_filename():
    assert derive_class_name({}, fallback="auto-claim") == "auto_claim"


def test_derive_class_name_sanitises_leading_digits():
    assert derive_class_name({}, fallback="9invoice") == "Schema_9invoice"


def test_allowed_keywords_constant_is_empty():
    assert len(ALLOWED_CPS_KEYWORDS) == 0

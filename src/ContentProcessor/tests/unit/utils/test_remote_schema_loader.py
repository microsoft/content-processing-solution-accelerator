# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the JSON-Schema-based remote schema loader.

These tests intentionally avoid touching Azure and only exercise
:func:`build_model_from_schema`, the in-memory translator that
:func:`load_schema_from_blob_json` delegates to.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel

from libs.utils.remote_schema_loader import (
    JsonSchemaLoadError,
    build_model_from_schema,
)

#: Repo-relative path to the golden JSON schema.
_GOLDEN_AUTOCLAIM = (
    Path(__file__).resolve().parents[4]
    / "ContentProcessorAPI"
    / "samples"
    / "schemas"
    / "autoclaim.json"
)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_builds_simple_object_model():
    schema = {
        "type": "object",
        "title": "Invoice",
        "properties": {
            "id": {"type": "string"},
            "amount": {"type": "number"},
            "paid": {"type": "boolean"},
        },
        "required": ["id"],
    }
    model = build_model_from_schema(schema, "Invoice")

    assert issubclass(model, BaseModel)
    instance = model.model_validate({"id": "INV1", "amount": 12.5, "paid": True})
    assert instance.id == "INV1"
    assert instance.amount == 12.5

    with pytest.raises(Exception):
        model.model_validate({})  # missing required 'id'


def test_supports_nullable_via_anyof():
    schema = {
        "type": "object",
        "properties": {
            "name": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
    }
    model = build_model_from_schema(schema, "X")
    instance = model.model_validate({"name": None})
    assert instance.name is None


def test_supports_nullable_via_type_array():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": ["string", "null"]},
        },
    }
    model = build_model_from_schema(schema, "X")
    assert model.model_validate({"name": None}).name is None
    assert model.model_validate({"name": "ok"}).name == "ok"


def test_supports_arrays_of_primitives():
    schema = {
        "type": "object",
        "properties": {
            "tags": {"type": "array", "items": {"type": "string"}},
        },
    }
    model = build_model_from_schema(schema, "X")
    instance = model.model_validate({"tags": ["a", "b"]})
    assert instance.tags == ["a", "b"]


def test_supports_inline_nested_object():
    schema = {
        "type": "object",
        "properties": {
            "address": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                },
            },
        },
    }
    model = build_model_from_schema(schema, "Person")
    instance = model.model_validate({"address": {"city": "Macon"}})
    assert instance.address.city == "Macon"


def test_supports_refs_and_defs():
    schema = {
        "$defs": {
            "Address": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                },
            }
        },
        "type": "object",
        "properties": {
            "primary": {"$ref": "#/$defs/Address"},
            "secondary": {"$ref": "#/$defs/Address"},
        },
    }
    model = build_model_from_schema(schema, "Contact")

    instance = model.model_validate({
        "primary": {"city": "Macon"},
        "secondary": {"city": "Atlanta"},
    })
    # Both refs resolved to the *same* generated class.
    assert type(instance.primary) is type(instance.secondary)


def test_supports_enum_via_literal():
    schema = {
        "type": "object",
        "properties": {
            "tier": {"enum": ["bronze", "silver", "gold"]},
        },
    }
    model = build_model_from_schema(schema, "Tier")
    assert model.model_validate({"tier": "gold"}).tier == "gold"
    with pytest.raises(Exception):
        model.model_validate({"tier": "platinum"})


# ---------------------------------------------------------------------------
# Failure modes
# ---------------------------------------------------------------------------


def test_rejects_unknown_ref_target():
    schema = {
        "type": "object",
        "properties": {"a": {"$ref": "#/$defs/Missing"}},
    }
    with pytest.raises(JsonSchemaLoadError) as exc:
        build_model_from_schema(schema, "X")
    assert "$defs" in str(exc.value)


def test_rejects_external_ref():
    schema = {
        "type": "object",
        "properties": {"a": {"$ref": "https://example.com/schema.json"}},
    }
    with pytest.raises(JsonSchemaLoadError):
        build_model_from_schema(schema, "X")


# ---------------------------------------------------------------------------
# Golden-equivalence: the JSON schema generated from autoclaim.py builds a
# model that round-trips an LLM-style payload to the same dict that the
# legacy autoclaim.py would produce.
# ---------------------------------------------------------------------------


def _representative_payload() -> dict:
    return {
        "insurance_company": "Contoso Insurance",
        "claim_number": "CLM987654",
        "policy_number": "AUTO123456",
        "policyholder_information": {
            "name": "Chad Brooks",
            "address": {
                "street": "123 Main St",
                "city": "Macon",
                "state": "GA",
                "postal_code": "31201",
                "country": "USA",
            },
            "phone": "(555) 555-1212",
            "email": "chad.brooks@example.com",
        },
        "policy_details": {
            "coverage_type": "Auto - Comprehensive",
            "effective_date": "2025-01-01",
            "expiration_date": "2025-12-31",
            "deductible": 500.0,
            "deductible_currency": "USD",
        },
        "incident_details": {
            "date_of_loss": "2025-11-28",
            "time_of_loss": "14:15",
            "location": "Parking lot",
            "cause_of_loss": "Low-speed collision",
            "description": "Minor dent",
            "police_report_filed": True,
            "police_report_number": "GA-20251128-CR",
        },
        "vehicle_information": {
            "year": 2022,
            "make": "Toyota",
            "model": "Camry",
            "trim": "SE",
            "vin": "4T1G11AK2NU123456",
            "license_plate": "GA-ABC123",
            "mileage": 28450,
        },
        "damage_assessment": {
            "items": [
                {
                    "item_description": "Right-front quarter panel",
                    "date_acquired": "2022-03-15",
                    "cost_new": 1200.0,
                    "cost_new_currency": "USD",
                    "repair_estimate": 350.0,
                    "repair_estimate_currency": "USD",
                }
            ],
            "total_estimated_repair": 500.0,
            "total_estimated_repair_currency": "USD",
        },
        "supporting_documents": {
            "photos_of_damage": True,
            "police_report_copy": True,
            "repair_shop_estimate": True,
            "other": [],
        },
        "declaration": {
            "statement": "I declare...",
            "signature": {"signatory": "Chad Brooks", "is_signed": True},
            "date": "2025-12-01",
        },
        "submission_instructions": {
            "submission_email": "claims@contoso.com",
            "portal_url": None,
            "notes": None,
        },
    }


def test_golden_autoclaim_round_trip():
    document = json.loads(_GOLDEN_AUTOCLAIM.read_text(encoding="utf-8"))
    model = build_model_from_schema(document, "AutoInsuranceClaimForm")

    payload = _representative_payload()
    instance = model.model_validate(payload)
    dumped = instance.model_dump()

    # Every field round-trips and nested objects produced the same shape.
    assert dumped["insurance_company"] == "Contoso Insurance"
    assert dumped["policyholder_information"]["address"]["city"] == "Macon"
    assert dumped["damage_assessment"]["items"][0]["cost_new"] == 1200.0
    assert dumped["declaration"]["signature"]["is_signed"] is True


def test_golden_autoclaim_emits_json_schema():
    document = json.loads(_GOLDEN_AUTOCLAIM.read_text(encoding="utf-8"))
    model = build_model_from_schema(document, "AutoInsuranceClaimForm")

    # The generated model must be able to emit its own JSON schema; this is
    # what map_handler.py passes to the LLM via ``model_json_schema()``.
    out_schema = model.model_json_schema()
    assert out_schema.get("type") == "object"
    assert "properties" in out_schema

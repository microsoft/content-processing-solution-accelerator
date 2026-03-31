# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for schema-vault domain models."""

from __future__ import annotations

import json

from app.routers.models.schmavault.model import (
    Schema,
    SchemaVaultRegisterRequest,
    SchemaVaultUnregisterRequest,
    SchemaVaultUnregisterResponse,
    SchemaVaultUpdateRequest,
)


class TestSchemaModel:
    def test_parse_dates_from_iso_string(self):
        schema = Schema(
            Id="s1",
            ClassName="Invoice",
            Description="desc",
            FileName="invoice.py",
            ContentType="text/x-python",
            Created_On="2025-01-01T00:00:00Z",
            Updated_On="2025-06-15T12:30:00Z",
        )
        assert schema.Created_On is not None
        assert schema.Created_On.year == 2025
        assert schema.Updated_On.month == 6

    def test_parse_dates_none(self):
        schema = Schema(
            Id="s1",
            ClassName="Invoice",
            Description="desc",
            FileName="invoice.py",
            ContentType="text/x-python",
        )
        assert schema.Created_On is None
        assert schema.Updated_On is None


class TestSchemaVaultRegisterRequest:
    def test_from_json_string(self):
        raw = json.dumps({"ClassName": "MyClass", "Description": "A schema"})
        req = SchemaVaultRegisterRequest.model_validate_json(raw)
        assert req.ClassName == "MyClass"
        assert req.Description == "A schema"

    def test_from_dict(self):
        req = SchemaVaultRegisterRequest(ClassName="C", Description="D")
        assert req.ClassName == "C"


class TestSchemaVaultUpdateRequest:
    def test_from_json_string(self):
        raw = json.dumps({"SchemaId": "id1", "ClassName": "Updated"})
        req = SchemaVaultUpdateRequest.model_validate_json(raw)
        assert req.SchemaId == "id1"
        assert req.ClassName == "Updated"


class TestSchemaVaultUnregisterRequest:
    def test_from_json_string(self):
        raw = json.dumps({"SchemaId": "id2"})
        req = SchemaVaultUnregisterRequest.model_validate_json(raw)
        assert req.SchemaId == "id2"


class TestSchemaVaultUnregisterResponse:
    def test_to_dict(self):
        resp = SchemaVaultUnregisterResponse(
            Status="Success",
            SchemaId="s1",
            ClassName="Invoice",
            FileName="invoice.py",
        )
        d = resp.to_dict()
        assert d["Status"] == "Success"
        assert d["SchemaId"] == "s1"

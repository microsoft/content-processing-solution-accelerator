# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for contentprocessor model validators (model.py)."""

from __future__ import annotations

import json

from app.routers.models.contentprocessor.model import (
    ContentProcessorBatchFileAddRequest,
    ContentProcessorRequest,
)


class TestContentProcessorBatchFileAddRequest:
    def test_from_json_string(self):
        raw = json.dumps({"Claim_Id": "c1", "Metadata_Id": "m1", "Schema_Id": "s1"})
        req = ContentProcessorBatchFileAddRequest.model_validate_json(raw)
        assert req.Claim_Id == "c1"
        assert req.Metadata_Id == "m1"
        assert req.Schema_Id == "s1"

    def test_from_dict(self):
        req = ContentProcessorBatchFileAddRequest(
            Claim_Id="c1", Metadata_Id="m1", Schema_Id="s1"
        )
        assert req.Claim_Id == "c1"


class TestContentProcessorRequest:
    def test_from_json_string(self):
        raw = json.dumps({"Schema_Id": "s1", "Metadata_Id": "m1"})
        req = ContentProcessorRequest.model_validate_json(raw)
        assert req.Schema_Id == "s1"

    def test_optional_fields_default_none(self):
        req = ContentProcessorRequest()
        assert req.Schema_Id is None
        assert req.Metadata_Id is None

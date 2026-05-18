# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

"""Unit tests for queue message parsing."""

import base64
import json

import pytest

from services.queue_service import parse_claim_task_parameters_from_queue_content


def test_parse_accepts_json_claim_process_id():
    payload = {"claim_process_id": "p1"}
    params = parse_claim_task_parameters_from_queue_content(json.dumps(payload))
    assert params.claim_process_id == "p1"


def test_parse_decodes_base64_json():
    payload = {"claim_process_id": "p1"}
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    params = parse_claim_task_parameters_from_queue_content(encoded)
    assert params.claim_process_id == "p1"


def test_parse_rejects_empty_content():
    with pytest.raises(ValueError, match=r"content is empty"):
        parse_claim_task_parameters_from_queue_content("   ")


def test_parse_rejects_non_json_payload():
    with pytest.raises(ValueError, match=r"must be JSON"):
        parse_claim_task_parameters_from_queue_content("p1")


def test_parse_rejects_json_missing_claim_id():
    with pytest.raises(ValueError, match=r"must include 'claim_process_id'"):
        parse_claim_task_parameters_from_queue_content(json.dumps({"x": 1}))

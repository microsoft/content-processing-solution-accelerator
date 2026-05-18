# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the Pydantic models in steps/models/."""

from __future__ import annotations

import datetime

import pytest

from steps.models.extracted_file import ExtractedFile
from steps.models.manifest import ClaimItem, ClaimProcess
from steps.models.output import (
    Executor_Output,
    Processed_Document_Info,
    Workflow_Output,
)
from steps.models.request import ClaimProcessTaskParameters


# ── ExtractedFile ────────────────────────────────────────────────────────────


class TestExtractedFile:
    def test_required_fields_only(self):
        ef = ExtractedFile(file_name="report.pdf", extracted_content="Hello")
        assert ef.file_name == "report.pdf"
        assert ef.extracted_content == "Hello"
        assert ef.mime_type == "application/octet-stream"

    def test_explicit_mime_type(self):
        ef = ExtractedFile(
            file_name="img.png",
            mime_type="image/png",
            extracted_content="<binary>",
        )
        assert ef.mime_type == "image/png"

    def test_missing_required_field_raises(self):
        with pytest.raises(Exception):
            ExtractedFile(file_name="a.txt")  # missing extracted_content

    def test_round_trip_serialization(self):
        ef = ExtractedFile(file_name="f.txt", extracted_content="body")
        data = ef.model_dump()
        restored = ExtractedFile.model_validate(data)
        assert restored == ef


# ── ClaimItem ────────────────────────────────────────────────────────────────


class TestClaimItem:
    def test_minimal_construction(self):
        item = ClaimItem(claim_id="c1", schema_id="s1", metadata_id="m1")
        assert item.claim_id == "c1"
        assert item.file_name is None
        assert item.size is None
        assert item.mime_type is None
        assert item.id is None

    def test_full_construction(self):
        item = ClaimItem(
            claim_id="c1",
            file_name="doc.pdf",
            size=1024,
            schema_id="s1",
            metadata_id="m1",
            mime_type="application/pdf",
            id="item-1",
        )
        assert item.file_name == "doc.pdf"
        assert item.size == 1024
        assert item.mime_type == "application/pdf"
        assert item.id == "item-1"


# ── ClaimProcess (manifest) ─────────────────────────────────────────────────


class TestClaimProcessManifest:
    def test_defaults(self):
        cp = ClaimProcess(claim_id="c1", schema_collection_id="sc1")
        assert cp.claim_id == "c1"
        assert cp.metadata_id is None
        assert cp.items == []
        assert isinstance(cp.created_time, datetime.datetime)
        assert isinstance(cp.last_modified_time, datetime.datetime)

    def test_with_items(self):
        item = ClaimItem(claim_id="c1", schema_id="s1", metadata_id="m1")
        cp = ClaimProcess(claim_id="c1", schema_collection_id="sc1", items=[item])
        assert len(cp.items) == 1
        assert cp.items[0].claim_id == "c1"


# ── Processed_Document_Info ──────────────────────────────────────────────────


class TestProcessedDocumentInfo:
    def test_construction(self):
        info = Processed_Document_Info(
            document_id="d1", status="processed", details="OK"
        )
        assert info.document_id == "d1"
        assert info.status == "processed"
        assert info.details == "OK"


# ── Executor_Output ──────────────────────────────────────────────────────────


class TestExecutorOutput:
    def test_construction(self):
        eo = Executor_Output(
            step_name="document_processing", output_data={"key": "value"}
        )
        assert eo.step_name == "document_processing"
        assert eo.output_data == {"key": "value"}


# ── Workflow_Output ──────────────────────────────────────────────────────────


class TestWorkflowOutput:
    def test_defaults(self):
        wo = Workflow_Output(claim_process_id="p1", schemaset_id="ss1")
        assert wo.claim_process_id == "p1"
        assert wo.schemaset_id == "ss1"
        assert wo.workflow_process_outputs == []

    def test_append_executor_output(self):
        wo = Workflow_Output(claim_process_id="p1", schemaset_id="ss1")
        eo = Executor_Output(step_name="step1", output_data={"a": 1})
        wo.workflow_process_outputs.append(eo)
        assert len(wo.workflow_process_outputs) == 1
        assert wo.workflow_process_outputs[0].step_name == "step1"

    def test_independent_default_lists(self):
        """Ensure each instance gets its own list (no shared mutable default)."""
        wo1 = Workflow_Output(claim_process_id="p1", schemaset_id="ss1")
        wo2 = Workflow_Output(claim_process_id="p2", schemaset_id="ss2")
        wo1.workflow_process_outputs.append(
            Executor_Output(step_name="x", output_data={})
        )
        assert len(wo2.workflow_process_outputs) == 0


# ── ClaimProcessTaskParameters ───────────────────────────────────────────────


class TestClaimProcessTaskParameters:
    def test_construction(self):
        params = ClaimProcessTaskParameters(claim_process_id="cp1")
        assert params.claim_process_id == "cp1"

    def test_missing_required_field_raises(self):
        with pytest.raises(Exception):
            ClaimProcessTaskParameters()

    def test_round_trip(self):
        params = ClaimProcessTaskParameters(claim_process_id="cp1")
        data = params.model_dump()
        restored = ClaimProcessTaskParameters.model_validate(data)
        assert restored.claim_process_id == "cp1"

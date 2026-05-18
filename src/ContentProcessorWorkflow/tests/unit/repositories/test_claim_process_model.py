# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for the Claim_Process domain models in repositories/model/."""

from __future__ import annotations

from repositories.model.claim_process import (
    Claim_Process,
    Claim_Steps,
    Content_Process,
)


# ── Claim_Steps enum ────────────────────────────────────────────────────────


class TestClaimSteps:
    def test_enum_values(self):
        assert Claim_Steps.PENDING == "Pending"
        assert Claim_Steps.DOCUMENT_PROCESSING == "Processing"
        assert Claim_Steps.SUMMARIZING == "Summarizing"
        assert Claim_Steps.GAP_ANALYSIS == "GapAnalysis"
        assert Claim_Steps.FAILED == "Failed"
        assert Claim_Steps.COMPLETED == "Completed"

    def test_enum_is_str(self):
        """Claim_Steps inherits from str so it can be used directly in JSON."""
        assert isinstance(Claim_Steps.PENDING, str)

    def test_enum_membership(self):
        assert Claim_Steps("Pending") is Claim_Steps.PENDING
        assert Claim_Steps("Completed") is Claim_Steps.COMPLETED


# ── Content_Process ──────────────────────────────────────────────────────────


class TestContentProcess:
    def test_defaults(self):
        cp = Content_Process(process_id="p1", file_name="doc.pdf")
        assert cp.process_id == "p1"
        assert cp.file_name == "doc.pdf"
        assert cp.mime_type is None
        assert cp.entity_score == 0.0
        assert cp.schema_score == 0.0
        assert cp.status is None
        assert cp.processed_time == ""

    def test_explicit_scores(self):
        cp = Content_Process(
            process_id="p1",
            file_name="doc.pdf",
            entity_score=0.95,
            schema_score=0.87,
        )
        assert cp.entity_score == 0.95
        assert cp.schema_score == 0.87


# ── Claim_Process ────────────────────────────────────────────────────────────


class TestClaimProcess:
    def test_defaults(self):
        cp = Claim_Process(id="p1", schemaset_id="ss1")
        assert cp.id == "p1"
        assert cp.process_name == "First Notice of Loss"
        assert cp.status == Claim_Steps.DOCUMENT_PROCESSING
        assert cp.processed_documents == []
        assert cp.process_summary == ""
        assert cp.process_gaps == ""
        assert cp.process_comment == ""
        assert cp.processed_time == ""
        assert cp.process_time != ""  # auto-generated timestamp

    def test_with_documents(self):
        doc = Content_Process(process_id="p1", file_name="a.pdf")
        cp = Claim_Process(id="p1", schemaset_id="ss1", processed_documents=[doc])
        assert len(cp.processed_documents) == 1
        assert cp.processed_documents[0].file_name == "a.pdf"

    def test_status_assignment(self):
        cp = Claim_Process(id="p1", schemaset_id="ss1", status=Claim_Steps.COMPLETED)
        assert cp.status == Claim_Steps.COMPLETED

    def test_independent_default_lists(self):
        """Each Claim_Process should have its own processed_documents list."""
        cp1 = Claim_Process(id="p1", schemaset_id="ss1")
        cp2 = Claim_Process(id="p2", schemaset_id="ss2")
        cp1.processed_documents.append(
            Content_Process(process_id="p1", file_name="x.pdf")
        )
        assert len(cp2.processed_documents) == 0

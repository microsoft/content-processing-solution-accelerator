# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for steps/claim_processor.py (workflow exception models)."""

from __future__ import annotations

import pytest

from steps.claim_processor import (
    WorkflowExecutorFailedException,
    WorkflowOutputMissingException,
)

# ── WorkflowExecutorFailedException ─────────────────────────────────────────


class TestWorkflowExecutorFailedException:
    def test_from_dict_details(self):
        details = {
            "executor_id": "summarizing",
            "error_type": "RuntimeError",
            "message": "Chat client not configured",
        }
        exc = WorkflowExecutorFailedException(details)
        assert "summarizing" in str(exc)
        assert "RuntimeError" in str(exc)
        assert "Chat client not configured" in str(exc)
        assert exc.details is details

    def test_from_dict_with_traceback(self):
        details = {
            "executor_id": "gap_analysis",
            "error_type": "ValueError",
            "message": "bad input",
            "traceback": "Traceback (most recent call last):\n  File ...",
        }
        exc = WorkflowExecutorFailedException(details)
        assert "Traceback" in str(exc)

    def test_from_none_details(self):
        exc = WorkflowExecutorFailedException(None)
        assert "<unknown>" in str(exc)

    def test_from_pydantic_model(self):
        """Simulates a Pydantic v2 model with model_dump()."""
        from pydantic import BaseModel

        class FakeDetails(BaseModel):
            executor_id: str = "doc_proc"
            error_type: str = "IOError"
            message: str = "blob not found"

        details = FakeDetails()
        exc = WorkflowExecutorFailedException(details)
        assert "doc_proc" in str(exc)
        assert "IOError" in str(exc)

    def test_from_plain_object(self):
        """Fallback to vars() for arbitrary objects."""

        class Obj:
            def __init__(self):
                self.executor_id = "step1"
                self.error_type = "Err"
                self.message = "oops"

        exc = WorkflowExecutorFailedException(Obj())
        assert "step1" in str(exc)

    def test_from_non_serializable_object(self):
        """Objects without vars() fall back to repr()."""

        class Opaque:
            __slots__ = ()

            def __repr__(self):
                return "Opaque()"

        exc = WorkflowExecutorFailedException(Opaque())
        # Should not raise; message should contain fallback text
        assert "<unknown>" in str(exc) or "Opaque" in str(exc)

    def test_can_be_raised_and_caught(self):
        """Verify it is a proper Exception subclass usable in try/except."""
        details = {
            "executor_id": "rai_analysis",
            "error_type": "RuntimeError",
            "message": "Content is considered unsafe by RAI analysis.",
        }
        with pytest.raises(WorkflowExecutorFailedException, match="rai_analysis"):
            raise WorkflowExecutorFailedException(details)

    def test_details_attribute_preserved(self):
        """The original details object is preserved on the exception."""
        details = {"executor_id": "rai_analysis", "message": "unsafe"}
        exc = WorkflowExecutorFailedException(details)
        assert exc.details is details
        assert exc.details["executor_id"] == "rai_analysis"


# ── WorkflowOutputMissingException ──────────────────────────────────────────


class TestWorkflowOutputMissingException:
    def test_with_executor_id(self):
        exc = WorkflowOutputMissingException("gap_analysis")
        assert exc.source_executor_id == "gap_analysis"
        assert "gap_analysis" in str(exc)

    def test_with_none_executor_id(self):
        exc = WorkflowOutputMissingException(None)
        assert "<unknown>" in str(exc)

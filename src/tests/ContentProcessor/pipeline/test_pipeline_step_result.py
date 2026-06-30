# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.entities.pipeline_step_result (StepResult model)."""

from __future__ import annotations

import pytest

from libs.pipeline.entities.pipeline_step_result import StepResult

# ── TestStepResult ──────────────────────────────────────────────────────


class TestStepResult:
    """Construction, defaults, and persistence guard."""

    def test_defaults(self):
        result = StepResult()
        assert result.process_id is None
        assert result.step_name is None
        assert result.result is None
        assert result.elapsed is None

    def test_construction(self):
        result = StepResult(
            process_id="p1",
            step_name="extract",
            result={"key": "value"},
            elapsed="00:00:05.000",
        )
        assert result.process_id == "p1"
        assert result.step_name == "extract"
        assert result.result == {"key": "value"}

    def test_save_to_persistent_storage_requires_process_id(self):
        result = StepResult(step_name="extract")
        with pytest.raises(ValueError, match="Process ID is required"):
            result.save_to_persistent_storage("https://example.com", "container")

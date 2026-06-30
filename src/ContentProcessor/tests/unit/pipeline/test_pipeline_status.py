# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.entities.pipeline_status (step tracking and status)."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from libs.pipeline.entities.pipeline_status import PipelineStatus
from libs.pipeline.entities.pipeline_step_result import StepResult

# ── TestPipelineStatus ──────────────────────────────────────────────────


class TestPipelineStatus:
    """Step tracking, result management, and persistence guard."""

    def test_defaults(self):
        status = PipelineStatus()
        assert status.completed is False
        assert status.process_id is None
        assert status.steps == []
        assert status.remaining_steps == []
        assert status.completed_steps == []
        assert status.process_results == []

    def test_update_step(self):
        status = PipelineStatus(active_step="step1")
        status._move_to_next_step = Mock()
        status.update_step()
        assert status.last_updated_time is not None
        status._move_to_next_step.assert_called_once_with("step1")

    def test_add_step_result_appends_new(self):
        status = PipelineStatus()
        result = StepResult(step_name="step1")
        status.add_step_result(result)
        assert status.process_results == [result]

    def test_add_step_result_updates_existing(self):
        status = PipelineStatus()
        status.add_step_result(StepResult(step_name="step1"))
        updated = StepResult(step_name="step1", status="completed")
        status.add_step_result(updated)
        assert status.process_results == [updated]

    def test_get_step_result_found(self):
        status = PipelineStatus()
        result = StepResult(step_name="step1")
        status.process_results.append(result)
        assert status.get_step_result("step1") == result

    def test_get_step_result_not_found(self):
        status = PipelineStatus()
        assert status.get_step_result("missing") is None

    def test_get_previous_step_result(self):
        status = PipelineStatus(completed_steps=["step1"])
        result = StepResult(step_name="step1")
        status.process_results.append(result)
        assert status.get_previous_step_result("step2") == result

    def test_get_previous_step_result_no_completed(self):
        status = PipelineStatus(completed_steps=[])
        assert status.get_previous_step_result("step2") is None

    def test_save_to_persistent_storage_requires_process_id(self):
        status = PipelineStatus()
        with pytest.raises(
            ValueError, match="Process ID is required to save the result."
        ):
            status.save_to_persistent_storage("https://example.com", "container")

    def test_move_to_next_step(self):
        status = PipelineStatus(remaining_steps=["step1", "step2"])
        status._move_to_next_step("step1")
        assert status.completed_steps == ["step1"]
        assert status.remaining_steps == ["step2"]
        assert status.completed is False

    def test_move_to_next_step_completes_pipeline(self):
        status = PipelineStatus(remaining_steps=["step1", "step2"])
        status._move_to_next_step("step1")
        status._move_to_next_step("step2")
        assert status.completed_steps == ["step1", "step2"]
        assert status.remaining_steps == []
        assert status.completed is True

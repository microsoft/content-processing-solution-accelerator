"""Tests for pipeline_step_helper module."""

from libs.pipeline.pipeline_step_helper import get_next_step_name
from libs.pipeline.entities.pipeline_status import PipelineStatus


class TestGetNextStepName:
    """Tests for get_next_step_name function."""

    def test_get_next_step_name_returns_next_step(self):
        """Test that get_next_step_name returns the next step in the pipeline."""
        status = PipelineStatus(
            steps=["step1", "step2", "step3"],
            active_step="step1",
            remaining_steps=["step2", "step3"],
            completed_steps=[],
        )
        result = get_next_step_name(status)
        assert result == "step2"

    def test_get_next_step_name_returns_none_on_last_step(self):
        """Test that get_next_step_name returns None when on the last step."""
        status = PipelineStatus(
            steps=["step1", "step2", "step3"],
            active_step="step3",
            remaining_steps=[],
            completed_steps=["step1", "step2"],
        )
        result = get_next_step_name(status)
        assert result is None

    def test_get_next_step_name_middle_step(self):
        """Test get_next_step_name when in the middle of the pipeline."""
        status = PipelineStatus(
            steps=["extract", "validate", "transform", "complete"],
            active_step="validate",
            remaining_steps=["transform", "complete"],
            completed_steps=["extract"],
        )
        result = get_next_step_name(status)
        assert result == "transform"

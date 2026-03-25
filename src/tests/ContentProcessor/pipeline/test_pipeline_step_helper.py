# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.pipeline_step_helper (step navigation)."""

from __future__ import annotations

from libs.pipeline.entities.pipeline_status import PipelineStatus
from libs.pipeline.pipeline_step_helper import get_next_step_name

# ── TestGetNextStepName ─────────────────────────────────────────────────


class TestGetNextStepName:
    """Determine the next step in the pipeline sequence."""

    def test_returns_next_step(self):
        status = PipelineStatus(
            steps=["extract", "transform", "save"],
            active_step="extract",
        )
        assert get_next_step_name(status) == "transform"

    def test_returns_none_at_last_step(self):
        status = PipelineStatus(
            steps=["extract", "transform", "save"],
            active_step="save",
        )
        assert get_next_step_name(status) is None

    def test_middle_step(self):
        status = PipelineStatus(
            steps=["extract", "transform", "save"],
            active_step="transform",
        )
        assert get_next_step_name(status) == "save"

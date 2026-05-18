# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.entities.pipeline_data (DataPipeline envelope)."""

from __future__ import annotations

import pytest

from libs.pipeline.entities.pipeline_data import DataPipeline
from libs.pipeline.entities.pipeline_file import ArtifactType
from libs.pipeline.entities.pipeline_status import PipelineStatus
from libs.pipeline.entities.pipeline_step_result import StepResult

# ── TestDataPipeline ────────────────────────────────────────────────────


class TestDataPipeline:
    """Canonical pipeline payload construction and helper methods."""

    def _make_pipeline(self, **status_kwargs):
        status = PipelineStatus(
            process_id="proc-1",
            active_step="extract",
            steps=["extract", "transform", "save"],
            remaining_steps=["extract", "transform", "save"],
            **status_kwargs,
        )
        return DataPipeline(process_id="proc-1", PipelineStatus=status)

    def test_construction(self):
        dp = self._make_pipeline()
        assert dp.process_id == "proc-1"
        assert dp.pipeline_status.active_step == "extract"
        assert dp.files == []

    def test_get_object_valid_json(self):
        dp = self._make_pipeline()
        json_str = dp.model_dump_json(by_alias=True)
        restored = DataPipeline.get_object(json_str)
        assert restored.process_id == "proc-1"

    def test_get_object_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Failed to parse"):
            DataPipeline.get_object("{invalid json}")

    def test_add_file(self):
        dp = self._make_pipeline()
        file_detail = dp.add_file("document.pdf", ArtifactType.SourceContent)
        assert len(dp.files) == 1
        assert file_detail.name == "document.pdf"
        assert file_detail.artifact_type == ArtifactType.SourceContent
        assert file_detail.process_id == "proc-1"
        assert file_detail.mime_type == "application/pdf"

    def test_get_source_files(self):
        dp = self._make_pipeline()
        dp.add_file("doc.pdf", ArtifactType.SourceContent)
        dp.add_file("extracted.json", ArtifactType.ExtractedContent)
        sources = dp.get_source_files()
        assert len(sources) == 1
        assert sources[0].name == "doc.pdf"

    def test_get_step_result_delegates_to_status(self):
        dp = self._make_pipeline()
        dp.pipeline_status.add_step_result(
            StepResult(step_name="extract", result={"data": "ok"})
        )
        result = dp.get_step_result("extract")
        assert result is not None
        assert result.result == {"data": "ok"}

    def test_get_step_result_returns_none_for_missing(self):
        dp = self._make_pipeline()
        assert dp.get_step_result("nonexistent") is None

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for services.content_process_models (Pydantic models and enums)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from services.content_process_models import (
    ArtifactType,
    ContentProcessMessage,
    ContentProcessRecord,
    PipelineStatus,
    PipelineStep,
    ProcessFile,
)

# ── ArtifactType Enum ───────────────────────────────────────────────────


class TestArtifactType:
    def test_values(self):
        assert ArtifactType.SourceContent == "source_content"
        assert ArtifactType.ExtractedContent == "extracted_content"
        assert ArtifactType.Undefined == "undefined"

    def test_is_str_enum(self):
        assert isinstance(ArtifactType.SourceContent, str)


# ── PipelineStep Enum ───────────────────────────────────────────────────


class TestPipelineStep:
    def test_values(self):
        assert PipelineStep.Extract == "extract"
        assert PipelineStep.Mapping == "map"
        assert PipelineStep.Evaluating == "evaluate"
        assert PipelineStep.Save == "save"

    def test_is_str_enum(self):
        assert isinstance(PipelineStep.Extract, str)


# ── ProcessFile Model ───────────────────────────────────────────────────


class TestProcessFile:
    def test_construction(self):
        pf = ProcessFile(
            process_id="p1",
            id="f1",
            name="test.pdf",
            size=1024,
            mime_type="application/pdf",
            artifact_type=ArtifactType.SourceContent,
            processed_by="Workflow",
        )
        assert pf.process_id == "p1"
        assert pf.name == "test.pdf"
        assert pf.artifact_type == ArtifactType.SourceContent

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            ProcessFile(process_id="p1")  # type: ignore[call-arg]


# ── PipelineStatus Model ────────────────────────────────────────────────


class TestPipelineStatus:
    def test_construction_with_defaults(self):
        ps = PipelineStatus(
            process_id="p1",
            schema_id="s1",
            metadata_id="m1",
            creation_time=datetime.now(timezone.utc),
        )
        assert ps.completed is False
        assert ps.steps == []
        assert ps.remaining_steps == []
        assert ps.completed_steps == []

    def test_construction_with_steps(self):
        steps = ["extract", "map", "evaluate", "save"]
        ps = PipelineStatus(
            process_id="p1",
            schema_id="s1",
            metadata_id="m1",
            creation_time=datetime.now(timezone.utc),
            steps=steps,
            remaining_steps=steps.copy(),
        )
        assert len(ps.steps) == 4
        assert ps.remaining_steps == steps


# ── ContentProcessMessage Model ─────────────────────────────────────────


class TestContentProcessMessage:
    def test_construction(self):
        ps = PipelineStatus(
            process_id="p1",
            schema_id="s1",
            metadata_id="m1",
            creation_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        msg = ContentProcessMessage(process_id="p1", pipeline_status=ps)
        assert msg.process_id == "p1"
        assert msg.files == []

    def test_serialization_roundtrip(self):
        msg = ContentProcessMessage(
            process_id="p1",
            files=[
                ProcessFile(
                    process_id="p1",
                    id="f1",
                    name="test.pdf",
                    size=100,
                    mime_type="application/pdf",
                    artifact_type=ArtifactType.SourceContent,
                    processed_by="Workflow",
                )
            ],
            pipeline_status=PipelineStatus(
                process_id="p1",
                schema_id="s1",
                metadata_id="m1",
                creation_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                steps=["extract", "map"],
            ),
        )
        json_str = msg.model_dump_json()
        restored = ContentProcessMessage.model_validate_json(json_str)
        assert restored.process_id == "p1"
        assert len(restored.files) == 1
        assert restored.pipeline_status.schema_id == "s1"


# ── ContentProcessRecord Model ──────────────────────────────────────────


class TestContentProcessRecord:
    def test_construction_with_defaults(self):
        rec = ContentProcessRecord(id="r1")
        assert rec.id == "r1"
        assert rec.process_id == ""
        assert rec.status is None
        assert rec.entity_score == 0.0
        assert rec.schema_score == 0.0

    def test_extra_fields_allowed(self):
        rec = ContentProcessRecord(id="r1", unknown_field="extra")
        assert rec.model_extra["unknown_field"] == "extra"

    def test_to_cosmos_dict_includes_id(self):
        rec = ContentProcessRecord(
            id="r1",
            process_id="r1",
            status="processing",
            imported_time=datetime.now(timezone.utc),
        )
        d = rec.to_cosmos_dict()
        assert d["id"] == "r1"
        assert d["process_id"] == "r1"
        assert "status" in d

    def test_model_dump_includes_all_fields(self):
        rec = ContentProcessRecord(
            id="r1",
            process_id="r1",
            processed_file_name="test.pdf",
            status="Completed",
            schema_score=0.95,
            entity_score=0.88,
        )
        d = rec.model_dump()
        assert d["processed_file_name"] == "test.pdf"
        assert d["schema_score"] == 0.95
        assert d["entity_score"] == 0.88

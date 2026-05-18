# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.entities.pipeline_file (ArtifactType, FileDetailBase, PipelineLogEntry)."""

from __future__ import annotations

from libs.pipeline.entities.pipeline_file import (
    ArtifactType,
    FileDetailBase,
    PipelineLogEntry,
)

# ── TestArtifactType ────────────────────────────────────────────────────


class TestArtifactType:
    """String enum for pipeline artifact classification."""

    def test_values(self):
        assert ArtifactType.Undefined == "undefined"
        assert ArtifactType.SourceContent == "source_content"
        assert ArtifactType.ExtractedContent == "extracted_content"
        assert ArtifactType.SchemaMappedData == "schema_mapped_data"
        assert ArtifactType.SavedContent == "saved_content"

    def test_membership(self):
        assert "source_content" in [e.value for e in ArtifactType]

    def test_string_inheritance(self):
        assert isinstance(ArtifactType.Undefined, str)


# ── TestPipelineLogEntry ────────────────────────────────────────────────


class TestPipelineLogEntry:
    """Log entry with source and message fields."""

    def test_construction(self):
        entry = PipelineLogEntry(source="extract", message="started")
        assert entry.source == "extract"
        assert entry.message == "started"
        assert entry.datetime_offset is not None


# ── TestFileDetailBase ──────────────────────────────────────────────────


class TestFileDetailBase:
    """File metadata model with log-entry support."""

    def test_required_process_id(self):
        detail = FileDetailBase(process_id="proc-1")
        assert detail.process_id == "proc-1"
        assert detail.name is None
        assert detail.log_entries == []

    def test_add_log_entry_returns_self(self):
        detail = FileDetailBase(process_id="proc-1")
        result = detail.add_log_entry("step", "done")
        assert result is detail
        assert len(detail.log_entries) == 1
        assert detail.log_entries[0].source == "step"

    def test_full_construction(self):
        detail = FileDetailBase(
            id="abc",
            process_id="proc-1",
            name="file.pdf",
            size=1024,
            mime_type="application/pdf",
            artifact_type=ArtifactType.SourceContent,
            processed_by="extract",
        )
        assert detail.name == "file.pdf"
        assert detail.size == 1024
        assert detail.artifact_type == ArtifactType.SourceContent

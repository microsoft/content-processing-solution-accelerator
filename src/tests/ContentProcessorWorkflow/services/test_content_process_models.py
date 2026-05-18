# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for content_process_models.py"""

from datetime import datetime
from services.content_process_models import (
    ArtifactType,
    PipelineStep,
    ProcessFile,
    PipelineStatus,
    ContentProcessMessage,
    ContentProcessRecord,
)


class TestArtifactType:
    """Test ArtifactType enum"""

    def test_artifact_type_values(self):
        """Test all artifact type enum values"""
        assert ArtifactType.Undefined == "undefined"
        assert ArtifactType.ConvertedContent == "converted_content"
        assert ArtifactType.ExtractedContent == "extracted_content"
        assert ArtifactType.SchemaMappedData == "schema_mapped_data"
        assert ArtifactType.ScoreMergedData == "score_merged_data"
        assert ArtifactType.SourceContent == "source_content"
        assert ArtifactType.SavedContent == "saved_content"


class TestPipelineStep:
    """Test PipelineStep enum"""

    def test_pipeline_step_values(self):
        """Test all pipeline step enum values"""
        assert PipelineStep.Transform == "transform"
        assert PipelineStep.Extract == "extract"
        assert PipelineStep.Mapping == "map"
        assert PipelineStep.Evaluating == "evaluate"
        assert PipelineStep.Save == "save"


class TestProcessFile:
    """Test ProcessFile model"""

    def test_process_file_creation(self):
        """Test creating a ProcessFile instance"""
        file = ProcessFile(
            process_id="proc-123",
            id="file-456",
            name="test.pdf",
            size=1024,
            mime_type="application/pdf",
            artifact_type=ArtifactType.SourceContent,
            processed_by="system"
        )

        assert file.process_id == "proc-123"
        assert file.id == "file-456"
        assert file.name == "test.pdf"
        assert file.size == 1024
        assert file.mime_type == "application/pdf"
        assert file.artifact_type == ArtifactType.SourceContent
        assert file.processed_by == "system"

    def test_process_file_serialization(self):
        """Test ProcessFile JSON serialization"""
        file = ProcessFile(
            process_id="proc-123",
            id="file-456",
            name="test.pdf",
            size=1024,
            mime_type="application/pdf",
            artifact_type=ArtifactType.SourceContent,
            processed_by="system"
        )

        data = file.model_dump()
        assert data["process_id"] == "proc-123"
        assert data["artifact_type"] == "source_content"


class TestPipelineStatus:
    """Test PipelineStatus model"""

    def test_pipeline_status_creation(self):
        """Test creating a PipelineStatus instance"""
        now = datetime.now()
        status = PipelineStatus(
            process_id="proc-123",
            schema_id="schema-1",
            metadata_id="meta-1",
            completed=False,
            creation_time=now,
            last_updated_time=now,
            steps=["extract", "map"],
            remaining_steps=["evaluate"],
            completed_steps=["extract"]
        )

        assert status.process_id == "proc-123"
        assert status.schema_id == "schema-1"
        assert status.metadata_id == "meta-1"
        assert status.completed is False
        assert status.creation_time == now
        assert status.steps == ["extract", "map"]
        assert status.remaining_steps == ["evaluate"]
        assert status.completed_steps == ["extract"]

    def test_pipeline_status_defaults(self):
        """Test PipelineStatus default values"""
        now = datetime.now()
        status = PipelineStatus(
            process_id="proc-123",
            schema_id="schema-1",
            metadata_id="meta-1",
            creation_time=now
        )

        assert status.completed is False
        assert status.last_updated_time is None
        assert status.steps == []
        assert status.remaining_steps == []
        assert status.completed_steps == []


class TestContentProcessMessage:
    """Test ContentProcessMessage model"""

    def test_content_process_message_creation(self):
        """Test creating a ContentProcessMessage instance"""
        now = datetime.now()

        file = ProcessFile(
            process_id="proc-123",
            id="file-456",
            name="test.pdf",
            size=1024,
            mime_type="application/pdf",
            artifact_type=ArtifactType.SourceContent,
            processed_by="system"
        )

        status = PipelineStatus(
            process_id="proc-123",
            schema_id="schema-1",
            metadata_id="meta-1",
            creation_time=now
        )

        message = ContentProcessMessage(
            process_id="proc-123",
            files=[file],
            pipeline_status=status
        )

        assert message.process_id == "proc-123"
        assert len(message.files) == 1
        assert message.files[0].name == "test.pdf"
        assert message.pipeline_status.schema_id == "schema-1"

    def test_content_process_message_defaults(self):
        """Test ContentProcessMessage default values"""
        now = datetime.now()

        # pipeline_status requires certain fields, so we provide them
        status = PipelineStatus(
            process_id="proc-123",
            schema_id="schema-1",
            metadata_id="meta-1",
            creation_time=now
        )

        message = ContentProcessMessage(
            process_id="proc-123",
            pipeline_status=status
        )

        assert message.process_id == "proc-123"
        assert message.files == []
        assert message.pipeline_status.process_id == "proc-123"


class TestContentProcessRecord:
    """Test ContentProcessRecord model"""

    def test_content_process_record_creation(self):
        """Test creating a ContentProcessRecord instance"""
        now = datetime.now()

        record = ContentProcessRecord(
            id="rec-123",
            process_id="proc-123",
            processed_file_name="test.pdf",
            processed_file_mime_type="application/pdf",
            processed_time="2026-01-01T00:00:00Z",
            imported_time=now,
            status="completed",
            entity_score=0.95,
            schema_score=0.90,
            result={"key": "value"},
            confidence={"score": 0.9}
        )

        assert record.id == "rec-123"
        assert record.process_id == "proc-123"
        assert record.processed_file_name == "test.pdf"
        assert record.processed_file_mime_type == "application/pdf"
        assert record.status == "completed"
        assert record.entity_score == 0.95
        assert record.schema_score == 0.90
        assert record.result == {"key": "value"}

    def test_content_process_record_defaults(self):
        """Test ContentProcessRecord default values"""
        record = ContentProcessRecord(id="rec-123")

        assert record.process_id == ""
        assert record.processed_file_name is None
        assert record.processed_file_mime_type is None
        assert record.entity_score == 0.0
        assert record.schema_score == 0.0

    def test_to_cosmos_dict(self):
        """Test ContentProcessRecord.to_cosmos_dict method"""
        now = datetime.now()

        record = ContentProcessRecord(
            id="rec-123",
            process_id="proc-123",
            processed_file_name="test.pdf",
            imported_time=now,
            status="completed"
        )

        cosmos_dict = record.to_cosmos_dict()

        assert cosmos_dict["id"] == "rec-123"
        assert cosmos_dict["process_id"] == "proc-123"
        assert cosmos_dict["processed_file_name"] == "test.pdf"
        assert cosmos_dict["status"] == "completed"
        # imported_time should remain as datetime object, not converted to string
        assert isinstance(cosmos_dict.get("imported_time"), datetime)

    def test_extra_fields_allowed(self):
        """Test that ContentProcessRecord allows extra fields"""
        record = ContentProcessRecord(
            id="rec-123",
            process_id="proc-123",
            extra_field="extra_value"
        )

        # Extra fields should be preserved in model_dump
        data = record.model_dump()
        assert data.get("extra_field") == "extra_value"

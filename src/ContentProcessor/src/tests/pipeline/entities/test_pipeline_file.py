"""Tests for pipeline_file module"""

from unittest.mock import patch, MagicMock

from libs.pipeline.entities.pipeline_file import (
    ArtifactType,
    PipelineLogEntry,
    FileDetailBase,
    FileDetails,
)


class TestArtifactType:
    """Tests for ArtifactType enum."""

    def test_artifact_types(self):
        """Test all artifact types exist."""
        assert ArtifactType.Undefined == "undefined"
        assert ArtifactType.ConvertedContent == "converted_content"
        assert ArtifactType.ExtractedContent == "extracted_content"
        assert ArtifactType.SchemaMappedData == "schema_mapped_data"
        assert ArtifactType.ScoreMergedData == "score_merged_data"
        assert ArtifactType.SourceContent == "source_content"
        assert ArtifactType.SavedContent == "saved_content"


class TestPipelineLogEntry:
    """Tests for PipelineLogEntry class."""

    def test_log_entry_creation(self):
        """Test creating a log entry."""
        entry = PipelineLogEntry(source="test_source", message="test message")
        assert entry.source == "test_source"
        assert entry.message == "test message"
        assert entry.datetime_offset is not None


class TestFileDetailBase:
    """Tests for FileDetailBase class."""

    def test_file_detail_base_creation(self):
        """Test creating a FileDetailBase."""
        detail = FileDetailBase(
            id="file-123",
            process_id="proc-456",
            name="test.pdf",
            size=1024,
            mime_type="application/pdf",
            artifact_type=ArtifactType.SourceContent,
            processed_by="extract",
        )
        assert detail.id == "file-123"
        assert detail.process_id == "proc-456"
        assert detail.name == "test.pdf"
        assert detail.size == 1024
        assert detail.mime_type == "application/pdf"
        assert detail.artifact_type == ArtifactType.SourceContent
        assert detail.processed_by == "extract"
        assert detail.log_entries == []

    def test_add_log_entry(self):
        """Test adding a log entry."""
        detail = FileDetailBase(process_id="proc-123")
        result = detail.add_log_entry(source="extract", message="Processing started")

        assert result is detail  # Returns self for chaining
        assert len(detail.log_entries) == 1
        assert detail.log_entries[0].source == "extract"
        assert detail.log_entries[0].message == "Processing started"

    def test_add_multiple_log_entries(self):
        """Test adding multiple log entries."""
        detail = FileDetailBase(process_id="proc-123")
        detail.add_log_entry(source="step1", message="Step 1 done")
        detail.add_log_entry(source="step2", message="Step 2 done")

        assert len(detail.log_entries) == 2


class TestFileDetails:
    """Tests for FileDetails class."""

    @patch("libs.pipeline.entities.pipeline_file.StorageBlobHelper")
    def test_download_stream(self, mock_storage_helper):
        """Test download_stream method."""
        mock_instance = MagicMock()
        mock_instance.download_stream.return_value = b"file content"
        mock_storage_helper.return_value = mock_instance

        detail = FileDetails(process_id="proc-123", name="test.pdf")
        result = detail.download_stream(
            account_url="https://storage.blob.core.windows.net",
            container_name="container",
        )

        assert result == b"file content"
        mock_storage_helper.assert_called_once_with(
            account_url="https://storage.blob.core.windows.net",
            container_name="container",
        )
        mock_instance.download_stream.assert_called_once_with(
            container_name="proc-123",
            blob_name="test.pdf",
        )

    @patch("libs.pipeline.entities.pipeline_file.StorageBlobHelper")
    def test_download_file(self, mock_storage_helper):
        """Test download_file method."""
        mock_instance = MagicMock()
        mock_storage_helper.return_value = mock_instance

        detail = FileDetails(process_id="proc-123", name="test.pdf")
        detail.download_file(
            account_url="https://storage.blob.core.windows.net",
            container_name="container",
            file_path="/tmp/test.pdf",
        )

        mock_storage_helper.assert_called_once_with(
            account_url="https://storage.blob.core.windows.net",
            container_name="container",
        )
        mock_instance.download_file.assert_called_once_with(
            container_name="proc-123",
            blob_name="test.pdf",
            download_path="/tmp/test.pdf",
        )

    @patch("libs.pipeline.entities.pipeline_file.StorageBlobHelper")
    def test_upload_stream(self, mock_storage_helper):
        """Test upload_stream method."""
        mock_instance = MagicMock()
        mock_storage_helper.return_value = mock_instance

        detail = FileDetails(process_id="proc-123", name="output.bin")
        stream_data = b"binary content data"
        detail.upload_stream(
            account_url="https://storage.blob.core.windows.net",
            container_name="container",
            stream=stream_data,
        )

        mock_storage_helper.assert_called_once_with(
            account_url="https://storage.blob.core.windows.net",
            container_name="container",
        )
        mock_instance.upload_stream.assert_called_once_with(
            container_name="proc-123",
            blob_name="output.bin",
            stream=stream_data,
        )
        assert detail.size == len(stream_data)

    @patch("libs.pipeline.entities.pipeline_file.StorageBlobHelper")
    def test_upload_json_text(self, mock_storage_helper):
        """Test upload_json_text method."""
        mock_instance = MagicMock()
        mock_storage_helper.return_value = mock_instance

        detail = FileDetails(process_id="proc-123", name="data.json")
        json_text = '{"key": "value"}'
        detail.upload_json_text(
            account_url="https://storage.blob.core.windows.net",
            container_name="container",
            text=json_text,
        )

        mock_storage_helper.assert_called_once_with(
            account_url="https://storage.blob.core.windows.net",
            container_name="container",
        )
        mock_instance.upload_text.assert_called_once_with(
            container_name="proc-123",
            blob_name="data.json",
            text=json_text,
        )
        assert detail.size == len(json_text)
        assert detail.mime_type == "application/json"

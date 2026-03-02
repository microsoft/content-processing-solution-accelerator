"""Tests for ContentProcess model."""

from unittest.mock import patch, MagicMock
from libs.models.content_process import ContentProcess, Step_Outputs


class TestStepOutputs:
    """Tests for Step_Outputs class."""

    def test_step_outputs_creation(self):
        """Test creating Step_Outputs."""
        step = Step_Outputs(
            step_name="extract",
            processed_time="2026-01-01T00:00:00Z",
            step_result={"extracted": "data"}
        )
        assert step.step_name == "extract"
        assert step.step_result == {"extracted": "data"}


class TestContentProcess:
    """Tests for ContentProcess class."""

    def test_content_process_creation(self):
        """Test creating ContentProcess."""
        process = ContentProcess(
            process_id="test-123",
            status="processing"
        )
        assert process.process_id == "test-123"
        assert process.status == "processing"

    @patch("libs.models.content_process.CosmosMongDBHelper")
    def test_update_process_status_to_cosmos_existing(self, mock_cosmos):
        """Test updating existing process status in Cosmos."""
        mock_instance = MagicMock()
        mock_instance.find_document.return_value = [{"process_id": "test-123"}]
        mock_cosmos.return_value = mock_instance

        process = ContentProcess(process_id="test-123", status="completed")
        process.update_process_status_to_cosmos(
            "connection_string",
            "database",
            "collection"
        )

        mock_instance.find_document.assert_called_once()
        mock_instance.update_document.assert_called_once()

    @patch("libs.models.content_process.CosmosMongDBHelper")
    def test_update_process_status_to_cosmos_new(self, mock_cosmos):
        """Test inserting new process status in Cosmos."""
        mock_instance = MagicMock()
        mock_instance.find_document.return_value = []
        mock_cosmos.return_value = mock_instance

        process = ContentProcess(process_id="test-123", status="processing")
        process.update_process_status_to_cosmos(
            "connection_string",
            "database",
            "collection"
        )

        mock_instance.find_document.assert_called_once()
        mock_instance.insert_document.assert_called_once()

    @patch("libs.models.content_process.CosmosMongDBHelper")
    def test_update_status_to_cosmos_existing(self, mock_cosmos):
        """Test updating existing status in Cosmos."""
        mock_instance = MagicMock()
        mock_instance.find_document.return_value = [{"process_id": "test-123"}]
        mock_cosmos.return_value = mock_instance

        process = ContentProcess(process_id="test-123", status="completed")
        process.update_status_to_cosmos(
            "connection_string",
            "database",
            "collection"
        )

        mock_instance.find_document.assert_called_once()
        mock_instance.update_document.assert_called_once()

    @patch("libs.models.content_process.CosmosMongDBHelper")
    def test_update_status_to_cosmos_new(self, mock_cosmos):
        """Test inserting new status in Cosmos."""
        mock_instance = MagicMock()
        mock_instance.find_document.return_value = []
        mock_cosmos.return_value = mock_instance

        process = ContentProcess(process_id="test-123", status="processing")
        process.update_status_to_cosmos(
            "connection_string",
            "database",
            "collection"
        )

        mock_instance.find_document.assert_called_once()
        mock_instance.insert_document.assert_called_once()

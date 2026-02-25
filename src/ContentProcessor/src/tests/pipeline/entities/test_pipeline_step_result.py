"""Tests for pipeline_step_result module."""

import pytest
from unittest.mock import patch, MagicMock

from libs.pipeline.entities.pipeline_step_result import StepResult


class TestStepResult:
    """Tests for StepResult class."""

    def test_step_result_creation(self):
        """Test creating a StepResult object."""
        result = StepResult(
            process_id="test-123",
            step_name="extract",
            result={"extracted": "data"},
            elapsed="00:01:30",
        )
        assert result.process_id == "test-123"
        assert result.step_name == "extract"
        assert result.result == {"extracted": "data"}
        assert result.elapsed == "00:01:30"

    def test_step_result_default_values(self):
        """Test StepResult with default values."""
        result = StepResult()
        assert result.process_id is None
        assert result.step_name is None
        assert result.result is None
        assert result.elapsed is None

    def test_save_to_persistent_storage_no_process_id_raises(self):
        """Test that save_to_persistent_storage raises when process_id is None."""
        result = StepResult(step_name="extract", result={"data": "value"})

        with pytest.raises(ValueError, match="Process ID is required"):
            result.save_to_persistent_storage(
                account_url="https://storage.blob.core.windows.net",
                container_name="container",
            )

    @patch("libs.pipeline.entities.pipeline_step_result.StorageBlobHelper")
    def test_save_to_persistent_storage_success(self, mock_storage_helper):
        """Test successful save to persistent storage."""
        mock_instance = MagicMock()
        mock_storage_helper.return_value = mock_instance

        result = StepResult(
            process_id="test-123",
            step_name="extract",
            result={"extracted": "data"},
        )

        result.save_to_persistent_storage(
            account_url="https://storage.blob.core.windows.net",
            container_name="container",
        )

        mock_storage_helper.assert_called_once_with(
            account_url="https://storage.blob.core.windows.net",
            container_name="container",
        )
        mock_instance.upload_text.assert_called_once()

        # Verify the arguments passed to upload_text
        call_args = mock_instance.upload_text.call_args
        assert call_args.kwargs["container_name"] == "test-123"
        assert call_args.kwargs["blob_name"] == "extract-result.json"

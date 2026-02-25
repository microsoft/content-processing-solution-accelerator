import pytest
from unittest.mock import Mock, patch, MagicMock
from libs.pipeline.entities.pipeline_step_result import StepResult
from libs.pipeline.entities.pipeline_status import PipelineStatus
from libs.pipeline.entities.pipeline_data import DataPipeline
from libs.pipeline.entities.pipeline_file import ArtifactType


def test_update_step():
    pipeline_status = PipelineStatus(active_step="step1")
    pipeline_status._move_to_next_step = Mock()
    pipeline_status.update_step()
    assert pipeline_status.last_updated_time is not None
    pipeline_status._move_to_next_step.assert_called_once_with("step1")


def test_add_step_result():
    pipeline_status = PipelineStatus()
    step_result = StepResult(step_name="step1")
    pipeline_status.add_step_result(step_result)
    assert pipeline_status.process_results == [step_result]

    # Update existing step result
    updated_step_result = StepResult(step_name="step1", status="completed")
    pipeline_status.add_step_result(updated_step_result)
    assert pipeline_status.process_results == [updated_step_result]


def test_get_step_result():
    pipeline_status = PipelineStatus()
    step_result = StepResult(step_name="step1")
    pipeline_status.process_results.append(step_result)
    result = pipeline_status.get_step_result("step1")
    assert result == step_result

    result = pipeline_status.get_step_result("step2")
    assert result is None


def test_get_previous_step_result():
    pipeline_status = PipelineStatus(completed_steps=["step1"])
    step_result = StepResult(step_name="step1")
    pipeline_status.process_results.append(step_result)
    result = pipeline_status.get_previous_step_result("step2")
    assert result == step_result

    pipeline_status.completed_steps = []
    result = pipeline_status.get_previous_step_result("step2")
    assert result is None


def test_save_to_persistent_storage_no_process_id():
    pipeline_status = PipelineStatus()
    with pytest.raises(ValueError, match="Process ID is required to save the result."):
        pipeline_status.save_to_persistent_storage("https://example.com", "container")


def test_move_to_next_step():
    pipeline_status = PipelineStatus(remaining_steps=["step1", "step2"])
    pipeline_status._move_to_next_step("step1")
    assert pipeline_status.completed_steps == ["step1"]
    assert pipeline_status.remaining_steps == ["step2"]
    assert pipeline_status.completed is False

    pipeline_status._move_to_next_step("step2")
    assert pipeline_status.completed_steps == ["step1", "step2"]
    assert pipeline_status.remaining_steps == []
    assert pipeline_status.completed is True


# DataPipeline Tests
class TestDataPipeline:
    """Tests for DataPipeline class."""

    def test_get_object_valid_json(self):
        """Test parsing valid JSON string to DataPipeline."""
        json_str = '{"process_id": "test-123", "PipelineStatus": {"Completed": false}, "Files": []}'
        result = DataPipeline.get_object(json_str)
        assert result.process_id == "test-123"
        assert result.pipeline_status is not None

    def test_get_object_invalid_json(self):
        """Test that invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Failed to parse"):
            DataPipeline.get_object("invalid json {")

    def test_add_file(self):
        """Test adding a file to the pipeline."""
        pipeline_status = PipelineStatus(process_id="test-123", active_step="step1")
        data_pipeline = DataPipeline(process_id="test-123", pipeline_status=pipeline_status)

        file = data_pipeline.add_file("document.pdf", ArtifactType.SourceContent)

        assert len(data_pipeline.files) == 1
        assert file.name == "document.pdf"
        assert file.artifact_type == ArtifactType.SourceContent
        assert file.processed_by == "step1"

    def test_get_step_result(self):
        """Test getting step result from DataPipeline."""
        pipeline_status = PipelineStatus(process_id="test-123")
        step_result = StepResult(step_name="extract", result={"data": "value"})
        pipeline_status.process_results.append(step_result)

        data_pipeline = DataPipeline(process_id="test-123", pipeline_status=pipeline_status)

        result = data_pipeline.get_step_result("extract")
        assert result == step_result

    def test_get_previous_step_result(self):
        """Test getting previous step result from DataPipeline."""
        pipeline_status = PipelineStatus(process_id="test-123", completed_steps=["step1"])
        step_result = StepResult(step_name="step1", result={"data": "value"})
        pipeline_status.process_results.append(step_result)

        data_pipeline = DataPipeline(process_id="test-123", pipeline_status=pipeline_status)

        result = data_pipeline.get_previous_step_result("step2")
        assert result == step_result

    def test_get_source_files(self):
        """Test getting source files from pipeline."""
        pipeline_status = PipelineStatus(process_id="test-123", active_step="step1")
        data_pipeline = DataPipeline(process_id="test-123", pipeline_status=pipeline_status)

        # Add source file
        data_pipeline.add_file("source.pdf", ArtifactType.SourceContent)
        # Add extracted file
        data_pipeline.add_file("output.json", ArtifactType.ExtractedContent)

        source_files = data_pipeline.get_source_files()

        assert len(source_files) == 1
        assert source_files[0].name == "source.pdf"

    def test_save_to_database_not_implemented(self):
        """Test that save_to_database raises NotImplementedError."""
        pipeline_status = PipelineStatus(process_id="test-123")
        data_pipeline = DataPipeline(process_id="test-123", pipeline_status=pipeline_status)

        with pytest.raises(NotImplementedError):
            data_pipeline.save_to_database()

    @patch("libs.pipeline.entities.pipeline_data.StorageBlobHelper")
    def test_save_to_persistent_storage(self, mock_storage_helper):
        """Test saving pipeline to persistent storage."""
        mock_instance = MagicMock()
        mock_storage_helper.return_value = mock_instance

        pipeline_status = PipelineStatus(process_id="test-123")
        data_pipeline = DataPipeline(process_id="test-123", pipeline_status=pipeline_status)

        data_pipeline.save_to_persistent_storage("https://storage.blob.core.windows.net", "container")

        mock_storage_helper.assert_called_once()
        mock_instance.upload_text.assert_called_once()
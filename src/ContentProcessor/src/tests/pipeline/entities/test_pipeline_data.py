import pytest
from unittest.mock import Mock
from libs.pipeline.entities.pipeline_step_result import StepResult
from libs.pipeline.entities.pipeline_status import PipelineStatus


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


# def test_save_to_persistent_storage(mocker):
#     # Mock the StorageBlobHelper.upload_text method
#     mock_upload_text = mocker.patch(
#         "libs.azure_helper.storage_blob.StorageBlobHelper.upload_text"
#     )

#     # Mock the StorageBlobHelper constructor to return a mock instance
#     mock_storage_blob_helper = mocker.patch(
#         "libs.azure_helper.storage_blob.StorageBlobHelper", autospec=True
#     )
#     mock_storage_blob_helper_instance = mock_storage_blob_helper.return_value

#     # Mock the create_container method on the container_client
#     mock_container_client = Mock()
#     mock_container_client.create_container = Mock()
#     mock_storage_blob_helper_instance._invalidate_container = Mock()
#     mock_storage_blob_helper_instance._invalidate_container.return_value = (
#         mock_container_client
#     )

#     # Create a PipelineStatus object with a process_id
#     pipeline_status = PipelineStatus(process_id="123")

#     # Mock the update_step method using pytest-mock
#     mock_update_step = mocker.patch.object(
#         PipelineStatus, "update_step", return_value=None
#     )

#     # Mock the model_dump_json method using pytest-mock
#     mock_model_dump_json = mocker.patch.object(
#         PipelineStatus, "model_dump_json", return_value='{"key": "value"}'
#     )

#     account_url = "https://example.com"
#     container_name = "container"

#     # Call the save_to_persistent_storage method
#     pipeline_status.save_to_persistent_storage(account_url, container_name)

#     # Assert that update_step was called once
#     mock_update_step.assert_called_once()

#     # Assert that model_dump_json was called once
#     mock_model_dump_json.assert_called_once()

#     # Assert that upload_text was called with the correct arguments
#     mock_upload_text.assert_called_once_with(
#         container_name="123", blob_name="process-status.json", text='{"key": "value"}'
#     )


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

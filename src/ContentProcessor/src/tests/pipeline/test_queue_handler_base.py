import pytest
from unittest.mock import MagicMock
from azure.storage.queue import QueueClient
from libs.pipeline.entities.pipeline_message_context import MessageContext
from libs.pipeline.entities.pipeline_step_result import StepResult
from libs.pipeline.queue_handler_base import HandlerBase
from libs.application.application_context import AppContext


@pytest.fixture
def mock_queue_helper(mocker):
    # Mock the helper methods
    mocker.patch(
        "libs.pipeline.pipeline_queue_helper.create_queue_client_name",
        return_value="test-queue",
    )
    mocker.patch(
        "libs.pipeline.pipeline_queue_helper.create_dead_letter_queue_client_name",
        return_value="test-dlq",
    )
    mocker.patch(
        "libs.pipeline.pipeline_queue_helper.create_or_get_queue_client",
        return_value=MagicMock(spec=QueueClient),
    )
    return mocker


@pytest.fixture
def mock_app_context():
    # Create a mock AppContext instance
    mock_app_context = MagicMock(spec=AppContext)

    # Mock the necessary fields for AppContext
    mock_configuration = MagicMock()
    mock_configuration.app_storage_queue_url = "https://testqueueurl.com"
    mock_configuration.app_storage_blob_url = "https://testbloburl.com"
    mock_configuration.app_cps_processes = "TestProcess"

    mock_app_context.configuration = mock_configuration
    mock_app_context.credential = MagicMock()

    return mock_app_context


class MockHandler(HandlerBase):
    async def execute(self, context: MessageContext) -> StepResult:
        return StepResult(
            process_id="1234",
            step_name="extract",
            result={"result": "success", "data": {"key": "value"}},
        )


@pytest.mark.asyncio
async def test_execute_method():
    mock_handler = MockHandler(appContext=MagicMock(), step_name="extract")
    message_context = MagicMock(spec=MessageContext)

    # Execute the handler
    result = await mock_handler.execute(message_context)

    assert result.step_name == "extract"
    assert result.result == {"result": "success", "data": {"key": "value"}}


def test_show_queue_information(mock_queue_helper, mock_app_context):
    handler = MockHandler(appContext=mock_app_context, step_name="extract")

    # Mock the queue client properties
    mock_queue_client = MagicMock(spec=QueueClient)
    mock_queue_client.url = "https://testurl"
    mock_queue_client.get_queue_properties.return_value = MagicMock(
        approximate_message_count=5
    )
    handler.queue_client = mock_queue_client

    handler._show_queue_information()

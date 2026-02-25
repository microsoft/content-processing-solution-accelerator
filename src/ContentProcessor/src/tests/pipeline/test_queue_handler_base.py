import pytest
from unittest.mock import MagicMock, patch
from azure.storage.queue import QueueClient
from libs.pipeline.entities.pipeline_message_context import MessageContext
from libs.pipeline.entities.pipeline_step_result import StepResult
from libs.pipeline.entities.pipeline_data import DataPipeline
from libs.pipeline.entities.pipeline_file import ArtifactType, FileDetails
from libs.pipeline.queue_handler_base import HandlerBase
from libs.application.application_context import AppContext


@pytest.fixture
def mock_app_context():
    """Create a mock AppContext instance."""
    mock_context = MagicMock(spec=AppContext)

    mock_configuration = MagicMock()
    mock_configuration.app_storage_queue_url = "https://testqueueurl.com"
    mock_configuration.app_storage_blob_url = "https://testbloburl.com"
    mock_configuration.app_cps_processes = "TestProcess"
    mock_configuration.app_message_queue_interval = 1
    mock_configuration.app_message_queue_process_timeout = 30
    mock_configuration.app_message_queue_visibility_timeout = 30
    mock_configuration.app_cosmos_connstr = "AccountEndpoint=https://test.documents.azure.com:443/;AccountKey=test=="
    mock_configuration.app_cosmos_database = "testdb"
    mock_configuration.app_cosmos_container_process = "processes"

    mock_context.configuration = mock_configuration
    mock_context.credential = MagicMock()

    return mock_context


class MockHandler(HandlerBase):
    """Concrete implementation of HandlerBase for testing."""
    async def execute(self, context: MessageContext) -> StepResult:
        return StepResult(
            process_id="1234",
            step_name="extract",
            result={"result": "success", "data": {"key": "value"}},
        )


def test_show_queue_information(mock_app_context):
    """Test _show_queue_information method."""
    handler = MockHandler(appContext=mock_app_context, step_name="extract")

    mock_queue_client = MagicMock(spec=QueueClient)
    mock_queue_client.url = "https://testurl"
    mock_queue_client.get_queue_properties.return_value = MagicMock(
        approximate_message_count=5
    )
    handler.queue_client = mock_queue_client

    handler._show_queue_information()
    mock_queue_client.get_queue_properties.assert_called_once()


@patch("libs.pipeline.queue_handler_base.pipeline_queue_helper")
def test_initialize_handler(mock_queue_helper, mock_app_context):
    """Test the __initialize_handler method."""
    mock_queue_client = MagicMock(spec=QueueClient)
    mock_queue_client.url = "https://testurl"
    mock_queue_client.get_queue_properties.return_value = MagicMock(
        approximate_message_count=0
    )
    mock_queue_helper.create_queue_client_name.return_value = "test-queue"
    mock_queue_helper.create_dead_letter_queue_client_name.return_value = "test-dlq"
    mock_queue_helper.create_or_get_queue_client.return_value = mock_queue_client

    handler = MockHandler(appContext=mock_app_context, step_name="extract")
    handler._HandlerBase__initialize_handler(mock_app_context, "extract")

    assert handler.handler_name == "extract"
    assert handler.application_context == mock_app_context
    assert handler.queue_name == "test-queue"
    assert handler.dead_letter_queue_name == "test-dlq"
    assert handler.queue_client == mock_queue_client
    mock_queue_helper.create_queue_client_name.assert_called_with("extract")
    mock_queue_helper.create_dead_letter_queue_client_name.assert_called_with("extract")


@patch("libs.pipeline.queue_handler_base.asyncio.run")
@patch("libs.pipeline.queue_handler_base.pipeline_queue_helper")
def test_connect_queue(mock_queue_helper, mock_asyncio_run, mock_app_context):
    """Test the connect_queue method."""
    handler = MockHandler(appContext=mock_app_context, step_name="extract")
    
    handler.connect_queue(
        show_information=False,
        app_context=mock_app_context,
        step_name="extract"
    )
    mock_asyncio_run.assert_called_once()


def test_download_output_file_to_json_string(mock_app_context):
    """Test downloading output file and converting to JSON string."""
    handler = MockHandler(appContext=mock_app_context, step_name="extract")
    handler.application_context = mock_app_context

    mock_file = MagicMock(spec=FileDetails)
    mock_file.processed_by = "extract"
    mock_file.artifact_type = ArtifactType.ExtractedContent
    mock_file.download_stream.return_value = b'{"key": "value"}'

    mock_data_pipeline = MagicMock(spec=DataPipeline)
    mock_data_pipeline.files = [mock_file]

    handler._current_message_context = MagicMock(spec=MessageContext)
    handler._current_message_context.data_pipeline = mock_data_pipeline

    result = handler.download_output_file_to_json_string(
        processed_by="extract",
        artifact_type=ArtifactType.ExtractedContent
    )

    assert result == '{"key": "value"}'
    mock_file.download_stream.assert_called_once_with(
        "https://testbloburl.com",
        "TestProcess"
    )


def test_download_output_file_no_matching_file_raises_error(mock_app_context):
    """Test download raises IndexError when no matching file is found."""
    handler = MockHandler(appContext=mock_app_context, step_name="extract")
    handler.application_context = mock_app_context

    mock_file = MagicMock(spec=FileDetails)
    mock_file.processed_by = "other-step"
    mock_file.artifact_type = ArtifactType.SourceContent

    mock_data_pipeline = MagicMock(spec=DataPipeline)
    mock_data_pipeline.files = [mock_file]
    
    handler._current_message_context = MagicMock(spec=MessageContext)
    handler._current_message_context.data_pipeline = mock_data_pipeline

    with pytest.raises(IndexError):
        handler.download_output_file_to_json_string(
            processed_by="extract",
            artifact_type=ArtifactType.ExtractedContent
        )

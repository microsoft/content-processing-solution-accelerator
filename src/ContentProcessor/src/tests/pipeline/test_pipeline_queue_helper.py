from unittest.mock import Mock
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.queue import QueueClient, QueueMessage
from libs.pipeline.entities.pipeline_data import DataPipeline
from libs.pipeline.pipeline_queue_helper import (
    create_queue_client_name,
    create_dead_letter_queue_client_name,
    invalidate_queue,
    create_or_get_queue_client,
    delete_queue_message,
    move_to_dead_letter_queue,
    has_messages,
    pass_data_pipeline_to_next_step,
    _create_queue_client,
)


def test_create_queue_client_name():
    assert create_queue_client_name("test") == "content-pipeline-test-queue"


def test_create_dead_letter_queue_client_name():
    assert (
        create_dead_letter_queue_client_name("test")
        == "content-pipeline-test-queue-dead-letter-queue"
    )


def test_invalidate_queue(mocker):
    queue_client = Mock(spec=QueueClient)
    queue_client.get_queue_properties.side_effect = ResourceNotFoundError
    invalidate_queue(queue_client)
    queue_client.create_queue.assert_called_once()


def test_create_or_get_queue_client(mocker):
    mocker.patch("libs.pipeline.pipeline_queue_helper.QueueClient")
    queue_name = "test-queue"
    account_url = "https://example.com"
    credential = Mock(spec=DefaultAzureCredential)

    # Mock the QueueClient instance
    mock_queue_client = Mock(spec=QueueClient)
    mock_queue_client.get_queue_properties.side_effect = ResourceNotFoundError
    mock_queue_client.create_queue = Mock()  # Ensure create_queue is a mock method
    mocker.patch(
        "libs.pipeline.pipeline_queue_helper.invalidate_queue",
        return_value=mock_queue_client,
    )

    queue_client = create_or_get_queue_client(queue_name, account_url, credential)
    assert queue_client is not None


def test_delete_queue_message():
    queue_client = Mock(spec=QueueClient)
    message = Mock(spec=QueueMessage)
    delete_queue_message(message, queue_client)
    queue_client.delete_message.assert_called_once_with(message=message)


def test_move_to_dead_letter_queue():
    queue_client = Mock(spec=QueueClient)
    dead_letter_queue_client = Mock(spec=QueueClient)
    message = Mock(spec=QueueMessage)
    message.content = "test content"
    move_to_dead_letter_queue(message, dead_letter_queue_client, queue_client)
    dead_letter_queue_client.send_message.assert_called_once_with(
        content=message.content
    )
    queue_client.delete_message.assert_called_once_with(message=message)


def test_has_messages():
    queue_client = Mock(spec=QueueClient)
    queue_client.peek_messages.return_value = [Mock(spec=QueueMessage)]
    assert has_messages(queue_client) != []

    queue_client.peek_messages.return_value = []
    assert has_messages(queue_client) == []


def test_pass_data_pipeline_to_next_step(mocker):
    # Mock the get_next_step_name function
    mocker.patch(
        "libs.pipeline.pipeline_step_helper.get_next_step_name",
        return_value="next_step",
    )

    # Mock the _create_queue_client function
    mock_create_queue_client = mocker.patch(
        "libs.pipeline.pipeline_queue_helper._create_queue_client"
    )

    # Create a mock DataPipeline object with the necessary attributes
    data_pipeline = Mock(spec=DataPipeline)
    data_pipeline.pipeline_status = Mock()
    data_pipeline.pipeline_status.active_step = "current_step"
    data_pipeline.model_dump_json.return_value = '{"key": "value"}'

    account_url = "https://example.com"
    credential = Mock(spec=DefaultAzureCredential)

    pass_data_pipeline_to_next_step(data_pipeline, account_url, credential)

    mock_create_queue_client.assert_called_once_with(
        account_url, "content-pipeline-next_step-queue", credential
    )
    mock_create_queue_client().send_message.assert_called_once_with('{"key": "value"}')


def test_create_queue_client(mocker):
    mocker.patch("azure.storage.queue.QueueClient")
    account_url = "https://example.com"
    queue_name = "test-queue"
    credential = Mock(spec=DefaultAzureCredential)

    # Mock the QueueClient instance
    mock_queue_client = Mock(spec=QueueClient)
    mock_queue_client.get_queue_properties.return_value = None
    mocker.patch(
        "libs.pipeline.pipeline_queue_helper.invalidate_queue",
        return_value=mock_queue_client,
    )

    queue_client = _create_queue_client(account_url, queue_name, credential)
    assert queue_client is not None

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for StorageQueueHelper."""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ContentProcessorAPI")))

from app.libs.azure.storage_queue.helper import StorageQueueHelper  # noqa: E402
from pydantic import BaseModel  # noqa: E402


class QueueTestMessage(BaseModel):
    """Test message model for testing."""
    content: str
    id: int


@patch("app.libs.azure.storage_queue.helper.get_azure_credential")
@patch("app.libs.azure.storage_queue.helper.QueueClient")
def test_storage_queue_helper_init(mock_queue_client_class, mock_get_credential):
    """Test StorageQueueHelper initialization."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_queue_client = MagicMock()
    mock_queue_client_class.return_value = mock_queue_client
    mock_queue_client.get_queue_properties.return_value = MagicMock()

    helper = StorageQueueHelper(
        account_url="https://test.queue.core.windows.net",
        queue_name="test-queue"
    )

    assert helper.queue_client == mock_queue_client


@patch("app.libs.azure.storage_queue.helper.get_azure_credential")
@patch("app.libs.azure.storage_queue.helper.QueueClient")
def test_drop_message(mock_queue_client_class, mock_get_credential):
    """Test drop_message method."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_queue_client = MagicMock()
    mock_queue_client_class.return_value = mock_queue_client
    mock_queue_client.get_queue_properties.return_value = MagicMock()

    helper = StorageQueueHelper(
        account_url="https://test.queue.core.windows.net",
        queue_name="test-queue"
    )

    message = QueueTestMessage(content="test", id=1)
    helper.drop_message(message)

    mock_queue_client.send_message.assert_called_once()


@patch("app.libs.azure.storage_queue.helper.get_azure_credential")
@patch("app.libs.azure.storage_queue.helper.QueueClient")
def test_invalidate_queue_creates_when_not_found(mock_queue_client_class, mock_get_credential):
    """Test _invalidate_queue creates the queue when ResourceNotFoundError is raised."""
    from azure.core.exceptions import ResourceNotFoundError

    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_queue_client = MagicMock()
    mock_queue_client_class.return_value = mock_queue_client
    mock_queue_client.get_queue_properties.side_effect = ResourceNotFoundError("not found")

    StorageQueueHelper(
        account_url="https://test.queue.core.windows.net",
        queue_name="test-queue"
    )

    mock_queue_client.create_queue.assert_called_once()

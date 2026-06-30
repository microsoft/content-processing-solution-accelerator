# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for StorageQueueHelper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.queue import QueueClient

with patch("app.utils.azure_credential_utils.get_azure_credential") as mock_cred:
    mock_cred.return_value = MagicMock()
    from app.libs.azure.storage_queue.helper import StorageQueueHelper


@pytest.fixture
def mock_queue_client(mocker):
    return mocker.Mock(spec=QueueClient)


@pytest.fixture
def storage_queue_helper(mock_queue_client, mocker):
    mocker.patch(
        "app.libs.azure.storage_queue.helper.QueueClient",
        return_value=mock_queue_client,
    )
    mock_queue_client.get_queue_properties.return_value = {}
    return StorageQueueHelper(
        account_url="https://example.queue.core.windows.net",
        queue_name="test-queue",
    )


def test_drop_message(storage_queue_helper, mock_queue_client):
    message = MagicMock()
    message.model_dump_json.return_value = '{"key":"value"}'

    storage_queue_helper.drop_message(message)
    mock_queue_client.send_message.assert_called_once_with(content='{"key":"value"}')


def test_invalidate_queue_creates_when_not_found(
    storage_queue_helper, mock_queue_client
):
    mock_queue_client.get_queue_properties.side_effect = ResourceNotFoundError(
        "Queue not found"
    )
    storage_queue_helper._invalidate_queue(mock_queue_client)
    mock_queue_client.create_queue.assert_called_once()


def test_invalidate_queue_noop_when_exists(storage_queue_helper, mock_queue_client):
    mock_queue_client.get_queue_properties.return_value = {"name": "test-queue"}
    mock_queue_client.create_queue.reset_mock()

    storage_queue_helper._invalidate_queue(mock_queue_client)
    mock_queue_client.create_queue.assert_not_called()


def test_create_or_get_queue_client(storage_queue_helper, mock_queue_client, mocker):
    mock_credential = MagicMock()
    new_client = mocker.Mock(spec=QueueClient)
    new_client.get_queue_properties.return_value = {}

    mocker.patch(
        "app.libs.azure.storage_queue.helper.QueueClient",
        return_value=new_client,
    )

    result = storage_queue_helper.create_or_get_queue_client(
        queue_name="new-queue",
        accouont_url="https://example.queue.core.windows.net",
        credential=mock_credential,
    )
    assert result == new_client

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.pipeline.pipeline_queue_helper (queue CRUD operations)."""

from __future__ import annotations

from unittest.mock import Mock

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.queue import QueueClient, QueueMessage

from libs.pipeline.entities.pipeline_data import DataPipeline
from libs.pipeline.pipeline_queue_helper import (
    _create_queue_client,
    create_dead_letter_queue_client_name,
    create_or_get_queue_client,
    create_queue_client_name,
    delete_queue_message,
    has_messages,
    invalidate_queue,
    move_to_dead_letter_queue,
    pass_data_pipeline_to_next_step,
)

# ── TestQueueNaming ─────────────────────────────────────────────────────


class TestQueueNaming:
    """Queue name derivation from step name."""

    def test_create_queue_client_name(self):
        assert create_queue_client_name("test") == "content-pipeline-test-queue"

    def test_create_dead_letter_queue_client_name(self):
        assert (
            create_dead_letter_queue_client_name("test")
            == "content-pipeline-test-queue-dead-letter-queue"
        )


# ── TestQueueOperations ────────────────────────────────────────────────


class TestQueueOperations:
    """Queue client creation, message routing, and dead-letter handling."""

    def test_invalidate_queue(self):
        queue_client = Mock(spec=QueueClient)
        queue_client.get_queue_properties.side_effect = ResourceNotFoundError
        invalidate_queue(queue_client)
        queue_client.create_queue.assert_called_once()

    def test_create_or_get_queue_client(self, mocker):
        mocker.patch("libs.pipeline.pipeline_queue_helper.QueueClient")
        mock_queue_client = Mock(spec=QueueClient)
        mock_queue_client.get_queue_properties.side_effect = ResourceNotFoundError
        mock_queue_client.create_queue = Mock()
        mocker.patch(
            "libs.pipeline.pipeline_queue_helper.invalidate_queue",
            return_value=mock_queue_client,
        )
        credential = Mock(spec=DefaultAzureCredential)
        queue_client = create_or_get_queue_client(
            "test-queue", "https://example.com", credential
        )
        assert queue_client is not None

    def test_delete_queue_message(self):
        queue_client = Mock(spec=QueueClient)
        message = Mock(spec=QueueMessage)
        delete_queue_message(message, queue_client)
        queue_client.delete_message.assert_called_once_with(message=message)

    def test_move_to_dead_letter_queue(self):
        queue_client = Mock(spec=QueueClient)
        dead_letter = Mock(spec=QueueClient)
        message = Mock(spec=QueueMessage)
        message.content = "test content"
        move_to_dead_letter_queue(message, dead_letter, queue_client)
        dead_letter.send_message.assert_called_once_with(content=message.content)
        queue_client.delete_message.assert_called_once_with(message=message)

    def test_has_messages_returns_nonempty(self):
        queue_client = Mock(spec=QueueClient)
        queue_client.peek_messages.return_value = [Mock(spec=QueueMessage)]
        assert has_messages(queue_client) != []

    def test_has_messages_returns_empty(self):
        queue_client = Mock(spec=QueueClient)
        queue_client.peek_messages.return_value = []
        assert has_messages(queue_client) == []

    def test_pass_data_pipeline_to_next_step(self, mocker):
        mocker.patch(
            "libs.pipeline.pipeline_step_helper.get_next_step_name",
            return_value="next_step",
        )
        mock_create = mocker.patch(
            "libs.pipeline.pipeline_queue_helper._create_queue_client"
        )
        data_pipeline = Mock(spec=DataPipeline)
        data_pipeline.pipeline_status = Mock()
        data_pipeline.pipeline_status.active_step = "current_step"
        data_pipeline.model_dump_json.return_value = '{"key": "value"}'
        credential = Mock(spec=DefaultAzureCredential)

        pass_data_pipeline_to_next_step(
            data_pipeline, "https://example.com", credential
        )
        mock_create.assert_called_once_with(
            "https://example.com", "content-pipeline-next_step-queue", credential
        )
        mock_create().send_message.assert_called_once_with('{"key": "value"}')

    def test_create_queue_client(self, mocker):
        mocker.patch("azure.storage.queue.QueueClient")
        mock_queue_client = Mock(spec=QueueClient)
        mock_queue_client.get_queue_properties.return_value = None
        mocker.patch(
            "libs.pipeline.pipeline_queue_helper.invalidate_queue",
            return_value=mock_queue_client,
        )
        credential = Mock(spec=DefaultAzureCredential)
        queue_client = _create_queue_client(
            "https://example.com", "test-queue", credential
        )
        assert queue_client is not None

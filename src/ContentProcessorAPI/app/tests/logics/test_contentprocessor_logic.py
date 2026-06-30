# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for the ContentProcessor logic class."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.routers.logics.contentprocessor import ContentProcessor


@pytest.fixture
def mock_app_context():
    ctx = MagicMock()
    ctx.configuration.app_storage_blob_url = "https://blob.example.com"
    ctx.configuration.app_cps_processes = "processes"
    ctx.configuration.app_storage_queue_url = "https://queue.example.com"
    ctx.configuration.app_message_queue_extract = "extract-queue"
    return ctx


@patch("app.routers.logics.contentprocessor.StorageQueueHelper")
@patch("app.routers.logics.contentprocessor.StorageBlobHelper")
def test_save_file_to_blob(MockBlob, MockQueue, mock_app_context):
    mock_blob = MockBlob.return_value

    cp = ContentProcessor(app_context=mock_app_context)
    cp.save_file_to_blob("process-1", b"file bytes", "doc.pdf")

    mock_blob.upload_blob.assert_called_once_with("doc.pdf", b"file bytes", "process-1")


@patch("app.routers.logics.contentprocessor.StorageQueueHelper")
@patch("app.routers.logics.contentprocessor.StorageBlobHelper")
def test_enqueue_message(MockBlob, MockQueue, mock_app_context):
    mock_queue = MockQueue.return_value

    cp = ContentProcessor(app_context=mock_app_context)
    message = MagicMock()
    cp.enqueue_message(message)

    mock_queue.drop_message.assert_called_once_with(message)

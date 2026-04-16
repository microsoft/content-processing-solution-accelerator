# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for the ClaimBatchProcessor logic class."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.routers.models.contentprocessor.claim import ClaimItem, ClaimProcess
from app.routers.models.contentprocessor.model import ClaimProcessRequest


@pytest.fixture
def mock_app_context():
    ctx = MagicMock()
    ctx.configuration.app_storage_blob_url = "https://blob.example.com"
    ctx.configuration.app_cps_process_batch = "batches"
    ctx.configuration.app_storage_queue_url = "https://queue.example.com"
    return ctx


@patch("app.routers.logics.claimbatchpocessor.StorageQueueHelper")
@patch("app.routers.logics.claimbatchpocessor.StorageBlobHelper")
def test_create_claim_container(MockBlob, MockQueue, mock_app_context):
    mock_blob = MockBlob.return_value

    from app.routers.logics.claimbatchpocessor import ClaimBatchProcessor

    bp = ClaimBatchProcessor(app_context=mock_app_context)
    result = bp.create_claim_container("schemaset-1")

    assert isinstance(result, ClaimProcess)
    assert result.schema_collection_id == "schemaset-1"
    assert result.claim_id  # non-empty UUID
    mock_blob.upload_blob.assert_called_once()  # manifest saved


@patch("app.routers.logics.claimbatchpocessor.StorageQueueHelper")
@patch("app.routers.logics.claimbatchpocessor.StorageBlobHelper")
def test_get_claim_manifest(MockBlob, MockQueue, mock_app_context):
    manifest = {
        "claim_id": "c1",
        "schema_collection_id": "ss1",
        "items": [],
    }
    mock_blob_inst = MockBlob.return_value
    mock_blob_inst.download_blob.return_value = json.dumps(manifest).encode()

    from app.routers.logics.claimbatchpocessor import ClaimBatchProcessor

    bp = ClaimBatchProcessor(app_context=mock_app_context)
    result = bp.get_claim_manifest("c1")

    assert isinstance(result, ClaimProcess)
    assert result.claim_id == "c1"


@patch("app.routers.logics.claimbatchpocessor.StorageQueueHelper")
@patch("app.routers.logics.claimbatchpocessor.StorageBlobHelper")
def test_add_claim_item(MockBlob, MockQueue, mock_app_context):
    manifest = {
        "claim_id": "c1",
        "schema_collection_id": "ss1",
        "items": [],
    }
    mock_blob_inst = MockBlob.return_value
    mock_blob_inst.download_blob.return_value = json.dumps(manifest).encode()

    from app.routers.logics.claimbatchpocessor import ClaimBatchProcessor

    bp = ClaimBatchProcessor(app_context=mock_app_context)
    item = ClaimItem(
        claim_id="c1", schema_id="s1", metadata_id="m1", file_name="doc.pdf"
    )
    result = bp.add_claim_item("c1", item)

    assert len(result.items) == 1
    assert result.items[0].id is not None  # UUID assigned
    assert mock_blob_inst.upload_blob.call_count == 1  # manifest re-saved


@patch("app.routers.logics.claimbatchpocessor.StorageQueueHelper")
@patch("app.routers.logics.claimbatchpocessor.StorageBlobHelper")
def test_add_file_to_claim(MockBlob, MockQueue, mock_app_context):
    mock_blob_inst = MockBlob.return_value

    from app.routers.logics.claimbatchpocessor import ClaimBatchProcessor

    bp = ClaimBatchProcessor(app_context=mock_app_context)
    bp.add_file_to_claim("c1", "doc.pdf", b"content")

    mock_blob_inst.upload_blob.assert_called_once_with("doc.pdf", b"content", "c1")


@patch("app.routers.logics.claimbatchpocessor.StorageQueueHelper")
@patch("app.routers.logics.claimbatchpocessor.StorageBlobHelper")
def test_delete_claim_container(MockBlob, MockQueue, mock_app_context):
    mock_blob_inst = MockBlob.return_value

    from app.routers.logics.claimbatchpocessor import ClaimBatchProcessor

    bp = ClaimBatchProcessor(app_context=mock_app_context)
    bp.delete_claim_container("c1")

    mock_blob_inst.delete_folder.assert_called_once_with(folder_name="c1")


@patch("app.routers.logics.claimbatchpocessor.StorageQueueHelper")
@patch("app.routers.logics.claimbatchpocessor.StorageBlobHelper")
def test_enqueue_claim_request(MockBlob, MockQueue, mock_app_context):
    mock_queue_inst = MockQueue.return_value

    from app.routers.logics.claimbatchpocessor import ClaimBatchProcessor

    bp = ClaimBatchProcessor(app_context=mock_app_context)
    req = ClaimProcessRequest(claim_process_id="c1")
    bp.enqueue_claim_request_for_processing(req)

    mock_queue_inst.drop_message.assert_called_once_with(req)

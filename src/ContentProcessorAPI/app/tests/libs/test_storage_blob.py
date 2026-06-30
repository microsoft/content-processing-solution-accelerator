# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for StorageBlobHelper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobClient, BlobServiceClient, ContainerClient

# Ensure Azure credentials are mocked before any imports
with patch("app.utils.azure_credential_utils.get_azure_credential") as mock_cred:
    mock_cred.return_value = MagicMock()
    from app.libs.azure.storage_blob.helper import StorageBlobHelper


@pytest.fixture
def mock_blob_service_client(mocker):
    return mocker.Mock(spec=BlobServiceClient)


@pytest.fixture
def mock_container_client(mocker):
    return mocker.Mock(spec=ContainerClient)


@pytest.fixture
def mock_blob_client(mocker):
    return mocker.Mock(spec=BlobClient)


@pytest.fixture
def storage_blob_helper(
    mock_blob_service_client, mock_container_client, mock_blob_client, mocker
):
    mocker.patch(
        "app.libs.azure.storage_blob.helper.BlobServiceClient",
        return_value=mock_blob_service_client,
    )
    mock_blob_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.get_blob_client.return_value = mock_blob_client
    return StorageBlobHelper(
        account_url="https://example.com", container_name="test-container"
    )


def test_upload_blob(storage_blob_helper, mock_container_client, mock_blob_client):
    file_stream = b"dummy content"
    result = storage_blob_helper.upload_blob("test-blob", file_stream)
    mock_container_client.get_blob_client.assert_called_once_with("test-blob")
    mock_blob_client.upload_blob.assert_called_once_with(file_stream, overwrite=True)
    assert result == mock_blob_client.upload_blob.return_value


def test_download_blob(storage_blob_helper, mock_container_client, mock_blob_client):
    mock_blob_client.download_blob.return_value.readall.return_value = b"dummy content"
    result = storage_blob_helper.download_blob("test-blob")
    mock_container_client.get_blob_client.assert_called_once_with("test-blob")
    mock_blob_client.download_blob.assert_called_once()
    assert result == b"dummy content"


def test_download_blob_not_found(
    storage_blob_helper, mock_container_client, mock_blob_client
):
    mock_blob_client.get_blob_properties.side_effect = ResourceNotFoundError
    with pytest.raises(
        ValueError, match="Blob 'test-blob' not found in container 'test-container'."
    ):
        storage_blob_helper.download_blob("test-blob", "test-container")


def test_replace_blob(storage_blob_helper, mock_container_client, mock_blob_client):
    file_stream = b"dummy content"
    result = storage_blob_helper.replace_blob("test-blob", file_stream)
    mock_container_client.get_blob_client.assert_called_once_with("test-blob")
    mock_blob_client.upload_blob.assert_called_once_with(file_stream, overwrite=True)
    assert result == mock_blob_client.upload_blob.return_value


def test_delete_blob(storage_blob_helper, mock_container_client, mock_blob_client):
    result = storage_blob_helper.delete_blob("test-blob")
    mock_container_client.get_blob_client.assert_called_once_with("test-blob")
    mock_blob_client.delete_blob.assert_called_once()
    assert result == mock_blob_client.delete_blob.return_value


def test_download_blob_empty_raises(
    storage_blob_helper, mock_container_client, mock_blob_client
):
    props = MagicMock()
    props.size = 0
    mock_blob_client.get_blob_properties.return_value = props
    with pytest.raises(ValueError, match="is empty"):
        storage_blob_helper.download_blob("empty-blob")


def test_get_container_client_no_name_raises(mocker):
    mocker.patch(
        "app.libs.azure.storage_blob.helper.BlobServiceClient",
        return_value=mocker.Mock(spec=BlobServiceClient),
    )
    helper = StorageBlobHelper(account_url="https://example.com", container_name=None)
    with pytest.raises(ValueError, match="Container name must be provided"):
        helper._get_container_client(None)


def test_get_container_client_with_sub_container(
    storage_blob_helper, mock_blob_service_client
):
    storage_blob_helper._get_container_client("sub-folder")
    mock_blob_service_client.get_container_client.assert_called_with(
        "test-container/sub-folder"
    )


def test_get_container_client_default(storage_blob_helper, mock_blob_service_client):
    storage_blob_helper._get_container_client(None)
    mock_blob_service_client.get_container_client.assert_called_with("test-container")


def test_delete_blob_and_cleanup_removes_folder_when_empty(
    storage_blob_helper,
    mock_container_client,
    mock_blob_client,
    mock_blob_service_client,
):
    mock_container_client.delete_blob.return_value = None
    mock_container_client.list_blobs.return_value = []
    mock_blob_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.get_blob_client.return_value = mock_blob_client

    storage_blob_helper.delete_blob_and_cleanup("file.pdf", "subfolder")
    mock_container_client.delete_blob.assert_called_once_with("file.pdf")
    mock_blob_client.delete_blob.assert_called()


def test_delete_blob_and_cleanup_keeps_folder_when_not_empty(
    storage_blob_helper, mock_container_client, mock_blob_client
):
    mock_container_client.delete_blob.return_value = None
    remaining_blob = MagicMock()
    remaining_blob.name = "other.pdf"
    mock_container_client.list_blobs.return_value = [remaining_blob]

    storage_blob_helper.delete_blob_and_cleanup("file.pdf", "subfolder")
    # folder blob should NOT be deleted since files remain
    mock_blob_client.delete_blob.assert_not_called()


def test_delete_blob_and_cleanup_suppresses_delete_error(
    storage_blob_helper, mock_container_client, mock_blob_client
):
    mock_container_client.delete_blob.side_effect = Exception("Gone")
    mock_container_client.list_blobs.return_value = []
    # should not raise
    storage_blob_helper.delete_blob_and_cleanup("file.pdf", "subfolder")


def test_delete_folder(
    storage_blob_helper,
    mock_container_client,
    mock_blob_client,
    mock_blob_service_client,
):
    blob1 = MagicMock()
    blob1.name = "folder/a.pdf"
    blob2 = MagicMock()
    blob2.name = "folder/b.pdf"
    mock_container_client.list_blobs.side_effect = [
        [blob1, blob2],  # first call: blobs under folder/
        [MagicMock()],  # second call: remaining blobs in container
    ]
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_blob_service_client.get_container_client.return_value = mock_container_client

    storage_blob_helper.delete_folder("folder")
    assert mock_blob_client.delete_blob.call_count >= 2

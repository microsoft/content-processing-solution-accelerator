# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Unit tests for StorageBlobHelper."""

import os
import sys
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "ContentProcessorAPI")))

from app.libs.azure.storage_blob.helper import StorageBlobHelper  # noqa: E402


@patch("app.libs.azure.storage_blob.helper.get_azure_credential")
@patch("app.libs.azure.storage_blob.helper.BlobServiceClient")
def test_storage_blob_helper_init(mock_blob_service, mock_get_credential):
    """Test StorageBlobHelper initialization."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_service_client = MagicMock()
    mock_blob_service.return_value = mock_service_client
    mock_container_client = MagicMock()
    mock_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.exists.return_value = True

    helper = StorageBlobHelper("https://test.blob.core.windows.net", "test-container")

    assert helper.parent_container_name == "test-container"
    mock_blob_service.assert_called_once_with(
        account_url="https://test.blob.core.windows.net",
        credential=mock_credential
    )


@patch("app.libs.azure.storage_blob.helper.get_azure_credential")
@patch("app.libs.azure.storage_blob.helper.BlobServiceClient")
def test_upload_blob(mock_blob_service, mock_get_credential):
    """Test upload_blob method."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_service_client = MagicMock()
    mock_blob_service.return_value = mock_service_client
    mock_container_client = MagicMock()
    mock_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.exists.return_value = True
    mock_blob_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_result = MagicMock()
    mock_blob_client.upload_blob.return_value = mock_result

    helper = StorageBlobHelper("https://test.blob.core.windows.net", "test-container")

    file_stream = b"test data"
    result = helper.upload_blob("test.txt", file_stream)

    assert result == mock_result
    mock_blob_client.upload_blob.assert_called_once_with(file_stream, overwrite=True)


@patch("app.libs.azure.storage_blob.helper.get_azure_credential")
@patch("app.libs.azure.storage_blob.helper.BlobServiceClient")
def test_download_blob(mock_blob_service, mock_get_credential):
    """Test download_blob method."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_service_client = MagicMock()
    mock_blob_service.return_value = mock_service_client
    mock_container_client = MagicMock()
    mock_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.exists.return_value = True
    mock_blob_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_properties = MagicMock()
    mock_properties.size = 100
    mock_blob_client.get_blob_properties.return_value = mock_properties

    mock_download_stream = MagicMock()
    mock_download_stream.readall.return_value = b"test data"
    mock_blob_client.download_blob.return_value = mock_download_stream

    helper = StorageBlobHelper("https://test.blob.core.windows.net", "test-container")
    result = helper.download_blob("test.txt")

    assert result == b"test data"
    mock_blob_client.download_blob.assert_called_once()


@patch("app.libs.azure.storage_blob.helper.get_azure_credential")
@patch("app.libs.azure.storage_blob.helper.BlobServiceClient")
def test_replace_blob(mock_blob_service, mock_get_credential):
    """Test replace_blob method."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_service_client = MagicMock()
    mock_blob_service.return_value = mock_service_client
    mock_container_client = MagicMock()
    mock_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.exists.return_value = True
    mock_blob_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_result = MagicMock()
    mock_blob_client.upload_blob.return_value = mock_result

    helper = StorageBlobHelper("https://test.blob.core.windows.net", "test-container")

    file_stream = b"new data"
    result = helper.replace_blob("test.txt", file_stream)

    assert result == mock_result


@patch("app.libs.azure.storage_blob.helper.get_azure_credential")
@patch("app.libs.azure.storage_blob.helper.BlobServiceClient")
def test_delete_blob(mock_blob_service, mock_get_credential):
    """Test delete_blob method."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_service_client = MagicMock()
    mock_blob_service.return_value = mock_service_client
    mock_container_client = MagicMock()
    mock_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.exists.return_value = True
    mock_blob_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_result = MagicMock()
    mock_blob_client.delete_blob.return_value = mock_result

    helper = StorageBlobHelper("https://test.blob.core.windows.net", "test-container")
    result = helper.delete_blob("test.txt")

    assert result == mock_result
    mock_blob_client.delete_blob.assert_called_once()


@patch("app.libs.azure.storage_blob.helper.get_azure_credential")
@patch("app.libs.azure.storage_blob.helper.BlobServiceClient")
def test_download_blob_not_found(mock_blob_service, mock_get_credential):
    """Test download_blob raises error when blob not found."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_service_client = MagicMock()
    mock_blob_service.return_value = mock_service_client
    mock_container_client = MagicMock()
    mock_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.exists.return_value = True
    mock_blob_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client
    mock_blob_client.get_blob_properties.side_effect = Exception("Not found")

    helper = StorageBlobHelper("https://test.blob.core.windows.net", "test-container")

    with pytest.raises(ValueError, match="Blob 'test.txt' not found"):
        helper.download_blob("test.txt")


@patch("app.libs.azure.storage_blob.helper.get_azure_credential")
@patch("app.libs.azure.storage_blob.helper.BlobServiceClient")
def test_download_blob_empty(mock_blob_service, mock_get_credential):
    """Test download_blob raises error when blob is empty."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_service_client = MagicMock()
    mock_blob_service.return_value = mock_service_client
    mock_container_client = MagicMock()
    mock_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.exists.return_value = True
    mock_blob_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    mock_properties = MagicMock()
    mock_properties.size = 0
    mock_blob_client.get_blob_properties.return_value = mock_properties

    helper = StorageBlobHelper("https://test.blob.core.windows.net", "test-container")

    with pytest.raises(ValueError, match="Blob 'test.txt' is empty"):
        helper.download_blob("test.txt")


@patch("app.libs.azure.storage_blob.helper.get_azure_credential")
@patch("app.libs.azure.storage_blob.helper.BlobServiceClient")
def test_delete_folder(mock_blob_service, mock_get_credential):
    """Test delete_folder method."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_service_client = MagicMock()
    mock_blob_service.return_value = mock_service_client
    mock_container_client = MagicMock()
    mock_service_client.get_container_client.return_value = mock_container_client
    mock_container_client.exists.return_value = True

    mock_blob1 = MagicMock()
    mock_blob1.name = "folder/file1.txt"
    mock_blob2 = MagicMock()
    mock_blob2.name = "folder/file2.txt"
    mock_container_client.list_blobs.side_effect = [[mock_blob1, mock_blob2], []]

    mock_blob_client = MagicMock()
    mock_container_client.get_blob_client.return_value = mock_blob_client

    helper = StorageBlobHelper("https://test.blob.core.windows.net", "test-container")
    helper.delete_folder("folder")

    assert mock_blob_client.delete_blob.call_count >= 2


@patch("app.libs.azure.storage_blob.helper.get_azure_credential")
@patch("app.libs.azure.storage_blob.helper.BlobServiceClient")
def test_get_container_client_no_container_raises_error(mock_blob_service, mock_get_credential):
    """Test _get_container_client raises error when no container name provided."""
    mock_credential = MagicMock()
    mock_get_credential.return_value = mock_credential
    mock_service_client = MagicMock()
    mock_blob_service.return_value = mock_service_client

    helper = StorageBlobHelper("https://test.blob.core.windows.net", None)

    with pytest.raises(ValueError, match="Container name must be provided"):
        helper._get_container_client()

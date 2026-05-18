# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Tests for libs.azure_helper.storage_blob (Azure Blob Storage helper)."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

with patch("libs.utils.azure_credential_utils.get_azure_credential") as _mock_cred:
    _mock_cred.return_value = MagicMock()
    from libs.azure_helper.storage_blob import StorageBlobHelper


@pytest.fixture
def mock_blob_service_client(mocker):
    return mocker.patch("libs.azure_helper.storage_blob.BlobServiceClient")


@pytest.fixture
def storage_blob_helper(mock_blob_service_client):
    return StorageBlobHelper(
        account_url="https://testaccount.blob.core.windows.net",
        container_name="testcontainer",
    )


def _blob_client(mock_blob_service_client, mocker):
    """Return a fresh mock blob client wired into the service client chain."""
    mock = mocker.MagicMock()
    mock_blob_service_client.return_value.get_container_client.return_value.get_blob_client.return_value = mock
    return mock


# ── TestStorageBlobHelper ───────────────────────────────────────────────


class TestStorageBlobHelper:
    """Upload, download, and container operations via StorageBlobHelper."""

    def test_get_container_client_with_parent_container(
        self, storage_blob_helper, mock_blob_service_client, mocker
    ):
        mock_container_client = mocker.MagicMock()
        mock_blob_service_client.return_value.get_container_client.return_value = (
            mock_container_client
        )
        mock_blob_service_client.return_value.get_container_client.reset_mock()
        container_client = storage_blob_helper._get_container_client()
        assert container_client == mock_container_client
        mock_blob_service_client.return_value.get_container_client.assert_called_once_with(
            "testcontainer"
        )

    def test_get_container_client_without_container_name(self, storage_blob_helper):
        storage_blob_helper.parent_container_name = None
        with pytest.raises(
            ValueError,
            match="Container name must be provided either during initialization or as a function argument.",
        ):
            storage_blob_helper._get_container_client()

    def test_upload_file(self, storage_blob_helper, mock_blob_service_client, mocker):
        mock = _blob_client(mock_blob_service_client, mocker)
        mocker.patch("builtins.open", mocker.mock_open(read_data="test content"))
        storage_blob_helper.upload_file("testcontainer", "testblob", "testfile.txt")
        mock.upload_blob.assert_called_once()

    def test_upload_stream(self, storage_blob_helper, mock_blob_service_client, mocker):
        mock = _blob_client(mock_blob_service_client, mocker)
        stream = BytesIO(b"test data")
        storage_blob_helper.upload_stream("testcontainer", "testblob", stream)
        mock.upload_blob.assert_called_once_with(stream, overwrite=True)

    def test_upload_text(self, storage_blob_helper, mock_blob_service_client, mocker):
        mock = _blob_client(mock_blob_service_client, mocker)
        storage_blob_helper.upload_text("testcontainer", "testblob", "test text")
        mock.upload_blob.assert_called_once_with("test text", overwrite=True)

    def test_download_file(self, storage_blob_helper, mock_blob_service_client, mocker):
        mock = _blob_client(mock_blob_service_client, mocker)
        mock.download_blob.return_value.readall.return_value = b"test data"
        mock_open = mocker.patch("builtins.open", mocker.mock_open())
        storage_blob_helper.download_file("testcontainer", "testblob", "downloaded.txt")
        mock_open.return_value.write.assert_called_once_with(b"test data")

    def test_download_stream(
        self, storage_blob_helper, mock_blob_service_client, mocker
    ):
        mock = _blob_client(mock_blob_service_client, mocker)
        mock.download_blob.return_value.readall.return_value = b"test data"
        stream = storage_blob_helper.download_stream("testcontainer", "testblob")
        assert stream == b"test data"

    def test_download_text(self, storage_blob_helper, mock_blob_service_client, mocker):
        mock = _blob_client(mock_blob_service_client, mocker)
        mock.download_blob.return_value.content_as_text.return_value = "test text"
        text = storage_blob_helper.download_text("testcontainer", "testblob")
        assert text == "test text"

    def test_delete_blob(self, storage_blob_helper, mock_blob_service_client, mocker):
        mock = _blob_client(mock_blob_service_client, mocker)
        storage_blob_helper.delete_blob("testcontainer", "testblob")
        mock.delete_blob.assert_called_once()

    def test_upload_blob_with_str(
        self, storage_blob_helper, mock_blob_service_client, mocker
    ):
        mock = _blob_client(mock_blob_service_client, mocker)
        storage_blob_helper.upload_blob("testcontainer", "testblob", "test string data")
        mock.upload_blob.assert_called_once_with("test string data", overwrite=True)

    def test_upload_blob_with_bytes(
        self, storage_blob_helper, mock_blob_service_client, mocker
    ):
        mock = _blob_client(mock_blob_service_client, mocker)
        storage_blob_helper.upload_blob("testcontainer", "testblob", b"test bytes data")
        mock.upload_blob.assert_called_once_with(b"test bytes data", overwrite=True)

    def test_upload_blob_with_io(
        self, storage_blob_helper, mock_blob_service_client, mocker
    ):
        mock = _blob_client(mock_blob_service_client, mocker)
        stream = BytesIO(b"test stream data")
        storage_blob_helper.upload_blob("testcontainer", "testblob", stream)
        mock.upload_blob.assert_called_once_with(stream, overwrite=True)

    def test_upload_blob_with_unsupported_type(self, storage_blob_helper):
        with pytest.raises(ValueError, match="Unsupported data type for upload"):
            storage_blob_helper.upload_blob("testcontainer", "testblob", 12345)

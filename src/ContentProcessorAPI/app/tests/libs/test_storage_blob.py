import pytest
from azure.storage.blob import BlobServiceClient, ContainerClient, BlobClient
from azure.core.exceptions import ResourceNotFoundError
from unittest.mock import MagicMock, patch

# Ensure Azure credentials are mocked before any imports
with patch("helpers.azure_credential_utils.get_azure_credential") as mock_cred:
    mock_cred.return_value = MagicMock()
    from app.libs.storage_blob.helper import StorageBlobHelper


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
        "app.libs.storage_blob.helper.BlobServiceClient",
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
    # mock_blob_client.get_blob_properties.assert_called_once()
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


# def test_delete_blob_and_cleanup(
#     storage_blob_helper, mock_container_client, mock_blob_client, mocker
# ):
#     # Mock the list_blobs method to return an object with _page_iterator attribute
#     mock_page_iterator = mocker.Mock()
#     # mock_page_iterator._page_iterator = True
#     mock_page_iterator.__iter__.return_value = iter([])
#     mock_container_client.list_blobs.return_value = mock_page_iterator

#     storage_blob_helper.delete_blob_and_cleanup("test-blob")

#     mock_container_client.get_blob_client.assert_called_with("test-blob")
#     mock_blob_client.delete_blob.assert_called_once()
#     mock_container_client.list_blobs.assert_called_once()
#     assert mock_page_iterator.__iter__.called

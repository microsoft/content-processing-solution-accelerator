# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Helper for Azure Blob Storage operations (upload, download, delete).

Used by the content-processing router to persist uploaded documents and
retrieve them during downstream pipeline stages.
"""

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from app.utils.azure_credential_utils import get_azure_credential


class StorageBlobHelper:
    """Convenience wrapper around BlobServiceClient for a single container tree.

    Responsibilities:
        1. Authenticate via DefaultAzureCredential.
        2. Auto-create the root container if it does not exist.
        3. Expose upload, download, replace, and delete operations.

    Attributes:
        blob_service_client: Authenticated BlobServiceClient.
        parent_container_name: Optional root container/virtual-folder prefix.
    """

    def __init__(self, account_url, container_name=None):
        """Create a helper bound to *account_url*.

        Args:
            account_url: Azure Blob Storage account URL.
            container_name: Optional default container (may include a virtual-folder
                path such as ``"mycontainer/subfolder"``).
        """
        credential = get_azure_credential()
        self.blob_service_client = BlobServiceClient(
            account_url=account_url, credential=credential
        )
        self.parent_container_name = container_name
        if container_name:
            container_name = container_name.split("/")[0]
            self._invalidate_container(container_name)

    def _get_container_client(self, container_name=None):
        """Build a ContainerClient, optionally scoped to a sub-folder.

        Args:
            container_name: Sub-container or virtual folder name.  When omitted,
                uses ``parent_container_name``.

        Raises:
            ValueError: If no container name is available from either argument
                or the instance default.
        """
        if container_name:
            full_container_name = (
                f"{self.parent_container_name}/{container_name}"
                if self.parent_container_name
                else container_name
            )
        elif self.parent_container_name is not None and container_name is None:
            full_container_name = self.parent_container_name
        else:
            raise ValueError(
                "Container name must be provided either during initialization or as a function argument."
            )

        container_client = self.blob_service_client.get_container_client(
            full_container_name
        )

        return container_client

    def _invalidate_container(self, container_name: str):
        """Create the container if it does not already exist."""
        container_client = self.blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            container_client.create_container()

    def upload_blob(self, blob_name, file_stream, container_name=None):
        """Upload *file_stream* as *blob_name*, overwriting if it exists."""
        container_client = self._get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        result = blob_client.upload_blob(file_stream, overwrite=True)
        return result

    def download_blob(self, blob_name, container_name=None):
        """Download a blob's full contents as bytes.

        Raises:
            ValueError: If the blob does not exist or is empty.
        """
        container_client = self._get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)

        try:
            blob_client.get_blob_properties()
        except Exception as e:
            raise ValueError(
                f"Blob '{blob_name}' not found in container '{container_name}'."
            ) from e

        blob_properties = blob_client.get_blob_properties()
        if blob_properties.size == 0:
            raise ValueError(f"Blob '{blob_name}' is empty.")

        download_stream = blob_client.download_blob()
        return download_stream.readall()

    def replace_blob(self, blob_name, file_stream, container_name=None):
        """Overwrite an existing blob (delegates to upload_blob)."""
        return self.upload_blob(blob_name, file_stream, container_name)

    def delete_blob(self, blob_name, container_name=None):
        """Delete a single blob."""
        container_client = self._get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        result = blob_client.delete_blob()
        return result

    def delete_blob_and_cleanup(self, blob_name, container_name=None):
        """Delete a blob and remove the virtual folder if it becomes empty."""
        container_client = self._get_container_client(container_name)
        try:
            container_client.delete_blob(blob_name)
        except ResourceNotFoundError:
            # Blob already absent; continue with folder cleanup checks.
            pass

        blobs = container_client.list_blobs()
        files = [blob for blob in blobs]
        if not files:
            container_client = self._get_container_client()
            blob_client = container_client.get_blob_client(container_name)
            blob_client.delete_blob()

    def delete_folder(self, folder_name, container_name=None):
        """Delete all blobs under *folder_name* and the virtual folder marker."""
        container_client = self._get_container_client(container_name)

        blobs_to_delete = container_client.list_blobs(
            name_starts_with=folder_name + "/"
        )

        for blob in blobs_to_delete:
            blob_client = container_client.get_blob_client(blob.name)
            blob_client.delete_blob()

        blobs_to_delete = container_client.list_blobs()
        files = [blob for blob in blobs_to_delete]
        if files:
            container_client = self._get_container_client()
            blob_client = container_client.get_blob_client(folder_name)
            blob_client.delete_blob()

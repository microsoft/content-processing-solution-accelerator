# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from helpers.azure_credential_utils import get_azure_credential
from azure.storage.blob import BlobServiceClient


class StorageBlobHelper:
    def __init__(self, account_url, container_name=None):
        credential = get_azure_credential()
        self.blob_service_client = BlobServiceClient(
            account_url=account_url, credential=credential
        )
        self.parent_container_name = container_name
        if container_name:
            # if containeer_name is provided, "container_name/folder name" is used, get container_name
            # and create container if not exists
            container_name = container_name.split("/")[0]
            self._invalidate_container(container_name)

    def _get_container_client(self, container_name=None):
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
        container_client = self.blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            container_client.create_container()

    def upload_blob(self, blob_name, file_stream, container_name=None):
        container_client = self._get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        result = blob_client.upload_blob(file_stream, overwrite=True)
        return result

    def download_blob(self, blob_name, container_name=None):
        container_client = self._get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)

        # Check if the blob exists
        try:
            blob_client.get_blob_properties()
        except Exception as e:
            raise ValueError(
                f"Blob '{blob_name}' not found in container '{container_name}'."
            ) from e

        # Check if the blob is empty
        blob_properties = blob_client.get_blob_properties()
        if blob_properties.size == 0:
            raise ValueError(f"Blob '{blob_name}' is empty.")

        download_stream = blob_client.download_blob()
        return download_stream.readall()

    def replace_blob(self, blob_name, file_stream, container_name=None):
        return self.upload_blob(blob_name, file_stream, container_name)

    def delete_blob(self, blob_name, container_name=None):
        container_client = self._get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        result = blob_client.delete_blob()
        return result

    def delete_blob_and_cleanup(self, blob_name, container_name=None):
        container_client = self._get_container_client(container_name)
        container_client.delete_blob(blob_name)

        # Check if the container is empty
        blobs = container_client.list_blobs()
        if not blobs._page_iterator:
            # Get Parent Container
            container_client = self._get_container_client()
            # Delete the (virtual) folder in the Container
            blob_client = container_client.get_blob_client(container_name)
            blob_client.delete_blob()

    def delete_folder(self, folder_name, container_name=None):
        container_client = self._get_container_client(container_name)

        # List all blobs inside the folder
        blobs_to_delete = container_client.list_blobs(name_starts_with=folder_name + "/")

        # Delete each blob
        for blob in blobs_to_delete:
            blob_client = container_client.get_blob_client(blob.name)
            blob_client.delete_blob()

        blobs_to_delete = container_client.list_blobs()
        if not blobs_to_delete:

            # Get Parent Container
            container_client = self._get_container_client()

            # Delete the (virtual) folder in the Container
            blob_client = container_client.get_blob_client(folder_name)
            blob_client.delete_blob()
